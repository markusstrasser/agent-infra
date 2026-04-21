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
    last_index_error_at: str | None
    errors_7d: int


def db_size_bytes(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def vendor_stats(db: sqlite3.Connection) -> list[VendorStat]:
    sql = """
        SELECT
            s.vendor,
            COUNT(DISTINCT s.session_pk) AS sessions,
            COUNT(DISTINCT r.run_id)     AS runs,
            COUNT(DISTINCT e.event_id)   AS events,
            COUNT(DISTINCT tc.tool_call_id) AS tool_calls,
            MAX(s.start_ts)              AS last_session_at
        FROM sessions s
        LEFT JOIN runs r       ON r.session_pk = s.session_pk
        LEFT JOIN events e     ON e.run_id = r.run_id
        LEFT JOIN tool_calls tc ON tc.run_id = r.run_id
        GROUP BY s.vendor
        ORDER BY s.vendor
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
                last_index_error_at=health["last_error_at"] if health else None,
                errors_7d=health["error_7d"] if health else 0,
            )
        )
    return out
