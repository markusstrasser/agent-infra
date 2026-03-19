#!/usr/bin/env python3
"""Analyze subagent usage from ~/.claude/subagent-log.jsonl.

Reads start/stop events, produces distribution, project breakdown,
output size stats, daily trend, and waste indicators.

Usage: uv run python3 scripts/subagent-analysis.py [--days N] [--verbose]
"""

import json
import sys
import os
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path

from common.paths import CLAUDE_DIR
LOGFILE = CLAUDE_DIR / "subagent-log.jsonl"


def parse_args():
    days = 7
    verbose = False
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--days" and i < len(sys.argv) - 1:
            days = int(sys.argv[i + 1])
        elif arg == "--verbose":
            verbose = True
    return days, verbose


def load_events(days: int) -> list[dict]:
    if not LOGFILE.exists():
        print(f"No log file at {LOGFILE}")
        sys.exit(1)

    cutoff = datetime.now() - timedelta(days=days)
    events = []
    for line in LOGFILE.read_text().splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        ts_str = entry.get("ts", "")
        try:
            # Parse ISO format with timezone
            ts = datetime.fromisoformat(ts_str.replace("+0000", "+00:00").replace("Z", "+00:00"))
            ts = ts.replace(tzinfo=None)  # Strip tz for comparison
        except (ValueError, AttributeError):
            continue

        if ts >= cutoff:
            entry["_ts"] = ts
            events.append(entry)

    return events


