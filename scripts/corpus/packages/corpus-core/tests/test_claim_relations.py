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
    support_balance_for_source,
)

ACTOR_ID = "urn:agent:service:test@0.0.1"
PAPER = "doi_10_1234_paperx"          # an objective corpus source (a real paper dir)
VIRTUAL = "internal_phenome"          # a virtual anchor (source-null phenome claims)


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
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


def _q(corpus_store, sql: str, params=None):
    con = duckdb.connect(str(corpus_store.graph_db_path()), read_only=True)
    try:
        return con.execute(sql, params or []).fetchall()
    finally:
        con.close()


# --- inline write + record shape ---------------------------------------------


def test_relation_rides_inline_on_annotation(corpus_root, corpus_store):
    rel = _rel(["repo:phenome:assertion:aaaa"], [f"corpus:{PAPER}"])
    aid = annotate(
        PAPER, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
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


def test_relation_projected_to_claim_relations(corpus_root, corpus_store):
    annotate(
        PAPER, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
        scope="claim_relation", output_uri="phenome://contradiction_pairs/p1",
        relation=_rel(["repo:phenome:assertion:aaaa"], [f"corpus:{PAPER}"], kind="subject_scope"),
    )
    rows = _q(corpus_store, "SELECT relation_class, kind, repo, status, anchor_source_id FROM claim_relations")
    assert len(rows) == 1
    assert rows[0] == ("refute", "subject_scope", "phenome", "active", PAPER)


def test_idempotent_same_relation(corpus_root, corpus_store):
    rel = _rel(["repo:phenome:assertion:aaaa"], [f"corpus:{PAPER}"])
    a1 = annotate(PAPER, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
                  scope="claim_relation", output_uri="phenome://contradiction_pairs/p1", relation=rel)
    a2 = annotate(PAPER, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
                  scope="claim_relation", output_uri="phenome://contradiction_pairs/p1", relation=rel)
    assert a1 == a2
    assert len(_jsonl(corpus_root, PAPER)) == 1
    assert len(_q(corpus_store, "SELECT 1 FROM claim_relations")) == 1


# --- bidirectional discoverability -------------------------------------------


def test_lookup_by_subject_object_anchor(corpus_root, corpus_store):
    # subject = a genomics claim; object = a corpus paper; anchored at the paper.
    subj = "repo:genomics:claim:variant_registry.rs1"
    annotate(
        PAPER, store=corpus_store, repo="genomics", actor_type="model", actor_id=ACTOR_ID,
        scope="claim_relation", output_uri="genomics://verdicts/v1",
        relation=_rel([subj], [f"corpus:{PAPER}"]),
    )
    rid = _q(corpus_store, "SELECT relation_id FROM claim_relations")[0][0]
    # the endpoint index returns the SAME relation from every participant
    by_subject = _q(corpus_store, "SELECT relation_id FROM claim_relation_endpoints WHERE endpoint_ref = ?", [subj])
    by_object = _q(corpus_store, "SELECT relation_id FROM claim_relation_endpoints WHERE endpoint_ref = ?", [f"corpus:{PAPER}"])
    assert {r[0] for r in by_subject} == {rid}
    assert rid in {r[0] for r in by_object}
    # the source-level read primitive finds it via the namespaced anchor/object
    found = active_relations_for_source(PAPER, store=corpus_store)
    assert len(found) == 1
    assert found[0]["relation_class"] == "refute"
    assert found[0]["repo"] == "genomics"
    assert subj in found[0]["subjects"]


def test_anchor_endpoint_present(corpus_root, corpus_store):
    annotate(
        VIRTUAL, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
        scope="claim_relation", output_uri="phenome://contradiction_pairs/p2",
        relation=_rel(["repo:phenome:assertion:aaaa"], ["repo:phenome:assertion:bbbb"]),
    )
    roles = {r[0] for r in _q(corpus_store, "SELECT role FROM claim_relation_endpoints")}
    assert roles == {"subject", "object", "anchor"}
    anchor = _q(corpus_store, "SELECT endpoint_ref FROM claim_relation_endpoints WHERE role = 'anchor'")
    assert anchor[0][0] == f"corpus:{VIRTUAL}"


# --- supersession + retraction (active-surface semantics) --------------------


def test_supersession_drops_prior_from_active(corpus_root, corpus_store):
    rel1 = _rel(["repo:phenome:assertion:aaaa"], ["repo:phenome:assertion:bbbb"], cls="refute")
    a1 = annotate(VIRTUAL, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
                  scope="claim_relation", output_uri="phenome://contradiction_pairs/p3@open", relation=rel1)
    # re-adjudicated to a different class → different relation; supersedes a1
    rel2 = _rel(["repo:phenome:assertion:aaaa"], ["repo:phenome:assertion:bbbb"], cls="background")
    annotate(VIRTUAL, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="phenome://contradiction_pairs/p3@resolved",
             relation=rel2, supersedes_annotation_id=a1)
    # per-write projection: only the superseding relation remains
    classes = {r[0] for r in _q(corpus_store, "SELECT relation_class FROM claim_relations")}
    assert classes == {"background"}
    # and the rebuild agrees + counts the superseded one
    report = rebuild_claim_relations(store=corpus_store)
    assert report["relations_seen"] == 2
    assert report["relations_superseded"] == 1
    assert report["relations_active"] == 1
    assert {r[0] for r in _q(corpus_store, "SELECT relation_class FROM claim_relations")} == {"background"}


def test_retracted_excluded_from_active(corpus_root, corpus_store):
    annotate(
        VIRTUAL, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
        scope="claim_relation", output_uri="phenome://contradiction_pairs/p4",
        relation=_rel(["repo:phenome:assertion:aaaa"], ["repo:phenome:assertion:bbbb"]),
        status="retracted",
    )
    assert len(_q(corpus_store, "SELECT 1 FROM claim_relations")) == 1
    assert len(_q(corpus_store, "SELECT 1 FROM claim_relations_active")) == 0
    assert active_relations_for_source(VIRTUAL, store=corpus_store) == []


# --- rebuild robustness ------------------------------------------------------


def test_rebuild_idempotent(corpus_root, corpus_store):
    annotate(PAPER, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="phenome://contradiction_pairs/p1",
             relation=_rel(["repo:phenome:assertion:aaaa"], [f"corpus:{PAPER}"]))
    r1 = rebuild_claim_relations(store=corpus_store)
    r2 = rebuild_claim_relations(store=corpus_store)
    assert r1 == r2
    assert r1["relations_active"] == 1
    assert r1["endpoints_written"] == 3  # subject + object + anchor


def test_malformed_relation_skipped_not_fatal(corpus_root, corpus_store):
    # a valid relation, then a hand-written bad line (missing object_refs)
    annotate(PAPER, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
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
    report = rebuild_claim_relations(store=corpus_store)
    assert report["relations_seen"] == 2
    assert report["relations_malformed"] == 1
    assert report["relations_active"] == 1  # the good one still projects


def test_unresolved_participant_counted(corpus_root, corpus_store):
    # object references a corpus source that has no dir → flagged in the health report
    annotate(PAPER, store=corpus_store, repo="genomics", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="genomics://verdicts/v9",
             relation=_rel([f"corpus:{PAPER}"], ["corpus:doi_does_not_exist"]))
    report = rebuild_claim_relations(store=corpus_store)
    assert report["participants_unresolved"] == 1


# --- support_balance (Phase 5: transparent linear net-support, never P(true)) ---


def test_support_balance_refute_is_symmetric(corpus_root, corpus_store):
    # a refutation lowers BOTH participants (conflict is symmetric)
    annotate(VIRTUAL, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="phenome://contradiction_pairs/p1",
             relation=_rel(["repo:phenome:assertion:aaaa"], ["repo:phenome:assertion:bbbb"], cls="refute"))
    bal = {r[0]: r[1] for r in _q(corpus_store, "SELECT claim_ref, support_balance FROM support_balance")}
    assert bal["repo:phenome:assertion:aaaa"] == -1.0
    assert bal["repo:phenome:assertion:bbbb"] == -1.0
    # the anchor (corpus:internal_phenome) is storage, not a participant → excluded
    assert "corpus:internal_phenome" not in bal


def test_support_balance_support_is_directional(corpus_root, corpus_store):
    # endorsement raises only the OBJECT, not the asserting subject
    annotate(PAPER, store=corpus_store, repo="genomics", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="genomics://verdicts/v1",
             relation=_rel(["repo:genomics:claim:x"], [f"corpus:{PAPER}"], cls="support"))
    bal = {r[0]: r[1] for r in _q(corpus_store, "SELECT claim_ref, support_balance FROM support_balance")}
    assert bal[f"corpus:{PAPER}"] == 1.0
    assert "repo:genomics:claim:x" not in bal


def test_support_balance_for_source_helper(corpus_root, corpus_store):
    annotate(PAPER, store=corpus_store, repo="genomics", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="genomics://verdicts/v1",
             relation=_rel(["repo:genomics:claim:x"], [f"corpus:{PAPER}"], cls="refute"))
    bal = support_balance_for_source(PAPER, store=corpus_store)
    assert bal is not None
    assert bal["support_balance"] == -1.0
    assert bal["n_refute"] == 1
    assert support_balance_for_source("doi_no_such_paper", store=corpus_store) is None  # no relations → None


def test_support_balance_grade_weighted(corpus_root, corpus_store):
    annotate(PAPER, store=corpus_store, repo="genomics", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="genomics://verdicts/v1",
             relation=_rel(["repo:genomics:claim:x"], [f"corpus:{PAPER}"], cls="refute", grade_weight=0.5))
    bal = support_balance_for_source(PAPER, store=corpus_store)
    assert bal["support_balance"] == -0.5  # linear: sign × grade_weight, no squash


# --- epistemic_surface (Phase 4: the read-loop conflict signal) --------------


def test_epistemic_surface_flags_conflict(corpus_root, corpus_store):
    from corpus_core.index import epistemic_surface
    # no relations → no conflict
    before = epistemic_surface(PAPER, store=corpus_store, retraction_status="unknown")
    assert before["epistemic"]["conflict"] is False
    assert before["epistemic"]["support_balance"] is None
    # the PAPER is the OBJECT of a refute (it is being refuted) → conflict
    annotate(PAPER, store=corpus_store, repo="genomics", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="genomics://verdicts/v1",
             relation=_rel(["repo:genomics:claim:x"], [f"corpus:{PAPER}"], cls="refute"))
    after = epistemic_surface(PAPER, store=corpus_store, retraction_status="unknown")
    ep = after["epistemic"]
    assert ep["conflict"] is True
    assert ep["active_relation_count"] == 1
    assert len(ep["refuting_relations"]) == 1
    assert ep["refuting_relations"][0]["repo"] == "genomics"
    assert ep["support_balance"]["support_balance"] == -1.0


# --- close-review fixes (cross-model adversarial findings) --------------------


def test_refuting_source_not_flagged_conflicted(corpus_root, corpus_store):
    """A gold-standard source used to REFUTE a wrong claim is the subject, not
    the object — it must NOT show conflict=true on its own lookup, and must not
    receive a support_balance penalty (only claim-typed endpoints are scored)."""
    from corpus_core.index import epistemic_surface
    (corpus_root / "db_x").mkdir(exist_ok=True)
    annotate("db_x", store=corpus_store, repo="genomics", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="genomics://verdicts/v1",
             relation=_rel(["corpus:db_x"], ["repo:genomics:claim:c1"], cls="refute"))
    surf = epistemic_surface("db_x", store=corpus_store, retraction_status="unknown")
    assert surf["epistemic"]["conflict"] is False  # db_x is the refuter, not refuted
    bal = {r[0]: r[1] for r in _q(corpus_store, "SELECT claim_ref, support_balance FROM support_balance")}
    assert bal.get("repo:genomics:claim:c1") == -1.0   # the CLAIM is penalised
    assert "corpus:db_x" not in bal                    # the SOURCE is not


def test_out_of_order_retraction_does_not_resurrect(corpus_root, corpus_store):
    """If a retraction is indexed BEFORE its target relation (out-of-order
    drain), the tombstone makes the later-arriving target project as superseded,
    never as a stale-active leaf. Pre-fix this resurrected the refute."""
    from corpus_core.index import _connect, _index_relation
    from corpus_core.identity import relation_content_sha
    subj, obj = ["repo:phenome:assertion:aaaa"], ["repo:phenome:assertion:bbbb"]
    rid_a = "rel_" + relation_content_sha(
        relation_class="refute", subject_refs=subj, object_refs=obj, detector="d")[:16]

    def _rec(ann_id, rel_class, *, supersedes=None, status="active"):
        rel = {"relation_class": rel_class, "subject_refs": subj, "object_refs": obj, "detector": "d"}
        rel["relation_id"] = "rel_" + relation_content_sha(
            relation_class=rel_class, subject_refs=subj, object_refs=obj, detector="d")[:16]
        rec = {"annotation_id": ann_id, "source_id": VIRTUAL, "status": status,
               "idempotency_key": json.dumps({"repo": "phenome"}),
               "asserted_at": "2026-06-01T00:00:00Z", "recorded_at": "2026-06-01T00:00:00Z",
               "relation": rel}
        if supersedes:
            rec["supersedes_annotation_id"] = supersedes
        return rec

    con = _connect(corpus_store)
    try:
        # retraction R (background, supersedes A) arrives FIRST; A not yet indexed
        _index_relation(con, _rec("ann_rrrrrrrrrrrrrrrr", "background",
                                   supersedes="ann_aaaaaaaaaaaaaaaa", status="retracted"))
        # the active refute A arrives SECOND
        _index_relation(con, _rec("ann_aaaaaaaaaaaaaaaa", "refute"))
        row = con.execute(
            "SELECT status FROM claim_relations WHERE annotation_id = 'ann_aaaaaaaaaaaaaaaa'"
        ).fetchone()
        assert row is not None and row[0] == "superseded"   # NOT active
        assert con.execute(
            "SELECT COUNT(*) FROM claim_relations_active WHERE relation_id = ?", [rid_a]
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_duplicate_endpoints_dedup(corpus_root, corpus_store):
    """A duplicated endpoint ref must not fork the relation_id nor double-count."""
    from corpus_core.identity import relation_content_sha
    once = relation_content_sha(relation_class="refute", subject_refs=["x"], object_refs=["y"], detector="d")
    twice = relation_content_sha(relation_class="refute", subject_refs=["x", "x"], object_refs=["y"], detector="d")
    assert once == twice  # set semantics — duplicate does not fork identity
    annotate(VIRTUAL, store=corpus_store, repo="phenome", actor_type="model", actor_id=ACTOR_ID,
             scope="claim_relation", output_uri="phenome://contradiction_pairs/p1",
             relation={"relation_class": "refute",
                       "subject_refs": ["repo:phenome:assertion:a", "repo:phenome:assertion:a"],
                       "object_refs": ["repo:phenome:assertion:b"], "detector": "d"})
    assert _q(corpus_store, "SELECT COUNT(*) FROM claim_relation_endpoints WHERE role = 'subject'")[0][0] == 1
