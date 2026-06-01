"""Cross-repo outbox primitive — schema, lifecycle migration, drain loop.

The outbox is the substrate-v2 cross-attestation pattern: per-repo
gateways INSERT annotation intent rows; this module's drain flushes
them to corpus filesystem via corpus_core.annotate.

drain() takes a path (not a connection): it manages its own RO + RW
connection pair to stay lock-friendly with concurrent writers. Tests
follow the pattern: setup-con → close → drain(path).

See: corpus_core/outbox.py;
decisions/2026-05-26-cross-attestation-substrate-v2.md.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pytest

from corpus_core.outbox import (
    OUTBOX_TABLE_NAME,
    DrainStats,
    abandoned_count,
    drain,
    ensure_lifecycle_columns,
    outbox_schema,
)


@pytest.fixture
def corpus_root(monkeypatch, tmp_path) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    monkeypatch.setenv("CORPUS_ROOT", str(root))
    return root


@pytest.fixture
def outbox_path(tmp_path: Path) -> Path:
    """Greenfield outbox DB with the verdict-shaped schema applied.
    Tests open their own writer-conn for setup INSERTs (and MUST close it
    before calling drain — drain opens its own RW conn briefly)."""
    path = tmp_path / "outbox.duckdb"
    con = duckdb.connect(str(path))
    try:
        con.execute(outbox_schema((("verdict_id", "VARCHAR"),)))
    finally:
        con.close()
    return path


def _enqueue(
    path: Path,
    *,
    verdict_id: str,
    canonical_source_id: str,
    output_uri: str | None = None,
    output_hash: str | None = None,
    annotation_status: str = "active",
    supersedes_annotation_id: str | None = None,
) -> None:
    """Open a transient writer-conn, INSERT one outbox row, close.
    Mirrors what a per-repo gateway would do inside its transaction —
    minus the surrounding domain write."""
    con = duckdb.connect(str(path))
    try:
        con.execute(
            f"""
            INSERT INTO {OUTBOX_TABLE_NAME}
                (verdict_id, canonical_source_id, actor_type, actor_id,
                 output_uri, output_hash, prompt_template_hash, asserted_at,
                 annotation_status, supersedes_annotation_id)
            VALUES (?, ?, 'service', 'urn:agent:service:test',
                    ?, ?, NULL, ?, ?, ?)
            ON CONFLICT (verdict_id, canonical_source_id) DO NOTHING
            """,
            [
                verdict_id,
                canonical_source_id,
                output_uri or f"genomics://verdicts/{verdict_id}",
                output_hash or "deadbeef" * 4,
                datetime.now(timezone.utc),
                annotation_status,
                supersedes_annotation_id,
            ],
        )
    finally:
        con.close()


def _read_outbox(path: Path, *, status: str | None = None) -> list[tuple]:
    con = duckdb.connect(str(path), read_only=True)
    try:
        if status is None:
            return con.execute(f"SELECT * FROM {OUTBOX_TABLE_NAME}").fetchall()
        return con.execute(
            f"SELECT retry_count, status, last_error FROM {OUTBOX_TABLE_NAME} "
            "WHERE status = ?",
            [status],
        ).fetchall()
    finally:
        con.close()


def _outbox_count(path: Path) -> int:
    con = duckdb.connect(str(path), read_only=True)
    try:
        return int(con.execute(f"SELECT COUNT(*) FROM {OUTBOX_TABLE_NAME}").fetchone()[0])
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_outbox_schema_includes_lifecycle_columns_inline():
    """Greenfield schema declares annotation_status + supersedes_annotation_id
    inline — no separate ensure_lifecycle_columns call needed for fresh
    outboxes."""
    ddl = outbox_schema((("cert_event_id", "VARCHAR"),))
    assert "annotation_status" in ddl
    assert "supersedes_annotation_id" in ddl
    assert "PRIMARY KEY (cert_event_id, canonical_source_id)" in ddl


def test_outbox_schema_supports_alternate_natural_key():
    """Schema is parametric on the natural key — phenome (cert_event_id),
    intel (contradiction_event_id), genomics (verdict_id) all work."""
    ddl = outbox_schema(
        (("contradiction_event_id", "VARCHAR"), ("schema_version", "INTEGER"))
    )
    assert "contradiction_event_id VARCHAR NOT NULL" in ddl
    assert "schema_version" in ddl
    assert "PRIMARY KEY (contradiction_event_id, schema_version, canonical_source_id)" in ddl


def test_outbox_schema_rejects_empty_natural_key():
    with pytest.raises(ValueError, match="natural_key"):
        outbox_schema(())


# ---------------------------------------------------------------------------
# Lifecycle migration
# ---------------------------------------------------------------------------


def test_ensure_lifecycle_columns_idempotent_on_existing(outbox_path):
    """Greenfield schema already has the columns; calling ensure is a no-op."""
    con = duckdb.connect(str(outbox_path))
    try:
        before = {r[1] for r in con.execute(
            f"PRAGMA table_info('{OUTBOX_TABLE_NAME}')"
        ).fetchall()}
        ensure_lifecycle_columns(con)
        after = {r[1] for r in con.execute(
            f"PRAGMA table_info('{OUTBOX_TABLE_NAME}')"
        ).fetchall()}
    finally:
        con.close()
    assert before == after


def test_ensure_lifecycle_columns_adds_on_legacy(tmp_path):
    """A pre-lifecycle outbox (no annotation_status, no supersedes pointer)
    gets the columns added with default annotation_status backfilled."""
    con = duckdb.connect(str(tmp_path / "legacy.duckdb"))
    try:
        # Simulate the pre-2026-05-27 genomics shape — no lifecycle cols.
        con.execute(
            f"""
            CREATE TABLE {OUTBOX_TABLE_NAME} (
                verdict_id VARCHAR PRIMARY KEY,
                canonical_source_id VARCHAR NOT NULL,
                actor_type VARCHAR NOT NULL,
                actor_id VARCHAR NOT NULL,
                output_uri VARCHAR NOT NULL,
                output_hash VARCHAR,
                prompt_template_hash VARCHAR,
                asserted_at TIMESTAMP NOT NULL,
                queued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_error VARCHAR,
                status VARCHAR NOT NULL DEFAULT 'pending'
            )
            """
        )
        con.execute(
            f"""INSERT INTO {OUTBOX_TABLE_NAME} VALUES
                ('v1', 'doi_x', 'service', 'urn:agent:service:t',
                 'g://v/v1', 'deadbeef' || 'deadbeef' || 'deadbeef' || 'deadbeef',
                 NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, NULL, 'pending')"""
        )

        ensure_lifecycle_columns(con)

        cols = {r[1] for r in con.execute(
            f"PRAGMA table_info('{OUTBOX_TABLE_NAME}')"
        ).fetchall()}
        assert "annotation_status" in cols
        assert "supersedes_annotation_id" in cols
        # Existing row backfilled to 'active' (not NULL).
        row = con.execute(
            f"SELECT annotation_status, supersedes_annotation_id "
            f"FROM {OUTBOX_TABLE_NAME} WHERE verdict_id='v1'"
        ).fetchone()
        assert row == ("active", None)
    finally:
        con.close()


def test_ensure_lifecycle_columns_safe_when_table_missing(tmp_path):
    """No outbox table → no-op, no exception."""
    con = duckdb.connect(str(tmp_path / "empty.duckdb"))
    try:
        ensure_lifecycle_columns(con)  # must not raise
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Drain
# ---------------------------------------------------------------------------


def test_drain_happy_path_flushes_and_deletes(outbox_path, corpus_root):
    """Pending row → corpus annotation written → outbox row deleted."""
    _enqueue(outbox_path, verdict_id="v1", canonical_source_id="doi_10_x")
    stats = drain(
        outbox_path, repo="genomics", scope="verdict",
        natural_key_cols=("verdict_id",),
    )
    assert stats == DrainStats(flushed=1, retried=0, abandoned=0)
    assert _outbox_count(outbox_path) == 0
    jsonl = corpus_root / "doi_10_x" / "annotations.jsonl"
    assert jsonl.exists()
    ann = json.loads(jsonl.read_text().strip())
    assert ann["scope"] == "verdict"
    assert ann["status"] == "active"


def test_drain_rejects_non_dict_relation_json(outbox_path, corpus_root):
    """A non-object relation_json ('[…]', '"x"') is a per-row data error
    (retry/abandon), NOT a batch crash (close-review: cross-model — a list
    would otherwise reach annotate() and AttributeError on .get())."""
    (corpus_root / "doi_bad").mkdir()
    con = duckdb.connect(str(outbox_path))
    try:
        con.execute(
            f"INSERT INTO {OUTBOX_TABLE_NAME} "
            "(verdict_id, canonical_source_id, actor_type, actor_id, output_uri, "
            " output_hash, prompt_template_hash, asserted_at, annotation_status, relation_json) "
            "VALUES ('rel_bad','doi_bad','service','urn:agent:service:test',"
            " 'genomics://verdicts/bad', NULL, NULL, ?, 'active', '[1,2]')",
            [datetime.now(timezone.utc)],
        )
    finally:
        con.close()
    stats = drain(outbox_path, repo="genomics", scope="verdict", natural_key_cols=("verdict_id",))
    assert stats.flushed == 0 and stats.retried == 1  # handled, not crashed
    pending = _read_outbox(outbox_path, status="pending")
    assert pending and "must be a JSON object" in (pending[0][2] or "")


def test_drain_passes_lifecycle_state_through(outbox_path, corpus_root):
    """annotation_status + supersedes_annotation_id propagate from row to
    corpus annotation — the lifecycle state is preserved end-to-end."""
    _enqueue(
        outbox_path, verdict_id="v_new", canonical_source_id="doi_xyz",
        supersedes_annotation_id="ann_deadbeef12345678",
    )
    drain(
        outbox_path, repo="genomics", scope="verdict",
        natural_key_cols=("verdict_id",),
    )
    jsonl = corpus_root / "doi_xyz" / "annotations.jsonl"
    ann = json.loads(jsonl.read_text().strip())
    assert ann["supersedes_annotation_id"] == "ann_deadbeef12345678"


def test_drain_alternate_natural_key_works(tmp_path, corpus_root):
    """Drain on a non-verdict shape (cert_event_id) — same API, different key."""
    path = tmp_path / "cert.duckdb"
    con = duckdb.connect(str(path))
    try:
        con.execute(outbox_schema((("cert_event_id", "VARCHAR"),)))
        con.execute(
            f"""
            INSERT INTO {OUTBOX_TABLE_NAME}
                (cert_event_id, canonical_source_id, actor_type, actor_id,
                 output_uri, output_hash, prompt_template_hash, asserted_at)
            VALUES ('ce_001', 'doi_x', 'service', 'urn:agent:service:t',
                    'phenome://cert_events/ce_001', 'deadbeef' || 'deadbeef',
                    NULL, CURRENT_TIMESTAMP)
            """
        )
    finally:
        con.close()
    stats = drain(
        path, repo="phenome", scope="cert_event",
        natural_key_cols=("cert_event_id",),
    )
    assert stats.flushed == 1
    ann = json.loads(
        (corpus_root / "doi_x" / "annotations.jsonl").read_text().strip()
    )
    assert ann["scope"] == "cert_event"
    idem = json.loads(ann["idempotency_key"])
    assert idem["repo"] == "phenome"


def test_drain_failure_increments_retry(outbox_path, corpus_root, monkeypatch):
    """Operational failure bumps retry_count + records last_error;
    row stays 'pending' for the next drain pass."""
    from corpus_core import outbox as outbox_mod

    def _boom(*_a, **_kw):
        raise OSError("simulated FS failure")

    monkeypatch.setattr(outbox_mod, "_annotate", _boom)
    _enqueue(outbox_path, verdict_id="v1", canonical_source_id="doi_x")
    stats = drain(
        outbox_path, repo="genomics", scope="verdict",
        natural_key_cols=("verdict_id",),
    )
    assert stats == DrainStats(flushed=0, retried=1, abandoned=0)
    rows = _read_outbox(outbox_path, status="pending")
    assert len(rows) == 1
    assert rows[0][0] == 1
    assert rows[0][1] == "pending"
    assert "simulated FS failure" in rows[0][2]


def test_drain_abandons_after_three_retries(outbox_path, corpus_root, monkeypatch):
    """Third failure flips status='abandoned'; abandoned rows excluded
    from the next drain (only 'pending' is read)."""
    from corpus_core import outbox as outbox_mod

    def _boom(*_a, **_kw):
        raise OSError("persistent")

    monkeypatch.setattr(outbox_mod, "_annotate", _boom)
    _enqueue(outbox_path, verdict_id="v1", canonical_source_id="doi_x")
    drain(outbox_path, repo="genomics", scope="verdict",
          natural_key_cols=("verdict_id",))
    drain(outbox_path, repo="genomics", scope="verdict",
          natural_key_cols=("verdict_id",))
    final = drain(outbox_path, repo="genomics", scope="verdict",
                  natural_key_cols=("verdict_id",))
    assert final.abandoned == 1
    assert abandoned_count(outbox_path) == 1
    again = drain(outbox_path, repo="genomics", scope="verdict",
                  natural_key_cols=("verdict_id",))
    assert again == DrainStats()


def test_drain_idempotent_on_corpus_side(outbox_path, corpus_root):
    """Two enqueue+drain cycles for the same (verdict, source) produce ONE
    annotation in corpus (stable_tuple idempotency in corpus_core.annotate).
    Outbox composite PK + corpus idempotency together prevent duplicates."""
    _enqueue(outbox_path, verdict_id="v1", canonical_source_id="doi_x")
    drain(outbox_path, repo="genomics", scope="verdict",
          natural_key_cols=("verdict_id",))
    _enqueue(outbox_path, verdict_id="v1", canonical_source_id="doi_x")
    drain(outbox_path, repo="genomics", scope="verdict",
          natural_key_cols=("verdict_id",))
    lines = [
        ln for ln in (corpus_root / "doi_x" / "annotations.jsonl").read_text().splitlines()
        if ln.strip()
    ]
    assert len(lines) == 1, "stable_tuple idempotency must collapse re-emit"


def test_drain_empty_outbox_is_noop(outbox_path):
    """Drain on an empty outbox returns zero counts; no exceptions."""
    stats = drain(outbox_path, repo="genomics", scope="verdict",
                  natural_key_cols=("verdict_id",))
    assert stats == DrainStats()


def test_drain_missing_db_is_noop(tmp_path):
    """Drain against a non-existent DB returns zero counts silently —
    safe steady-state for a new repo that hasn't enqueued anything yet."""
    stats = drain(tmp_path / "missing.duckdb", repo="genomics", scope="verdict",
                  natural_key_cols=("verdict_id",))
    assert stats == DrainStats()


