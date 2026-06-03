"""Phase A — bitemporal valid_from + chain-aware annotations_current view.

Caught-red-handed tests for the idempotency invariant and the chain
semantics. If a future change accidentally adds valid_from to
annotation_stable_tuple, test_valid_from_does_not_mutate_annotation_id
fails. If the view incorrectly collapses multi-leaf branches into one,
test_chain_returns_only_leaves fails.
"""
from __future__ import annotations

import duckdb
import pytest
from datetime import datetime, timezone

from corpus_core.annotate import annotate
from corpus_core.store import CorpusStore


def _ann_id_for_paper(store: CorpusStore, paper: str) -> str:
    return annotate(
        f"doi_test_{paper}",
        store=store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:bitemporal-test",
        scope="extract",
        output_uri=f"phenome://record/{paper}",
        output_hash=f"deadbeef0000{paper}".ljust(16, "f"),
        prompt_template_hash=f"cafebabe0000{paper}".ljust(16, "f"),
    )


def test_valid_from_does_not_mutate_annotation_id(corpus_root, corpus_store):
    """Idempotency invariant — load-bearing. If valid_from accidentally
    leaks into annotation_stable_tuple, this test fails immediately."""
    id_no_vf = annotate(
        "doi_test_idempotency",
        store=corpus_store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:foo",
        scope="extract",
        output_uri="phenome://record/x",
        output_hash="deadbeef00000000",
        prompt_template_hash="cafebabe00000000",
    )
    # Second call with a DIFFERENT valid_from but same stable_tuple:
    # idempotency check should fire, no second JSONL row written, same id.
    id_with_vf = annotate(
        "doi_test_idempotency",
        store=corpus_store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:foo",
        scope="extract",
        output_uri="phenome://record/x",
        output_hash="deadbeef00000000",
        prompt_template_hash="cafebabe00000000",
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    assert id_no_vf == id_with_vf

    # Annotations JSONL should have ONE row (idempotency).
    jsonl = corpus_root / "doi_test_idempotency" / "annotations.jsonl"
    assert sum(1 for _ in jsonl.open()) == 1


def test_valid_from_defaults_to_asserted_at(corpus_root, corpus_store):
    """When the caller doesn't pass valid_from, the JSONL record gets
    the writer's asserted_at as the bitemporal default."""
    annotate(
        "doi_test_default_vf",
        store=corpus_store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:foo",
        scope="extract",
        output_uri="phenome://record/y",
        output_hash="deadbeef00000001",
        prompt_template_hash="cafebabe00000001",
    )
    import json
    jsonl = corpus_root / "doi_test_default_vf" / "annotations.jsonl"
    rec = json.loads(jsonl.read_text().strip())
    assert "valid_from" in rec
    assert rec["valid_from"] == rec["asserted_at"]


def test_explicit_valid_from_lands_in_jsonl(corpus_root, corpus_store):
    annotate(
        "doi_test_explicit_vf",
        store=corpus_store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:foo",
        scope="extract",
        output_uri="phenome://record/z",
        output_hash="deadbeef00000002",
        prompt_template_hash="cafebabe00000002",
        valid_from="2026-01-15T08:00:00Z",
    )
    import json
    jsonl = corpus_root / "doi_test_explicit_vf" / "annotations.jsonl"
    rec = json.loads(jsonl.read_text().strip())
    assert rec["valid_from"] == "2026-01-15T08:00:00Z"


def test_valid_to_kwarg_is_rejected(corpus_root, corpus_store):
    """Design enforcement: pure-append-only has NO valid_to.
    Supersession is its own annotation event."""
    with pytest.raises(TypeError):
        annotate(  # type: ignore[call-arg]
            "doi_test_no_valid_to",
            store=corpus_store,
            repo="phenome",
            actor_type="service",
            actor_id="urn:agent:service:foo",
            scope="extract",
            output_uri="phenome://record/n",
            output_hash="deadbeef00000003",
            prompt_template_hash="cafebabe00000003",
            valid_to="2026-01-01T00:00:00Z",
        )


def test_chain_returns_only_leaves(corpus_root, corpus_store):
    """annotations_current excludes annotations that have been
    superseded by another annotation. Multi-leaf branches return both
    leaves (operator UX, not constraint violation)."""
    a_id = annotate(
        "doi_test_chain",
        store=corpus_store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:foo",
        scope="extract",
        output_uri="phenome://record/chain-a",
        output_hash="deadbeef0a000000",
        prompt_template_hash="cafebabe00000010",
    )
    b_id = annotate(
        "doi_test_chain",
        store=corpus_store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:foo",
        scope="extract",
        output_uri="phenome://record/chain-b",
        output_hash="deadbeef0b000000",
        prompt_template_hash="cafebabe00000010",
        supersedes_annotation_id=a_id,
    )

    con = duckdb.connect(str(corpus_store.graph_db_path()), read_only=True)
    try:
        all_rows = [r[0] for r in con.execute(
            "SELECT annotation_id FROM annotations WHERE source_id = ?",
            ["doi_test_chain"],
        ).fetchall()]
        current_rows = [r[0] for r in con.execute(
            "SELECT annotation_id FROM annotations_current WHERE source_id = ?",
            ["doi_test_chain"],
        ).fetchall()]
    finally:
        con.close()

    assert set(all_rows) == {a_id, b_id}
    assert current_rows == [b_id]  # a is superseded; only b is current


def test_chain_multi_leaf_returns_all_leaves(corpus_root, corpus_store):
    """v6 critique #7: two annotations LEGITIMATELY superseding the same
    prior is a curation prompt, not a DB violation. View returns both."""
    a_id = annotate(
        "doi_test_multileaf",
        store=corpus_store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:foo",
        scope="extract",
        output_uri="phenome://record/ml-a",
        output_hash="deadbeef0a100000",
        prompt_template_hash="cafebabe00000020",
    )
    b_id = annotate(
        "doi_test_multileaf",
        store=corpus_store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:foo",
        scope="extract",
        output_uri="phenome://record/ml-b",
        output_hash="deadbeef0b100000",
        prompt_template_hash="cafebabe00000020",
        supersedes_annotation_id=a_id,
    )
    c_id = annotate(
        "doi_test_multileaf",
        store=corpus_store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:foo",
        scope="extract",
        output_uri="phenome://record/ml-c",
        output_hash="deadbeef0c100000",
        prompt_template_hash="cafebabe00000020",
        supersedes_annotation_id=a_id,
    )

    con = duckdb.connect(str(corpus_store.graph_db_path()), read_only=True)
    try:
        current_rows = sorted(r[0] for r in con.execute(
            "SELECT annotation_id FROM annotations_current WHERE source_id = ?",
            ["doi_test_multileaf"],
        ).fetchall())
    finally:
        con.close()
    assert current_rows == sorted([b_id, c_id])  # both leaves; a is not


def test_physical_table_remains_insertable(corpus_root, corpus_store):
    """rebuild_annotations_index still INSERTs into the physical table;
    views are not writable in DuckDB. Sanity check that the view's
    existence didn't break the writer path."""
    annotate(
        "doi_test_writable",
        store=corpus_store,
        repo="phenome",
        actor_type="service",
        actor_id="urn:agent:service:foo",
        scope="extract",
        output_uri="phenome://record/w",
        output_hash="deadbeef00000004",
        prompt_template_hash="cafebabe00000004",
    )
    from corpus_core.index import rebuild_annotations_index
    stats = rebuild_annotations_index(store=corpus_store)
    assert stats["sources_scanned"] >= 1
    assert stats["rows_written"] >= 1
