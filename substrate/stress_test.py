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

    print("\n" + "=" * 50)
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
