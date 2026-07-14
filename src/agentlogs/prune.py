"""Retention prune for agentlogs.db.

The store is an append-only index of on-disk session JSONL files; left alone it
grows monotonically (14 GB / 3.3M events as of 2026-06-10). This module deletes
sessions older than a cutoff and reclaims the space.

Hard-won shape (every one of these was a real failure on 2026-06-10):

  1. ``events_fts`` is an EXTERNAL-CONTENT fts5 table whose sync triggers
     (events_ai/ad/au) may be dropped. A bare ``DELETE FROM events`` does NOT
     update it — search corrupts. We drop triggers, delete, ``'rebuild'`` the
     FTS from surviving content, recreate triggers.

  2. Recreate the triggers with individual ``execute()`` calls — NOT
     ``executescript()``, which issues an implicit COMMIT and detonated the
     explicit COMMIT that followed ("cannot commit - no transaction is active").

  3. ``foreign_keys=ON`` + bulk delete = O(N^2): most child FK columns are
     UNINDEXED (events.parent_event_id self-ref, file_touches.tool_call_id,
     the record-ref cols), so each deleted row triggers a full child scan.
     Fix: toggle ``foreign_keys=OFF`` (outside any txn) and delete children
     FIRST, by INDEXED keys, covering EVERY table that references what we
     remove — events, tool_calls, file_touches, run_edges, run_configs (by
     run_id); runs, trace_index (by session_pk); then sessions. Missing even
     one (run_edges/run_configs were missed first) leaves dangling rows.

  4. We KEEP sources/imports rows (the indexer's "already imported -> skip"
     markers). record_refs of now-empty imports are removed by import_id, and
     the handful of surviving file_touches/tool_calls that pointed at them are
     NULLed (those columns are nullable provenance offsets).

  5. A trust-but-verify ``foreign_key_check`` inside the txn fails loud
     (ROLLBACK) if we introduced any dangling rows. It tolerates the known
     PRE-EXISTING runs->sessions orphans (present in the data before any prune;
     110 as of 2026-06-10) so a real data-quality wart can't block retention.
"""

from __future__ import annotations

import sqlite3
import sys
import time
from dataclasses import asdict, dataclass


def _log(msg: str) -> None:
    print(f"[prune] {msg}", file=sys.stderr, flush=True)


_FTS_TRIGGERS = ("events_ai", "events_ad", "events_au")

# Individual statements — see docstring note 2 (no executescript()).
_RECREATE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN "
    "INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text); END",
    "CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN "
    "INSERT INTO events_fts(events_fts, rowid, text) VALUES('delete', old.rowid, old.text); END",
    "CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE ON events BEGIN "
    "INSERT INTO events_fts(events_fts, rowid, text) VALUES('delete', old.rowid, old.text); "
    "INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text); END",
)

_OLD_SESSIONS = ("SELECT session_pk FROM sessions "
                 "WHERE start_ts IS NOT NULL AND start_ts < datetime('now', :cut)")
_OLD_RUNS = f"SELECT run_id FROM runs WHERE session_pk IN ({_OLD_SESSIONS})"

# (table, where-clause) deleted by old run_id, children-first.
_BY_RUN = (
    ("events", f"run_id IN ({_OLD_RUNS})"),
    ("tool_calls", f"run_id IN ({_OLD_RUNS})"),
    ("file_touches", f"run_id IN ({_OLD_RUNS})"),
    ("run_edges", f"src_run_id IN ({_OLD_RUNS}) OR dst_run_id IN ({_OLD_RUNS})"),
    ("run_configs", f"run_id IN ({_OLD_RUNS})"),
)
# Deleted by old session_pk (after the run-scoped children).
_BY_SESSION = (
    ("runs", f"session_pk IN ({_OLD_SESSIONS})"),
    ("trace_index", f"session_pk IN ({_OLD_SESSIONS})"),
)

