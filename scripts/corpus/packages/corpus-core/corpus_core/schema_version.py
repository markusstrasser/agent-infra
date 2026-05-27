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


GRAPH_SCHEMA_VERSION = "1.0.0"   # bumps to 1.1.0 after Phase A
OUTBOX_SCHEMA_VERSION = "1.2.0"  # bumps to 1.3.0 after Phase A
GRAPH_MIN_READER = "1.0.0"
OUTBOX_MIN_READER = "1.2.0"


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
    """Bump the artifact's schema version. Called inside the same connection
    as the DDL migration; reverting the migration also reverts the row."""
    ensure_meta_table(con)
    # DuckDB's ON CONFLICT DO UPDATE parser treats bare `CURRENT_TIMESTAMP`
    # on the RHS as a column reference (Binder Error). Use now() instead;
    # both evaluate to the current UTC timestamp.
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
    """One-shot: seed corpus_schema_meta on an existing pre-G0 DB.

    Used by the maintain CLI for the G0 transition. Idempotent. Returns
    True if it actually inserted a row, False if the row was already
    present (or DB doesn't exist).
    """
    import duckdb

    db_path = Path(db_path)
    if not db_path.exists():
        return False

    con = duckdb.connect(str(db_path))
    try:
        existing = _read_meta_row(con, artifact)
        if existing is not None:
            return False
        if artifact == "graph":
            seed_graph_meta(con)
        elif artifact == "outbox":
            seed_outbox_meta(con)
        else:
            raise ValueError(f"unknown artifact {artifact!r}")
        return True
    finally:
        con.close()


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