def analyze(events: list[dict], verbose: bool):
    starts = [e for e in events if e.get("event") == "subagent_start"]
    stops = [e for e in events if e.get("event") == "subagent_stop"]
    researcher_checks = [e for e in events if e.get("event") == "researcher_stop_check"]

    if not starts and not stops:
        print("No subagent events found in the time range.")
        return

    # --- Distribution ---
    type_counts = Counter(e.get("agent_type", "unknown") for e in starts)
    total = len(starts)

    print(f"## Subagent Distribution ({total} spawns)\n")
    print("| Agent Type | Count | Share |")
    print("|------------|-------|-------|")
    for atype, count in type_counts.most_common():
        pct = count / total * 100 if total else 0
        print(f"| {atype} | {count} | {pct:.1f}% |")
    print()

    # --- Per-project breakdown ---
    project_counts = Counter(e.get("project", "unknown") for e in starts)
    print(f"## Per-Project Breakdown\n")
    print("| Project | Count | Share |")
    print("|---------|-------|-------|")
    for proj, count in project_counts.most_common():
        pct = count / total * 100 if total else 0
        print(f"| {proj} | {count} | {pct:.1f}% |")
    print()

    # --- Output size distribution ---
    sizes = [e.get("output_len", 0) for e in stops if e.get("output_len")]
    if sizes:
        print(f"## Output Size Distribution ({len(sizes)} completions)\n")
        buckets = {"<200 chars": 0, "200-2K": 0, "2K-10K": 0, "10K-50K": 0, ">50K": 0}
        for s in sizes:
            if s < 200:
                buckets["<200 chars"] += 1
            elif s < 2000:
                buckets["200-2K"] += 1
            elif s < 10000:
                buckets["2K-10K"] += 1
            elif s < 50000:
                buckets["10K-50K"] += 1
            else:
                buckets[">50K"] += 1

        print("| Size Bucket | Count | Share |")
        print("|-------------|-------|-------|")
        for bucket, count in buckets.items():
            pct = count / len(sizes) * 100 if sizes else 0
            print(f"| {bucket} | {count} | {pct:.1f}% |")

        avg_size = sum(sizes) / len(sizes)
        median_size = sorted(sizes)[len(sizes) // 2]
        print(f"\nMean: {avg_size:.0f} chars ({avg_size / 1024:.1f} KB)")
        print(f"Median: {median_size} chars ({median_size / 1024:.1f} KB)")
        print()

    # --- Start/stop pairing ---
    start_ids = {e.get("agent_id") for e in starts if e.get("agent_id")}
    stop_ids = {e.get("agent_id") for e in stops if e.get("agent_id")}
    paired = start_ids & stop_ids
    unpaired_starts = start_ids - stop_ids
    if start_ids:
        pair_rate = len(paired) / len(start_ids) * 100
        print(f"## Event Pairing\n")
        print(f"- Starts: {len(start_ids)}, Stops: {len(stop_ids)}")
        print(f"- Paired: {len(paired)} ({pair_rate:.1f}%)")
        if unpaired_starts:
            print(f"- Unpaired starts: {len(unpaired_starts)} (may still be running)")
        print()

    # --- Daily trend ---
    daily = defaultdict(int)
    for e in starts:
        day = e["_ts"].strftime("%Y-%m-%d")
        daily[day] += 1

    if daily:
        print("## Daily Trend\n")
        print("| Date | Spawns |")
        print("|------|--------|")
        for day in sorted(daily.keys()):
            print(f"| {day} | {daily[day]} |")
        print()

    # --- Waste indicators ---
    waste_patterns = {
        "suggestion_brainstorm": 0,
        "single_tool_likely": 0,
        "gp_as_explore": 0,
        "tiny_output": 0,
    }

    # Check starts for description-based patterns
    # (We don't have descriptions in logs — would need pretool gate logs)
    # Check stops for tiny output from non-code agents
    for e in stops:
        if e.get("output_len", 0) < 200 and e.get("agent_type") not in ("Explore", "Plan", "statusline-setup"):
            waste_patterns["tiny_output"] += 1

    # general-purpose share
    gp_count = type_counts.get("general-purpose", 0)
    gp_share = gp_count / total * 100 if total else 0

    print("## Waste Indicators\n")
    print(f"- general-purpose share: {gp_share:.1f}% ({gp_count}/{total}) — target: <40%")
    print(f"- Tiny output (<200 chars): {waste_patterns['tiny_output']} — possible overhead-exceeds-work")
    print()

    # --- Researcher citation checks ---
    if researcher_checks:
        would_block = sum(1 for e in researcher_checks if e.get("would_block"))
        rate = would_block / len(researcher_checks) * 100
        print(f"## Researcher Citation Checks ({len(researcher_checks)} stops)\n")
        print(f"- Would-block triggers: {would_block} ({rate:.1f}%) — target: ≤10% before promotion to blocking")
        print()

    # --- Researcher-specific metrics ---
    researcher_starts = [e for e in starts if e.get("agent_type") == "researcher"]
    researcher_stops = [e for e in stops if e.get("agent_type") == "researcher"]

    if researcher_starts:
        r_start_ids = {e.get("agent_id") for e in researcher_starts if e.get("agent_id")}
        r_stop_ids = {e.get("agent_id") for e in researcher_stops if e.get("agent_id")}
        r_paired = r_start_ids & r_stop_ids
        r_unpaired = r_start_ids - r_stop_ids

        print(f"## Researcher Metrics ({len(researcher_starts)} spawns)\n")

        # Completion rate
        if r_start_ids:
            comp_rate = len(r_paired) / len(r_start_ids) * 100
            print(f"- Completion rate: {comp_rate:.1f}% ({len(r_paired)}/{len(r_start_ids)}) — target: >75%")
            print(f"- Unpaired (silent failures): {len(r_unpaired)}")

        # Weekly completion trend
        weekly_starts = defaultdict(int)
        weekly_stops = defaultdict(int)
        for e in researcher_starts:
            week = e["_ts"].strftime("%Y-W%W")
            weekly_starts[week] += 1
        for e in researcher_stops:
            if e.get("agent_id") in r_start_ids:
                week = e["_ts"].strftime("%Y-W%W")
                weekly_stops[week] += 1

        all_weeks = sorted(set(weekly_starts) | set(weekly_stops))
        if len(all_weeks) > 1:
            print("\n### Weekly Completion Trend\n")
            print("| Week | Starts | Completions | Rate |")
            print("|------|--------|-------------|------|")
            for week in all_weeks:
                s = weekly_starts[week]
                c = weekly_stops[week]
                rate = c / s * 100 if s else 0
                print(f"| {week} | {s} | {c} | {rate:.0f}% |")

        # Output quality tiers
        r_sizes = [e.get("output_len", 0) for e in researcher_stops if e.get("output_len")]
        if r_sizes:
            tiers = {"empty (<200)": 0, "stub (200-2K)": 0, "partial (2K-5K)": 0, "full (>5K)": 0}
            for s in r_sizes:
                if s < 200:
                    tiers["empty (<200)"] += 1
                elif s < 2000:
                    tiers["stub (200-2K)"] += 1
                elif s < 5000:
                    tiers["partial (2K-5K)"] += 1
                else:
                    tiers["full (>5K)"] += 1

            print("\n### Output Quality Tiers\n")
            print("| Tier | Count | Share |")
            print("|------|-------|-------|")
            for tier, count in tiers.items():
                pct = count / len(r_sizes) * 100
                print(f"| {tier} | {count} | {pct:.1f}% |")

            mean_size = sum(r_sizes) / len(r_sizes)
            print(f"\nMean researcher output: {mean_size:.0f} chars — target: >6000")

        # Provenance compliance from researcher_stop_check events
        if researcher_checks:
            substantial = [e for e in researcher_checks if e.get("output_len", 0) >= 2000]
            if substantial:
                compliant = sum(1 for e in substantial if e.get("has_tags"))
                comp_rate = compliant / len(substantial) * 100
                print(f"\n### Provenance Compliance (output ≥2K chars)\n")
                print(f"- Compliant: {compliant}/{len(substantial)} ({comp_rate:.1f}%) — target: >80%")

        # Duration distribution (pair starts and stops by agent_id)
        start_times = {e.get("agent_id"): e["_ts"] for e in researcher_starts if e.get("agent_id")}
        durations = []
        for e in researcher_stops:
            aid = e.get("agent_id")
            if aid and aid in start_times:
                dur = (e["_ts"] - start_times[aid]).total_seconds()
                if 0 < dur < 3600:  # Sanity: 0-60 minutes
                    durations.append(dur)

        if durations:
            durations.sort()
            mean_dur = sum(durations) / len(durations)
            median_dur = durations[len(durations) // 2]
            print(f"\n### Duration Distribution ({len(durations)} paired runs)\n")
            print(f"- Mean: {mean_dur:.0f}s ({mean_dur / 60:.1f} min)")
            print(f"- Median: {median_dur:.0f}s ({median_dur / 60:.1f} min)")
            print(f"- Range: {durations[0]:.0f}s — {durations[-1]:.0f}s")

        # Cost estimate
        cost_per_run = 2.0
        total_cost = len(researcher_starts) * cost_per_run
        waste = len(r_unpaired) * cost_per_run
        print(f"\n### Cost Estimate\n")
        print(f"- Total researcher cost: ${total_cost:.0f} ({len(researcher_starts)} × ${cost_per_run})")
        print(f"- Waste (unpaired): ${waste:.0f} ({len(r_unpaired)} × ${cost_per_run})")
        if total_cost:
            print(f"- Waste ratio: {waste / total_cost * 100:.0f}%")

        print()

    # --- Verbose: per-type output sizes ---
    if verbose and stops:
        type_sizes = defaultdict(list)
        for e in stops:
            type_sizes[e.get("agent_type", "unknown")].append(e.get("output_len", 0))

        print("## Per-Type Output Sizes (verbose)\n")
        print("| Agent Type | Count | Mean | Median | Max |")
        print("|------------|-------|------|--------|-----|")
        for atype, szs in sorted(type_sizes.items()):
            szs_sorted = sorted(szs)
            mean = sum(szs) / len(szs)
            median = szs_sorted[len(szs) // 2]
            mx = max(szs)
            print(f"| {atype} | {len(szs)} | {mean:.0f} | {median} | {mx} |")
        print()


def main():
    days, verbose = parse_args()
    print(f"# Subagent Analysis — last {days} days\n")
    events = load_events(days)
    analyze(events, verbose)


if __name__ == "__main__":
    main()