_ORPHANED_RECORD_REFS_DELETE = (
    "DELETE FROM record_refs WHERE import_id IN ("
    " SELECT i.import_id FROM imports i"
    " WHERE NOT EXISTS (SELECT 1 FROM events e WHERE e.import_id = i.import_id))"
)
# NULL surviving pointers into just-deleted record_refs (rare cross-import case).
_NULL_DANGLING_REFS = (
    "UPDATE file_touches SET record_ref_id=NULL WHERE record_ref_id IS NOT NULL "
    "AND NOT EXISTS(SELECT 1 FROM record_refs r WHERE r.record_ref_id=file_touches.record_ref_id)",
    "UPDATE tool_calls SET start_record_ref_id=NULL WHERE start_record_ref_id IS NOT NULL "
    "AND NOT EXISTS(SELECT 1 FROM record_refs r WHERE r.record_ref_id=tool_calls.start_record_ref_id)",
    "UPDATE tool_calls SET end_record_ref_id=NULL WHERE end_record_ref_id IS NOT NULL "
    "AND NOT EXISTS(SELECT 1 FROM record_refs r WHERE r.record_ref_id=tool_calls.end_record_ref_id)",
)

# Pre-existing orphans tolerated by the post-delete FK gate (see docstring 5).
_KNOWN_PREEXISTING_FK = {("runs", "sessions")}


@dataclass
class PrunePlan:
    keep_days: int
    cutoff: str
    sessions: int
    runs: int
    events: int
    tool_calls: int
    file_touches: int
    record_refs: int
    size_before_mb: float
    size_after_mb: float | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _db_size_mb(db: sqlite3.Connection) -> float:
    pc = db.execute("PRAGMA page_count").fetchone()[0]
    ps = db.execute("PRAGMA page_size").fetchone()[0]
    return round(pc * ps / 1024 / 1024, 1)


def plan_prune(db: sqlite3.Connection, keep_days: int) -> PrunePlan:
    """Compute what a prune would delete. Read-only, all indexed/cheap counts."""
    p = {"cut": f"-{keep_days} days"}
    cutoff = db.execute("SELECT datetime('now', :cut)", p).fetchone()[0]
    sessions = db.execute(f"SELECT COUNT(*) FROM ({_OLD_SESSIONS})", p).fetchone()[0]
    runs = db.execute(f"SELECT COUNT(*) FROM ({_OLD_RUNS})", p).fetchone()[0]
    events = db.execute(
        f"SELECT COUNT(*) FROM events WHERE run_id IN ({_OLD_RUNS})", p).fetchone()[0]
    tool_calls = db.execute(
        f"SELECT COUNT(*) FROM tool_calls WHERE run_id IN ({_OLD_RUNS})", p).fetchone()[0]
    file_touches = db.execute(
        f"SELECT COUNT(*) FROM file_touches WHERE run_id IN ({_OLD_RUNS})", p).fetchone()[0]
    total_refs, total_events = db.execute(
        "SELECT (SELECT COUNT(*) FROM record_refs), (SELECT COUNT(*) FROM events)"
    ).fetchone()
    record_refs = int(events * total_refs / total_events) if total_events else 0
    return PrunePlan(
        keep_days=keep_days, cutoff=cutoff, sessions=sessions, runs=runs,
        events=events, tool_calls=tool_calls, file_touches=file_touches,
        record_refs=record_refs, size_before_mb=_db_size_mb(db))


def _new_fk_violations(db: sqlite3.Connection) -> list:
    rows = db.execute(
        'SELECT DISTINCT "table", "parent" FROM pragma_foreign_key_check').fetchall()
    return [(t, par) for (t, par) in rows if (t, par) not in _KNOWN_PREEXISTING_FK]


# Light-path VACUUM gate: below this free-page fraction a VACUUM buys nothing
# worth an O(db-size) rewrite (2026-07-14: a zero-delete weekly run spent >1h
# rebuilding FTS + vacuuming 10.5GB under launchd's low-priority I/O).
_VACUUM_FREELIST_FRACTION = 0.05


