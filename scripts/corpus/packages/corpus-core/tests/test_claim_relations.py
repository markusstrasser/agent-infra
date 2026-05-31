"""Epistemic core: inline claim_relation annotations + their graph.duckdb projection.

Covers the Phase-1 substrate invariants:
  - a relation rides inline on a scope='claim_relation' annotation (schema 1-0-1),
    content-addressed relation_id, single atomic append (no sidecar)
  - projection into claim_relations + claim_relation_endpoints (per-write + rebuild)
  - bidirectional discoverability: lookup by subject == by object == by anchor
  - supersession drops the prior relation from the active surface
  - retracted status is excluded from claim_relations_active
  - rebuild is idempotent and reports a health summary
  - a malformed relation line is skipped + counted, never crashes the rebuild
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from corpus_core.annotate import annotate
from corpus_core.identity import relation_content_sha
from corpus_core.index import (
    active_relations_for_source,
    rebuild_claim_relations,
)
from corpus_core.store import graph_db_path

ACTOR_ID = "urn:agent:service:test@0.0.1"
PAPER = "doi_10_1234_paperx"          # an objective corpus source (a real paper dir)
VIRTUAL = "internal_phenome"          # a virtual anchor (source-null phenome claims)


@pytest.fixture
def corpus_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    monkeypatch.setenv("CORPUS_ROOT", str(root))
    (root / PAPER).mkdir()
    (root / VIRTUAL).mkdir()
    return root


def _rel(subjects, objects, cls="refute", detector="phenome:detect:abcd1234", **extra):
    r = {
        "relation_class": cls,
        "subject_refs": subjects,
        "object_refs": objects,
        "detector": detector,
    }
    r.update(extra)
    return r


def _jsonl(corpus_root: Path, source_id: str) -> list[dict]:
    path = corpus_root / source_id / "annotations.jsonl"
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()] if path.exists() else []


def _q(sql: str, params=None):
    con = duckdb.connect(str(graph_db_path()), read_only=True)
    try:
        return con.execute(sql, params or []).fetchall()
    finally:
        con.close()


# --- inline write + record shape ---------------------------------------------


def test_relation_rides_inline_on_annotation(corpus_root):
    rel = _rel(["repo:phenome:assertion:aaaa"], [f"corpus:{PAPER}"])
    aid = annotate(
        PAPER, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
        scope="claim_relation", output_uri="phenome://contradiction_pairs/p1",
        relation=rel,
    )
    rows = _jsonl(corpus_root, PAPER)
    assert len(rows) == 1
    r = rows[0]
    # advanced to the addition schema; one atomic line carries the whole relation
    assert r["schema_version"] == "1-0-1"
    assert r["conformsTo"] == "https://schema.local/corpus/annotation/v1.0.1"
    assert r["annotation_id"] == aid
    assert "relation" in r
    # content-addressed relation_id is stamped by the substrate, not the caller
    expect_sha = relation_content_sha(
        relation_class="refute",
        subject_refs=["repo:phenome:assertion:aaaa"],
        object_refs=[f"corpus:{PAPER}"],
        detector="phenome:detect:abcd1234",
    )
    assert r["relation"]["relation_id"] == f"rel_{expect_sha[:16]}"
    assert r["result"]["hash"] == expect_sha  # output_hash drives idempotency


def test_relation_projected_to_claim_relations(corpus_root):
    annotate(
        PAPER, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
        scope="claim_relation", output_uri="phenome://contradiction_pairs/p1",
        relation=_rel(["repo:phenome:assertion:aaaa"], [f"corpus:{PAPER}"], kind="subject_scope"),
    )
    rows = _q("SELECT relation_class, kind, repo, status, anchor_source_id FROM claim_relations")
    assert len(rows) == 1
    assert rows[0] == ("refute", "subject_scope", "phenome", "active", PAPER)


def test_idempotent_same_relation(corpus_root):
    rel = _rel(["repo:phenome:assertion:aaaa"], [f"corpus:{PAPER}"])
    a1 = annotate(PAPER, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
                  scope="claim_relation", output_uri="phenome://contradiction_pairs/p1", relation=rel)
    a2 = annotate(PAPER, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
                  scope="claim_relation", output_uri="phenome://contradiction_pairs/p1", relation=rel)
    assert a1 == a2
    assert len(_jsonl(corpus_root, PAPER)) == 1
    assert len(_q("SELECT 1 FROM claim_relations")) == 1


# --- bidirectional discoverability -------------------------------------------


def test_lookup_by_subject_object_anchor(corpus_root):
    # subject = a genomics claim; object = a corpus paper; anchored at the paper.
    subj = "repo:genomics:claim:variant_registry.rs1"
    annotate(
        PAPER, repo="genomics", actor_type="model", actor_id=ACTOR_ID,
        scope="claim_relation", output_uri="genomics://verdicts/v1",
        relation=_rel([subj], [f"corpus:{PAPER}"]),
    )
    rid = _q("SELECT relation_id FROM claim_relations")[0][0]
    # the endpoint index returns the SAME relation from every participant
    by_subject = _q("SELECT relation_id FROM claim_relation_endpoints WHERE endpoint_ref = ?", [subj])
    by_object = _q("SELECT relation_id FROM claim_relation_endpoints WHERE endpoint_ref = ?", [f"corpus:{PAPER}"])
    assert {r[0] for r in by_subject} == {rid}
    assert rid in {r[0] for r in by_object}
    # the source-level read primitive finds it via the namespaced anchor/object
    found = active_relations_for_source(PAPER)
    assert len(found) == 1
    assert found[0]["relation_class"] == "refute"
    assert found[0]["repo"] == "genomics"
    assert subj in found[0]["subjects"]


def test_anchor_endpoint_present(corpus_root):
    annotate(
        VIRTUAL, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
        scope="claim_relation", output_uri="phenome://contradiction_pairs/p2",
        relation=_rel(["repo:phenome:assertion:aaaa"], ["repo:phenome:assertion:bbbb"]),
    )
    roles = {r[0] for r in _q("SELECT role FROM claim_relation_endpoints")}
    assert roles == {"subject", "object", "anchor"}
    anchor = _q("SELECT endpoint_ref FROM claim_relation_endpoints WHERE role = 'anchor'")
    assert anchor[0][0] == f"corpus:{VIRTUAL}"


# --- supersession + retraction (active-surface semantics) --------------------


def test_supersession_drops_prior_from_active(corpus_root):
    rel1 = _rel(["repo:phenome:assertion:aaaa"], ["repo:phenome:assertion:bbbb"], cls="refute")
    a1 = annotate(VIRTUAL, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
                  scope="claim_relation", output_uri="phenome://contradiction_pairs/p3@open", relation=rel1)
    # re-adjudicated to a different class → different relation; supersedes a1
    rel2 = _rel(["repo:phenome:assertion:aaaa"], ["repo:phenome:assertion:bbbb"], cls="background")
    annotate(VIRTUAL, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="phenome://contradiction_pairs/p3@resolved",
             relation=rel2, supersedes_annotation_id=a1)
    # per-write projection: only the superseding relation remains
    classes = {r[0] for r in _q("SELECT relation_class FROM claim_relations")}
    assert classes == {"background"}
    # and the rebuild agrees + counts the superseded one
    report = rebuild_claim_relations()
    assert report["relations_seen"] == 2
    assert report["relations_superseded"] == 1
    assert report["relations_active"] == 1
    assert {r[0] for r in _q("SELECT relation_class FROM claim_relations")} == {"background"}


def test_retracted_excluded_from_active(corpus_root):
    annotate(
        VIRTUAL, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
        scope="claim_relation", output_uri="phenome://contradiction_pairs/p4",
        relation=_rel(["repo:phenome:assertion:aaaa"], ["repo:phenome:assertion:bbbb"]),
        status="retracted",
    )
    assert len(_q("SELECT 1 FROM claim_relations")) == 1
    assert len(_q("SELECT 1 FROM claim_relations_active")) == 0
    assert active_relations_for_source(VIRTUAL) == []


# --- rebuild robustness ------------------------------------------------------


def test_rebuild_idempotent(corpus_root):
    annotate(PAPER, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="phenome://contradiction_pairs/p1",
             relation=_rel(["repo:phenome:assertion:aaaa"], [f"corpus:{PAPER}"]))
    r1 = rebuild_claim_relations()
    r2 = rebuild_claim_relations()
    assert r1 == r2
    assert r1["relations_active"] == 1
    assert r1["endpoints_written"] == 3  # subject + object + anchor


def test_malformed_relation_skipped_not_fatal(corpus_root):
    # a valid relation, then a hand-written bad line (missing object_refs)
    annotate(PAPER, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="phenome://contradiction_pairs/p1",
             relation=_rel(["repo:phenome:assertion:aaaa"], [f"corpus:{PAPER}"]))
    bad = {
        "annotation_id": "ann_deadbeefdeadbeef",
        "source_id": PAPER,
        "scope": "claim_relation",
        "status": "active",
        "relation": {"relation_id": "rel_0000000000000000", "relation_class": "refute",
                     "subject_refs": ["repo:phenome:assertion:zzzz"]},  # no object_refs
    }
    path = corpus_root / PAPER / "annotations.jsonl"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(bad) + "\n")
    report = rebuild_claim_relations()
    assert report["relations_seen"] == 2
    assert report["relations_malformed"] == 1
    assert report["relations_active"] == 1  # the good one still projects


def test_unresolved_participant_counted(corpus_root):
    # object references a corpus source that has no dir → flagged in the health report
    annotate(PAPER, repo="genomics", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="genomics://verdicts/v9",
             relation=_rel([f"corpus:{PAPER}"], ["corpus:doi_does_not_exist"]))
    report = rebuild_claim_relations()
    assert report["participants_unresolved"] == 1
