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
