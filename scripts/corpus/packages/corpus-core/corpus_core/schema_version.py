"""DB-resident schema version + preflight for the corpus substrate.

Two artifacts versioned independently:

  - 'graph'   ~/Projects/corpus/graph.duckdb (canonical projection)
  - 'outbox'  per-repo theses.duckdb / genomics.duckdb / phenome.duckdb

Each carries its own `corpus_schema_meta` row. Readers and writers call the
relevant verify_* before touching the DB; the call raises a loud
SchemaVersionMismatch carrying path, artifact, expected/found versions, and
the migration command. This is the alternative to bare BinderException at
random read sites when the schema drifts under us.

Phase G0 of `.claude/plans/2026-05-27-knowledge-infra-next-foundations.md`.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import duckdb


GRAPH_SCHEMA_VERSION = "1.2.0"   # Epistemic core: +claim_relations(+endpoints,+active view)
OUTBOX_SCHEMA_VERSION = "1.4.0"  # Epistemic core: +relation_json passthrough
# Both bumps are ADDITIVE (new tables / new nullable column), so the minimum
# reader stays back: a 1.1.0 graph reader and a 1.3.0 outbox reader keep working.
GRAPH_MIN_READER = "1.1.0"
OUTBOX_MIN_READER = "1.3.0"


SCHEMA_META_DDL = """
CREATE TABLE IF NOT EXISTS corpus_schema_meta (
    artifact             VARCHAR PRIMARY KEY,
    schema_version       VARCHAR NOT NULL,
    min_reader_version   VARCHAR NOT NULL,
    min_writer_version   VARCHAR NOT NULL,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes                VARCHAR
);
""".strip()


class SchemaVersionMismatch(Exception):
    """Raised when on-disk schema version is incompatible with the code's
    expected version. Carries enough context to act on without re-reading
    the source: path, artifact, expected/found versions, migration command."""

    def __init__(
        self,
        *,
        db_path: str,
        artifact: str,
        expected: str,
        found: str,
        migration_cmd: str,
    ):
        self.db_path = db_path
        self.artifact = artifact
        self.expected = expected
        self.found = found
        self.migration_cmd = migration_cmd
        super().__init__(
            f"corpus {artifact} schema mismatch at {db_path}: "
            f"expected={expected} found={found}. Run: {migration_cmd}"
        )


def _parse_version(v: str) -> tuple[int, ...]:
    """Loose semver parse: split on '.', take leading integer fragment of
    each piece. Treats '1.2.3-rc1' as (1,2,3)."""
    parts: list[int] = []
    for piece in v.split("."):
        num = ""
        for ch in piece:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    return tuple(parts)


def _read_meta_row(
    con: "duckdb.DuckDBPyConnection", artifact: str
) -> Optional[tuple[str, str, str]]:
    """Returns (schema_version, min_reader, min_writer) for `artifact`,
    or None if the meta table doesn't exist or has no row for `artifact`."""
    import duckdb

    try:
        row = con.execute(
            "SELECT schema_version, min_reader_version, min_writer_version "
            "FROM corpus_schema_meta WHERE artifact = ?",
            [artifact],
        ).fetchone()
    except (duckdb.BinderException, duckdb.CatalogException):
        return None
    if row is None:
        return None
    return (str(row[0]), str(row[1]), str(row[2]))


