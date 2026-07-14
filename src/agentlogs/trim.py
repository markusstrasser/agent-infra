"""Backfill the whole-context text cap over rows indexed before it existed.

The codex adapter now caps `message` text at ingest (see textcap.py). This
applies the SAME cap — same module, no re-stated constants — to the rows already
in the DB. Measured 2026-07-14: 47,289 rows over the cap holding 2.6GB.

The events_au trigger keeps events_fts in sync on UPDATE, so the FTS index
(a second tokenized copy of this text) shrinks with it.

REVERSIBILITY, precisely: the DB is a derived index; the raw JSONL is source of
truth and is untouched (internal for recent sessions, /Volumes/2TBPNY for the
archived tail, plus a full pre-trim DB snapshot). But a plain re-index RE-APPLIES
the cap — restoring verbatim text into the DB means raising HEAD_CHARS/TAIL_CHARS
in textcap.py first, THEN re-indexing. Reversible, not free.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass

from .textcap import CAP_CHARS, CAPPED_KINDS, cap_text

# Only codex's injected-context rows. Two exclusions, both load-bearing:
#   vendor_kind='message' — the codex adapter's whole-context rows. Genuine typed
#     text (claude adapter, vendor_kind 'user') is 39MB DB-wide and is never touched.
#   kind IN CAPPED_KINDS  — assistant OUTPUT is exempt (see textcap).
# The kind list is LOADED from textcap, never re-stated here: ingest and backfill
# must name the same set or they would disagree about what gets capped.
_KIND_PLACEHOLDERS = ", ".join(f"'{k}'" for k in sorted(CAPPED_KINDS))
_OVERSIZED = f"""
    SELECT event_id, text FROM events
    WHERE vendor_kind = 'message'
      AND kind IN ({_KIND_PLACEHOLDERS})
      AND text IS NOT NULL
      AND LENGTH(text) > :cap
"""


def _db_size_mb(db: sqlite3.Connection) -> float:
    page_count, page_size = db.execute(
        "SELECT page_count, page_size FROM pragma_page_count(), pragma_page_size()"
    ).fetchone()
    return page_count * page_size / 1_048_576


def _log(msg: str) -> None:
    print(f"  trim: {msg}", flush=True)


@dataclass
class TrimPlan:
    rows: int
    bytes_before: int
    bytes_after: int
    size_before_mb: float
    size_after_mb: float | None = None

    @property
    def bytes_saved(self) -> int:
        return self.bytes_before - self.bytes_after


def plan_trim(db: sqlite3.Connection) -> TrimPlan:
    """Cost the cap without writing. Computes the post-cap size by actually
    running cap_text — no estimate, the same function the apply path uses."""
    rows = before = after = 0
    for _, text in db.execute(_OVERSIZED, {"cap": CAP_CHARS}):
        capped = cap_text(text)
        if capped == text:  # already capped (sentinel) — not a candidate
            continue
        rows += 1
        before += len(text)
        after += len(capped or "")
    return TrimPlan(rows=rows, bytes_before=before, bytes_after=after,
                    size_before_mb=_db_size_mb(db))


def apply_trim(db: sqlite3.Connection) -> TrimPlan:
    plan = plan_trim(db)
    if not plan.rows:
        plan.size_after_mb = plan.size_before_mb
        return plan

    t0 = time.monotonic()
    _log(f"capping {plan.rows:,} rows "
         f"({plan.bytes_before / 1_048_576:.0f}MB → {plan.bytes_after / 1_048_576:.0f}MB text)...")

    # Batched: the events_au trigger rewrites an FTS row per UPDATE, so this is
    # the expensive part. One transaction keeps events and FTS consistent.
    db.execute("BEGIN IMMEDIATE")
    try:
        updates = []
        for event_id, text in db.execute(_OVERSIZED, {"cap": CAP_CHARS}).fetchall():
            capped = cap_text(text)
            if capped != text:
                updates.append((capped, event_id))
        db.executemany("UPDATE events SET text = ? WHERE event_id = ?", updates)
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    _log(f"committed ({time.monotonic() - t0:.0f}s)")

    integ = db.execute("PRAGMA integrity_check").fetchone()[0]
    if integ != "ok":
        raise RuntimeError(f"integrity_check after trim: {integ}")

    _log("VACUUM...")
    db.execute("VACUUM")

    from .prune import truncate_wal
    truncate_wal(db)

    plan.size_after_mb = _db_size_mb(db)
    _log(f"done ({time.monotonic() - t0:.0f}s total)")
    return plan
