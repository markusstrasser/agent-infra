#!/usr/bin/env python3
"""Tool-opportunity utilization model — ATP tipping detection.

Measures tool usage per session normalized by task type to detect capability
abandonment (agents choosing not to use available tools). Raw tool-use rates
are confounded by task mix (Simpson's paradox) — this script normalizes.

Task types are inferred from tool-call patterns within each session:
  research  — dominated by search/fetch/MCP tools
  code-edit — dominated by Read/Edit/Write/Bash
  analysis  — dominated by Bash/Read with DuckDB/data tools
  mixed     — no dominant pattern

ATP signal: if normalized tool utilization drops >20% over 14 days within
a task type, that's a tipping indicator.

Usage:
    tool-trajectory.py [--days N] [--project P] [--json] [--backtest]
"""

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, stdev

from config import METRICS_FILE, log_metric

DB_PATH = Path.home() / ".claude" / "runlogs.db"

# Tool categories for task-type classification
RESEARCH_TOOLS = {
    "mcp__exa__web_search_exa", "mcp__exa__web_search_advanced_exa",
    "mcp__brave-search__brave_web_search", "mcp__paper-search__search_arxiv",
    "mcp__paper-search__search_pubmed", "mcp__research__search_papers",
    "mcp__research__fetch_paper", "mcp__research__save_paper",
    "mcp__research__read_paper", "mcp__research__ask_papers",
    "mcp__perplexity__perplexity_ask", "mcp__perplexity__perplexity_research",
    "mcp__perplexity__perplexity_reason", "mcp__perplexity__perplexity_search",
    "WebSearch", "WebFetch",
}

CODE_EDIT_TOOLS = {"Read", "Edit", "Write", "Bash", "Grep", "Glob"}

ANALYSIS_TOOLS = {
    "mcp__duckdb__execute_query", "Bash",  # Bash is dual-use
}

# Minimum tools per session to be meaningful
MIN_TOOLS = 5


@dataclass
class SessionProfile:
    run_id: str
    project: str
    started_at: str
    tool_counts: Counter = field(default_factory=Counter)
    total_tools: int = 0
    task_type: str = "unknown"
    tool_diversity: float = 0.0
    tools_per_minute: float = 0.0
    duration_min: float = 0.0


def classify_task_type(tool_counts: Counter) -> str:
    """Classify session task type from tool usage pattern."""
    total = sum(tool_counts.values())
    if total < MIN_TOOLS:
        return "minimal"

    research = sum(tool_counts.get(t, 0) for t in RESEARCH_TOOLS)
    code_edit = sum(tool_counts.get(t, 0) for t in CODE_EDIT_TOOLS)
    analysis = sum(tool_counts.get(t, 0) for t in ANALYSIS_TOOLS)

    research_frac = research / total
    code_frac = code_edit / total
    # Don't double-count Bash in analysis
    analysis_frac = (analysis - tool_counts.get("Bash", 0) * 0.5) / total

    if research_frac > 0.3:
        return "research"
    elif code_frac > 0.6:
        return "code-edit"
    elif analysis_frac > 0.2:
        return "analysis"
    else:
        return "mixed"


