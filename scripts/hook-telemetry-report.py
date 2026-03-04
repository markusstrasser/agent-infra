#!/usr/bin/env python3
"""Hook telemetry report — reads ~/.claude/hook-triggers.jsonl and produces
a summary table: per-hook trigger count, block/warn/allow rates, by project, by day.

Usage:
    uv run python3 scripts/hook-telemetry-report.py [--days N] [--hook NAME]
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "hook-triggers.jsonl"


def load_entries(days: int = 7, hook_filter: str | None = None) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = []
    for line in LOG_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Parse timestamp
        ts_str = entry.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if ts < cutoff:
            continue
        if hook_filter and entry.get("hook") != hook_filter:
            continue
        entry["_ts"] = ts
        entries.append(entry)
    return entries


def report(entries: list[dict]) -> str:
    if not entries:
        return "No hook triggers found in the specified period."

    lines = []

    # Summary table
    hook_stats: dict[str, Counter] = defaultdict(Counter)
    hook_projects: dict[str, set] = defaultdict(set)
    for e in entries:
        hook = e.get("hook", "unknown")
        action = e.get("action", "unknown")
        hook_stats[hook][action] += 1
        hook_stats[hook]["_total"] += 1
        hook_projects[hook].add(e.get("project", "?"))

    lines.append("## Hook Telemetry Report")
    lines.append("")
    lines.append(f"**Period:** last {len(set(e['_ts'].date() for e in entries))} days "
                 f"({len(entries)} total triggers)")
    lines.append("")
    lines.append("| Hook | Total | Block | Warn | Allow | Remind | Log | Projects |")
    lines.append("|------|------:|------:|-----:|------:|-------:|----:|----------|")

    for hook in sorted(hook_stats, key=lambda h: -hook_stats[h]["_total"]):
        s = hook_stats[hook]
        projects = ", ".join(sorted(hook_projects[hook]))
        lines.append(
            f"| {hook} | {s['_total']} | {s.get('block', 0)} | {s.get('warn', 0)} | "
            f"{s.get('allow', 0)} | {s.get('remind', 0)} | {s.get('log', 0)} | {projects} |"
        )

    # Daily breakdown
    lines.append("")
    lines.append("### Daily Breakdown")
    lines.append("")
    daily: dict[str, Counter] = defaultdict(Counter)
    for e in entries:
        day = e["_ts"].strftime("%Y-%m-%d")
        daily[day][e.get("hook", "unknown")] += 1
        daily[day]["_total"] += 1

    lines.append("| Date | Total | Top Hook |")
    lines.append("|------|------:|----------|")
    for day in sorted(daily):
        total = daily[day]["_total"]
        top = daily[day].most_common(2)
        top_hook = top[0][0] if top[0][0] != "_total" else (top[1][0] if len(top) > 1 else "—")
        lines.append(f"| {day} | {total} | {top_hook} |")

    # High false-positive flag (blocks that got overridden — heuristic: same hook
    # blocks > 20% of the time across projects)
    lines.append("")
    lines.append("### Hooks to Watch")
    lines.append("")
    for hook in sorted(hook_stats):
        s = hook_stats[hook]
        total = s["_total"]
        blocks = s.get("block", 0)
        if total >= 5 and blocks / total > 0.2:
            lines.append(f"- **{hook}**: {blocks}/{total} blocks ({blocks*100//total}%) — "
                         f"review for false positives")

    return "\n".join(lines)


def main():
    days = 7
    hook_filter = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--days" and i + 1 < len(args):
            days = int(args[i + 1])
            i += 2
        elif args[i] == "--hook" and i + 1 < len(args):
            hook_filter = args[i + 1]
            i += 2
        else:
            i += 1

    entries = load_entries(days=days, hook_filter=hook_filter)
    print(report(entries))


if __name__ == "__main__":
    main()
