#!/usr/bin/env python3
"""Analyze overview trigger logs across projects.

Reads .claude/overview-trigger.log from each opted-in project.
Outputs trigger frequency, scope breakdown, and threshold recommendations.

Usage:
    uv run python3 scripts/overview-trigger-analysis.py [--days N]
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# Projects to scan (add more as they opt in)
PROJECTS = [
    Path.home() / "Projects" / "intel",
    Path.home() / "Projects" / "selve",
    Path.home() / "Projects" / "genomics",
    Path.home() / "Projects" / "meta",
]

def load_logs(days: int = 14) -> list[dict]:
    """Load trigger log entries from all projects within the given window."""
    cutoff = datetime.now() - timedelta(days=days)
    entries = []

    for project_dir in PROJECTS:
        log_path = project_dir / ".claude" / "overview-trigger.log"
        if not log_path.is_file():
            continue
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry["ts"])
                    if ts >= cutoff:
                        entries.append(entry)
                except (json.JSONDecodeError, KeyError):
                    continue

    return sorted(entries, key=lambda e: e["ts"])


def analyze(entries: list[dict]) -> None:
    """Print analysis of trigger patterns."""
    if not entries:
        print("No trigger log entries found.")
        print(f"Checked: {', '.join(p.name for p in PROJECTS)}")
        return

    # Per-project stats
    by_project: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_project[e.get("project", "unknown")].append(e)

    print(f"=== Overview Trigger Analysis ({len(entries)} entries) ===\n")

    for project, proj_entries in sorted(by_project.items()):
        print(f"## {project} ({len(proj_entries)} triggers)")

        # Scope frequency
        scope_counts: dict[str, int] = defaultdict(int)
        scope_loc: dict[str, list[int]] = defaultdict(list)
        trigger_reasons: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for e in proj_entries:
            for scope in e.get("scopes_triggered", []):
                scope_counts[scope] += 1
                loc = e.get("lines_changed", {}).get(scope, 0)
                scope_loc[scope].append(loc)
                for reason in e.get("trigger_reasons", {}).get(scope, []):
                    kind = reason.split(":")[0]
                    trigger_reasons[scope][kind] += 1

        for scope in sorted(scope_counts.keys()):
            count = scope_counts[scope]
            locs = scope_loc[scope]
            avg_loc = sum(locs) / len(locs) if locs else 0
            reasons = trigger_reasons[scope]
            reason_str = ", ".join(f"{k}={v}" for k, v in sorted(reasons.items()))
            print(f"  {scope}: {count}x (avg LOC: {avg_loc:.0f}, reasons: {reason_str})")

        # LOC distribution for threshold tuning
        all_locs = []
        for e in proj_entries:
            for scope, loc in e.get("lines_changed", {}).items():
                if loc > 0:
                    all_locs.append(loc)

        if all_locs:
            all_locs.sort()
            p25 = all_locs[len(all_locs) // 4] if len(all_locs) >= 4 else all_locs[0]
            p50 = all_locs[len(all_locs) // 2]
            p75 = all_locs[3 * len(all_locs) // 4] if len(all_locs) >= 4 else all_locs[-1]
            print(f"  LOC distribution: p25={p25}, p50={p50}, p75={p75}")

        # Trigger frequency
        if len(proj_entries) >= 2:
            first = datetime.fromisoformat(proj_entries[0]["ts"])
            last = datetime.fromisoformat(proj_entries[-1]["ts"])
            days_span = max((last - first).days, 1)
            rate = len(proj_entries) / days_span
            print(f"  Rate: {rate:.1f} triggers/day over {days_span} days")

        print()

    # Threshold recommendations
    print("## Threshold Recommendations")
    print("(Based on observed LOC distributions — tune to minimize FP+FN)")
    for project, proj_entries in sorted(by_project.items()):
        all_locs = []
        for e in proj_entries:
            for loc in e.get("lines_changed", {}).values():
                if loc > 0:
                    all_locs.append(loc)
        if all_locs:
            # Recommend p25 as threshold (catches 75% of changes)
            all_locs.sort()
            suggested = all_locs[len(all_locs) // 4] if len(all_locs) >= 4 else all_locs[0]
            print(f"  {project}: suggested LOC threshold = {suggested} (current triggers at p25)")
        else:
            print(f"  {project}: insufficient data")


def main():
    days = 14
    if len(sys.argv) > 1 and sys.argv[1] == "--days":
        days = int(sys.argv[2])

    entries = load_logs(days)
    analyze(entries)


if __name__ == "__main__":
    main()
