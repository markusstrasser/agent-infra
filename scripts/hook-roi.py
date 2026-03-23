#!/usr/bin/env python3
"""Hook ROI telemetry — analyze hook trigger patterns.

Reads ~/.claude/hook-triggers.jsonl to show:
- Triggers per hook (total, warn, block)
- False positive candidates (blocks followed by immediate user override)
- Triggers by project
- Trend over time
- Transfer effectiveness (--transfer): per-project hook success for cross-project deployment tracking

Usage:
    hook-roi.py [--days N] [--verbose]
    hook-roi.py --transfer [--since YYYY-MM-DD] [--days N]
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from common.paths import TRIGGERS_FILE


def load_triggers(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def parse_ts(ts: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return datetime.min


def main(days: int = 7, verbose: bool = False):
    if days == 7 and "--days" in sys.argv:  # legacy CLI compat
        pass
    if "--verbose" in sys.argv:
        verbose = True
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    cutoff = datetime.now() - timedelta(days=days)
    triggers = load_triggers(TRIGGERS_FILE)
    recent = [t for t in triggers if parse_ts(t.get("ts", "")) > cutoff]

    if not recent:
        print(f"No hook triggers in the last {days} days.")
        if not TRIGGERS_FILE.exists():
            print(f"Trigger log not found at {TRIGGERS_FILE}")
            print("Hooks need to call hook-trigger-log.sh to populate this.")
        elif triggers:
            print(f"({len(triggers)} total triggers on file, all older than {days} days)")
        return

    # --- By hook ---
    by_hook: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t in recent:
        hook = t.get("hook", "?")
        action = t.get("action", "?")
        by_hook[hook][action] += 1
        by_hook[hook]["total"] += 1

    # --- By project ---
    by_project: dict[str, int] = defaultdict(int)
    for t in recent:
        by_project[t.get("project", "?")] += 1

    # --- By tool ---
    by_tool: dict[str, int] = defaultdict(int)
    for t in recent:
        tool = t.get("tool", "")
        if tool:
            by_tool[tool] += 1

    # --- By day ---
    by_day: dict[str, int] = defaultdict(int)
    for t in recent:
        day = t.get("ts", "")[:10]
        if day:
            by_day[day] += 1

    # --- Print ---
    print(f"{'=' * 55}")
    print(f"  Hook ROI Analysis — last {days} days")
    print(f"{'=' * 55}")
    print()
    print(f"  Total triggers:  {len(recent)}")
    print(f"  Unique hooks:    {len(by_hook)}")
    print()

    # Hook breakdown
    print("  By hook:")
    sorted_hooks = sorted(by_hook.items(), key=lambda x: x[1]["total"], reverse=True)
    for hook, actions in sorted_hooks:
        total = actions["total"]
        warns = actions.get("warn", 0)
        blocks = actions.get("block", 0)
        reminds = actions.get("remind", 0)
        allows = actions.get("allow", 0)
        parts = []
        if blocks:
            parts.append(f"{blocks} block")
        if warns:
            parts.append(f"{warns} warn")
        if reminds:
            parts.append(f"{reminds} remind")
        if allows:
            parts.append(f"{allows} allow")
        detail = ", ".join(parts) if parts else "?"
        print(f"    {hook:<30} {total:>4}  ({detail})")
    print()

    # Project breakdown
    print("  By project:")
    for proj, count in sorted(by_project.items(), key=lambda x: -x[1]):
        print(f"    {proj:<25} {count:>4}")
    print()

    # Tool breakdown
    if by_tool:
        print("  By tool (top 10):")
        for tool, count in sorted(by_tool.items(), key=lambda x: -x[1])[:10]:
            print(f"    {tool:<30} {count:>4}")
        print()

    # Daily trend
    if len(by_day) > 1:
        print("  Daily trend:")
        for day in sorted(by_day.keys()):
            bar = "#" * min(by_day[day], 50)
            print(f"    {day}  {by_day[day]:>4}  {bar}")
        print()

    # False positive candidates: blocks that are high-frequency
    # (if a hook blocks often, it might be too aggressive)
    block_heavy = [
        (h, a) for h, a in sorted_hooks
        if a.get("block", 0) > 5 and a.get("block", 0) / a["total"] > 0.5
    ]
    if block_heavy:
        print("  Potential false-positive hooks (>50% block rate, >5 blocks):")
        for hook, actions in block_heavy:
            rate = actions["block"] / actions["total"]
            print(f"    {hook}: {actions['block']}/{actions['total']} ({rate:.0%} block rate)")
        print()

    if verbose and triggers:
        print(f"  All-time: {len(triggers)} total triggers")

    # Recommendations
    print("  Recommendations:")
    for hook, actions in sorted_hooks:
        total = actions["total"]
        blocks = actions.get("block", 0)
        if total == 0:
            continue
        if blocks > 10 and blocks / total > 0.8:
            print(f"    DEMOTE? {hook} — {blocks}/{total} blocks ({blocks/total:.0%}). May be too aggressive.")
        elif total > 20 and blocks == 0:
            print(f"    PROMOTE? {hook} — {total} triggers, 0 blocks. Consider upgrading to block.")
    if not any(a["total"] > 10 for _, a in sorted_hooks):
        print("    (Not enough data yet for recommendations. Collect more triggers.)")
    print()


def transfer_report(triggers: list[dict], days: int, since: str | None = None) -> None:
    """Cross-project transfer effectiveness: per-hook × per-project breakdown.

    Shows which hooks deployed globally are effective across projects.
    Flags low-volume projects (<20 sessions) as underpowered.
    """
    cutoff_dt = datetime.now() - timedelta(days=days)
    if since:
        cutoff_dt = max(cutoff_dt, datetime.strptime(since, "%Y-%m-%d"))
    cutoff = cutoff_dt.isoformat()
    recent = [t for t in triggers if t.get("ts", "") >= cutoff]

    if not recent:
        print("No triggers in the transfer window.")
        return

    # hook × project matrix
    matrix: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    project_session_counts: dict[str, set] = defaultdict(set)

    for t in recent:
        hook = t.get("hook", "?")
        proj = t.get("project", "?")
        action = t.get("action", "?")
        session = t.get("session_id", t.get("ts", "")[:16])
        matrix[hook][proj][action] += 1
        matrix[hook][proj]["total"] += 1
        project_session_counts[proj].add(session)

    min_sessions = 20
    print(f"{'=' * 60}")
    print(f"  Hook Transfer Report — since {cutoff[:10]}")
    print(f"{'=' * 60}")
    print()

    for hook in sorted(matrix.keys()):
        projects = matrix[hook]
        total = sum(p["total"] for p in projects.values())
        if total < 3:
            continue
        print(f"  {hook} ({total} total):")
        for proj in sorted(projects.keys()):
            counts = projects[proj]
            n_sessions = len(project_session_counts.get(proj, set()))
            underpowered = " [UNDERPOWERED]" if n_sessions < min_sessions else ""
            blocks = counts.get("block", 0)
            warns = counts.get("warn", 0)
            t = counts["total"]
            block_rate = blocks / t if t else 0
            print(f"    {proj:<20} {t:>3} triggers ({blocks} block, {warns} warn, "
                  f"block_rate={block_rate:.0%}){underpowered}")
        print()

    print("  Project session counts (for denominator check):")
    for proj, sessions in sorted(project_session_counts.items(),
                                  key=lambda x: -len(x[1])):
        n = len(sessions)
        flag = " < min" if n < min_sessions else ""
        print(f"    {proj:<20} {n:>3} sessions{flag}")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hook ROI telemetry")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--transfer", action="store_true",
                        help="Show per-hook × per-project transfer report")
    parser.add_argument("--since", type=str,
                        help="Filter triggers since YYYY-MM-DD (with --transfer)")
    args = parser.parse_args()

    triggers = load_triggers(TRIGGERS_FILE)
    if args.transfer:
        transfer_report(triggers, args.days, args.since)
    else:
        main(args.days, args.verbose)
