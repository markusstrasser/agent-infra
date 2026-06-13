"""SQLite connection policy defaults."""

import sqlite3
from pathlib import Path
from typing import Literal

_IsolationLevel = Literal["DEFERRED", "EXCLUSIVE", "IMMEDIATE"] | None


def open_db(path: Path | str, *, wal: bool = True, timeout: float = 5.0,
            foreign_keys: bool = False,
            isolation_level: _IsolationLevel = "DEFERRED") -> sqlite3.Connection:
    """Open SQLite DB with consistent policy defaults."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=timeout,
                         isolation_level=isolation_level)
    db.row_factory = sqlite3.Row
    if wal:
        db.execute("PRAGMA journal_mode=WAL")
    if foreign_keys:
        db.execute("PRAGMA foreign_keys = ON")
    return db


def open_db_ro(path: Path | str, *, timeout: float = 5.0) -> sqlite3.Connection:
    """Open a SQLite DB read-only (immutable consumers of a DB they don't own).

    Uses URI mode=ro so a reader never creates the file or its WAL/journal
    sidecars on a store another process owns (e.g. agentlogs.db). Caller must
    handle sqlite3.Error if the file is absent. Returns plain tuples (no
    row_factory) — these consumers use positional access.
    """
    return sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True, timeout=timeout)
