"""Phase G0 — DB-resident schema version + preflight.

Covers: stale-DB raises informative SchemaVersionMismatch, current-DB
passes, greenfield (no file) is silent pass, bootstrap is idempotent.
"""
from __future__ import annotations

import duckdb
import pytest

from corpus_core.schema_version import (
    GRAPH_SCHEMA_VERSION,
    OUTBOX_SCHEMA_VERSION,
    SCHEMA_META_DDL,
    SchemaVersionMismatch,
    bootstrap_db,
    bump_schema,
    seed_graph_meta,
    seed_outbox_meta,
    verify_graph_schema,
    verify_outbox_schema,
)


def test_verify_greenfield_no_db_is_silent(tmp_path):
    """No DB file → no preflight failure (writer creates fresh state)."""
    verify_graph_schema(tmp_path / "absent-graph.duckdb")
    verify_outbox_schema(tmp_path / "absent-outbox.duckdb")


def test_verify_pre_g0_db_raises_informative(tmp_path):
    """Existing DB with no corpus_schema_meta table → loud raise with
    db_path, artifact, expected/found, migration_cmd."""
    db = tmp_path / "legacy-graph.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "CREATE TABLE annotations ("
        "annotation_id VARCHAR PRIMARY KEY, "
        "asserted_at TIMESTAMP)"
    )
    con.close()

    with pytest.raises(SchemaVersionMismatch) as exc_info:
        verify_graph_schema(db)
    err = exc_info.value
    assert str(db) == err.db_path
    assert err.artifact == "graph"
    assert err.expected == GRAPH_SCHEMA_VERSION
    assert "pre-G0" in err.found or "no corpus_schema_meta" in err.found
    assert "bootstrap-schema-meta" in err.migration_cmd


def test_verify_low_version_raises(tmp_path):
    """DB seeded at 0.5.0 → code at 1.0.0 raises with the version delta."""
    db = tmp_path / "old-graph.duckdb"
    con = duckdb.connect(str(db))
    con.execute(SCHEMA_META_DDL)
    bump_schema(
        con,
        artifact="graph",
        new_version="0.5.0",
        min_reader="0.5.0",
        min_writer="0.5.0",
        notes="pre-release",
    )
    con.close()

    with pytest.raises(SchemaVersionMismatch) as exc_info:
        verify_graph_schema(db)
    assert exc_info.value.found == "0.5.0"


def test_verify_current_version_passes(tmp_path):
    """DB seeded at current version → preflight passes silently."""
    db = tmp_path / "current-graph.duckdb"
    con = duckdb.connect(str(db))
    seed_graph_meta(con)
    con.close()

    verify_graph_schema(db)


def test_outbox_preflight_symmetric(tmp_path):
    """Same shape for outbox artifact."""
    db = tmp_path / "outbox.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE pending_corpus_attestations (vid VARCHAR)")
    con.close()
    with pytest.raises(SchemaVersionMismatch):
        verify_outbox_schema(db)

    con = duckdb.connect(str(db))
    seed_outbox_meta(con)
    con.close()
    verify_outbox_schema(db)


def test_bootstrap_db_idempotent(tmp_path):
    """First call seeds + bumps (True); second call no-ops (False).
    Uses the realistic pre-Phase-A annotations shape (all v1 columns
    minus valid_from) so the bootstrap ALTER + UPDATE paths exercise
    correctly. Schema_sql's CREATE TABLE IF NOT EXISTS is a no-op for
    the existing table; the migration tail handles the upgrade."""
    db = tmp_path / "graph.duckdb"
    con = duckdb.connect(str(db))
    # Realistic pre-Phase-A substrate-v1 annotations table — the same
    # shape that existed before this commit landed.
    con.execute(
        """
        CREATE TABLE annotations (
            annotation_id            VARCHAR PRIMARY KEY,
            source_id                VARCHAR NOT NULL,
            source_type              VARCHAR,
            repo                     VARCHAR NOT NULL,
            actor_type               VARCHAR NOT NULL,
            actor_id                 VARCHAR NOT NULL,
            scope                    VARCHAR NOT NULL,
            tool                     VARCHAR,
            prompt_template_hash     VARCHAR,
            output_uri               VARCHAR,
            output_hash              VARCHAR,
            source_content_hash      VARCHAR,
            supersedes_annotation_id VARCHAR,
            status                   VARCHAR NOT NULL,
            asserted_at              TIMESTAMP NOT NULL,
            recorded_at              TIMESTAMP NOT NULL,
            schema_version           VARCHAR NOT NULL
        )
        """
    )
    con.close()

    assert bootstrap_db(db, artifact="graph") is True
    assert bootstrap_db(db, artifact="graph") is False
    # Now verify passes — preflight finds 1.1.0, expects 1.1.0.
    verify_graph_schema(db)


