"""Retention prune for agentlogs.db.

The store is an append-only index of on-disk session JSONL files; left alone it
grows monotonically (14 GB / 3.3M events as of 2026-06-10). This module deletes
sessions older than a cutoff and reclaims the space.

Why this is not a one-liner DELETE:

  - ``events_fts`` is an EXTERNAL-CONTENT fts5 table (``content='events'``).
    Its sync triggers (events_ai/ad/au) are dropped during bulk indexing and
    may be absent. A bare ``DELETE FROM events`` therefore does NOT update the
    FTS index — search silently corrupts. We mirror the proven ``index --bulk``
    pattern: drop triggers, delete, ``'rebuild'`` the FTS from the surviving
    content, recreate triggers.

  - We KEEP ``sources``/``imports`` rows. They are the indexer's
    "already imported this sha → skip" markers. Deleting them would make the
    next ``agentlogs index`` re-import the still-on-disk JSONL and undo the
    prune. We delete only the heavy content (events + cascaded tool_calls /
    file_touches, plus now-unreferenced record_refs).

Cascade map (foreign_keys=ON, set by db.connect):
    sessions --PK--> runs (ON DELETE CASCADE)
    runs --run_id--> events / tool_calls / file_touches (ON DELETE CASCADE)
    record_refs: NOT cascaded by session delete (keyed on import/source) —
    cleaned explicitly by "unreferenced by any surviving row".
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass


_FTS_TRIGGERS = ("events_ai", "events_ad", "events_au")

# Canonical trigger bodies — copied verbatim from migrations/001_initial.sql so
# the post-prune DB is byte-identical in shape to a freshly-indexed one.
_RECREATE_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
    INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text);
END;
CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
    INSERT INTO events_fts(events_fts, rowid, text) VALUES('delete', old.rowid, old.text);
END;
CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE ON events BEGIN
    INSERT INTO events_fts(events_fts, rowid, text) VALUES('delete', old.rowid, old.text);
    INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text);
END;
"""

# record_refs no surviving row points at. Each leg is IS NOT NULL guarded so the
# NOT IN set never contains NULL (which would make NOT IN match nothing).
_UNREFERENCED_RECORD_REFS = """
record_ref_id NOT IN (
    SELECT record_ref_id        FROM events       WHERE record_ref_id        IS NOT NULL
    UNION SELECT start_record_ref_id FROM tool_calls  WHERE start_record_ref_id IS NOT NULL
    UNION SELECT end_record_ref_id   FROM tool_calls  WHERE end_record_ref_id   IS NOT NULL
    UNION SELECT record_ref_id        FROM file_touches WHERE record_ref_id      IS NOT NULL
)
"""


@dataclass
class PrunePlan:
    keep_days: int
    cutoff: str
    sessions: int
    runs: int
    events: int
    tool_calls: int
    file_touches: int
    record_refs: int  # estimate in dry-run, actual in apply
    size_before_mb: float
    size_after_mb: float | None = None

    def as_dict(self) -> dict:
        return asdict(self)


# Subquery reused across counts and the delete; NULL start_ts is always KEPT
# (we can't date it, so we never delete it). Cutoff bound via the :cut param.
_OLD_SESSIONS_SQL = (
    "SELECT session_pk FROM sessions "
    "WHERE start_ts IS NOT NULL AND start_ts < datetime('now', :cut)"
)


def _db_size_mb(db: sqlite3.Connection) -> float:
    pc = db.execute("PRAGMA page_count").fetchone()[0]
    ps = db.execute("PRAGMA page_size").fetchone()[0]
    return round(pc * ps / 1024 / 1024, 1)


