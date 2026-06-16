"""Health + stats surface for `agentlogs stats`."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class VendorStat:
    vendor: str
    sessions: int
    runs: int
    events: int
    tool_calls: int
    last_session_at: str | None
    last_index_success_at: str | None
    last_parse_error_at: str | None
    parse_errors_7d: int
    orphaned_7d: int


def db_size_bytes(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def vendor_stats(db: sqlite3.Connection) -> list[VendorStat]:
    # Aggregate each child table separately: events and tool_calls both fan out
    # from runs, so a single joined query materializes events x tool_calls rows
    # PER RUN before COUNT(DISTINCT) — minutes of temp-spill at ~500K events
    # ("database or disk is full" on large DBs).
    sql = """
        WITH session_counts AS (
            SELECT vendor, COUNT(*) AS sessions, MAX(start_ts) AS last_session_at
            FROM sessions GROUP BY vendor
        ),
        run_counts AS (
            SELECT s.vendor, COUNT(*) AS runs
            FROM runs r JOIN sessions s ON s.session_pk = r.session_pk
            GROUP BY s.vendor
        ),
        event_counts AS (
            SELECT s.vendor, COUNT(*) AS events
            FROM events e JOIN runs r ON r.run_id = e.run_id
            JOIN sessions s ON s.session_pk = r.session_pk
            GROUP BY s.vendor
        ),
        tc_counts AS (
            SELECT s.vendor, COUNT(*) AS tool_calls
            FROM tool_calls tc JOIN runs r ON r.run_id = tc.run_id
            JOIN sessions s ON s.session_pk = r.session_pk
            GROUP BY s.vendor
        )
        SELECT
            sc.vendor,
            sc.sessions,
            COALESCE(rc.runs, 0)        AS runs,
            COALESCE(ec.events, 0)      AS events,
            COALESCE(tcc.tool_calls, 0) AS tool_calls,
            sc.last_session_at
        FROM session_counts sc
        LEFT JOIN run_counts rc   ON rc.vendor = sc.vendor
        LEFT JOIN event_counts ec ON ec.vendor = sc.vendor
        LEFT JOIN tc_counts tcc   ON tcc.vendor = sc.vendor
        ORDER BY sc.vendor
    """
    health_rows = {
        row["vendor"]: row
        for row in db.execute("SELECT * FROM v_indexer_health")
    }
    out: list[VendorStat] = []
    for row in db.execute(sql):
        v = row["vendor"]
        health = health_rows.get(v)
        out.append(
            VendorStat(
                vendor=v,
                sessions=row["sessions"],
                runs=row["runs"],
                events=row["events"],
                tool_calls=row["tool_calls"],
                last_session_at=row["last_session_at"],
                last_index_success_at=health["last_success_at"] if health else None,
                # last_parse_error_at = the timestamp of the last GENUINE parse/vendor
                # error (not a reaped OrphanedRun crash row). This is the field an
                # operator should react to; OrphanedRun is operational crash-recovery.
                last_parse_error_at=health["last_parse_error_at"] if health else None,
                parse_errors_7d=health["parse_errors_7d"] if health else 0,
                orphaned_7d=health["orphaned_7d"] if health else 0,
            )
        )
    return out
