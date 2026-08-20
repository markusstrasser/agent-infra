"""Explicit v9 -> v10 repair for amplified per-import provenance.

The live v9 store can contain tens of millions of duplicate ``record_refs``.
Ordinary connect-time migrations must stay fast and observable, so a populated
store is repaired explicitly under the single-writer lock. The operation is
transactional: child pointers are remapped to one source-stable record, the old
table is replaced, and any new foreign-key violation rolls the transaction back.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


LEGACY_VERSION = 9
CANONICAL_VERSION = 10


@dataclass(frozen=True)
class RepairPlan:
    record_refs: int
    pointer_upper_bound: int
    size_before_mb: float


@dataclass(frozen=True)
class RepairResult:
    record_refs_before: int
    record_refs_after: int
    size_before_mb: float
    size_after_mb: float
    elapsed_s: float


def open_unmigrated(path: Path | str) -> sqlite3.Connection:
    """Open a store without applying migrations (repair command only)."""
    db = sqlite3.connect(str(path), timeout=1800.0, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=1800000")
    db.execute("PRAGMA trusted_schema=ON")
    db.execute("PRAGMA cache_size=-524288")
    db.execute("PRAGMA mmap_size=8589934592")
    return db


def _size_mb(db: sqlite3.Connection) -> float:
    pages = int(db.execute("PRAGMA page_count").fetchone()[0])
    page_size = int(db.execute("PRAGMA page_size").fetchone()[0])
    return pages * page_size / 1_048_576


def _require_legacy(db: sqlite3.Connection) -> None:
    version = int(db.execute("PRAGMA user_version").fetchone()[0])
    if version != LEGACY_VERSION:
        raise RuntimeError(
            f"repair-provenance requires schema v{LEGACY_VERSION}; got v{version}"
        )


def plan_repair(db: sqlite3.Connection) -> RepairPlan:
    _require_legacy(db)
    refs = int(db.execute("SELECT COUNT(*) FROM record_refs").fetchone()[0])
    pointers = int(db.execute(
        "SELECT "
        "(SELECT COUNT(record_ref_id) FROM events) + "
        "(SELECT COUNT(start_record_ref_id) FROM tool_calls) + "
        "(SELECT COUNT(end_record_ref_id) FROM tool_calls) + "
        "(SELECT COUNT(record_ref_id) FROM file_touches)"
    ).fetchone()[0])
    return RepairPlan(refs, pointers, _size_mb(db))


def _fk_rows(db: sqlite3.Connection) -> set[tuple]:
    return {tuple(row) for row in db.execute("PRAGMA foreign_key_check")}


def apply_repair(
    db: sqlite3.Connection,
    *,
    vacuum: bool = True,
    log: Callable[[str], None] = print,
) -> RepairResult:
    """Canonicalize record refs transactionally, then optionally VACUUM."""
    _require_legacy(db)
    t0 = time.monotonic()
    size_before = _size_mb(db)
    before = int(db.execute("SELECT COUNT(*) FROM record_refs").fetchone()[0])
    baseline_fk = _fk_rows(db)

    db.execute("PRAGMA foreign_keys=OFF")
    db.execute("BEGIN IMMEDIATE")
    try:
        log("[repair] collecting referenced provenance ids...")
        db.execute("DROP TABLE IF EXISTS temp.live_ref_ids")
        db.execute(
            "CREATE TEMP TABLE live_ref_ids "
            "(record_ref_id INTEGER PRIMARY KEY) WITHOUT ROWID"
        )
        for table, column in (
            ("events", "record_ref_id"),
            ("tool_calls", "start_record_ref_id"),
            ("tool_calls", "end_record_ref_id"),
            ("file_touches", "record_ref_id"),
        ):
            db.execute(
                f"INSERT OR IGNORE INTO live_ref_ids "
                f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL"
            )

        log("[repair] choosing one canonical id per source record...")
        db.execute("DROP TABLE IF EXISTS temp.canonical_ref_ids")
        db.execute(
            "CREATE TEMP TABLE canonical_ref_ids ("
            "source_id INTEGER NOT NULL, raw_record_key TEXT NOT NULL, "
            "canonical_id INTEGER NOT NULL, metadata_id INTEGER NOT NULL, "
            "PRIMARY KEY(source_id, raw_record_key)) WITHOUT ROWID"
        )
        db.execute(
            "INSERT INTO canonical_ref_ids "
            "SELECT r.source_id, r.raw_record_key, "
            "MIN(r.record_ref_id), MAX(r.record_ref_id) "
            "FROM record_refs r JOIN live_ref_ids l USING(record_ref_id) "
            "GROUP BY r.source_id, r.raw_record_key"
        )

        db.execute("DROP TABLE IF EXISTS temp.ref_id_map")
        db.execute(
            "CREATE TEMP TABLE ref_id_map ("
            "old_id INTEGER PRIMARY KEY, canonical_id INTEGER NOT NULL) WITHOUT ROWID"
        )
        db.execute(
            "INSERT INTO ref_id_map "
            "SELECT r.record_ref_id, c.canonical_id "
            "FROM record_refs r "
            "JOIN live_ref_ids l USING(record_ref_id) "
            "JOIN canonical_ref_ids c "
            "ON c.source_id=r.source_id AND c.raw_record_key=r.raw_record_key"
        )

        log("[repair] materializing the canonical provenance table...")
        db.execute("DROP TABLE IF EXISTS record_refs_v10")
        db.execute(
            "CREATE TABLE record_refs_v10 ("
            "record_ref_id INTEGER PRIMARY KEY, "
            "source_id INTEGER NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE, "
            "raw_record_hash TEXT NOT NULL, raw_record_key TEXT NOT NULL, "
            "line_no INTEGER, byte_start INTEGER, byte_end INTEGER, ts_raw TEXT, "
            "UNIQUE(source_id, raw_record_key))"
        )
        db.execute(
            "INSERT INTO record_refs_v10 "
            "SELECT c.canonical_id, r.source_id, r.raw_record_hash, r.raw_record_key, "
            "r.line_no, r.byte_start, r.byte_end, r.ts_raw "
            "FROM record_refs r "
            "JOIN canonical_ref_ids c ON c.metadata_id=r.record_ref_id"
        )

        log("[repair] remapping event, tool, and file pointers...")
        for table, column in (
            ("events", "record_ref_id"),
            ("tool_calls", "start_record_ref_id"),
            ("tool_calls", "end_record_ref_id"),
            ("file_touches", "record_ref_id"),
        ):
            db.execute(
                f"UPDATE {table} SET {column}=("
                f"SELECT canonical_id FROM ref_id_map m WHERE m.old_id={table}.{column}) "
                f"WHERE {column} IS NOT NULL"
            )

        log("[repair] replacing the legacy table and adding FK indexes...")
        db.execute("DROP TABLE record_refs")
        db.execute("ALTER TABLE record_refs_v10 RENAME TO record_refs")
        db.execute(
            "CREATE INDEX idx_tool_calls_start_record_ref "
            "ON tool_calls(start_record_ref_id)"
        )
        db.execute(
            "CREATE INDEX idx_tool_calls_end_record_ref "
            "ON tool_calls(end_record_ref_id)"
        )
        db.execute(
            "CREATE INDEX idx_file_touches_record_ref "
            "ON file_touches(record_ref_id)"
        )
        db.execute(f"PRAGMA user_version={CANONICAL_VERSION}")

        introduced = _fk_rows(db) - baseline_fk
        if introduced:
            raise RuntimeError(
                f"provenance repair introduced foreign-key violations: {sorted(introduced)[:10]}"
            )
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    finally:
        db.execute("PRAGMA foreign_keys=ON")

    after = int(db.execute("SELECT COUNT(*) FROM record_refs").fetchone()[0])
    db.execute("ANALYZE record_refs")
    if vacuum:
        log("[repair] VACUUM reclaiming legacy pages...")
        db.execute("VACUUM")
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"integrity_check after provenance repair: {integrity}")
    return RepairResult(
        record_refs_before=before,
        record_refs_after=after,
        size_before_mb=size_before,
        size_after_mb=_size_mb(db),
        elapsed_s=time.monotonic() - t0,
    )