def test_drain_rejects_empty_natural_key(outbox_path):
    with pytest.raises(ValueError, match="natural_key_cols"):
        drain(outbox_path, repo="genomics", scope="verdict", natural_key_cols=())


def test_abandoned_count_on_missing_table(tmp_path):
    """abandoned_count returns 0 on a DB without the outbox (graceful)."""
    path = tmp_path / "empty.duckdb"
    duckdb.connect(str(path)).close()
    assert abandoned_count(path) == 0


def test_abandoned_count_on_missing_db(tmp_path):
    """abandoned_count returns 0 when the DB file doesn't exist."""
    assert abandoned_count(tmp_path / "never.duckdb") == 0


# ── enqueue_relation: the validated front door ────────────────────────────
from corpus_core.outbox import enqueue_relation  # noqa: E402
from corpus_core.annotate import AnnotationSchemaError  # noqa: E402

_GOOD_REL = {
    "relation_class": "support",
    "subject_refs": ["repo:genomics:GENE:MONDO:1"],
    "object_refs": ["repo:phenome:assertion:abc"],
    "detector": "genomic-phenotype-linker:v1",
    "kind": "exact",
    "grade_weight": 0.9,
    "home_verdict_id": "GENE:MONDO:1",
}


def _outbox_con():
    con = duckdb.connect(":memory:")
    con.execute(outbox_schema((("cert_event_id", "VARCHAR"),)))
    return con


