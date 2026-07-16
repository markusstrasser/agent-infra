#!/usr/bin/env python3
"""Export answer-bearing agentlogs turns for prior-context retrieval.

Each real user/assistant turn is an independently retrievable record. Session-level
retrieval is recovered by ``metadata.parent_id`` deduplication in emb. This preserves
late decisions and avoids embedding system/tool noise or truncating a whole session.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Iterator


DEFAULT_DB = Path.home() / ".claude" / "agentlogs.db"
MESSAGE_VENDOR_KINDS = {None, "message", "user", "assistant"}
INJECTED_PREFIXES = (
    "# AGENTS.md instructions for ",
    "<codex_delegation>",
    "<permissions instructions>",
    "<app-context>",
    "<collaboration_mode>",
    "<skills_instructions>",
    "<apps_instructions>",
    "<plugins_instructions>",
    "<environment_context>",
    "<recommended_plugins>",
)


def normalize(text: str) -> str:
    return " ".join(text.split())


def is_retrievable_turn(role: str | None, vendor_kind: str | None, text: str | None) -> bool:
    if role not in {"user", "assistant"} or vendor_kind not in MESSAGE_VENDOR_KINDS:
        return False
    stripped = (text or "").strip()
    return bool(stripped) and not stripped.startswith(INJECTED_PREFIXES)


def iter_turn_records(
    con: sqlite3.Connection,
    *,
    operator_only: bool = True,
    vendor: str | None = None,
    project: str | None = None,
    min_lines: int = 40,
    limit: int = 0,
) -> Iterator[dict]:
    where = ["s.session_uuid IS NOT NULL", "s.transcript_lines >= ?"]
    params: list[object] = [min_lines]
    if operator_only:
        where.append("s.is_subagent = 0")
    if vendor:
        where.append("s.vendor = ?")
        params.append(vendor)
    if project:
        where.append("s.project_slug = ?")
        params.append(project)
    sql = f"""
        SELECT s.session_pk, s.session_uuid, s.vendor_session_id, s.vendor,
               s.project_slug, s.start_ts, s.transcript_lines
        FROM sessions s
        WHERE {' AND '.join(where)}
        ORDER BY s.start_ts DESC, s.session_pk DESC
    """
    if limit:
        sql += " LIMIT ?"
        params.append(limit)

    for session in con.execute(sql, params):
        events = con.execute(
            """
            SELECT e.event_id, e.seq, e.role, e.vendor_kind, e.text
            FROM events e
            JOIN runs r ON r.run_id = e.run_id
            WHERE r.session_pk = ? AND e.text IS NOT NULL AND e.text != ''
            ORDER BY r.run_id, e.seq
            """,
            (session["session_pk"],),
        )
        for event in events:
            if not is_retrievable_turn(event["role"], event["vendor_kind"], event["text"]):
                continue
            text = normalize(event["text"])
            role = event["role"]
            session_uuid = session["session_uuid"]
            yield {
                "id": f"{session_uuid}:{event['event_id']}",
                "text": text,
                "source": "agentlogs",
                "title": f"{session['project_slug'] or 'unknown'} · {session['vendor']} · {role}",
                "date": (session["start_ts"] or "")[:10],
                "metadata": {
                    "parent_id": session_uuid,
                    "session_uuid": session_uuid,
                    "vendor_session_id": session["vendor_session_id"],
                    "session_pk": session["session_pk"],
                    "project": session["project_slug"],
                    "vendor": session["vendor"],
                    "role": role,
                    "event_id": event["event_id"],
                    "event_seq": event["seq"],
                    "transcript_lines": session["transcript_lines"],
                },
            }


def write_jsonl_atomic(path: Path, records: Iterator[dict]) -> tuple[int, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    count = 0
    sessions: set[str] = set()
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
                sessions.add(record["metadata"]["session_uuid"])
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return count, len(sessions)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int, default=0, help="0 = all matching sessions")
    parser.add_argument("--min-lines", type=int, default=40)
    parser.add_argument("--vendor")
    parser.add_argument("--project")
    parser.add_argument("--include-subagents", action="store_true")
    args = parser.parse_args()

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        count, sessions = write_jsonl_atomic(
            args.out,
            iter_turn_records(
                con,
                operator_only=not args.include_subagents,
                vendor=args.vendor,
                project=args.project,
                min_lines=args.min_lines,
                limit=args.limit,
            ),
        )
    finally:
        con.close()
    print(json.dumps({"records": count, "sessions": sessions, "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