def apply_prune(db: sqlite3.Connection, keep_days: int) -> PrunePlan:
    """Delete old sessions (FK-off, children-first, all tables), rebuild FTS,
    verify no NEW dangling refs, VACUUM. Raises (after ROLLBACK) on any
    introduced FK violation or integrity failure.

    No-op weeks take a LIGHT PATH: when zero sessions are over retention, the
    heavy transaction (trigger drop, FTS rebuild, unconditional VACUUM) is
    skipped entirely — only orphaned record_refs cleanup runs (small standalone
    txn, no FTS interplay), and VACUUM fires only past a freelist threshold.
    """
    p = {"cut": f"-{keep_days} days"}
    cutoff = db.execute("SELECT datetime('now', :cut)", p).fetchone()[0]
    size_before = _db_size_mb(db)
    t0 = time.monotonic()
    counts: dict[str, int] = {}

    old_sessions = db.execute(f"SELECT COUNT(*) FROM ({_OLD_SESSIONS})", p).fetchone()[0]
    if old_sessions == 0:
        _log("0 sessions over retention — light path (no FTS rebuild)")
        db.execute("BEGIN IMMEDIATE")
        try:
            refs = db.execute(_ORPHANED_RECORD_REFS_DELETE).rowcount
            for stmt in _NULL_DANGLING_REFS:
                db.execute(stmt)
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
        freelist, pages = db.execute(
            "SELECT freelist_count, page_count FROM pragma_freelist_count(), pragma_page_count()"
        ).fetchone()
        if pages and freelist / pages >= _VACUUM_FREELIST_FRACTION:
            _log(f"VACUUM (freelist {freelist:,}/{pages:,} pages)...")
            db.execute("VACUUM")
        else:
            _log(f"VACUUM skipped (freelist {freelist:,}/{pages:,} pages below "
                 f"{_VACUUM_FREELIST_FRACTION:.0%})")
        _log(f"done ({time.monotonic()-t0:.0f}s total, light path)")
        return PrunePlan(
            keep_days=keep_days, cutoff=cutoff, sessions=0, runs=0, events=0,
            tool_calls=0, file_touches=0, record_refs=refs,
            size_before_mb=size_before, size_after_mb=_db_size_mb(db))

    db.execute("PRAGMA foreign_keys=OFF")  # only legal outside a transaction
    db.execute("BEGIN IMMEDIATE")
    try:
        for trig in _FTS_TRIGGERS:
            db.execute(f"DROP TRIGGER IF EXISTS {trig}")
        for table, where in _BY_RUN:
            counts[table] = db.execute(f"DELETE FROM {table} WHERE {where}", p).rowcount
            _log(f"deleted {counts[table]:,} {table} ({time.monotonic()-t0:.0f}s)")
        for table, where in _BY_SESSION:
            counts[table] = db.execute(f"DELETE FROM {table} WHERE {where}", p).rowcount
        counts["sessions"] = db.execute(
            "DELETE FROM sessions WHERE start_ts IS NOT NULL AND start_ts < datetime('now', :cut)",
            p).rowcount
        counts["record_refs"] = db.execute(_ORPHANED_RECORD_REFS_DELETE).rowcount
        for stmt in _NULL_DANGLING_REFS:
            db.execute(stmt)
        _log("rebuilding FTS...")
        db.execute("INSERT INTO events_fts(events_fts) VALUES('rebuild')")
        for stmt in _RECREATE_TRIGGERS:
            db.execute(stmt)
        _log("foreign_key_check...")
        bad = _new_fk_violations(db)
        if bad:
            raise RuntimeError(f"prune introduced FK violations: {bad}")
        db.execute("COMMIT")
        _log(f"committed ({time.monotonic()-t0:.0f}s)")
    except Exception:
        db.execute("ROLLBACK")
        db.execute("PRAGMA foreign_keys=ON")
        raise

    db.execute("PRAGMA foreign_keys=ON")
    _log("integrity_check...")
    integ = db.execute("PRAGMA integrity_check").fetchone()[0]
    if integ != "ok":
        raise RuntimeError(f"integrity_check after prune: {integ}")
    db.execute("ANALYZE events")
    db.execute("ANALYZE runs")
    _log("VACUUM...")
    db.execute("VACUUM")
    _log(f"done ({time.monotonic()-t0:.0f}s total)")

    return PrunePlan(
        keep_days=keep_days, cutoff=cutoff, sessions=counts["sessions"],
        runs=counts["runs"], events=counts["events"], tool_calls=counts["tool_calls"],
        file_touches=counts["file_touches"], record_refs=counts["record_refs"],
        size_before_mb=size_before, size_after_mb=_db_size_mb(db))
