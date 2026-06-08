"""Database connection policy for agentlogs.

Opens the unified agentlogs.db with the pragmas required for:
  - WAL concurrency (reader does not block writer)
  - 30s busy_timeout (launchd indexer vs interactive queries)
  - Foreign keys enforced
  - Trusted schema (required for FTS5 triggers)
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from .migrations import apply_migrations


DEFAULT_DB_PATH = Path(os.environ.get(
    "AGENTLOGS_DB",
    str(Path.home() / ".claude" / "agentlogs.db"),
))


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Open the agentlogs database with standard pragmas and migrations applied."""
    db_path = Path(path) if path else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(str(db_path), timeout=30.0, isolation_level=None)
    db.row_factory = sqlite3.Row
    # WAL must be set before schema operations; NORMAL is the right durability
    # point for a local append-heavy store where the last few seconds of writes
    # are recoverable from source JSONL anyway.
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=30000")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA trusted_schema=ON")
    # The store is ~11GB / 2.76M events with 7 indexes on `events`; per-source
    # inserts and the denorm subqueries are disk-bound when the working set spills
    # the default 2MB page cache (state-UN I/O stalls). A larger cache + memory-
    # mapped reads keep hot B-tree pages resident — measured the dominant lever on
    # bulk-import throughput. cache_size is negative = KiB; mmap_size is bytes.
    db.execute("PRAGMA cache_size=-1048576")   # 1 GiB page cache
    db.execute("PRAGMA mmap_size=8589934592")  # 8 GiB memory-mapped I/O

    apply_migrations(db)
    return db


def current_version(db: sqlite3.Connection) -> int:
    row = db.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0
