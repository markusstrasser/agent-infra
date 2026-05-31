"""Read-loop: `active_annotations_for_source` surfaces verdicts (especially
retractions) so an agent SEES what's already attested about a source before
acting on it. This closes the READ half of the attestation ledger — the half
that was never wired (substrate-v1 ritual got ~0 read invocations in 9 months,
which was a wiring gap, not a value gap). corpus_lookup rides this so the verdict
travels with the lookup an agent already does.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from corpus_core.annotate import annotate
from corpus_core.index import active_annotations_for_source

SOURCE = "doi_10_9999_readloop"
ACTOR = "urn:agent:service:readloop-test@1"


@pytest.fixture
def corpus_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    monkeypatch.setenv("CORPUS_ROOT", str(root))
    (root / SOURCE).mkdir()
    (root / SOURCE / "metadata.json").write_text(
        json.dumps(
            {
                "source_id": SOURCE,
                "source_type": "paper",
                "schema_version": "1-0-0",
                "content_hash": "0" * 64,
                "retrieved_at": "2026-05-31T00:00:00Z",
            }
        )
    )
    return root


def _db(root: Path) -> Path:
    return root / "graph.duckdb"


def test_empty_when_no_annotations(corpus_root):
    assert active_annotations_for_source(SOURCE, db_path=_db(corpus_root)) == []


def test_surfaces_active_verdict(corpus_root):
    annotate(
        SOURCE, repo="genomics", actor_type="service", actor_id=ACTOR,
        scope="verdict", output_uri="genomics://verdicts/v1",
    )
    out = active_annotations_for_source(SOURCE, db_path=_db(corpus_root))
    assert len(out) == 1
    assert out[0]["repo"] == "genomics"
    assert out[0]["status"] == "active"
    assert out[0]["output_uri"] == "genomics://verdicts/v1"


def test_surfaces_retraction(corpus_root):
    # Load-bearing case: an agent must SEE a retracted verdict before reusing the claim.
    annotate(
        SOURCE, repo="genomics", actor_type="service", actor_id=ACTOR,
        scope="verdict", output_uri="genomics://verdicts/v1", status="retracted",
    )
    out = active_annotations_for_source(SOURCE, db_path=_db(corpus_root))
    retracted = [a for a in out if a["status"] == "retracted"]
    assert retracted, "read loop must surface the retracted verdict"
    assert retracted[0]["output_uri"] == "genomics://verdicts/v1"


def test_fail_soft_when_graph_missing(tmp_path):
    assert active_annotations_for_source(SOURCE, db_path=tmp_path / "nope.duckdb") == []