def plan_prune(db: sqlite3.Connection, keep_days: int) -> PrunePlan:
    """Compute what a prune would delete. Read-only."""
    cut = f"-{keep_days} days"
    p = {"cut": cut}
    cutoff = db.execute("SELECT datetime('now', :cut)", p).fetchone()[0]
    old_s = _OLD_SESSIONS_SQL
    old_runs = f"SELECT run_id FROM runs WHERE session_pk IN ({old_s})"

    sessions = db.execute(f"SELECT COUNT(*) FROM ({old_s})", p).fetchone()[0]
    runs = db.execute(f"SELECT COUNT(*) FROM ({old_runs})", p).fetchone()[0]
    events = db.execute(
        f"SELECT COUNT(*) FROM events WHERE run_id IN ({old_runs})", p
    ).fetchone()[0]
    tool_calls = db.execute(
        f"SELECT COUNT(*) FROM tool_calls WHERE run_id IN ({old_runs})", p
    ).fetchone()[0]
    file_touches = db.execute(
        f"SELECT COUNT(*) FROM file_touches WHERE run_id IN ({old_runs})", p
    ).fetchone()[0]

    # record_refs estimate: those referenced ONLY by rows that will be deleted,
    # i.e. not referenced by any surviving event/tool_call/file_touch. Surviving
    # rows are those whose run is NOT in the old set.
    keep_runs = f"SELECT run_id FROM runs WHERE session_pk NOT IN ({old_s})"
    record_refs = db.execute(
        f"""
        SELECT COUNT(*) FROM record_refs WHERE record_ref_id NOT IN (
            SELECT record_ref_id FROM events
                WHERE record_ref_id IS NOT NULL AND run_id IN ({keep_runs})
            UNION SELECT start_record_ref_id FROM tool_calls
                WHERE start_record_ref_id IS NOT NULL AND run_id IN ({keep_runs})
            UNION SELECT end_record_ref_id FROM tool_calls
                WHERE end_record_ref_id IS NOT NULL AND run_id IN ({keep_runs})
            UNION SELECT record_ref_id FROM file_touches
                WHERE record_ref_id IS NOT NULL AND run_id IN ({keep_runs})
        )
        """,
        p,
    ).fetchone()[0]

    return PrunePlan(
        keep_days=keep_days, cutoff=cutoff,
        sessions=sessions, runs=runs, events=events,
        tool_calls=tool_calls, file_touches=file_touches,
        record_refs=record_refs, size_before_mb=_db_size_mb(db),
    )


def apply_prune(db: sqlite3.Connection, keep_days: int) -> PrunePlan:
    """Delete old sessions, rebuild FTS, recreate triggers, integrity-check, VACUUM.

    Raises on integrity/FK failure (after ROLLBACK) — the DB is left untouched.
    """
    plan = plan_prune(db, keep_days)
    cut = f"-{keep_days} days"
    p = {"cut": cut}

    db.execute("BEGIN IMMEDIATE")
    try:
        for trig in _FTS_TRIGGERS:
            db.execute(f"DROP TRIGGER IF EXISTS {trig}")
        # Cascades to runs -> events / tool_calls / file_touches.
        db.execute(
            "DELETE FROM sessions "
            "WHERE start_ts IS NOT NULL AND start_ts < datetime('now', :cut)",
            p,
        )
        cur = db.execute(f"DELETE FROM record_refs WHERE {_UNREFERENCED_RECORD_REFS}")
        actual_refs = cur.rowcount
        # Rebuild external-content FTS from surviving events, then restore triggers.
        db.execute("INSERT INTO events_fts(events_fts) VALUES('rebuild')")
        db.executescript(_RECREATE_TRIGGERS)
        # Integrity gates INSIDE the transaction — rollback if anything is wrong.
        fk = db.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            raise RuntimeError(f"foreign_key_check failed: {fk[:5]}")
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise

    integ = db.execute("PRAGMA integrity_check").fetchone()[0]
    if integ != "ok":
        raise RuntimeError(f"integrity_check after prune: {integ}")
    # Planner stats (migration 004: planner over-trusts idx_events_kind without
    # fresh stats) + reclaim free pages to disk.
    db.execute("ANALYZE events")
    db.execute("ANALYZE runs")
    db.execute("VACUUM")

    plan.record_refs = actual_refs
    plan.size_after_mb = _db_size_mb(db)
    return plan
