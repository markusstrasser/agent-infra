#!/usr/bin/env python3
"""Session automation telemetry from agentlogs.

llm: none

Usage:
  session_automation_telemetry.py --days 7
  session_automation_telemetry.py --days 7 --project genomics --json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from tool_contract import LlmClass, print_llm_header

DB = Path.home() / ".claude" / "agentlogs.db"


def classify_row(row: dict) -> str:
    """Bucket one session. sessions.session_role (the vendor's own origin stamp) decides
    operator vs automation; the text heuristics only name the kind of dispatch. Before
    the role existed, "operator" meant not-a-subagent and at least 5 minutes, which
    counted long `claude -p` ticks and `codex exec` runs as the operator's."""
    role = row.get("session_role")
    if role == "operator":
        return "operator"
    if role == "subagent":
        return "subagent"
    if role is None:
        return "undetermined"
    fm = (row.get("first_message") or "").lower()
    slug = (row.get("project_slug") or "").lower()
    dur = float(row.get("duration_min") or 0)
    vendor = (row.get("vendor") or "").lower()
    if "review an ai coding agent" in fm:
        return "stop_hook"
    if "steer-mining" in slug:
        return "steer_worker"
    if slug == "bare" and dur < 2:
        return "codex_bootstrap"
    if "llmx-cursor" in slug or "cache-llmx-cursor" in slug:
        return "transport_probe"
    if vendor == "cursor" and any(k in fm for k in ("code reviewer", "premise scout", "/debug", "bug hunt", "audit")):
        return "cursor_scout"
    return "dispatch"


def fetch_sessions(db: Path, days: int, project: str | None) -> list[dict]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    q = """
        SELECT vendor, project_slug, duration_min, session_role, first_message
        FROM sessions WHERE start_ts >= datetime('now', ?)
    """
    params: list = [f"-{days} days"]
    if project:
        q += " AND project_slug = ?"
        params.append(project)
    rows = con.execute(q, params).fetchall()
    con.close()
    return [dict(r) for r in rows]


def summarize(rows: list[dict]) -> dict:
    buckets: dict[str, int] = {}
    for row in rows:
        b = classify_row(row)
        buckets[b] = buckets.get(b, 0) + 1
    total = len(rows)
    undetermined = buckets.get("undetermined", 0)
    known = total - undetermined
    auto = known - buckets.get("operator", 0)
    return {
        "total": total,
        "automation": auto,
        "operator": buckets.get("operator", 0),
        "undetermined": undetermined,
        # share of sessions with a known origin; undetermined ones are reported, not guessed
        "automation_pct": round(100 * auto / known, 1) if known else 0,
        "buckets": dict(sorted(buckets.items(), key=lambda x: -x[1])),
    }


def render(summary: dict, days: int, project: str | None) -> str:
    scope = project or "all projects"
    lines = [
        f"## Session automation telemetry ({days}d, {scope})",
        f"- total: **{summary['total']}** · automation: **{summary['automation']}** "
        f"({summary['automation_pct']}%) · operator: **{summary['operator']}** · "
        f"undetermined: **{summary['undetermined']}**",
        "", "| bucket | n |", "|--------|---|",
    ]
    for k, n in summary["buckets"].items():
        lines.append(f"| {k} | {n} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--project", help="Filter project_slug e.g. genomics")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--db", type=Path, default=DB)
    args = ap.parse_args()

    print_llm_header(LlmClass.NONE)
    rows = fetch_sessions(args.db, args.days, args.project)
    summary = summarize(rows)
    if args.json:
        print(json.dumps(summary, indent=2))
        return 0
    print(render(summary, args.days, args.project))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
