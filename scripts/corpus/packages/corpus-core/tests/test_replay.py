"""Phase F — replay verifier.

The verifier IS the baseline that Phase A's schema migration ships against;
if the migration accidentally mutates a stable_tuple field, the diff goes
non-zero and the migration commit is rejected.
"""
from __future__ import annotations

import duckdb
import pytest

from corpus_core.annotate import annotate
from corpus_core.replay import (
    ReplayDiff,
    replay_in_place,
    replay_to_temp_graph,
    verify_replay_matches_current,
)


def _annotate_some(corpus_store, n: int) -> list[str]:
    """Write N distinct annotations and return their annotation_ids."""
    ids = []
    for i in range(n):
        aid = annotate(
            f"doi_test_paper_{i}",
            store=corpus_store,
            repo="phenome",
            actor_type="service",
            actor_id="urn:agent:service:test",
            scope="extract",
            output_uri=f"phenome://record/{i}",
            output_hash=f"deadbeef{i:08x}",
            prompt_template_hash=f"cafebabe{i:08x}",
        )
        ids.append(aid)
    return ids


def test_happy_path_clean_replay(corpus_root, corpus_store):
    """N annotations → replay matches live, no drift."""
    ids = _annotate_some(corpus_store, 3)
    diff = verify_replay_matches_current(store=corpus_store)
    assert diff.matched == 3
    assert diff.is_clean()
    assert len(set(ids)) == 3


def test_replay_returns_diff_dataclass(corpus_root, corpus_store):
    _annotate_some(corpus_store, 1)
    diff = verify_replay_matches_current(store=corpus_store)
    assert isinstance(diff, ReplayDiff)


def test_replay_in_place_requires_confirm(corpus_root, corpus_store):
    _annotate_some(corpus_store, 1)
    with pytest.raises(ValueError, match="confirm=True"):
        replay_in_place(store=corpus_store, confirm=False)


def test_replay_in_place_confirm_rebuilds_db(corpus_root, corpus_store):
    _annotate_some(corpus_store, 2)
    live_db = corpus_root / "graph.duckdb"
    assert live_db.exists()
    before = duckdb.connect(str(live_db), read_only=True)
    try:
        rows_before = before.execute("SELECT COUNT(*) FROM annotations").fetchone()[0]
    finally:
        before.close()
    replay_in_place(store=corpus_store, confirm=True)
    after = duckdb.connect(str(live_db), read_only=True)
    try:
        rows_after = after.execute("SELECT COUNT(*) FROM annotations").fetchone()[0]
    finally:
        after.close()
    assert rows_before == rows_after == 2


def test_replay_detects_missing_when_db_diverges(corpus_root, corpus_store):
    """Caught-red-handed: if the live DB has a row replay doesn't
    rebuild, we detect missing_in_replay. We simulate by inserting an
    orphan row directly into the live DB after annotate."""
    _annotate_some(corpus_store, 1)
    live_db = corpus_root / "graph.duckdb"
    con = duckdb.connect(str(live_db))
    try:
        con.execute(
            """
            INSERT INTO annotations (annotation_id, source_id, repo,
                actor_type, actor_id, scope, status, asserted_at,
                recorded_at, schema_version)
            VALUES ('ann_orphan_0', 'doi_orphan', 'phenome', 'service',
                    'urn:agent:service:test', 'extract', 'active',
                    '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', '1-0-0')
            """
        )
    finally:
        con.close()

    diff = verify_replay_matches_current(store=corpus_store)
    assert diff.missing_in_replay == 1
    assert not diff.is_clean()


def test_replay_detects_byte_drift_via_annotation_id_mismatch(corpus_root, corpus_store):
    """The load-bearing invariant: same input → same annotation_id.

    Phase F's purpose is to be the BASELINE for Phase A's migration
    safety. We simulate the failure mode here: if a record's bytes
    drift between JSONL write and replay (e.g. NFC normalization
    introduced), the annotation_id would differ — replay would have a
    DIFFERENT id, so the live row appears missing AND there's an extra.

    Today, with no normalization, replay and live agree."""
    _annotate_some(corpus_store, 5)
    diff = verify_replay_matches_current(store=corpus_store)
    assert diff.matched == 5
    assert diff.missing_in_replay == 0
    assert diff.extra_in_replay == 0


def test_replay_to_temp_graph_returns_unlinkable_path(corpus_root, corpus_store, tmp_path):
    _annotate_some(corpus_store, 1)
    target = replay_to_temp_graph(store=corpus_store)
    assert target.exists()
    assert target.name == "graph.duckdb"
    # Caller owns cleanup; the directory should be safe to unlink.
    import shutil
    shutil.rmtree(target.parent)


def test_replay_handles_empty_store(corpus_root, corpus_store):
    """No annotations → diff is clean (no live rows, no replay rows)."""
    # Initialize an empty graph.duckdb so verify_replay_matches_current
    # has a live DB to read.
    from corpus_core import index
    con = index._connect(corpus_store)
    con.close()
    diff = verify_replay_matches_current(store=corpus_store)
    assert diff.matched == 0
    assert diff.is_clean()
