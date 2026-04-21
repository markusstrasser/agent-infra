"""Render a session transcript for human consumption."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Iterator


@dataclass(slots=True)
class RenderedEvent:
    seq: int
    ts: str | None
    kind: str
    role: str | None
    text: str | None
    tool_name: str | None
    tool_args: dict | None


def iter_session_events(
    db: sqlite3.Connection, session_pk: int
) -> Iterator[RenderedEvent]:
    sql = """
        SELECT
            e.seq, e.ts, e.kind, e.role, e.text, e.tool_call_id,
            tc.tool_name, tc.args_json
        FROM events e
        JOIN runs r ON r.run_id = e.run_id
        LEFT JOIN tool_calls tc ON tc.tool_call_id = e.tool_call_id
        WHERE r.session_pk = ?
        ORDER BY r.started_at, e.seq
    """
    for row in db.execute(sql, (session_pk,)):
        args = None
        if row["args_json"]:
            try:
                args = json.loads(row["args_json"])
            except Exception:
                args = {"_raw": row["args_json"]}
        yield RenderedEvent(
            seq=row["seq"],
            ts=row["ts"],
            kind=row["kind"],
            role=row["role"],
            text=row["text"],
            tool_name=row["tool_name"],
            tool_args=args,
        )


def render_text(db: sqlite3.Connection, session_pk: int) -> str:
    """Plain-text transcript. Tool calls shown as one-line summaries."""
    lines: list[str] = []
    session = db.execute(
        "SELECT vendor, project_slug, model, start_ts FROM sessions WHERE session_pk = ?",
        (session_pk,),
    ).fetchone()
    if session is None:
        return f"# session {session_pk} not found\n"
    lines.append(
        f"# session {session_pk} · {session['vendor']} · "
        f"{session['project_slug'] or '-'} · {session['model'] or '-'}"
    )
    if session["start_ts"]:
        lines.append(f"# started {session['start_ts']}")
    lines.append("")

    for ev in iter_session_events(db, session_pk):
        prefix = f"[{ev.ts or '-'}] {ev.kind}"
        if ev.role and ev.role != ev.kind:
            prefix += f" ({ev.role})"
        if ev.tool_name:
            args_repr = (
                json.dumps(ev.tool_args, separators=(",", ":"))[:200]
                if ev.tool_args
                else ""
            )
            lines.append(f"{prefix} → {ev.tool_name} {args_repr}")
        else:
            body = (ev.text or "").strip()
            if body:
                lines.append(prefix)
                for line in body.splitlines():
                    lines.append(f"  {line}")
            else:
                lines.append(prefix)
    return "\n".join(lines) + "\n"


def render_json(db: sqlite3.Connection, session_pk: int) -> str:
    session = db.execute(
        "SELECT * FROM sessions WHERE session_pk = ?", (session_pk,)
    ).fetchone()
    if session is None:
        return json.dumps({"error": f"session {session_pk} not found"})
    events = [
        {
            "seq": ev.seq,
            "ts": ev.ts,
            "kind": ev.kind,
            "role": ev.role,
            "text": ev.text,
            "tool_name": ev.tool_name,
            "tool_args": ev.tool_args,
        }
        for ev in iter_session_events(db, session_pk)
    ]
    return json.dumps(
        {"session": dict(session), "events": events},
        indent=2,
        default=str,
    )
