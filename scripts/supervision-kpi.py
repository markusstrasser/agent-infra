#!/usr/bin/env python3
# Gov-ID: tool:supervision-kpi
# goal: CLI for supervision_session — per-session JSONL + observe report artifacts.
# verifier: scripts/tests/test_supervision_taxonomy.py · test_supervision_session.py
# blast_radius: local
"""Supervision KPI CLI — direction vector over human corrections.

Thin wrapper over `supervision_session.py` + `supervision_taxonomy.py`.
See those modules for the architecture; this file is transport + stderr summary only.

Usage:
    supervision-kpi.py --today
    supervision-kpi.py --days 30 [--project intel] [--output artifacts/supervision-kpi.jsonl]
    supervision-kpi.py --days 7 --project agent-infra --report artifacts/observe/supervision-report.json
    supervision-kpi.py --days 30 --compare 2026-05-15
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import supervision_session as ss
import supervision_taxonomy as tax

AGENTLOGS_DB = Path.home() / ".claude" / "agentlogs.db"
_BYPASS_MODES = frozenset({"bypassPermissions", "dontAsk", "never", "auto"})


def query_approval_mode_stats(days: int = 21) -> dict | None:
    if not AGENTLOGS_DB.is_file():
        return None
    try:
        from common.db import open_db_ro
        with open_db_ro(AGENTLOGS_DB) as con:
            dist = {
                row[0]: row[1] for row in con.execute(
                    "SELECT COALESCE(approval_mode, '(null)') AS mode, COUNT(*) "
                    "FROM runs WHERE started_at > datetime('now', ?) GROUP BY mode",
                    (f"-{days} days",),
                )
            }
            recent = {
                row[0]: row[1] for row in con.execute(
                    "SELECT COALESCE(approval_mode, '(null)'), COUNT(*) FROM runs "
                    "WHERE started_at > datetime('now', '-7 days') GROUP BY 1"
                )
            }
            prior = {
                row[0]: row[1] for row in con.execute(
                    "SELECT COALESCE(approval_mode, '(null)'), COUNT(*) FROM runs "
                    "WHERE started_at BETWEEN datetime('now', '-14 days') "
                    "AND datetime('now', '-7 days') GROUP BY 1"
                )
            }
    except Exception:
        return None
    if not dist:
        return None

    def bypass_share(d: dict[str, int]) -> float:
        total = sum(d.values()) or 1
        bypass = sum(n for m, n in d.items() if m in _BYPASS_MODES)
        return bypass / total

    return {
        "days": days,
        "distribution": dist,
        "bypass_share_recent_7d": round(bypass_share(recent), 3),
        "bypass_share_prior_7d": round(bypass_share(prior), 3),
        "total_runs": sum(dist.values()),
    }


def _print_approval_mode_stats(window_days: int, records: list[ss.SessionRecord]) -> None:
    if window_days < 7:
        return
    stats = query_approval_mode_stats(window_days)
    if not stats:
        return
    dist = stats["distribution"]
    top = sorted(dist.items(), key=lambda x: -x[1])[:5]
    parts = ", ".join(f"{m}={n}" for m, n in top)
    print(f"APPROVAL_MODES ({stats['total_runs']} runs, {window_days}d): {parts}", file=sys.stderr)
    br, bp = stats["bypass_share_recent_7d"], stats["bypass_share_prior_7d"]
    if br != bp:
        print(f"  bypass-mode share: {bp:.1%} → {br:.1%} (7d prior → recent)", file=sys.stderr)
    air_sessions = [r for r in records if r.air is not None]
    if air_sessions and br > bp + 0.05:
        total_hooks = sum(r.hooks_shown for r in air_sessions)
        total_after = sum(r.corrections_after_hooks for r in air_sessions)
        air = total_after / total_hooks if total_hooks else 0
        if air > 0.05:
            print(
                "  ⚠ PROBLEM-HIDING? bypass-mode share rose while AIR elevated "
                f"({air:.3f}) — supervision may be dropping via mode, not hooks",
                file=sys.stderr,
            )


def _load_records(since: datetime, project: str | None) -> list[ss.SessionRecord]:
    from config import extract_project_name

    paths = ss.find_sessions_by_date(since)
    if project:
        paths = [p for p in paths if extract_project_name(p.parent.name) == project]
    records: list[ss.SessionRecord] = []
    for path in paths:
        try:
            records.append(ss.analyze_session(path))
        except Exception as e:
            print(f"WARN: failed to process {path.name}: {e}", file=sys.stderr)
    return ss.filter_by_start_date(records, since)


def _print_summary(records: list[ss.SessionRecord], args, window_days: int) -> None:
    n = len(records)
    if not n:
        return
    loads = sorted(r.load for r in records)
    mean_load = sum(loads) / n
    median_load = loads[n // 2] if n % 2 else (loads[n // 2 - 1] + loads[n // 2]) / 2
    days_label = "today" if getattr(args, "today", False) else f"{window_days}-day"

    print(file=sys.stderr)
    print(f"{days_label} summary: {n} sessions, mean load: {mean_load:.1f}, median load: {median_load:.1f}", file=sys.stderr)

    agg = ss.aggregate_vector(records)
    user_turns = sum(r.user_turns for r in records)
    correction_events = sum(sum(r.by_type.values()) for r in records)
    rate = 100 * correction_events / user_turns if user_turns else 0
    print(f"CORRECTION RATE: {correction_events}/{user_turns} user turns ({rate:.1f}%)", file=sys.stderr)
    print("SUPERVISION VECTOR (by direction):", file=sys.stderr)
    for d in tax.Direction:
        label = {
            "raise_autonomy": "was TIMID → loosen/act more  [pure autonomy signal]",
            "reduce_error": "was WRONG → correctness guardrail",
            "grow_coverage": "missed CONTEXT → add detector",
            "amplify_taste": "missed TASTE → options, keep human judge",
        }[d.value]
        print(f"  {d.value:14s} {agg[d.value]:4d}  — {label}", file=sys.stderr)

    oc = sum(r.by_type.get("over_caution", 0) for r in records)
    if oc:
        flagged = sorted(
            (r for r in records if r.by_type.get("over_caution", 0)),
            key=lambda r: -r.by_type["over_caution"],
        )[:6]
        names = ", ".join(
            f"{r.project}/{r.session_id[:8]}({r.by_type['over_caution']})" for r in flagged
        )
        print(
            f"OVER-CAUTION: {oc} — declining this = autonomy gain. [{names}]",
            file=sys.stderr,
        )

    trends = ss.compute_direction_trends(records)
    reading = ss.autonomy_reading(trends)
    if trends:
        print(
            f"TRENDS (+ = rate declining/improving): "
            f"autonomy {trends['raise_autonomy']:+.3f}, error {trends['reduce_error']:+.3f}, "
            f"coverage {trends['grow_coverage']:+.3f}, load {trends['load']:+.3f}",
            file=sys.stderr,
        )
    verdict = {
        "genuine_gain": "genuine autonomy gain (timidity ↓, errors/misses not rising)",
        "timidity_down_errors_up": "MIXED — timidity ↓ but errors rising",
        "timidity_rising": "REGression — timidity-corrections rising",
        "mixed": "MIXED — read the vector; falling load may hide rising errors or timidity",
        "insufficient_data": "insufficient data (need 5+ sessions)",
    }[reading]
    print(f"AUTONOMY READING: {verdict}", file=sys.stderr)

    from collections import defaultdict
    by_project: dict[str, list[float]] = defaultdict(list)
    for r in records:
        by_project[r.project].append(r.load)
    if len(by_project) > 1:
        parts = [f"{p}={sum(v) / len(v):.1f}" for p, v in sorted(by_project.items())]
        print(f"By project (mean load): {', '.join(parts)}", file=sys.stderr)

    air_sessions = [r for r in records if r.air is not None]
    if air_sessions:
        total_hooks = sum(r.hooks_shown for r in air_sessions)
        total_after = sum(r.corrections_after_hooks for r in air_sessions)
        overall_air = total_after / total_hooks if total_hooks else 0
        print(
            f"AIR: {overall_air:.3f} ({total_after}/{total_hooks} corrections after hooks, lower = better)",
            file=sys.stderr,
        )

    _print_approval_mode_stats(window_days, records)


def _print_comparison(records: list[ss.SessionRecord], compare_end: datetime, window_days: int, project: str | None) -> None:
    compare_start = compare_end - timedelta(days=window_days)
    paths = ss.find_sessions_by_date(compare_start, compare_end)
    from config import extract_project_name
    if project:
        paths = [p for p in paths if extract_project_name(p.parent.name) == project]
    prev: list[ss.SessionRecord] = []
    for path in paths:
        try:
            prev.append(ss.analyze_session(path))
        except Exception:
            pass
    if not prev:
        print(f"No comparison sessions found for period ending {compare_end.date()}", file=sys.stderr)
        return
    curr_v, prev_v = ss.aggregate_vector(records), ss.aggregate_vector(prev)
    print(file=sys.stderr)
    print(f"=== COMPARISON vs {compare_end.date()} (per-direction, per-session mean) ===", file=sys.stderr)
    for d in tax.Direction:
        c = curr_v[d.value] / len(records)
        p = prev_v[d.value] / len(prev)
        print(f"  {d.value:14s} {p:.2f} → {c:.2f}  ({c - p:+.2f})", file=sys.stderr)
    if len(prev) < 20 or len(records) < 20:
        print("  WARNING: <20 sessions in one period — estimate underpowered", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Supervision KPI — direction vector over human corrections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true")
    group.add_argument("--days", type=int)
    group.add_argument("--since", type=str)
    parser.add_argument("--project", "-p")
    parser.add_argument("--output", "-o", help="Write per-session JSONL")
    parser.add_argument(
        "--report", "-r",
        help="Write observe aggregate report JSON (supervision.report.v1)",
    )
    parser.add_argument("--compare", metavar="YYYY-MM-DD")
    args = parser.parse_args()

    if args.today:
        since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        window_days = 1
    elif args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d")
        window_days = (datetime.now() - since).days
    else:
        since = datetime.now() - timedelta(days=args.days)
        window_days = args.days

    records = _load_records(since, args.project)
    if not records:
        print(f"No sessions started in window (since {since.date()}).", file=sys.stderr)
        sys.exit(0)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w") as f:
            for r in records:
                f.write(json.dumps(r.to_kpi_dict()) + "\n")
        print(f"Wrote {len(records)} sessions to {out}", file=sys.stderr)
    elif not args.report:
        for r in records:
            print(json.dumps(r.to_kpi_dict()))

    if args.report:
        report = ss.build_report(
            records,
            days=window_days if not args.today else 1,
            since=since,
            project_filter=args.project,
        )
        for w in report.get("metric_integrity", {}).get("warnings", []):
            print(f"⚠ METRIC_INTEGRITY: {w}", file=sys.stderr)
        rp = Path(args.report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, indent=2))
        print(f"Wrote report → {rp}", file=sys.stderr)

    _print_summary(records, args, window_days)

    if args.compare:
        _print_comparison(records, datetime.strptime(args.compare, "%Y-%m-%d"), window_days, args.project)


if __name__ == "__main__":
    main()
