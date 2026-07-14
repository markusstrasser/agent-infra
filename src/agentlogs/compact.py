"""One-shot reclaim of write-only payload bloat in agentlogs.db.

Two passes, mirroring the two ingest-side drops in index.trim_payload:
- status_update payloads (never read; dropped at ingest since 2026-06-14)
- text-backed payloads (tool_result/error/reasoning/tool_call envelopes whose
  content lives in events.text; dropped at ingest since 2026-07-14) — the kind
  set is LOADED from index.py, never re-stated, so ingest and backfill cannot
  disagree about what gets dropped. Rows with empty text keep their payload
  (sole DB copy). Reversible only via re-index from JSONL.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .index import TEXT_BACKED_PAYLOADLESS_KINDS


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


_KIND_LIST = ", ".join(f"'{k}'" for k in sorted(TEXT_BACKED_PAYLOADLESS_KINDS))

# Same predicate as index.trim_payload's text-backed drop: kind in the set AND
# text non-empty. Rows with empty text keep their payload (sole DB copy).
_TEXT_BACKED_WHERE = f"""
    kind IN ({_KIND_LIST})
    AND payload_json IS NOT NULL AND payload_json != ''
    AND text IS NOT NULL AND text != ''
"""


def plan_compact_text_backed_payloads(db: sqlite3.Connection) -> CompactPlan:
    row = db.execute(
        f"""
        SELECT COUNT(*), COALESCE(SUM(LENGTH(payload_json)), 0)
        FROM events WHERE {_TEXT_BACKED_WHERE}
        """
    ).fetchone()
    return CompactPlan(
        kind="text_backed",
        rows=int(row[0]),
        payload_bytes=int(row[1]),
        size_before_mb=_db_size_mb(db),
    )


def apply_compact_status_payloads(db: sqlite3.Connection) -> CompactPlan:
    """Both write-only passes + one VACUUM. Name kept for the CLI's sake; the
    returned plan aggregates status_update + text-backed rows/bytes."""
    status = plan_compact_status_payloads(db)
    text_backed = plan_compact_text_backed_payloads(db)
    plan = CompactPlan(
        kind="status_update+text_backed",
        rows=status.rows + text_backed.rows,
        payload_bytes=status.payload_bytes + text_backed.payload_bytes,
        size_before_mb=status.size_before_mb,
    )
    if plan.rows:
        db.execute(
            """
            UPDATE events
            SET payload_json = NULL
            WHERE kind = 'status_update' AND payload_json IS NOT NULL AND payload_json != ''
            """
        )
        db.execute(f"UPDATE events SET payload_json = NULL WHERE {_TEXT_BACKED_WHERE}")
        db.commit()
        db.execute("VACUUM")
        db.commit()
        from agentlogs.prune import truncate_wal
        truncate_wal(db)
    plan.size_after_mb = _db_size_mb(db)
    return plan