def test_bootstrap_missing_db_returns_false(tmp_path):
    assert bootstrap_db(tmp_path / "nope.duckdb", artifact="graph") is False


def test_g2_outbox_at_low_version_raises_informative(tmp_path):
    """Phase G2: stale outbox DB at v1.2.0 (no valid_from) raises
    SchemaVersionMismatch (NOT bare BinderException). The G0 preflight
    catches this before any SELECT touches the missing column.
    """
    db = tmp_path / "stale-outbox.duckdb"
    con = duckdb.connect(str(db))
    # Hand-craft a v1.2.0 outbox: composite-PK + lifecycle, NO valid_from.
    con.execute(SCHEMA_META_DDL)
    bump_schema(
        con,
        artifact="outbox",
        new_version="1.2.0",
        min_reader="1.2.0",
        min_writer="1.2.0",
        notes="composite-PK + lifecycle (pre-valid_from)",
    )
    con.execute(
        """
        CREATE TABLE pending_corpus_attestations (
            verdict_id VARCHAR NOT NULL,
            canonical_source_id VARCHAR NOT NULL,
            actor_type VARCHAR NOT NULL,
            actor_id VARCHAR NOT NULL,
            output_uri VARCHAR NOT NULL,
            output_hash VARCHAR,
            prompt_template_hash VARCHAR,
            asserted_at TIMESTAMP NOT NULL,
            queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            retry_count INTEGER DEFAULT 0,
            last_error VARCHAR,
            status VARCHAR DEFAULT 'pending',
            annotation_status VARCHAR DEFAULT 'active',
            supersedes_annotation_id VARCHAR,
            PRIMARY KEY (verdict_id, canonical_source_id)
        )
        """
    )
    con.close()

    with pytest.raises(SchemaVersionMismatch) as exc:
        verify_outbox_schema(db)
    assert exc.value.found == "1.2.0"
    assert "bootstrap-schema-meta" in exc.value.migration_cmd


def test_bump_schema_overwrites(tmp_path):
    db = tmp_path / "graph.duckdb"
    con = duckdb.connect(str(db))
    seed_graph_meta(con)
    bump_schema(
        con,
        artifact="graph",
        new_version="1.1.0",
        min_reader="1.0.0",
        min_writer="1.1.0",
        notes="+valid_from",
    )
    row = con.execute(
        "SELECT schema_version, notes FROM corpus_schema_meta WHERE artifact='graph'"
    ).fetchone()
    con.close()
    assert row[0] == "1.1.0"
    assert "valid_from" in row[1]


def test_graph_schema_sql_seeds_meta(tmp_path, monkeypatch):
    """The canonical graph_schema.sql, when applied, seeds the meta row
    (caught-red-handed: before this change, running schema_sql gave a
    DB with no meta, breaking preflight)."""
    monkeypatch.setenv("CORPUS_ROOT", str(tmp_path / "corpus"))
    # Use index._connect which applies the canonical schema_sql.
    from corpus_core import index

    con = index._connect()
    try:
        row = con.execute(
            "SELECT schema_version FROM corpus_schema_meta WHERE artifact='graph'"
        ).fetchone()
    finally:
        con.close()
    assert row is not None
    assert row[0] == GRAPH_SCHEMA_VERSION


def test_outbox_schema_seeds_meta():
    """outbox_schema() DDL includes meta seed."""
    from corpus_core.outbox import outbox_schema

    sql = outbox_schema((("verdict_id", "VARCHAR"),))
    assert "corpus_schema_meta" in sql
    assert OUTBOX_SCHEMA_VERSION in sql
