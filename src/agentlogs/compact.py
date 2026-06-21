"""One-shot reclaim of write-only payload bloat in agentlogs.db.

status_update payloads are never read (index.py drops them on ingest going
forward); this clears historical rows. Reversible only via re-index from JSONL.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class CompactPlan:
    kind: str
    rows: int
    payload_bytes: int
    size_before_mb: float
    size_after_mb: float | None = None


def _db_size_mb(db: sqlite3.Connection) -> float:
    page_count, page_size = db.execute(
        "SELECT page_count, page_size FROM pragma_page_count(), pragma_page_size()"
    ).fetchone()
    return page_count * page_size / 1_048_576


def plan_compact_status_payloads(db: sqlite3.Connection) -> CompactPlan:
    row = db.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(LENGTH(payload_json)), 0)
        FROM events
        WHERE kind = 'status_update' AND payload_json IS NOT NULL AND payload_json != ''
        """
    ).fetchone()
    return CompactPlan(
        kind="status_update",
        rows=int(row[0]),
        payload_bytes=int(row[1]),
        size_before_mb=_db_size_mb(db),
    )


def apply_compact_status_payloads(db: sqlite3.Connection) -> CompactPlan:
    plan = plan_compact_status_payloads(db)
    if plan.rows:
        db.execute(
            """
            UPDATE events
            SET payload_json = NULL
            WHERE kind = 'status_update' AND payload_json IS NOT NULL AND payload_json != ''
            """
        )
        db.commit()
        db.execute("VACUUM")
        db.commit()
    plan.size_after_mb = _db_size_mb(db)
    return plan
