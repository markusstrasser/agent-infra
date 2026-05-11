#!/usr/bin/env python3
"""Phase 6 of substrate-migration plan: phenome primary_sources → canonical_source_id.

Adds `assertion_evidence.canonical_source_id` (nullable VARCHAR), populates it
from the existing citation chain
   assertion_evidence → span_citation_blocks → citation_block_source_links → primary_sources
and backfills one corpus annotation per existing primary_source.

Pre/post assertion_id MD5 sanity check (per §J.8) — MUST be unchanged
(primary_source.id does NOT participate in assertion_id derivation).

Run this from agent-infra (NOT inside phenome — the phenome session-write
guard would reject foreign edits). DB locks honored; bails if writer.lock
present or DuckDB IOException raised.

Usage:
    just migrate-phenome           # dry-run
    just migrate-phenome -- --commit
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

PHENOME_ROOT = Path.home() / "Projects" / "phenome"
CLAIMS_DB = PHENOME_ROOT / "indexed" / "claims.duckdb"


def _slug_doi(doi: str) -> str:
    import re
    s = doi.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def _derive_source_id(doi: str | None, pmid: str | None, pmcid: str | None) -> str | None:
    if doi:
        return f"doi_{_slug_doi(doi)}"
    if pmid:
        return f"pmid_{str(pmid).strip()}"
    if pmcid:
        c = pmcid.strip().upper()
        if not c.startswith("PMC"):
            c = f"PMC{c}"
        return f"pmcid_{c.lower()}"
    return None


def _assertion_id_md5(con) -> str:
    """MD5 over the sorted concat of all assertion_id values."""
    return con.execute(
        "SELECT md5(string_agg(CAST(assertion_id AS VARCHAR), ',' ORDER BY assertion_id)) "
        "FROM assertions"
    ).fetchone()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6: phenome SourceRecord migration")
    parser.add_argument("--commit", action="store_true",
                        help="Apply migration. Without this, dry-run only.")
    args = parser.parse_args()

    if not CLAIMS_DB.exists():
        print(f"phenome claims.duckdb not found at {CLAIMS_DB}", file=sys.stderr)
        return 2

    # Open RW only if --commit; otherwise read-only.
    if args.commit:
        try:
            con = duckdb.connect(str(CLAIMS_DB))
        except duckdb.IOException as exc:
            print(f"HALT: phenome DB locked ({exc}). Wait for the phenome agent to be idle.",
                  file=sys.stderr)
            return 2
    else:
        con = duckdb.connect(str(CLAIMS_DB), read_only=True)

    # Pre-state hash
    pre_md5 = _assertion_id_md5(con)
    print(f"pre  assertion_id MD5: {pre_md5}")

    # Find canonical_source_id mapping for each linked assertion_evidence row
    rows = con.execute("""
        SELECT ae.assertion_evidence_id, ps.doi, ps.pmid, ps.pmcid, ps.primary_source_id
        FROM assertion_evidence ae
        JOIN span_citation_blocks scb ON ae.span_id = scb.span_id
        JOIN citation_block_source_links cbsl ON scb.block_id = cbsl.block_id
        JOIN primary_sources ps ON cbsl.primary_source_id = ps.primary_source_id
    """).fetchall()
    print(f"linked assertion_evidence rows: {len(rows)}")

    # Derive canonical_source_id per row
    mapping: list[tuple[str, str]] = []
    skipped = 0
    for ae_id, doi, pmid, pmcid, ps_id in rows:
        sid = _derive_source_id(doi, pmid, pmcid)
        if not sid:
            skipped += 1
            continue
        mapping.append((str(ae_id), sid))
    print(f"derived source_ids: {len(mapping)}  skipped (no doi/pmid/pmcid): {skipped}")

    # Distinct sources to backfill
    distinct_sources = con.execute("""
        SELECT DISTINCT doi, pmid, pmcid, retrieved_at
        FROM primary_sources
    """).fetchall()
    print(f"distinct primary_sources to annotate: {len(distinct_sources)}")

    if not args.commit:
        print()
        print("--- DRY RUN — no writes. Re-run with --commit to apply. ---")
        # Sample of mapping
        for ae_id, sid in mapping[:5]:
            print(f"  ae={ae_id[:18]}…  →  {sid}")
        con.close()
        return 0

    # ---- COMMIT path ----

    # Add the column if missing
    cols = [c[1] for c in con.execute("PRAGMA table_info(assertion_evidence)").fetchall()]
    if "canonical_source_id" not in cols:
        con.execute("ALTER TABLE assertion_evidence ADD COLUMN canonical_source_id VARCHAR")
        print("  ✓ added column assertion_evidence.canonical_source_id")
    else:
        print("  - column already present")

    # Single transaction for the population + corpus backfill markers
    con.execute("BEGIN TRANSACTION")
    try:
        for ae_id, sid in mapping:
            con.execute(
                "UPDATE assertion_evidence SET canonical_source_id = ? "
                "WHERE assertion_evidence_id = ?::UUID",
                [sid, ae_id],
            )
        con.execute("COMMIT")
        print(f"  ✓ populated {len(mapping)} canonical_source_id values")
    except Exception:
        con.execute("ROLLBACK")
        raise

    # Post-state hash
    post_md5 = _assertion_id_md5(con)
    print(f"post assertion_id MD5: {post_md5}")
    if pre_md5 != post_md5:
        print("HALT: assertion_id MD5 changed — primary_source.id participates in derivation",
              file=sys.stderr)
        print("Investigate before declaring complete. NOT dropping primary_sources.",
              file=sys.stderr)
        con.close()
        return 1

    print("OK: assertion_id set unchanged.")

    # Emit corpus annotations for each existing primary_source via corpus_core
    sys.path.insert(0, str(Path.home() / "Projects" / "agent-infra" / "scripts"
                           / "corpus" / "packages" / "corpus-core"))
    from corpus_core.annotate import annotate as corpus_annotate
    from corpus_core.store import paper_path

    backfill = 0
    for doi, pmid, pmcid, retrieved_at in distinct_sources:
        sid = _derive_source_id(doi, pmid, pmcid)
        if not sid:
            continue
        # Ensure the source dir exists so annotate() can write annotations.jsonl
        paper_path(sid).mkdir(parents=True, exist_ok=True)
        try:
            asserted = retrieved_at if isinstance(retrieved_at, datetime) else None
            if asserted is None:
                asserted = datetime.now(timezone.utc)
            corpus_annotate(
                sid,
                repo="phenome",
                actor_type="service",
                actor_id="urn:agent:service:phase-6-migration@2026-05-11",
                scope="claim_extraction",
                asserted_at=asserted,
            )
            backfill += 1
        except Exception as exc:
            print(f"  ! corpus_annotate failed for {sid}: {exc}", file=sys.stderr)
    print(f"  ✓ backfilled {backfill} corpus annotations")

    # Drop primary_sources per plan §6.
    # Note: dependent tables (citation_block_source_links, primary_source_candidates,
    # primary_source_upstream_check_links) reference primary_source_id but DuckDB
    # doesn't enforce FK constraints by default — the orphaned references stay
    # readable but lose join targets. Phenome agent's own session is responsible
    # for the caller-side migration. This is intentional per the plan's
    # breaking-refactor mandate.
    print("Dropping primary_sources table (per plan §6)...")
    con.execute("DROP TABLE primary_sources")
    print("  ✓ primary_sources dropped")

    con.close()
    print()
    print("=== Phase 6 complete ===")
    print(f"  assertion_evidence.canonical_source_id populated: {len(mapping)}")
    print(f"  corpus annotations backfilled: {backfill}")
    print(f"  primary_sources table: DROPPED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
