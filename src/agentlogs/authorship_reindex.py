"""Backfill canonical authorship labels over previously indexed Codex, Cursor and
Claude events. Text rules only: Claude's origin stamps are not stored, so a frame
recognized only by its stamp gets its label when its transcript is re-imported."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .authorship import is_claude_harness_text, is_injected_user_text


@dataclass(frozen=True)
class AuthorshipPlan:
    rows: int
    sessions: int


def _candidates(db: sqlite3.Connection) -> list[tuple[str, str, int]]:
    rows = db.execute(
        "SELECT e.event_id, e.text, s.session_pk, s.vendor "
        "FROM events e JOIN runs r USING(run_id) JOIN sessions s USING(session_pk) "
        "WHERE e.kind='user_message' AND e.role='user' AND e.text IS NOT NULL "
        "AND ((s.vendor='codex' AND e.vendor_kind='message') "
        "OR (s.vendor IN ('cursor', 'claude') AND e.vendor_kind='user'))"
    )
    return [
        (str(row[0]), str(row[1]), int(row[2]))
        for row in rows
        if (is_claude_harness_text if row[3] == "claude" else is_injected_user_text)(row[1])
    ]


def plan_reindex(db: sqlite3.Connection) -> AuthorshipPlan:
    rows = _candidates(db)
    return AuthorshipPlan(rows=len(rows), sessions=len({row[2] for row in rows}))


def apply_reindex(db: sqlite3.Connection) -> AuthorshipPlan:
    rows = _candidates(db)
    if not rows:
        return AuthorshipPlan(rows=0, sessions=0)
    session_pks = sorted({row[2] for row in rows})
    db.execute("BEGIN IMMEDIATE")
    try:
        db.executemany(
            "UPDATE events SET vendor_kind='meta_injected' WHERE event_id=?",
            [(row[0],) for row in rows],
        )
        # Recompute the affected session list surfaces using the same canonical
        # denormalizer as ingest; it already excludes meta_injected rows.
        from .index import _refresh_session_denorm

        _refresh_session_denorm(db, session_pks)
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    return AuthorshipPlan(rows=len(rows), sessions=len(session_pks))