def load_sessions(days: int = 90, project: str | None = None) -> list[SessionProfile]:
    """Load session profiles from runlog DB."""
    if not DB_PATH.exists():
        print(f"ERROR: No runlog DB at {DB_PATH}")
        sys.exit(1)

    from common.db import open_db
    db = open_db(DB_PATH)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Get runs with their session info
    query = """
        SELECT r.run_id, r.started_at, r.ended_at, s.project_slug
        FROM runs r
        JOIN sessions s ON r.session_pk = s.session_pk
        WHERE r.started_at >= ?
          AND r.vendor = 'claude'
    """
    params: list = [cutoff]
    if project:
        query += " AND s.project_slug = ?"
        params.append(project)

    query += " ORDER BY r.started_at"
    runs = db.execute(query, params).fetchall()

    # Get tool calls per run
    profiles = []
    for run in runs:
        tools = db.execute(
            "SELECT tool_name FROM tool_calls WHERE run_id = ?",
            (run["run_id"],),
        ).fetchall()

        tool_counts = Counter(t["tool_name"] for t in tools)
        total = sum(tool_counts.values())

        if total < MIN_TOOLS:
            continue

        # Calculate duration
        duration_min = 0.0
        if run["started_at"] and run["ended_at"]:
            try:
                start = datetime.fromisoformat(run["started_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(run["ended_at"].replace("Z", "+00:00"))
                duration_min = max((end - start).total_seconds() / 60, 0.1)
            except (ValueError, TypeError):
                duration_min = 1.0

        profile = SessionProfile(
            run_id=run["run_id"],
            project=run["project_slug"] or "unknown",
            started_at=run["started_at"],
            tool_counts=tool_counts,
            total_tools=total,
            task_type=classify_task_type(tool_counts),
            tool_diversity=len(tool_counts) / max(total, 1),
            tools_per_minute=total / max(duration_min, 0.1),
            duration_min=duration_min,
        )
        profiles.append(profile)

    db.close()
    return profiles


def compute_baselines(profiles: list[SessionProfile]) -> dict[str, dict]:
    """Compute per-task-type tool usage baselines."""
    by_type: dict[str, list[SessionProfile]] = defaultdict(list)
    for p in profiles:
        if p.task_type != "minimal":
            by_type[p.task_type].append(p)

    baselines = {}
    for task_type, sessions in by_type.items():
        totals = [s.total_tools for s in sessions]
        diversities = [s.tool_diversity for s in sessions]
        rates = [s.tools_per_minute for s in sessions]

        baselines[task_type] = {
            "count": len(sessions),
            "tools_mean": mean(totals),
            "tools_std": stdev(totals) if len(totals) > 1 else 0,
            "diversity_mean": mean(diversities),
            "diversity_std": stdev(diversities) if len(diversities) > 1 else 0,
            "rate_mean": mean(rates),
            "rate_std": stdev(rates) if len(rates) > 1 else 0,
        }

    return baselines


def compute_rolling_utilization(
    profiles: list[SessionProfile],
    baselines: dict[str, dict],
    window_days: int = 7,
) -> list[dict]:
    """Compute rolling tool utilization z-scores by task type."""
    # Sort by date
    dated = []
    for p in profiles:
        if p.task_type == "minimal":
            continue
        try:
            ts = datetime.fromisoformat(p.started_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        dated.append((ts, p))

    dated.sort(key=lambda x: x[0])

    if not dated:
        return []

    # Compute per-day averages
    by_day: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for ts, p in dated:
        day = ts.strftime("%Y-%m-%d")
        baseline = baselines.get(p.task_type)
        if not baseline or baseline["tools_std"] == 0:
            continue
        z = (p.total_tools - baseline["tools_mean"]) / baseline["tools_std"]
        by_day[day][p.task_type].append(z)

    # Rolling window
    all_days = sorted(by_day.keys())
    results = []

    for i, day in enumerate(all_days):
        # Collect window
        window_start = (
            datetime.strptime(day, "%Y-%m-%d") - timedelta(days=window_days)
        ).strftime("%Y-%m-%d")

        window_z: dict[str, list] = defaultdict(list)
        for d in all_days[max(0, i - window_days * 2):i + 1]:
            if d >= window_start:
                for tt, zs in by_day[d].items():
                    window_z[tt].extend(zs)

        entry = {"date": day, "by_type": {}}
        for tt, zs in window_z.items():
            entry["by_type"][tt] = {
                "mean_z": round(mean(zs), 3),
                "n": len(zs),
            }
        results.append(entry)

    return results


def detect_tipping(
    rolling: list[dict],
    threshold: float = -0.5,
    trend_days: int = 14,
) -> list[dict]:
    """Detect tipping signals: sustained downward trends in tool utilization."""
    if len(rolling) < trend_days:
        return []

    alerts = []
    recent = rolling[-trend_days:]

    # Check each task type for sustained below-threshold
    task_types = set()
    for r in recent:
        task_types.update(r["by_type"].keys())

    for tt in task_types:
        values = []
        for r in recent:
            if tt in r["by_type"]:
                values.append(r["by_type"][tt]["mean_z"])

        if len(values) < 3:
            continue

        avg_z = mean(values)
        if avg_z < threshold:
            # Check if trend is downward (last 7 days worse than first 7)
            mid = len(values) // 2
            first_half = mean(values[:mid]) if values[:mid] else 0
            second_half = mean(values[mid:]) if values[mid:] else 0

            if second_half < first_half:
                alerts.append({
                    "task_type": tt,
                    "mean_z": round(avg_z, 3),
                    "trend": round(second_half - first_half, 3),
                    "period": f"{recent[0]['date']} to {recent[-1]['date']}",
                    "signal": "TIPPING" if avg_z < -1.0 else "WARNING",
                })

    return alerts


def backtest(profiles: list[SessionProfile]) -> dict:
    """Backtest: split data into train/test, check if model detects anomalies."""
    if len(profiles) < 20:
        return {"error": "Insufficient data for backtest", "n": len(profiles)}

    # Split 70/30
    split = int(len(profiles) * 0.7)
    train = profiles[:split]
    test = profiles[split:]

    baselines = compute_baselines(train)

    # Score test sessions
    scores = []
    for p in test:
        if p.task_type == "minimal" or p.task_type not in baselines:
            continue
        bl = baselines[p.task_type]
        if bl["tools_std"] == 0:
            continue
        z = (p.total_tools - bl["tools_mean"]) / bl["tools_std"]
        scores.append({
            "run_id": p.run_id[:8],
            "task_type": p.task_type,
            "z_score": round(z, 3),
            "flagged": z < -1.0,
        })

    flagged = sum(1 for s in scores if s["flagged"])
    return {
        "train_sessions": len(train),
        "test_sessions": len(test),
        "scored": len(scores),
        "flagged": flagged,
        "flag_rate": round(flagged / max(len(scores), 1), 4),
        "baselines": {
            tt: {"mean": round(b["tools_mean"], 1), "std": round(b["tools_std"], 1), "n": b["count"]}
            for tt, b in baselines.items()
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Tool-opportunity utilization model")
    parser.add_argument("--days", type=int, default=90, help="Lookback period")
    parser.add_argument("--project", type=str, help="Filter by project")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--backtest", action="store_true", help="Run backtest")
    parser.add_argument("--window", type=int, default=7, help="Rolling window days")
    args = parser.parse_args()

    profiles = load_sessions(days=args.days, project=args.project)

    if not profiles:
        print("No sessions found.")
        return

    baselines = compute_baselines(profiles)
    rolling = compute_rolling_utilization(profiles, baselines, window_days=args.window)
    alerts = detect_tipping(rolling)

    if args.backtest:
        bt = backtest(profiles)
        if args.json:
            print(json.dumps(bt, indent=2))
        else:
            print(f"\n{'=' * 55}")
            print("  Tool Trajectory Backtest")
            print(f"{'=' * 55}")
            print(f"\n  Train: {bt['train_sessions']}, Test: {bt['test_sessions']}")
            print(f"  Scored: {bt['scored']}, Flagged: {bt['flagged']} ({bt['flag_rate']:.1%})")
            print(f"\n  Baselines (from train):")
            for tt, b in sorted(bt.get("baselines", {}).items()):
                print(f"    {tt:<12} mean={b['mean']:.0f} std={b['std']:.0f} n={b['n']}")
        return

    result = {
        "period_days": args.days,
        "project": args.project,
        "total_sessions": len(profiles),
        "task_type_dist": Counter(p.task_type for p in profiles),
        "baselines": {
            tt: {k: round(v, 2) for k, v in b.items()}
            for tt, b in baselines.items()
        },
        "alerts": alerts,
        "rolling_latest": rolling[-5:] if rolling else [],
    }

    if args.json:
        # Counter isn't JSON-serializable
        result["task_type_dist"] = dict(result["task_type_dist"])
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'=' * 55}")
        print("  Tool-Opportunity Utilization Model")
        print(f"{'=' * 55}")
        print(f"\n  Period:    {args.days} days")
        print(f"  Sessions:  {len(profiles)} (min {MIN_TOOLS} tools)")
        if args.project:
            print(f"  Project:   {args.project}")

        print(f"\n  Task type distribution:")
        for tt, n in sorted(result["task_type_dist"].items(), key=lambda x: -x[1]):
            print(f"    {tt:<12} {n:>4} sessions")

        print(f"\n  Baselines (tools per session):")
        for tt, b in sorted(baselines.items()):
            print(f"    {tt:<12} mean={b['tools_mean']:.0f} ± {b['tools_std']:.0f}  (n={b['count']})")

        if alerts:
            print(f"\n  ALERTS ({len(alerts)}):")
            for a in alerts:
                print(f"    [{a['signal']}] {a['task_type']}: z={a['mean_z']}, trend={a['trend']}")
                print(f"      Period: {a['period']}")
        else:
            print(f"\n  No tipping signals detected.")

        if rolling:
            print(f"\n  Latest rolling ({args.window}d window):")
            for r in rolling[-3:]:
                types_str = ", ".join(
                    f"{tt}: z={v['mean_z']:.2f} (n={v['n']})"
                    for tt, v in sorted(r["by_type"].items())
                )
                print(f"    {r['date']}  {types_str}")

    log_metric(
        "tool_trajectory",
        period_days=args.days,
        project=args.project,
        total_sessions=len(profiles),
        task_types=dict(Counter(p.task_type for p in profiles)),
        alerts=len(alerts),
    )

    if not args.json:
        print(f"\n  Logged to {METRICS_FILE}")


if __name__ == "__main__":
    main()
