#!/usr/bin/env python3
"""Claude Code session dashboard.

Reads ~/.claude/session-receipts.jsonl and ~/.claude/compact-log.jsonl
to show weekly/all-time stats: cost, duration, compactions, top projects.

Usage: uv run python3 scripts/dashboard.py [--days N]
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

RECEIPTS = Path.home() / ".claude" / "session-receipts.jsonl"
COMPACTIONS = Path.home() / ".claude" / "compact-log.jsonl"
EPISTEMIC_METRICS = Path.home() / ".claude" / "epistemic-metrics.jsonl"


def load_jsonl(path: Path) -> list[dict]:
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
    # Handle both ISO formats
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return datetime.min


def main():
    days = 7
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    cutoff = datetime.now() - timedelta(days=days)

    # --- Load data ---
    receipts = load_jsonl(RECEIPTS)
    compactions = load_jsonl(COMPACTIONS)

    recent = [r for r in receipts if parse_ts(r.get("ts", "")) > cutoff]
    recent_compactions = [c for c in compactions if parse_ts(c.get("ts", "")) > cutoff]

    if not recent:
        print(f"No sessions in the last {days} days.")
        if receipts:
            print(f"({len(receipts)} total receipts on file)")
        else:
            print("No receipts yet. Receipts are written when sessions end.")
        return

    # --- Aggregate ---
    # Sum cost including compaction iterations (top-level usage excludes compaction)
    total_cost = 0.0
    for r in recent:
        base_cost = float(r.get("cost_usd", 0))
        # Check for compaction iteration costs (usage.iterations[] array)
        iterations = r.get("usage", {}).get("iterations", []) if isinstance(r.get("usage"), dict) else []
        iter_cost = sum(float(it.get("cost_usd", 0)) for it in iterations if isinstance(it, dict))
        total_cost += base_cost + iter_cost
    total_mins = sum(float(r.get("duration_min", 0)) for r in recent)
    total_lines_add = sum(int(r.get("lines_added", 0)) for r in recent)
    total_lines_rm = sum(int(r.get("lines_removed", 0)) for r in recent)
    avg_context = sum(int(r.get("context_pct", 0)) for r in recent) / len(recent)

    # By project
    by_project: dict[str, dict] = defaultdict(lambda: {"sessions": 0, "cost": 0.0, "mins": 0.0})
    for r in recent:
        p = r.get("project", "?")
        by_project[p]["sessions"] += 1
        by_project[p]["cost"] += float(r.get("cost_usd", 0))
        by_project[p]["mins"] += float(r.get("duration_min", 0))

    # By model
    by_model: dict[str, int] = defaultdict(int)
    for r in recent:
        by_model[r.get("model", "?")] += 1

    # Exit reasons
    by_reason: dict[str, int] = defaultdict(int)
    for r in recent:
        by_reason[r.get("reason", "?")] += 1

    # --- Print ---
    print(f"{'=' * 50}")
    print(f"  Claude Code Dashboard — last {days} days")
    print(f"{'=' * 50}")
    print()
    print(f"  Sessions:     {len(recent)}")
    print(f"  Total cost:   ${total_cost:.2f}")
    print(f"  Total time:   {total_mins:.0f} min ({total_mins/60:.1f} hrs)")
    print(f"  Avg context:  {avg_context:.0f}% at exit")
    print(f"  Code churn:   +{total_lines_add} / -{total_lines_rm}")
    print(f"  Compactions:  {len(recent_compactions)}")
    print()

    # By project table
    print("  By project:")
    sorted_projects = sorted(by_project.items(), key=lambda x: x[1]["cost"], reverse=True)
    for proj, stats in sorted_projects:
        print(f"    {proj:<20} {stats['sessions']:>3} sessions  ${stats['cost']:>6.2f}  {stats['mins']:>5.0f}m")
    print()

    # By model
    print("  By model:")
    for model, count in sorted(by_model.items(), key=lambda x: x[1], reverse=True):
        print(f"    {model:<20} {count:>3} sessions")
    print()

    # Exit reasons
    print("  Exit reasons:")
    for reason, count in sorted(by_reason.items(), key=lambda x: x[1], reverse=True):
        print(f"    {reason:<20} {count:>3}")
    print()

    # All-time summary if we have more data
    if len(receipts) > len(recent):
        all_cost = 0.0
        for r in receipts:
            base = float(r.get("cost_usd", 0))
            iters = r.get("usage", {}).get("iterations", []) if isinstance(r.get("usage"), dict) else []
            all_cost += base + sum(float(it.get("cost_usd", 0)) for it in iters if isinstance(it, dict))
        print(f"  All-time: {len(receipts)} sessions, ${all_cost:.2f} total")

    # --- Epistemic metrics panel ---
    print_epistemic_panel(cutoff)


def print_epistemic_panel(cutoff: datetime):
    """Print epistemic health metrics from epistemic-metrics.jsonl."""
    metrics = load_jsonl(EPISTEMIC_METRICS)
    if not metrics:
        return

    recent = [m for m in metrics if parse_ts(m.get("ts", "")) > cutoff]
    if not recent:
        return

    print()
    print(f"{'=' * 50}")
    print("  Epistemic Health")
    print(f"{'=' * 50}")
    print()

    # Latest pushback index
    pushback = [m for m in recent if m.get("metric") == "pushback_index"]
    if pushback:
        latest = pushback[-1]
        rate = latest.get("overall_rate", 0)
        zero = latest.get("zero_pushback_sessions", 0)
        sessions = latest.get("sessions", 0)
        print(f"  Pushback index:     {rate:.1%} ({zero} zero-pushback of {sessions} sessions)")
        by_proj = latest.get("by_project", {})
        if by_proj:
            parts = [f"{p}={v:.0%}" for p, v in sorted(by_proj.items())]
            print(f"    by project: {', '.join(parts)}")

    # Latest lint results
    lint = [m for m in recent if m.get("metric") == "epistemic_lint"]
    if lint:
        latest = lint[-1]
        unsourced = latest.get("unsourced_claims", 0)
        files = latest.get("files_scanned", 0)
        issue_rate = latest.get("issue_rate", 0)
        print(f"  Epistemic lint:     {unsourced} unsourced claims ({issue_rate:.0%} of {files} files)")
        by_type = latest.get("by_type", {})
        if by_type:
            top3 = sorted(by_type.items(), key=lambda x: -x[1])[:3]
            parts = [f"{t}={c}" for t, c in top3]
            print(f"    top types: {', '.join(parts)}")

    # Latest SAFE-lite eval
    safe = [m for m in recent if m.get("metric") == "safe_lite_eval"]
    if safe:
        latest = safe[-1]
        precision = latest.get("factual_precision")
        checked = latest.get("claims_checked", 0)
        supported = latest.get("supported", 0)
        contradicted = latest.get("contradicted", 0)
        if precision is not None:
            print(f"  SAFE-lite precision: {precision:.1%} ({supported}S/{contradicted}C of {checked} claims)")
        else:
            print(f"  SAFE-lite:          {checked} claims checked, no judged results")

    # Trend: show all pushback entries for trend direction
    if len(pushback) >= 2:
        rates = [m.get("overall_rate", 0) for m in pushback]
        if rates[-1] > rates[0]:
            trend = "improving"
        elif rates[-1] < rates[0]:
            trend = "declining"
        else:
            trend = "flat"
        print(f"  Pushback trend:     {trend} ({rates[0]:.1%} → {rates[-1]:.1%})")

    # Latest fold metrics
    if pushback:
        latest = pushback[-1]
        fold_rate = latest.get("fold_rate")
        if fold_rate is not None:
            total_p = latest.get("total_pressured", 0)
            total_f = latest.get("total_folds", 0)
            print(f"  Fold rate:          {fold_rate:.1%} ({total_f} folds of {total_p} pressured turns)")

    # Latest claims reader
    claims = [m for m in recent if m.get("metric") == "claims_reader"]
    if claims:
        latest = claims[-1]
        total = latest.get("total_claims", 0)
        vr = latest.get("verified_rate", 0)
        sr = latest.get("sourced_rate", 0)
        print(f"  Claims:             {total} total, {vr:.0%} verified, {sr:.0%} sourced")

    print()


if __name__ == "__main__":
    main()
