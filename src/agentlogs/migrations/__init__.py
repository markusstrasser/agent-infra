"""Versioned schema migrations for agentlogs.

On connect, `apply_migrations` compares PRAGMA user_version against the N in
every `00N_*.sql` file in this package and applies missing ones in order
within a transaction.

Convention: each migration file ends with `PRAGMA user_version = N;` so the
version bump is atomic with the schema change.
"""

from __future__ import annotations

import re
import sqlite3
from importlib import resources


_MIGRATION_RE = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")


def _migration_files() -> list[tuple[int, str]]:
    """Return [(version, filename), …] sorted by version."""
    files: list[tuple[int, str]] = []
    package_files = resources.files(__name__)
    for entry in package_files.iterdir():
        match = _MIGRATION_RE.match(entry.name)
        if match:
            files.append((int(match.group(1)), entry.name))
    files.sort()
    return files


def _read_migration(filename: str) -> str:
    return resources.files(__name__).joinpath(filename).read_text(encoding="utf-8")


def apply_migrations(db: sqlite3.Connection) -> list[int]:
    """Apply any migrations whose version exceeds PRAGMA user_version.

    Returns the list of versions applied. Idempotent — safe to call on every
    connection (fast path: one PRAGMA read when already current).
    """
    current = int(db.execute("PRAGMA user_version").fetchone()[0])
    applied: list[int] = []
    for version, filename in _migration_files():
        if version <= current:
            continue
        sql = _read_migration(filename)
        db.execute("BEGIN")
        try:
            db.executescript(sql)
        except Exception:
            db.execute("ROLLBACK")
            raise
        # executescript committed via the migration's own PRAGMA bump; ensure
        # a clean transaction state regardless.
        db.execute("COMMIT") if db.in_transaction else None
        new_version = int(db.execute("PRAGMA user_version").fetchone()[0])
        if new_version != version:
            raise RuntimeError(
                f"Migration {filename} did not set PRAGMA user_version = {version} "
                f"(got {new_version})"
            )
        applied.append(version)
    return applied
