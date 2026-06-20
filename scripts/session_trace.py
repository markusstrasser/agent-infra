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


# ---------------------------------------------------------------------------
# F1 — typed trace IR (HTIR 2606.06324, minimal schema; derived view, no new DB).
# Lets diagnosis group by *effect/flaw* not anecdote, and makes "did the intended
# mechanism fire?" a query over typed steps rather than a transcript re-read.
# pi-cwl (2606.11213) caveat: provenance edges are INFERRED forensic hints from
# temporal+resource co-occurrence, NEVER causal ground truth — labelled as such.
# ---------------------------------------------------------------------------

# Cross-vendor effect-kind taxonomy. file_touches.op is authoritative when present;
# this classifies the remainder by tool_name. Covers Claude / Codex / Cursor verbs.
_EFFECT_BY_TOOL = {
    # read
    "Read": "read", "Grep": "read", "Glob": "read", "LS": "read",
    "NotebookRead": "read", "search": "read", "query_json": "read",
    "list_artifacts": "read",
    # mutate
    "Write": "mutate", "Edit": "mutate", "MultiEdit": "mutate",
    "StrReplace": "mutate", "apply_patch": "mutate", "NotebookEdit": "mutate",
    # exec (generic shell — refined to read/mutate by file_touches when available)
    "Bash": "exec", "Shell": "exec", "exec_command": "exec",
    "write_stdin": "exec", "js": "exec",
    # network
    "WebFetch": "network", "WebSearch": "network",
    # spawn / orchestration
    "Agent": "spawn", "Task": "spawn", "Workflow": "spawn", "Skill": "spawn",
    # plan / bookkeeping
    "update_plan": "plan", "TaskCreate": "plan", "TaskUpdate": "plan",
    # capability discovery
    "ToolSearch": "search",
}
_MUTATE_OPS = {"edit", "write", "delete", "create", "append"}


def _effect_kind(tool_name: str | None, mcp_server: str | None, ops: set[str]) -> str:
    """Resolve effect_kind: file_touches.op authoritative, then tool_name, then mcp shape."""
    if ops & _MUTATE_OPS:
        return "mutate"
    if ops and ops <= {"read", "grep"}:
        return "read"
    base = _EFFECT_BY_TOOL.get(tool_name or "")
    if base:
        return base
    name = (tool_name or "").lower()
    if mcp_server:
        return "network" if ("search" in name or "fetch" in name or "research" in name) else "read"
    return "other"


def _args_resource(args_json: str | None) -> str | None:
    """Best-effort resource_ref from a tool's args when no file_touches row exists."""
    if not args_json:
        return None
    try:
        a = json.loads(args_json)
    except (json.JSONDecodeError, TypeError):
        return (args_json or "")[:80].replace("\n", " ").strip() or None
    if not isinstance(a, dict):
        return None
    for key in ("file_path", "path", "notebook_path", "url", "pattern", "query"):
        v = a.get(key)
        if isinstance(v, str) and v:
            return v[:120]
    for key in ("command", "cmd", "prompt"):
        v = a.get(key)
        if isinstance(v, str) and v:
            return v[:80].replace("\n", " ").strip()
    return None


def to_typed_ir(con, session_pk: int) -> dict:
    """Compile one session into typed TraceSteps + inferred provenance edges."""
    runs = [
        r[0] for r in con.execute(
            "SELECT run_id FROM runs WHERE session_pk=? ORDER BY rowid", (session_pk,)
        )
    ]
    # Per-tool_call file ops + paths (authoritative effect + resource source).
    ops_by_call: dict[str, set[str]] = {}
    paths_by_call: dict[str, list[str]] = {}
    if runs:
        qmarks = ",".join("?" * len(runs))
        for tcid, op, path in con.execute(
            f"SELECT tool_call_id, op, path FROM file_touches WHERE run_id IN ({qmarks})",
            runs,
        ):
            if tcid is None:
                continue
            ops_by_call.setdefault(tcid, set()).add((op or "").lower())
            if path:
                paths_by_call.setdefault(tcid, []).append(path)

    steps: list[dict] = []
    seq = 0
    for run_id in runs:
        for tcid, name, mcp_server, status, args_json in con.execute(
            "SELECT tool_call_id, tool_name, mcp_server, status, substr(args_json,1,400) "
            "FROM tool_calls WHERE run_id=? ORDER BY ts_start", (run_id,),
        ):
            seq += 1
            ops = ops_by_call.get(tcid, set())
            paths = paths_by_call.get(tcid, [])
            effect = _effect_kind(name, mcp_server, ops)
            resource = paths[0] if paths else _args_resource(args_json)
            steps.append({
                "id": tcid or f"step-{seq}",
                "seq": seq,
                "run_id": run_id,
                "tool_name": name,
                "effect_kind": effect,
                "resource_ref": resource,
                "status": status,
                "ops": sorted(ops) or None,
            })

    # Inferred provenance edges: a later read of a path written earlier in-session.
    # ALL edges inferred=true (pi-cwl): co-occurrence, not observed causality.
    last_writer: dict[str, dict] = {}
    edges: list[dict] = []
    for st in steps:
        for p in paths_by_call.get(st["id"], []):
            prod = last_writer.get(p)
            if prod and st["effect_kind"] == "read" and prod["id"] != st["id"]:
                edges.append({
                    "from": prod["id"], "to": st["id"],
                    "via_resource": p, "kind": "data_flow", "inferred": True,
                })
            if st["effect_kind"] == "mutate":
                last_writer[p] = st

    by_effect: dict[str, int] = {}
    for st in steps:
        by_effect[st["effect_kind"]] = by_effect.get(st["effect_kind"], 0) + 1
    return {
        "steps": steps,
        "step_count": len(steps),
        "effect_histogram": by_effect,
        "provenance_edges": edges,
        "edges_all_inferred": True,
    }


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
    ap.add_argument("--format", choices=("json", "otel", "text", "ir"), default="json")
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
        if args.format == "ir":
            ir = to_typed_ir(con, session["session_pk"])
            print(json.dumps({
                "session_uuid": session["session_uuid"],
                "vendor": session["vendor"],
                **ir,
            }, indent=2))
            return 0
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
