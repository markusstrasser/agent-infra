#!/usr/bin/env python3
"""Summarize pre-compaction nuance signals from compact-log.jsonl.

This is not a causal post-compaction loss measurement; it is a lightweight
baseline check over the signals already captured by the PreCompact hook.
"""

import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from config import METRICS_FILE, log_metric

from common.paths import COMPACT_LOG as COMPACTIONS
from common.io import load_jsonl


def parse_ts(ts: str) -> datetime:
    if not ts:
        return datetime.min
    if ts.endswith("Z"):
        try:
            return datetime.fromisoformat(ts[:-1] + "+00:00").replace(tzinfo=None)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(ts).replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return datetime.min


def extract_project(cwd: str) -> str:
    if "/Projects/" not in cwd:
        return "unknown"
    return cwd.split("/Projects/")[-1].split("/")[0] or "unknown"


def main() -> None:
    days = 30
    project_filter = None

    args = sys.argv[1:]
    if "--days" in args:
        idx = args.index("--days")
        if idx + 1 < len(args):
            days = int(args[idx + 1])
    if "--project" in args:
        idx = args.index("--project")
        if idx + 1 < len(args):
            project_filter = args[idx + 1]

    cutoff = datetime.now() - timedelta(days=days)
    events = [
        e for e in load_jsonl(COMPACTIONS)
        if parse_ts(e.get("ts", "")) > cutoff
    ]
    if project_filter:
        events = [e for e in events if extract_project(e.get("cwd", "")) == project_filter]

    if not events:
        print(f"No compactions found in the last {days} days.")
        return

    session_counts = Counter(e.get("session", "?") for e in events)
    multi_compaction_sessions = sum(1 for _, count in session_counts.items() if count > 1)

    densities = []
    zero_provenance_events = 0
    low_nuance_events = 0
    memory_written_events = 0
    by_project: dict[str, list[float]] = defaultdict(list)

    for event in events:
        words = int(event.get("assistant_word_count", 0) or 0)
        hedging = int(event.get("hedging_count", 0) or 0)
        qualifiers = int(event.get("qualifier_count", 0) or 0)
        provenance = int(event.get("provenance_tag_count", 0) or 0)
        project = extract_project(event.get("cwd", ""))

        if event.get("clir", {}).get("memory_written"):
            memory_written_events += 1

        if words <= 0:
            continue

        density = (hedging + qualifiers + provenance) / words
        densities.append(density)
        by_project[project].append(density)

        if provenance == 0:
            zero_provenance_events += 1
        if words >= 500 and density < 0.005:
            low_nuance_events += 1

    hedging_data_available = bool(densities)
    avg_density = round(sum(densities) / len(densities), 4) if densities else None
    median_density = round(statistics.median(densities), 4) if densities else None
    by_project_avg = {
        project: round(sum(vals) / len(vals), 4)
        for project, vals in by_project.items()
        if vals
    }

    print(f"{'=' * 55}")
    print(f"  Compaction Nuance — last {days} days")
    print(f"{'=' * 55}")
    print()
    print(f"  Events:                {len(events)}")
    print(f"  Sessions:              {len(session_counts)}")
    print(f"  Multi-compaction:      {multi_compaction_sessions}")
    print(f"  Memory recently written:{memory_written_events:>4} events")
    if hedging_data_available:
        print(f"  Avg nuance density:    {avg_density:.4f}")
        print(f"  Median density:        {median_density:.4f}")
        print(f"  Zero provenance:       {zero_provenance_events}")
        print(f"  Low nuance events:     {low_nuance_events}")
    else:
        print("  No nuance density data available.")
    if by_project_avg:
        print()
        print("  By project:")
        for project, density in sorted(by_project_avg.items()):
            print(f"    {project:<18} {density:.4f}")
    print()

    log_metric(
        "compaction_nuance",
        days=days,
        events=len(events),
        sessions=len(session_counts),
        multi_compaction_sessions=multi_compaction_sessions,
        hedging_data_available=hedging_data_available,
        avg_density=avg_density,
        median_density=median_density,
        zero_provenance_events=zero_provenance_events,
        low_nuance_events=low_nuance_events,
        memory_written_events=memory_written_events,
        by_project=by_project_avg,
    )
    print(f"  Logged to {METRICS_FILE}")


if __name__ == "__main__":
    main()
