"""Full-text and structured search across agentlogs."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal


SearchMode = Literal["session", "event"]


@dataclass(slots=True)
class SessionHit:
    session_pk: int
    session_uuid: str | None
    vendor: str
    project_slug: str | None
    start_ts: str | None
    first_message: str | None
    matching_events: int
    snippet: str | None


@dataclass(slots=True)
class EventHit:
    event_id: str
    run_id: str
    session_pk: int
    vendor: str
    project_slug: str | None
    ts: str | None
    kind: str
    role: str | None
    snippet: str


def _fts_query(user_query: str) -> str:
    """FTS5 treats user input verbatim. We drop stray quotes; callers can use
    explicit FTS5 operators (AND, OR, NOT, "phrase", prefix*)."""
    return user_query.replace('"', '""')


def search_sessions(
    db: sqlite3.Connection,
    query: str,
    *,
    vendor: str | None = None,
    project: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 50,
) -> list[SessionHit]:
    """Sessions whose events contain the FTS query, ranked by match count.

    Aggregates events_fts hits by session for "did this session mention X".
    """
    # FTS5 snippet() requires a non-grouped FTS context, so compute matches in
    # a CTE and fetch a representative snippet per session in a correlated
    # subquery.
    filters_sql = ""
    filters_params: list[object] = []
    if vendor:
        filters_sql += " AND s.vendor = ?"
        filters_params.append(vendor)
    if project:
        filters_sql += " AND s.project_slug = ?"
        filters_params.append(project)
    if since:
        filters_sql += " AND COALESCE(s.start_ts, e.ts) >= ?"
        filters_params.append(since)
    if until:
        filters_sql += " AND COALESCE(s.start_ts, e.ts) <= ?"
        filters_params.append(until)

    sql = f"""
        WITH matched AS (
            SELECT
                s.session_pk,
                s.session_uuid,
                s.vendor,
                s.project_slug,
                s.start_ts,
                s.first_message,
                COUNT(*) AS matching_events
            FROM events_fts
            JOIN events e   ON e.rowid = events_fts.rowid
            JOIN runs r     ON r.run_id = e.run_id
            JOIN sessions s ON s.session_pk = r.session_pk
            WHERE events_fts MATCH ?
            {filters_sql}
            GROUP BY s.session_pk
        )
        SELECT m.*,
            (
                SELECT snippet(events_fts, -1, '[', ']', '…', 16)
                FROM events_fts
                JOIN events e2 ON e2.rowid = events_fts.rowid
                JOIN runs r2   ON r2.run_id = e2.run_id
                WHERE events_fts MATCH ?
                  AND r2.session_pk = m.session_pk
                LIMIT 1
            ) AS snippet
        FROM matched m
        ORDER BY m.matching_events DESC, m.start_ts DESC
        LIMIT ?
    """
    fts_q = _fts_query(query)
    params: list[object] = [fts_q, *filters_params, fts_q, limit]

    return [
        SessionHit(
            session_pk=row["session_pk"],
            session_uuid=row["session_uuid"],
            vendor=row["vendor"],
            project_slug=row["project_slug"],
            start_ts=row["start_ts"],
            first_message=row["first_message"],
            matching_events=row["matching_events"],
            snippet=row["snippet"],
        )
        for row in db.execute(sql, params)
    ]


def search_events(
    db: sqlite3.Connection,
    query: str,
    *,
    vendor: str | None = None,
    project: str | None = None,
    since: str | None = None,
    until: str | None = None,
    kind: str | None = None,
    limit: int = 100,
) -> list[EventHit]:
    """Events matching the FTS query."""
    sql = """
        SELECT
            e.event_id, e.run_id, e.kind, e.role, e.ts,
            s.session_pk, s.vendor, s.project_slug,
            snippet(events_fts, -1, '[', ']', '…', 16) AS snippet
        FROM events_fts
        JOIN events e   ON e.rowid   = events_fts.rowid
        JOIN runs r     ON r.run_id  = e.run_id
        JOIN sessions s ON s.session_pk = r.session_pk
        WHERE events_fts MATCH ?
    """
    params: list[object] = [_fts_query(query)]
    if vendor:
        sql += " AND s.vendor = ?"
        params.append(vendor)
    if project:
        sql += " AND s.project_slug = ?"
        params.append(project)
    if since:
        sql += " AND e.ts >= ?"
        params.append(since)
    if until:
        sql += " AND e.ts <= ?"
        params.append(until)
    if kind:
        sql += " AND e.kind = ?"
        params.append(kind)
    sql += " ORDER BY e.ts DESC LIMIT ?"
    params.append(limit)

    return [
        EventHit(
            event_id=row["event_id"],
            run_id=row["run_id"],
            session_pk=row["session_pk"],
            vendor=row["vendor"],
            project_slug=row["project_slug"],
            ts=row["ts"],
            kind=row["kind"],
            role=row["role"],
            snippet=row["snippet"],
        )
        for row in db.execute(sql, params)
    ]


def get_session(db: sqlite3.Connection, uuid_or_pk: str | int) -> sqlite3.Row | None:
    """Look up a session by uuid or integer pk. Returns None if not found."""
    if isinstance(uuid_or_pk, int) or (isinstance(uuid_or_pk, str) and uuid_or_pk.isdigit()):
        row = db.execute(
            "SELECT * FROM sessions WHERE session_pk = ?", (int(uuid_or_pk),)
        ).fetchone()
        if row:
            return row
    return db.execute(
        "SELECT * FROM sessions WHERE session_uuid = ? "
        "OR vendor_session_id = ? OR synthetic_session_key = ? LIMIT 1",
        (str(uuid_or_pk), str(uuid_or_pk), str(uuid_or_pk)),
    ).fetchone()


def recent_sessions(
    db: sqlite3.Connection,
    *,
    vendor: str | None = None,
    project: str | None = None,
    limit: int = 20,
) -> list[sqlite3.Row]:
    sql = """
        SELECT
            session_pk, session_uuid, vendor, project_slug,
            start_ts, duration_min, model, first_message
        FROM sessions
        WHERE 1=1
    """
    params: list[object] = []
    if vendor:
        sql += " AND vendor = ?"
        params.append(vendor)
    if project:
        sql += " AND project_slug = ?"
        params.append(project)
    sql += " ORDER BY COALESCE(start_ts, indexed_at) DESC LIMIT ?"
    params.append(limit)
    return list(db.execute(sql, params))