def test_enqueue_relation_inserts_then_idempotent():
    con = _outbox_con()
    assert enqueue_relation(
        con, relation=dict(_GOOD_REL), natural_key={"cert_event_id": "relpair_1"},
        canonical_source_id="internal_phenome", actor_type="model",
        actor_id="urn:agent:model:test", output_uri="x://1",
    ) is True
    # same natural key + source → ON CONFLICT DO NOTHING
    assert enqueue_relation(
        con, relation=dict(_GOOD_REL), natural_key={"cert_event_id": "relpair_1"},
        canonical_source_id="internal_phenome", actor_type="model",
        actor_id="urn:agent:model:test",
    ) is False
    row = con.execute(
        "SELECT actor_type, status, annotation_status, relation_json "
        "FROM pending_corpus_attestations"
    ).fetchone()
    assert row[0] == "model" and row[1] == "pending" and row[2] == "active"
    body = json.loads(row[3])
    assert body["relation_class"] == "support"
    assert "relation_id" not in body  # derived at drain, never enqueued


def test_enqueue_relation_rejects_malformed_eagerly():
    con = _outbox_con()
    # the exact bug class this front door exists to catch: an extra key that the
    # closed corpus schema rejects — caught HERE, not hours later at drain.
    with pytest.raises(AnnotationSchemaError, match="Additional properties"):
        enqueue_relation(
            con, relation={**_GOOD_REL, "evidence": {"x": 1}},
            natural_key={"cert_event_id": "relpair_2"},
            canonical_source_id="internal_phenome", actor_type="model",
            actor_id="urn:agent:model:test",
        )
    # bad relation_class enum
    with pytest.raises(AnnotationSchemaError):
        enqueue_relation(
            con, relation={**_GOOD_REL, "relation_class": "endorses"},
            natural_key={"cert_event_id": "relpair_3"},
            canonical_source_id="internal_phenome", actor_type="model",
            actor_id="urn:agent:model:test",
        )
    # caller must not pre-set relation_id (substrate derives it)
    with pytest.raises(AnnotationSchemaError, match="relation_id"):
        enqueue_relation(
            con, relation={**_GOOD_REL, "relation_id": "rel_deadbeef"},
            natural_key={"cert_event_id": "relpair_4"},
            canonical_source_id="internal_phenome", actor_type="model",
            actor_id="urn:agent:model:test",
        )
    # nothing was inserted by the rejected calls
    assert con.execute("SELECT count(*) FROM pending_corpus_attestations").fetchone()[0] == 0


def test_enqueue_relation_retraction_lifecycle():
    con = _outbox_con()
    enqueue_relation(
        con, relation=dict(_GOOD_REL), natural_key={"cert_event_id": "relpair_retract_1"},
        canonical_source_id="internal_phenome", actor_type="model",
        actor_id="urn:agent:model:test", output_uri="x://retract/1",
        supersedes_annotation_id="ann_prior", annotation_status="retracted",
    )
    row = con.execute(
        "SELECT annotation_status, supersedes_annotation_id "
        "FROM pending_corpus_attestations"
    ).fetchone()
    assert row == ("retracted", "ann_prior")
