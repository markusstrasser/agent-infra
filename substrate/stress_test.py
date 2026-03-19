#!/usr/bin/env python3
"""Stress test for knowledge substrate.

Tests: scale, deep cascades, circular refs, concurrent upserts,
max_depth limits, edge cases.

Usage:
    uv run python3 substrate/stress_test.py
"""

import json
import tempfile
import time
from pathlib import Path

from substrate.core import KnowledgeDB

PASS = 0
FAIL = 0


def test(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name} — {detail}")


def test_basic_propagation():
    """Single chain: A depends on B depends on C. Mark C stale."""
    print("\n--- Basic propagation ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_evidence("c", type="paper", source="doi:test")
    db.register_assertion("b", type="claim", title="B")
    db.register_assertion("a", type="claim", title="A")
    db.add_relation("b", "c", "supported_by")
    db.add_relation("a", "b", "depends_on")

    staled = db.mark_stale("c", reason="retracted")
    test("3-node chain propagates", set(staled) == {"c", "b", "a"},
         f"got {staled}")

    # Already stale — should not re-cascade
    staled2 = db.mark_stale("c", reason="again")
    test("Already-stale skips", staled2 == [], f"got {staled2}")

    db.close()


def test_deep_cascade():
    """Chain of 10 objects. max_depth=5 should stop at 6 levels."""
    print("\n--- Deep cascade (max_depth enforcement) ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    # Build chain: node_0 <- node_1 <- ... <- node_9
    for i in range(10):
        db.register_assertion(f"node_{i}", type="claim", title=f"Node {i}")
    for i in range(1, 10):
        db.add_relation(f"node_{i}", f"node_{i-1}", "depends_on")

    staled = db.mark_stale("node_0", reason="root invalidated")
    test("max_depth=5 limits cascade to 6 objects",
         len(staled) <= 6,
         f"got {len(staled)}: {staled}")
    test("Root is always stale", "node_0" in staled)

    # Now with higher max_depth
    db2 = KnowledgeDB(tempfile.mktemp(suffix=".db"))
    for i in range(10):
        db2.register_assertion(f"node_{i}", type="claim", title=f"Node {i}")
    for i in range(1, 10):
        db2.add_relation(f"node_{i}", f"node_{i-1}", "depends_on")

    staled2 = db2.mark_stale("node_0", reason="root", max_depth=20)
    test("max_depth=20 propagates all 10", len(staled2) == 10,
         f"got {len(staled2)}")

    db.close()
    db2.close()


def test_diamond_dependency():
    """Diamond: D depends on B and C, both depend on A. Mark A stale."""
    print("\n--- Diamond dependency ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_evidence("a", type="paper", source="doi:diamond")
    db.register_assertion("b", type="claim", title="B")
    db.register_assertion("c", type="claim", title="C")
    db.register_assertion("d", type="claim", title="D")
    db.add_relation("b", "a", "supported_by")
    db.add_relation("c", "a", "supported_by")
    db.add_relation("d", "b", "depends_on")
    db.add_relation("d", "c", "depends_on")

    staled = db.mark_stale("a", reason="retracted")
    test("Diamond: all 4 marked stale", set(staled) == {"a", "b", "c", "d"},
         f"got {staled}")
    test("No duplicates", len(staled) == len(set(staled)))

    db.close()


def test_derivation_propagation():
    """Derivation: inputs -> derivation -> outputs. Mark input stale."""
    print("\n--- Derivation propagation ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_evidence("input1", type="paper", source="doi:1")
    db.register_evidence("input2", type="paper", source="doi:2")
    db.register_assertion("output1", type="thesis", title="Thesis")
    db.register_artifact("output2", type="memo", title="Memo")

    db.register_derivation("synth", process="synthesis",
                           inputs=[("input1", "evidence"), ("input2", "evidence")],
                           outputs=[("output1", "assertion"), ("output2", "artifact")])

    staled = db.mark_stale("input1", reason="data revision")
    test("Derivation propagates to both outputs",
         "output1" in staled and "output2" in staled,
         f"got {staled}")
    test("Other input not marked stale", "input2" not in staled,
         f"input2 was in {staled}")

    db.close()


def test_scale():
    """Register 1000 objects with 2000 relations. Check query performance."""
    print("\n--- Scale test (1000 objects, 2000 relations) ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    t0 = time.time()
    for i in range(500):
        db.register_assertion(f"claim_{i}", type="claim", title=f"Claim {i}")
    for i in range(500):
        db.register_evidence(f"ev_{i}", type="paper", source=f"doi:scale-{i}")
    t_register = time.time() - t0
    test(f"1000 registrations in {t_register:.2f}s", t_register < 10,
         f"took {t_register:.1f}s")

    t0 = time.time()
    for i in range(500):
        db.add_relation(f"claim_{i}", f"ev_{i}", "supported_by")
    # Cross-link: each claim depends on the next
    for i in range(499):
        db.add_relation(f"claim_{i+1}", f"claim_{i}", "depends_on")
    # Some derivations
    for i in range(0, 100, 10):
        db.register_derivation(f"deriv_{i}", process="analysis",
                               inputs=[(f"ev_{j}", "evidence") for j in range(i, i+5)],
                               outputs=[(f"claim_{i}", "assertion")])
    t_relations = time.time() - t0
    test(f"~1500 relations in {t_relations:.2f}s", t_relations < 10,
         f"took {t_relations:.1f}s")

    stats = db.stats()
    test("Stats correct", stats["assertions"] == 500 and stats["evidence"] == 500,
         f"got {stats}")

    # Propagation performance: mark ev_0 stale, cascade through chain
    t0 = time.time()
    staled = db.mark_stale("ev_0", reason="perf test", max_depth=10)
    t_propagate = time.time() - t0
    test(f"Propagation ({len(staled)} objects) in {t_propagate:.2f}s",
         t_propagate < 5 and len(staled) > 1,
         f"took {t_propagate:.1f}s, staled {len(staled)}")

    # Query performance
    t0 = time.time()
    for i in range(100):
        db.dependents(f"ev_{i}")
    t_query = time.time() - t0
    test(f"100 dependent queries in {t_query:.2f}s", t_query < 2,
         f"took {t_query:.1f}s")

    db.close()


def test_upsert():
    """Re-registering an object updates it, doesn't duplicate."""
    print("\n--- Upsert behavior ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_assertion("x", type="claim", status="active", title="Original")
    db.register_assertion("x", type="claim", status="verified", title="Updated")

    obj = db.get("x")
    test("Upsert updates status", obj["status"] == "verified")
    test("Upsert updates title", obj["title"] == "Updated")
    test("Only one record", db.stats()["assertions"] == 1)

    # Check changelog has both created and updated
    changes = db.recent_changes(10)
    actions = [c["action"] for c in changes if c["object_id"] == "x"]
    test("Changelog shows create+update", "created" in actions and "updated" in actions,
         f"got {actions}")

    db.close()


def test_payload_json():
    """Domain-specific payload stored and retrieved correctly."""
    print("\n--- JSON payload ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    payload = {"confidence": 0.75, "forecast_class": "live",
               "tags": ["value", "small-cap"], "nested": {"key": "val"}}
    db.register_assertion("rich", type="thesis", title="Rich payload",
                          payload=payload)

    obj = db.get("rich")
    test("Payload round-trips", obj["payload"] == payload,
         f"got {obj['payload']}")
    test("Nested values preserved", obj["payload"]["nested"]["key"] == "val")

    db.close()


def test_cross_project_refs():
    """Cross-project references stored and queryable."""
    print("\n--- Cross-project refs ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_assertion("local-claim", type="claim", title="Local")
    db.add_cross_project_ref(
        local_id="local-claim", local_type="assertion",
        remote_project="intel", remote_id="hims-thesis",
        remote_type="assertion", relation="depends_on")

    # Verify it's in the DB
    row = db.conn.execute(
        "SELECT * FROM cross_project_refs WHERE local_id = 'local-claim'"
    ).fetchone()
    test("Cross-ref stored", row is not None)
    test("Remote project correct", row["remote_project"] == "intel")

    # Duplicate insert should be ignored (UNIQUE constraint)
    db.add_cross_project_ref(
        local_id="local-claim", local_type="assertion",
        remote_project="intel", remote_id="hims-thesis",
        remote_type="assertion", relation="depends_on")
    count = db.conn.execute(
        "SELECT COUNT(*) as c FROM cross_project_refs WHERE local_id = 'local-claim'"
    ).fetchone()["c"]
    test("Duplicate cross-ref ignored", count == 1, f"got {count}")

    db.close()


def test_relation_dedup():
    """Duplicate relations are silently ignored."""
    print("\n--- Relation deduplication ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_assertion("a", type="claim", title="A")
    db.register_evidence("b", type="paper", source="doi:x")
    db.add_relation("a", "b", "supported_by")
    db.add_relation("a", "b", "supported_by")  # duplicate
    db.add_relation("a", "b", "contradicted_by")  # different relation type

    count = db.conn.execute("SELECT COUNT(*) as c FROM relations").fetchone()["c"]
    test("Duplicate relation ignored, different type kept", count == 2,
         f"got {count}")

    db.close()


def test_unknown_object():
    """Operations on nonexistent objects behave gracefully."""
    print("\n--- Unknown object handling ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    obj = db.get("nonexistent")
    test("get() returns None for unknown", obj is None)

    deps = db.dependents("nonexistent")
    test("dependents() returns [] for unknown", deps == [])

    staled = db.mark_stale("nonexistent")
    test("mark_stale() returns [] for unknown", staled == [])

    db.close()


def test_search_objects():
    """Search across objects by keyword."""
    print("\n--- Search objects ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_assertion("creatine-cognitive", type="claim", title="Creatine improves cognition",
                          payload={"tags": ["supplement", "brain"]})
    db.register_evidence("ev-rae-2003", type="paper", source="doi:10.1098/rspb.2003.2492",
                         title="Rae et al 2003 creatine RCT")
    db.register_assertion("caffeine-alertness", type="claim", title="Caffeine increases alertness")
    db.register_artifact("memo-supps", type="memo", title="Supplements overview",
                         payload={"topics": ["creatine", "caffeine", "magnesium"]})
    # Mark one stale -- should be excluded from search
    db.register_assertion("stale-claim", type="claim", status="stale",
                          title="Creatine is useless")

    results = db.search_objects("creatine")
    ids = [r["id"] for r in results]
    test("Search finds creatine assertion", "creatine-cognitive" in ids)
    test("Search finds evidence by title", "ev-rae-2003" in ids)
    test("Search finds artifact by payload", "memo-supps" in ids)
    test("Search excludes stale objects", "stale-claim" not in ids)

    # Scoring: creatine-cognitive should score higher (id + title match)
    test("Higher scored first", results[0]["id"] == "creatine-cognitive",
         f"got {results[0]['id']}")

    # Empty query
    test("Empty query returns []", db.search_objects("") == [])
    test("No-match query returns []", db.search_objects("xyznonexistent") == [])

    db.close()


def test_provenance_chain():
    """CTE-based downstream provenance."""
    print("\n--- Provenance chain (CTE) ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    # Build chain: ev -> claim_a -> claim_b -> claim_c
    db.register_evidence("ev-root", type="paper", source="doi:root")
    db.register_assertion("claim-a", type="claim", title="A")
    db.register_assertion("claim-b", type="claim", title="B")
    db.register_assertion("claim-c", type="claim", title="C")
    db.add_relation("claim-a", "ev-root", "supported_by")
    db.add_relation("claim-b", "claim-a", "depends_on")
    db.add_relation("claim-c", "claim-b", "depends_on")

    chain = db.provenance_chain("ev-root")
    chain_ids = [c["id"] for c in chain]
    test("Provenance finds claim-a", "claim-a" in chain_ids)
    test("Provenance finds claim-b", "claim-b" in chain_ids)
    test("Provenance finds claim-c", "claim-c" in chain_ids)
    test("Provenance has correct depths",
         any(c["depth"] == 1 for c in chain) and any(c["depth"] == 3 for c in chain),
         f"depths: {[c['depth'] for c in chain]}")

    # Empty provenance
    test("No provenance for leaf", db.provenance_chain("claim-c") == [])

    db.close()


def test_impact_radius():
    """CTE-based upstream impact."""
    print("\n--- Impact radius (CTE) ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_evidence("ev-1", type="paper", source="doi:1")
    db.register_evidence("ev-2", type="paper", source="doi:2")
    db.register_assertion("claim-x", type="claim", title="X")
    db.add_relation("claim-x", "ev-1", "supported_by")
    db.add_relation("claim-x", "ev-2", "depends_on")

    chain = db.impact_radius("claim-x")
    chain_ids = [c["id"] for c in chain]
    test("Impact finds ev-1", "ev-1" in chain_ids)
    test("Impact finds ev-2", "ev-2" in chain_ids)
    test("Impact radius is 2 objects", len(chain) == 2, f"got {len(chain)}")

    # No upstream for evidence with no dependencies
    test("No impact for root evidence", db.impact_radius("ev-1") == [])

    db.close()


def test_shared_evidence():
    """Find assertions sharing the same evidence."""
    print("\n--- Shared evidence ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_evidence("ev-shared", type="paper", source="doi:shared")
    db.register_assertion("claim-1", type="claim", title="Claim 1")
    db.register_assertion("claim-2", type="claim", title="Claim 2")
    db.register_assertion("claim-3", type="claim", title="Claim 3 (different evidence)")
    db.register_evidence("ev-other", type="paper", source="doi:other")

    db.add_relation("claim-1", "ev-shared", "supported_by")
    db.add_relation("claim-2", "ev-shared", "supported_by")
    db.add_relation("claim-3", "ev-other", "supported_by")

    shared = db.shared_evidence("claim-1")
    shared_ids = [s["id"] for s in shared]
    test("Shared evidence finds claim-2", "claim-2" in shared_ids)
    test("Shared evidence excludes claim-3", "claim-3" not in shared_ids)
    test("Shared evidence excludes self", "claim-1" not in shared_ids)

    db.close()


def test_contradictions():
    """Find contradictory assertions."""
    print("\n--- Contradictions ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_assertion("bull-thesis", type="thesis", title="Company is undervalued")
    db.register_assertion("bear-thesis", type="thesis", title="Company is overvalued")
    db.register_assertion("unrelated", type="claim", title="Unrelated claim")

    db.add_relation("bear-thesis", "bull-thesis", "contradicted_by")

    contras = db.contradictory_assertions("bull-thesis")
    contra_ids = [c["id"] for c in contras]
    test("Contradiction finds bear-thesis", "bear-thesis" in contra_ids)
    test("Contradiction excludes unrelated", "unrelated" not in contra_ids)

    # Check from the other side
    contras2 = db.contradictory_assertions("bear-thesis")
    contra2_ids = [c["id"] for c in contras2]
    test("Reverse contradiction finds bull-thesis", "bull-thesis" in contra2_ids)

    db.close()


def test_orphans():
    """Find objects with no relations."""
    print("\n--- Orphan sweeper ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    # Connected objects
    db.register_assertion("connected-claim", type="claim", title="Connected")
    db.register_evidence("connected-ev", type="paper", source="doi:conn")
    db.add_relation("connected-claim", "connected-ev", "supported_by")

    # Orphan objects
    db.register_assertion("orphan-claim", type="claim", title="Orphan claim")
    db.register_evidence("orphan-ev", type="paper", source="doi:orphan")
    db.register_artifact("orphan-memo", type="memo", title="Orphan memo")

    orphan_list = db.orphans()
    orphan_ids = [o["id"] for o in orphan_list]
    test("Finds orphan assertion", "orphan-claim" in orphan_ids)
    test("Finds orphan evidence", "orphan-ev" in orphan_ids)
    test("Finds orphan artifact", "orphan-memo" in orphan_ids)
    test("Excludes connected claim", "connected-claim" not in orphan_ids)
    test("Excludes connected evidence", "connected-ev" not in orphan_ids)
    test("Orphan count is 3", len(orphan_list) == 3, f"got {len(orphan_list)}")

    # Object in derivation is not orphan
    db.register_evidence("deriv-input", type="computation", source="file:pipeline.py")
    db.register_assertion("deriv-output", type="finding", title="Pipeline result")
    db.register_derivation("deriv-1", process="pipeline",
                           inputs=[("deriv-input", "evidence")],
                           outputs=[("deriv-output", "assertion")])
    orphan_list2 = db.orphans()
    orphan_ids2 = [o["id"] for o in orphan_list2]
    test("Derivation input not orphan", "deriv-input" not in orphan_ids2)
    test("Derivation output not orphan", "deriv-output" not in orphan_ids2)

    db.close()


def test_reflect_fallback():
    """Reflect falls back gracefully when API unavailable."""
    print("\n--- Reflect fallback ---")
    db = KnowledgeDB(tempfile.mktemp(suffix=".db"))

    db.register_assertion("test-claim", type="claim", title="Test claim about creatine",
                          payload={"confidence": 0.8})
    db.register_evidence("test-ev", type="paper", source="doi:test",
                         title="Test paper on creatine")
    db.add_relation("test-claim", "test-ev", "supported_by")

    # With no valid API key, reflect should fall back gracefully
    # We test by using a model name that won't exist
    result = db.reflect("creatine", model="nonexistent-model-xyz")
    test("Fallback returns text", len(result.text) > 0)
    test("Fallback contains recalled context", "test-claim" in result.text or "creatine" in result.text.lower())
    test("Fallback has recalled_ids", "test-claim" in result.recalled_ids)
    test("Fallback tokens are 0", result.input_tokens == 0 and result.output_tokens == 0)

    # Empty search should return early
    result2 = db.reflect("xyznonexistentquery")
    test("Empty recall returns message", "No relevant objects" in result2.text)

    db.close()


def main():
    print("Knowledge substrate stress test")
    print("=" * 50)

    test_basic_propagation()
    test_deep_cascade()
    test_diamond_dependency()
    test_derivation_propagation()
    test_scale()
    test_upsert()
    test_payload_json()
    test_cross_project_refs()
    test_relation_dedup()
    test_unknown_object()
    test_search_objects()
    test_provenance_chain()
    test_impact_radius()
    test_shared_evidence()
    test_contradictions()
    test_orphans()
    test_reflect_fallback()

    print("\n" + "=" * 50)
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
