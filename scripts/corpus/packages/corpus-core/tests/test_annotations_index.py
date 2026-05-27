"""Phase 2: annotations table in graph.duckdb — projection of annotations.jsonl."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from corpus_core.annotate import annotate
from corpus_core.index import rebuild_annotations_index
from corpus_core.store import paper_path


SOURCE_A = "doi_10_1234_alpha"
SOURCE_B = "doi_10_1234_beta"
ACTOR = "urn:agent:service:phase2-test@0.0.1"


@pytest.fixture
def corpus_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    monkeypatch.setenv("CORPUS_ROOT", str(root))
    for sid in (SOURCE_A, SOURCE_B):
        (root / sid).mkdir()
        # metadata.json with source_type so the projection can denormalize it
        (root / sid / "metadata.json").write_text(
            json.dumps({"source_id": sid, "source_type": "paper",
                        "schema_version": "1-0-0",
                        "content_hash": "0" * 64,
                        "retrieved_at": "2026-05-11T00:00:00Z"})
        )
    return root


def _query(root: Path, sql: str, *params):
    con = duckdb.connect(str(root / "graph.duckdb"), read_only=True)
    try:
        return con.execute(sql, list(params)).fetchall()
    finally:
        con.close()


def test_annotate_writes_to_duckdb_projection(corpus_root):
    aid = annotate(
        SOURCE_A, repo="agent-infra", actor_type="service", actor_id=ACTOR,
        scope="raw_fetch",
    )
    rows = _query(corpus_root, "SELECT annotation_id, source_id, repo, scope FROM annotations")
    assert len(rows) == 1
    assert rows[0] == (aid, SOURCE_A, "agent-infra", "raw_fetch")


def test_source_type_denormalized(corpus_root):
    annotate(SOURCE_A, repo="agent-infra", actor_type="service",
             actor_id=ACTOR, scope="x")
    rows = _query(corpus_root, "SELECT source_type FROM annotations WHERE source_id = ?", SOURCE_A)
    assert rows[0][0] == "paper"


def test_query_by_repo_returns_only_matching(corpus_root):
    annotate(SOURCE_A, repo="agent-infra", actor_type="service",
             actor_id=ACTOR, scope="a1")
    annotate(SOURCE_A, repo="phenome", actor_type="service",
             actor_id=ACTOR, scope="a2")
    annotate(SOURCE_B, repo="phenome", actor_type="service",
             actor_id=ACTOR, scope="b1")
    rows = _query(corpus_root, "SELECT source_id, scope FROM annotations WHERE repo = ? ORDER BY scope",
                  "phenome")
    assert [r for r in rows] == [(SOURCE_A, "a2"), (SOURCE_B, "b1")]


def test_rebuild_is_idempotent(corpus_root):
    annotate(SOURCE_A, repo="agent-infra", actor_type="service",
             actor_id=ACTOR, scope="x")
    annotate(SOURCE_B, repo="phenome", actor_type="model",
             actor_id="urn:agent:model:test@1", scope="y")
    s1 = rebuild_annotations_index()
    s2 = rebuild_annotations_index()
    assert s1 == s2
    rows = _query(corpus_root, "SELECT COUNT(*) FROM annotations")
    assert rows[0][0] == 2


def test_jsonl_is_truth_for_rebuild(corpus_root):
    """Wipe a row from the DB manually; rebuild restores it from JSONL."""
    aid = annotate(SOURCE_A, repo="agent-infra", actor_type="service",
                   actor_id=ACTOR, scope="x")
    # Wipe out the row directly
    con = duckdb.connect(str(corpus_root / "graph.duckdb"))
    con.execute("DELETE FROM annotations")
    con.close()
    rows = _query(corpus_root, "SELECT COUNT(*) FROM annotations")
    assert rows[0][0] == 0
    # Rebuild from JSONL truth
    stats = rebuild_annotations_index()
    assert stats["rows_written"] == 1
    rows = _query(corpus_root, "SELECT annotation_id FROM annotations")
    assert rows[0][0] == aid


def test_close_review_finding_3_rebuild_is_atomic(corpus_root, monkeypatch):
    """Plan-close review #3 (CONFIRMED): rebuild_annotations_index is
    now wrapped in a transaction. If iteration raises mid-rebuild, the
    prior projection survives (vs. pre-fix: DELETE landed first, leaving
    the table empty until the next rebuild).

    Caught-red-handed: monkeypatch the iter helper to raise mid-way;
    assert the existing rows are preserved.
    """
    from corpus_core import index as idx_mod
    aid = annotate(SOURCE_A, repo="agent-infra", actor_type="service",
                   actor_id=ACTOR, scope="x")
    # Confirm baseline.
    rows = _query(corpus_root, "SELECT annotation_id FROM annotations")
    assert rows[0][0] == aid

    # Force a failure mid-rebuild by monkeypatching _iter_jsonl to raise.
    def _boom(_path):
        raise RuntimeError("synthetic mid-rebuild failure")
    monkeypatch.setattr(idx_mod, "_iter_jsonl", _boom)

    with pytest.raises(RuntimeError, match="synthetic"):
        idx_mod.rebuild_annotations_index()

    # CRH: pre-fix this assertion would FAIL — DELETE landed first, the
    # row would be gone. With BEGIN/ROLLBACK, the original row survives.
    rows = _query(corpus_root, "SELECT annotation_id FROM annotations")
    assert len(rows) == 1
    assert rows[0][0] == aid


def test_idempotent_annotate_does_not_double_insert(corpus_root):
    a1 = annotate(SOURCE_A, repo="agent-infra", actor_type="service",
                  actor_id=ACTOR, scope="x")
    a2 = annotate(SOURCE_A, repo="agent-infra", actor_type="service",
                  actor_id=ACTOR, scope="x")
    assert a1 == a2
    rows = _query(corpus_root, "SELECT COUNT(*) FROM annotations")
    assert rows[0][0] == 1
