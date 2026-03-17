"""Shared knowledge substrate — provenance state and dependency tracking.

Per-project SQLite databases with shared schema. Each project owns its DB;
cross-project references use project:id foreign references (not FK constraints).

Usage:
    from substrate import KnowledgeDB

    db = KnowledgeDB("path/to/knowledge.db")
    db.register_assertion("creatine-cognitive", type="claim", status="verified",
                          payload={"confidence": 0.7})
    db.register_evidence("ev-rae-2003", type="paper", source="doi:10.1098/rspb.2003.2492")
    db.add_relation("creatine-cognitive", "ev-rae-2003", "supported_by")
    db.mark_stale("ev-rae-2003")  # propagates to downstream assertions
"""