def _verify(
    db_path: Path,
    *,
    artifact: str,
    expected_version: str,
    code_min_reader: str,
    migration_cmd: str,
) -> None:
    """Strict preflight. Greenfield (file missing) is a silent pass — the
    first writer will create+seed via the canonical schema_sql / outbox_schema.

    Once the DB file exists, missing meta is treated as a pre-G0 legacy DB
    and raises with a loud "needs bootstrap" message.
    """
    import duckdb

    db_path = Path(db_path)
    if not db_path.exists():
        return

    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except duckdb.IOException:
        # DB is contended; defer to the writer. Skipping preflight is safe
        # because the writer will hit the BinderException loudly anyway,
        # and this RO probe is best-effort early warning, not a barrier.
        return
    try:
        row = _read_meta_row(con, artifact)
    finally:
        con.close()

    if row is None:
        raise SchemaVersionMismatch(
            db_path=str(db_path),
            artifact=artifact,
            expected=expected_version,
            found="<no corpus_schema_meta row — pre-G0 DB>",
            migration_cmd=migration_cmd,
        )

    found_version = row[0]
    if _parse_version(found_version) < _parse_version(code_min_reader):
        raise SchemaVersionMismatch(
            db_path=str(db_path),
            artifact=artifact,
            expected=f">={code_min_reader}",
            found=found_version,
            migration_cmd=migration_cmd,
        )


def verify_graph_schema(db_path: Path) -> None:
    _verify(
        db_path,
        artifact="graph",
        expected_version=GRAPH_SCHEMA_VERSION,
        code_min_reader=GRAPH_MIN_READER,
        migration_cmd="uv run corpus maintain --bootstrap-schema-meta",
    )


def verify_outbox_schema(db_path: Path) -> None:
    """Outbox preflight. Returns silently if the outbox table itself
    doesn't exist — the DB belongs to a repo that doesn't yet enqueue
    corpus attestations (intel pre-Phase-I, or a fresh repo). The drain
    code's missing-table check covers the no-op path; preflight only
    matters when there's a partially-migrated state to detect.
    """
    import duckdb

    db_path = Path(db_path)
    if not db_path.exists():
        return
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except duckdb.IOException:
        return
    try:
        try:
            rows = con.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'pending_corpus_attestations'"
            ).fetchall()
        except (duckdb.BinderException, duckdb.CatalogException):
            return
        if not rows:
            return  # no outbox table → nothing to verify
    finally:
        con.close()

    _verify(
        db_path,
        artifact="outbox",
        expected_version=OUTBOX_SCHEMA_VERSION,
        code_min_reader=OUTBOX_MIN_READER,
        migration_cmd="uv run corpus maintain --bootstrap-schema-meta",
    )


def ensure_meta_table(con: "duckdb.DuckDBPyConnection") -> None:
    """Idempotently create the corpus_schema_meta table on this connection."""
    con.execute(SCHEMA_META_DDL)


def seed_graph_meta(
    con: "duckdb.DuckDBPyConnection",
    *,
    version: str = GRAPH_SCHEMA_VERSION,
    notes: str = "pre-bitemporal substrate v2.x",
) -> None:
    """Idempotent seed: insert the graph artifact's meta row if absent.
    Never overwrites — that's bump_schema's job."""
    ensure_meta_table(con)
    con.execute(
        """
        INSERT INTO corpus_schema_meta
            (artifact, schema_version, min_reader_version, min_writer_version, notes)
        VALUES ('graph', ?, ?, ?, ?)
        ON CONFLICT (artifact) DO NOTHING
        """,
        [version, GRAPH_MIN_READER, GRAPH_MIN_READER, notes],
    )


def seed_outbox_meta(
    con: "duckdb.DuckDBPyConnection",
    *,
    version: str = OUTBOX_SCHEMA_VERSION,
    notes: str = "composite-PK + lifecycle columns",
) -> None:
    """Idempotent seed: insert the outbox artifact's meta row if absent."""
    ensure_meta_table(con)
    con.execute(
        """
        INSERT INTO corpus_schema_meta
            (artifact, schema_version, min_reader_version, min_writer_version, notes)
        VALUES ('outbox', ?, ?, ?, ?)
        ON CONFLICT (artifact) DO NOTHING
        """,
        [version, OUTBOX_MIN_READER, OUTBOX_MIN_READER, notes],
    )


