#!/usr/bin/env python3
"""Compaction Nuance Drift Tracker — monitor epistemic quality across compaction events.

Reads ~/.claude/compact-log.jsonl for sessions with hedging/qualifier density
fields (added by extended precompact-log.sh hook) and tracks density trends.

LIMITATION: No PostCompact hook exists in Claude Code. This measures
hedging density drift over time, NOT causal before/after compaction loss.
Topic changes alone can shift density — this is drift detection, not
attribution. See plan Phase 1.4 for full context.

Usage: uv run python3 scripts/compaction-analysis.py [--days N] [--verbose]
"""

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from config import log_metric

COMPACT_LOG = Path.home() / ".claude" / "compact-log.jsonl"


def load_compact_log() -> list[dict]:
    """Load compact-log.jsonl entries."""
    import json

    if not COMPACT_LOG.exists():
        return []
    entries = []
    with open(COMPACT_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    return entries


def parse_ts(ts: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return datetime.min


def compute_density(entry: dict) -> float | None:
    """Compute hedging/qualifier density for a compaction entry.

    Returns (hedging_count + qualifier_count + provenance_tag_count) / word_count,
    or None if the required fields aren't present.
    """
    hedging = entry.get("hedging_count")
    qualifiers = entry.get("qualifier_count")
    provenance = entry.get("provenance_tag_count")
    words = entry.get("assistant_word_count")

    if hedging is None or words is None or words == 0:
        return None

    total = (hedging or 0) + (qualifiers or 0) + (provenance or 0)
    return total / words


def main():
    days = 30
    verbose = False

    args = sys.argv[1:]
    if "--days" in args:
        idx = args.index("--days")
        if idx + 1 < len(args):
            days = int(args[idx + 1])
    if "--verbose" in args:
        verbose = True

    cutoff = datetime.now() - timedelta(days=days)
    entries = load_compact_log()
    recent = [e for e in entries if parse_ts(e.get("ts", "")) > cutoff]

    if not recent:
        print(f"No compaction events in the last {days} days.")
        return

    # Group by session
    by_session: dict[str, list[dict]] = defaultdict(list)
    for entry in recent:
        sid = entry.get("session", "")
        if sid and sid != "test-123":
            by_session[sid].append(entry)

    # Check if hedging fields exist
    has_hedging = any(e.get("hedging_count") is not None for e in recent)

    print(f"{'=' * 55}")
    print(f"  Compaction Nuance Drift — last {days} days")
    print(f"{'=' * 55}")
    print()
    print(f"  Compaction events:  {len(recent)}")
    print(f"  Sessions:           {len(by_session)}")
    print(f"  Multi-compaction:   {sum(1 for v in by_session.values() if len(v) > 1)}")
    print()

    if not has_hedging:
        print("  ⚠ No hedging density fields found in compact-log.jsonl.")
        print("  The precompact-log.sh hook extension is needed to capture:")
        print("    hedging_count, provenance_tag_count, qualifier_count, assistant_word_count")
        print()
        print("  Current data available: session counts, transcript sizes, CLIR fields.")
        print()

        # Still report what we can — transcript size trends
        if verbose:
            print("  Transcript sizes at compaction:")
            for sid, events in sorted(by_session.items(), key=lambda x: x[1][0].get("ts", "")):
                sizes = [e.get("transcript_lines", 0) for e in events]
                cwd = events[0].get("cwd", "").split("/")[-1]
                sizes_str = " → ".join(str(s) for s in sizes)
                print(f"    {sid[:8]}  {cwd:<15} {sizes_str} lines")
            print()

        # Log baseline metrics (without hedging data)
        log_metric(
            "compaction_nuance",
            days=days,
            events=len(recent),
            sessions=len(by_session),
            multi_compaction_sessions=sum(1 for v in by_session.values() if len(v) > 1),
            hedging_data_available=False,
        )
        print(f"  Logged to epistemic-metrics.jsonl")
        return

    # --- With hedging data ---
    drift_events = []
    all_densities = []

    for sid, events in by_session.items():
        densities = []
        for e in events:
            d = compute_density(e)
            if d is not None:
                densities.append((e, d))
                all_densities.append(d)

        # Check for drift: >50% density drop between consecutive compactions
        for i in range(len(densities) - 1):
            prev_entry, prev_d = densities[i]
            curr_entry, curr_d = densities[i + 1]
            if prev_d > 0 and curr_d / prev_d < 0.5:
                drift_events.append({
                    "session": sid,
                    "from_density": round(prev_d, 4),
                    "to_density": round(curr_d, 4),
                    "drop_pct": round((1 - curr_d / prev_d) * 100, 1),
                    "cwd": curr_entry.get("cwd", ""),
                })

    if all_densities:
        avg_density = sum(all_densities) / len(all_densities)
        print(f"  Avg nuance density: {avg_density:.4f} (hedging+qualifiers+provenance / words)")
        print(f"  Drift events (>50%): {len(drift_events)}")
        print()

        if verbose and drift_events:
            print("  Drift events:")
            for de in drift_events:
                cwd = de["cwd"].split("/")[-1] if de["cwd"] else "?"
                print(
                    f"    {de['session'][:8]}  {cwd:<15} "
                    f"{de['from_density']:.4f} → {de['to_density']:.4f} "
                    f"(-{de['drop_pct']}%)"
                )
            print()

    # Log metrics
    log_metric(
        "compaction_nuance",
        days=days,
        events=len(recent),
        sessions=len(by_session),
        multi_compaction_sessions=sum(1 for v in by_session.values() if len(v) > 1),
        hedging_data_available=True,
        avg_density=round(avg_density, 4) if all_densities else None,
        drift_events=len(drift_events),
    )
    print(f"  Logged to epistemic-metrics.jsonl")


if __name__ == "__main__":
    main()
