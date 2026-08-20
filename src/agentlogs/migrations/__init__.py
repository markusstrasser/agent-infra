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


class ExplicitProvenanceRepairRequired(RuntimeError):
    """A populated v9 store must use the observable provenance repair path."""


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


def _split_sql(text: str) -> list[str]:
    """Split a SQL script on `;` boundaries.

    `Connection.executescript()` issues an implicit COMMIT before executing,
    so it cannot provide atomicity. We split statements ourselves using
    `sqlite3.complete_statement` for correctness — it understands BEGIN/END
    trigger bodies and quoted strings.
    """
    import sqlite3 as _sqlite3

    statements: list[str] = []
    buf: list[str] = []
    for line in text.splitlines(keepends=True):
        buf.append(line)
        candidate = "".join(buf)
        # complete_statement returns True when the buffer ends with a
        # statement terminator and BEGIN/END nesting balances.
        if _sqlite3.complete_statement(candidate):
            stmt = candidate.strip()
            if stmt:
                statements.append(stmt)
            buf = []
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def apply_migrations(db: sqlite3.Connection) -> list[int]:
    """Apply any migrations whose version exceeds PRAGMA user_version.

    Each migration runs as a single transaction (BEGIN ... COMMIT) with
    statements split out manually because `Connection.executescript()` issues
    an implicit COMMIT before executing, defeating atomicity. On any failure
    we ROLLBACK and leave user_version unchanged.

    Idempotent — safe to call on every connection (fast path: one PRAGMA
    read when already current).
    """
    current = int(db.execute("PRAGMA user_version").fetchone()[0])
    applied: list[int] = []
    for version, filename in _migration_files():
        if version <= current:
            continue
        if version == 10 and current == 9:
            # Migration 010 changes the identity and shape of the 16+ GiB
            # provenance table. Never let an ordinary read command silently
            # launch that rewrite. Fresh databases are empty and can migrate
            # normally; populated stores use the progress-reporting repair CLI
            # on a verified clone before an atomic swap.
            populated = db.execute("SELECT 1 FROM record_refs LIMIT 1").fetchone()
            if populated is not None:
                raise ExplicitProvenanceRepairRequired(
                    "agentlogs schema v9 contains legacy per-import provenance; "
                    "clone the database and run `agentlogs --db <clone> "
                    "repair-provenance --yes`, then verify and atomically swap"
                )
        statements = _split_sql(_read_migration(filename))
        db.execute("BEGIN")
        try:
            for stmt in statements:
                db.execute(stmt)
        except Exception:
            db.execute("ROLLBACK")
            raise
        db.execute("COMMIT")
        new_version = int(db.execute("PRAGMA user_version").fetchone()[0])
        if new_version != version:
            raise RuntimeError(
                f"Migration {filename} did not set PRAGMA user_version = {version} "
                f"(got {new_version})"
            )
        applied.append(version)
    return applied