def bump_schema(
    con: "duckdb.DuckDBPyConnection",
    *,
    artifact: str,
    new_version: str,
    min_reader: str,
    min_writer: str,
    notes: str,
) -> None:
    """Bump the artifact's schema version MONOTONICALLY.

    Refuses to downgrade — calling this with a new_version LOWER than
    the existing row's schema_version is a no-op (silent). Prevents the
    "older client reapplies older schema_sql to a newer DB and silently
    overwrites the meta row" failure mode (plan-close finding #1).

    Reverting a migration must explicitly use a downgrade path that
    drops the meta row first; never via bump_schema alone.
    """
    ensure_meta_table(con)
    # DuckDB's ON CONFLICT DO UPDATE parser treats bare `CURRENT_TIMESTAMP`
    # on the RHS as a column reference (Binder Error). Use now() instead;
    # both evaluate to the current UTC timestamp.
    #
    # Monotonic guard via WHERE on the EXCLUDED.schema_version compared
    # to the existing schema_version. DuckDB lacks a clean COMPARE() for
    # semver-string ordering, so we do it in Python: check before INSERT.
    existing = _read_meta_row(con, artifact)
    if existing is not None:
        existing_version = existing[0]
        if _parse_version(new_version) < _parse_version(existing_version):
            # Downgrade attempt — silently no-op. The caller may be a
            # stale client whose schema_sql was committed before the
            # newer migration shipped.
            return
    con.execute(
        """
        INSERT INTO corpus_schema_meta
            (artifact, schema_version, min_reader_version,
             min_writer_version, notes, updated_at)
        VALUES (?, ?, ?, ?, ?, now())
        ON CONFLICT (artifact) DO UPDATE SET
            schema_version       = EXCLUDED.schema_version,
            min_reader_version   = EXCLUDED.min_reader_version,
            min_writer_version   = EXCLUDED.min_writer_version,
            notes                = EXCLUDED.notes,
            updated_at           = now()
        """,
        [artifact, new_version, min_reader, min_writer, notes],
    )


def bootstrap_db(db_path: Path, *, artifact: str) -> bool:
    """One-shot: apply the canonical current-version schema to an existing
    DB. For graph DBs this opens via index._connect (running the full
    graph_schema.sql, which seeds + bumps meta + applies all ALTERs
    idempotently). For outbox DBs it ensures lifecycle columns + seeds
    the meta row.

    Returns True if the meta row landed/advanced; False if the DB doesn't
    exist OR the meta was already at the current version.
    """
    import duckdb

    db_path = Path(db_path)
    if not db_path.exists():
        return False

    if artifact == "graph":
        # index._connect applies graph_schema.sql which idempotently
        # ALTERs to add new columns and bumps the meta row via ON
        # CONFLICT DO UPDATE. Open then close — work happens at connect.
        from .index import _connect
        before = None
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            before = _read_meta_row(con, "graph")
        finally:
            con.close()
        _connect(db_path).close()
        after = None
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            after = _read_meta_row(con, "graph")
        finally:
            con.close()
        return after != before

    if artifact == "outbox":
        con = duckdb.connect(str(db_path))
        try:
            existing = _read_meta_row(con, "outbox")
            if existing is not None and _parse_version(existing[0]) >= _parse_version(OUTBOX_SCHEMA_VERSION):
                return False
            # Apply lifecycle ALTERs + seed (handles legacy outboxes
            # that pre-date G0).
            from .outbox import ensure_lifecycle_columns
            ensure_lifecycle_columns(con)
            # ensure_lifecycle_columns calls seed_outbox_meta with default
            # (current) version; the row is at OUTBOX_SCHEMA_VERSION after.
            return True
        finally:
            con.close()

    raise ValueError(f"unknown artifact {artifact!r}")


__all__ = [
    "GRAPH_SCHEMA_VERSION",
    "GRAPH_MIN_READER",
    "OUTBOX_SCHEMA_VERSION",
    "OUTBOX_MIN_READER",
    "SCHEMA_META_DDL",
    "SchemaVersionMismatch",
    "bootstrap_db",
    "bump_schema",
    "ensure_meta_table",
    "seed_graph_meta",
    "seed_outbox_meta",
    "verify_graph_schema",
    "verify_outbox_schema",
]
