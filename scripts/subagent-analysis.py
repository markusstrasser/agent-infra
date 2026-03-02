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

LOGFILE = Path.home() / ".claude" / "subagent-log.jsonl"


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
