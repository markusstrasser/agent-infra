#!/usr/bin/env python3
"""Claude Code session dashboard.

Reads ~/.claude/session-receipts.jsonl and ~/.claude/compact-log.jsonl
to show weekly/all-time stats: cost, duration, compactions, top projects.

Includes SPC-style trend panel for epistemic metrics with sparklines.

Usage: uv run python3 scripts/dashboard.py [--days N]
"""

import json
import math
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

    # --- SPC trend panel ---
    all_metrics = load_jsonl(EPISTEMIC_METRICS)
    if all_metrics:
        print_spc_panel(all_metrics)


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


# --- SPC Trend Panel ---

SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float], min_val: float = 0.0, max_val: float = 1.0) -> str:
    """Render a sequence of values as a sparkline string."""
    if not values:
        return ""
    span = max_val - min_val
    if span == 0:
        return SPARKLINE_CHARS[4] * len(values)
    result = []
    for v in values:
        # Clamp to [0, 1] normalized range
        normalized = max(0.0, min(1.0, (v - min_val) / span))
        idx = min(int(normalized * (len(SPARKLINE_CHARS) - 1)), len(SPARKLINE_CHARS) - 1)
        result.append(SPARKLINE_CHARS[idx])
    return "".join(result)


def extract_metric_series(metrics: list[dict], metric_name: str, field: str) -> list[float]:
    """Extract a time-ordered series of values for a metric field."""
    values = []
    for m in metrics:
        if m.get("metric") == metric_name:
            v = m.get(field)
            if v is not None and isinstance(v, (int, float)):
                values.append(float(v))
    return values


def spearman_rho(x: list[float], y: list[float]) -> float | None:
    """Compute Spearman rank correlation coefficient."""
    n = min(len(x), len(y))
    if n < 3:
        return None
    x, y = x[:n], y[:n]

    def rank(vals: list[float]) -> list[float]:
        sorted_idx = sorted(range(len(vals)), key=lambda i: vals[i])
        ranks = [0.0] * len(vals)
        for r, i in enumerate(sorted_idx):
            ranks[i] = float(r)
        return ranks

    rx, ry = rank(x), rank(y)
    d_sq = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1 - (6 * d_sq) / (n * (n * n - 1))


def compute_correlations(metrics: list[dict]) -> list[tuple[str, str, float, int]]:
    """Compute Spearman correlations for metric pairs with n>=8."""
    # Define metric series to track
    series_defs = [
        ("pushback_index", "overall_rate", "pushback_rate"),
        ("pushback_index", "fold_rate", "fold_rate"),
        ("safe_lite_eval", "factual_precision", "factual_prec"),
        ("claims_reader", "sourced_rate", "sourced_rate"),
        ("claims_reader", "verified_rate", "verified_rate"),
    ]

    extracted = {}
    for metric_name, field, label in series_defs:
        series = extract_metric_series(metrics, metric_name, field)
        if series:
            extracted[label] = series

    results = []
    labels = list(extracted.keys())
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = labels[i], labels[j]
            n = min(len(extracted[a]), len(extracted[b]))
            if n >= 8:
                rho = spearman_rho(extracted[a], extracted[b])
                if rho is not None:
                    results.append((a, b, rho, n))
    return results


def print_spc_panel(metrics: list[dict]):
    """Print SPC-style trend panel with sparklines and control indicators."""
    # Define metrics to track: (metric_name, field, display_label, format_as_pct)
    tracked = [
        ("pushback_index", "overall_rate", "pushback_rate", True),
        ("pushback_index", "fold_rate", "fold_rate", True),
        ("safe_lite_eval", "factual_precision", "factual_prec", True),
        ("claims_reader", "sourced_rate", "sourced_rate", True),
        ("claims_reader", "verified_rate", "verified_rate", True),
    ]

    # Collect hook bypass rate from hook_event entries
    hook_events = [m for m in metrics if m.get("metric") == "hook_event"]
    if hook_events:
        triggered = sum(1 for h in hook_events if h.get("triggered"))
        bypassed = sum(1 for h in hook_events if h.get("bypassed"))
        if triggered > 0:
            tracked.append(("_hook_bypass", "_computed", "hook_bypass", True))

    # Extract all series
    series_data = {}
    for metric_name, field, label, _ in tracked:
        if metric_name == "_hook_bypass":
            # Compute bypass rate from hook events in batches
            # For now, just compute overall rate as a single point
            if hook_events:
                rate = bypassed / max(triggered, 1)
                series_data[label] = [rate]
            continue
        values = extract_metric_series(metrics, metric_name, field)
        if values:
            series_data[label] = values

    if not series_data:
        return

    total_points = sum(len(v) for v in series_data.values())
    max_n = max(len(v) for v in series_data.values()) if series_data else 0

    print(f"{'═' * 50}")
    if max_n >= 20:
        print(f"  Epistemic Trends (n={max_n}, control limits active)")
    else:
        print(f"  Epistemic Trends (n={max_n}, need 20 for control limits)")
    print(f"{'═' * 50}")
    print()

    for metric_name, field, label, as_pct in tracked:
        values = series_data.get(label)
        if not values:
            continue

        # Show last 10 values as sparkline
        display_vals = values[-10:]
        min_v = min(values)
        max_v = max(values)
        latest = values[-1]
        spark = sparkline(display_vals, min_v, max_v)

        if as_pct:
            latest_str = f"{latest:.0%}"
            range_str = f"{min_v:.0%}-{max_v:.0%}"
        else:
            latest_str = f"{latest:.2f}"
            range_str = f"{min_v:.2f}-{max_v:.2f}"

        # Alert if latest is historical min or max
        alert = ""
        if len(values) >= 3:
            if latest == min_v:
                alert = " [!min]"
            elif latest == max_v:
                alert = " [!max]"

        # p-chart control limits for n>=20
        control_str = ""
        if len(values) >= 20 and as_pct:
            mean = sum(values) / len(values)
            # Average sample size approximation — use 1 as placeholder
            # since we don't have per-measurement sample sizes here
            se = math.sqrt(mean * (1 - mean) / len(values)) if 0 < mean < 1 else 0
            ucl = min(1.0, mean + 3 * se)
            lcl = max(0.0, mean - 3 * se)
            if latest > ucl or latest < lcl:
                control_str = " [OOC]"  # out of control

        print(f"    {label:<16} {spark}  {latest_str:<6} [range: {range_str}]{alert}{control_str}")

    print()

    # Correlation panel
    correlations = compute_correlations(metrics)
    if correlations:
        print("  Metric correlations (Spearman ρ, n≥8):")
        for a, b, rho, n in sorted(correlations, key=lambda x: -abs(x[2])):
            flag = ""
            if abs(rho) > 0.7:
                flag = " ←strong"
            elif abs(rho) < 0.2:
                flag = " ←weak"
            print(f"    {a} × {b}: ρ={rho:+.2f} (n={n}){flag}")
        print()


if __name__ == "__main__":
    main()
