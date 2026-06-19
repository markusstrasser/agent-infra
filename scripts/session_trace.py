#!/usr/bin/env python3
"""Session trace — Eve-shaped span replay from agentlogs.db.

Read-only forensic CLI: turn → events → tool_calls hierarchy for one session.
Complements blindspot-miner (semantic) with structural replay.

  just session-trace <session-uuid-prefix>
  just session-trace codex:019ed6 --format text
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from common.db import open_db_ro
from common.paths import CLAUDE_DIR

DEFAULT_DB = CLAUDE_DIR / "agentlogs.db"


def resolve_session(con, token: str) -> dict | None:
    row = con.execute(
        "SELECT session_pk, session_uuid, vendor, transcript_lines, start_ts "
        "FROM sessions WHERE session_uuid = ? OR session_uuid LIKE ? "
        "ORDER BY start_ts DESC LIMIT 1",
        (token, f"{token}%"),
    ).fetchone()
    if not row:
        return None
    return {
        "session_pk": row[0],
        "session_uuid": row[1],
        "vendor": row[2],
        "transcript_lines": row[3],
        "start_ts": row[4],
    }


def trace_session(con, session_pk: int) -> dict:
    cur = con.execute(
        "SELECT run_id, vendor, approval_mode, started_at, status "
        "FROM runs WHERE session_pk=? ORDER BY rowid",
        (session_pk,),
    )
    runs = [
        {
            "run_id": r[0], "vendor": r[1], "approval_mode": r[2],
            "started_at": r[3], "status": r[4],
        }
        for r in cur.fetchall()
    ]
    spans: list[dict] = []
    for run in runs:
        run_id = run["run_id"]
        turn: dict = {
            "type": "ai.agentinfra.turn",
            "run_id": run_id,
            "vendor": run["vendor"],
            "approval_mode": run.get("approval_mode"),
            "events": [],
            "tool_calls": [],
        }
        for row in con.execute(
            "SELECT kind, role, text, tool_call_id, parent_event_id, seq "
            "FROM events WHERE run_id=? ORDER BY seq",
            (run_id,),
        ):
            kind, role, text, tcid, parent, seq = row
            if kind not in (
                "user_message", "assistant_message", "tool_use", "tool_result",
                "error", "permission_denied", "permission_requested",
            ):
                continue
            turn["events"].append({
                "type": f"ai.event.{kind}",
                "kind": kind,
                "role": role,
                "tool_call_id": tcid,
                "parent_event_id": parent,
                "seq": seq,
                "text_preview": (text or "")[:200],
            })
        for row in con.execute(
            "SELECT tool_call_id, tool_name, status, ts_start, ts_end, "
            "substr(args_json,1,300) AS args_preview "
            "FROM tool_calls WHERE run_id=? ORDER BY ts_start",
            (run_id,),
        ):
            tcid, name, status, ts_start, ts_end, args_preview = row
            turn["tool_calls"].append({
                "type": "ai.toolCall",
                "tool_call_id": tcid,
                "name": name,
                "status": status,
                "ts_start": ts_start,
                "ts_end": ts_end,
                "args_preview": args_preview,
            })
        spans.append(turn)
    return {"turns": spans, "turn_count": len(spans)}


def render_text(session: dict, trace: dict) -> str:
    lines = [
        f"session {session['session_uuid']}",
        f"  vendor={session['vendor']} lines={session['transcript_lines']}",
        f"  turns={trace['turn_count']}",
    ]
    for i, turn in enumerate(trace["turns"], 1):
        lines.append(f"  turn {i} run={turn['run_id'][:12]} approval={turn.get('approval_mode')}")
        for ev in turn["events"][:8]:
            preview = (ev.get("text_preview") or "").replace("\n", " ")[:70]
            lines.append(f"    {ev['kind']:18} {preview}")
        for tc in turn["tool_calls"][:12]:
            lines.append(f"    tool:{tc['name']:20} status={tc['status']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Eve-shaped session trace from agentlogs")
    ap.add_argument("session", help="session_uuid or prefix")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--format", choices=("json", "otel", "text"), default="json")
    args = ap.parse_args()

    db = Path(os.path.expanduser(args.db))
    if not db.is_file():
        print(f"agentlogs db not found: {db}", file=sys.stderr)
        return 1

    with open_db_ro(db) as con:
        session = resolve_session(con, args.session)
        if not session:
            print(f"session not found: {args.session}", file=sys.stderr)
            return 1
        trace = trace_session(con, session["session_pk"])

    payload = {
        "session_uuid": session["session_uuid"],
        "vendor": session["vendor"],
        "transcript_lines": session["transcript_lines"],
        **trace,
    }

    if args.format == "text":
        print(render_text(session, trace))
    elif args.format == "otel":
        # Flatten to span list for OTel export adapters
        spans = []
        for turn in trace["turns"]:
            spans.append({
                "name": "ai.agentinfra.turn",
                "attributes": {
                    "run_id": turn["run_id"],
                    "vendor": turn["vendor"],
                    "approval_mode": turn.get("approval_mode"),
                },
                "children": [
                    {"name": ev["type"], "attributes": {"kind": ev["kind"], "seq": ev["seq"]}}
                    for ev in turn["events"]
                ] + [
                    {"name": "ai.toolCall", "attributes": {"tool.name": tc["name"], "status": tc["status"]}}
                    for tc in turn["tool_calls"]
                ],
            })
        print(json.dumps({"resourceSpans": [{"scopeSpans": [{"spans": spans}]}]}, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
