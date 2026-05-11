#!/usr/bin/env python3
"""Phase 5 of substrate-migration plan: genomics source_observations →
canonical_source_id + corpus annotation backfill.

Mirrors the phenome Phase 6 reference impl (migrate_phenome_source_records.py):
add a canonical_source_id column instead of in-place re-slug. The native
':'-prefix-typed source_id remains authoritative for in-DB use; the new
canonical column is the join key to the corpus.

Why not in-place re-slug (as the original Phase 5 plan suggested):
  * observation_id_for(obs) hashes source_id (mutation_gateway.py:103) —
    future re-writes would compute a different observation_id, producing
    duplicates under ON CONFLICT DO NOTHING.
  * binding_id_for(verdict_id, observation_id, ...) inherits the cascade.
  * compute_evidence_projection_hash hashes (source_id, ...) triples.
  * config/source_registry.json (493) + config/claim_registry.json (1221)
    use ':'-form; claim_binding_hash via SourceSnapshot would diverge.
  * Phenome migrate_phenome_source_records.py already established the
    canonical-column pattern. Phase 5 mirrors it for consistency across
    the substrate.

Run from agent-infra (not inside genomics — genomics' session-write guard
rejects foreign edits). Honors writer.lock + DuckDB IOException.

Usage:
    uv run python3 scripts/migrate_genomics_phase5.py            # dry-run
    uv run python3 scripts/migrate_genomics_phase5.py --commit   # apply
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

GENOMICS_ROOT = Path.home() / "Projects" / "genomics"
KNOWLEDGE_DB = GENOMICS_ROOT / "data" / "knowledge" / "knowledge.duckdb"
WRITER_LOCK = GENOMICS_ROOT / "data" / "knowledge" / "writer.lock"


def _canonicalize(source_id: str) -> str:
    """Map a genomics ':'-prefix-typed source_id to the corpus filesystem slug.

    `[^a-z0-9]+ → _`, collapse repeats, strip trailing.
    Lossy but deterministic; collision check is part of the migration.
    """
    s = source_id.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def _verdict_set_md5(con) -> str:
    return con.execute(
        "SELECT md5(string_agg(CAST(verdict_id AS VARCHAR), ',' ORDER BY verdict_id)) "
        "FROM claim_verdicts"
    ).fetchone()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5: genomics source canonicalization + corpus annotation backfill")
    parser.add_argument("--commit", action="store_true", help="Apply migration. Without this, dry-run only.")
    args = parser.parse_args()

    if not KNOWLEDGE_DB.exists():
        print(f"knowledge.duckdb not found at {KNOWLEDGE_DB}", file=sys.stderr)
        return 2

    if WRITER_LOCK.exists():
        print(f"HALT: writer.lock present at {WRITER_LOCK}. Wait for drain.", file=sys.stderr)
        return 2

    try:
        con = duckdb.connect(str(KNOWLEDGE_DB), read_only=not args.commit)
    except duckdb.IOException as exc:
        print(f"HALT: knowledge.duckdb locked ({exc}).", file=sys.stderr)
        return 2

    # Pre-state hashes
    pre_md5 = _verdict_set_md5(con)
    pre_support = dict(con.execute(
        "SELECT support_state, COUNT(*) FROM claim_verdicts WHERE review_status='current' GROUP BY 1 ORDER BY 1"
    ).fetchall())
    pre_obs_count = con.execute("SELECT COUNT(*) FROM source_observations").fetchone()[0]
    pre_distinct_sids = con.execute("SELECT COUNT(DISTINCT source_id) FROM source_observations").fetchone()[0]

    print(f"pre  verdict_set_md5: {pre_md5}")
    print(f"pre  support_state: {pre_support}")
    print(f"pre  source_observations: {pre_obs_count} rows, {pre_distinct_sids} distinct source_id")

    # Distinct source_ids → canonical mapping
    distinct = con.execute("SELECT DISTINCT source_id FROM source_observations").fetchall()
    mapping = [(sid, _canonicalize(sid)) for (sid,) in distinct]

    # Collision check
    by_canonical: dict[str, list[str]] = {}
    for sid, canon in mapping:
        by_canonical.setdefault(canon, []).append(sid)
    collisions = {c: origs for c, origs in by_canonical.items() if len(origs) > 1}
    print(f"distinct source_ids: {len(mapping)}  collisions: {len(collisions)}")
    if collisions:
        print("COLLISIONS:")
        for c, origs in list(collisions.items())[:10]:
            print(f"  {c}: {origs}")
        print("HALT: collisions in canonical mapping. Resolve before --commit.", file=sys.stderr)
        con.close()
        return 1

    # Verdicts that will get annotations (review_status='current' with at least one binding)
    current_verdicts = con.execute("""
        SELECT cv.verdict_id, cv.model_version, cv.prompt_template_hash,
               cv.verdict_projection_hash, cv.asserted_at,
               (SELECT so.source_id
                FROM evidence_bindings eb
                JOIN source_observations so ON eb.observation_id = so.observation_id
                WHERE eb.verdict_id = cv.verdict_id
                ORDER BY eb.binding_id LIMIT 1) AS pick_source_id
        FROM claim_verdicts cv
        WHERE cv.review_status = 'current'
    """).fetchall()
    with_binding = [r for r in current_verdicts if r[5]]
    no_binding = [r for r in current_verdicts if not r[5]]
    print(f"current verdicts: {len(current_verdicts)}  with-binding: {len(with_binding)}  no-binding: {len(no_binding)}")

    if not args.commit:
        print()
        print("--- DRY RUN — no writes. Re-run with --commit to apply. ---")
        print("Sample canonical mapping:")
        for sid, canon in mapping[:10]:
            print(f"  {sid!r:50s} → {canon!r}")
        print(f"\nWould add column: source_observations.canonical_source_id")
        print(f"Would write ~{len(with_binding)} corpus annotations (skipping {len(no_binding)} no-binding)")
        con.close()
        return 0

    # ---- COMMIT path ----

    # Add the column if missing
    cols = [c[1] for c in con.execute("PRAGMA table_info(source_observations)").fetchall()]
    if "canonical_source_id" not in cols:
        con.execute("ALTER TABLE source_observations ADD COLUMN canonical_source_id VARCHAR")
        print("  ✓ added column source_observations.canonical_source_id")
    else:
        print("  - column already present (idempotent re-run)")

    # Single transaction for the population
    con.execute("BEGIN TRANSACTION")
    try:
        for sid, canon in mapping:
            con.execute(
                "UPDATE source_observations SET canonical_source_id = ? WHERE source_id = ?",
                [canon, sid],
            )
        con.execute("COMMIT")
        # Verify
        n_populated = con.execute(
            "SELECT COUNT(*) FROM source_observations WHERE canonical_source_id IS NOT NULL"
        ).fetchone()[0]
        n_null = con.execute(
            "SELECT COUNT(*) FROM source_observations WHERE canonical_source_id IS NULL"
        ).fetchone()[0]
        print(f"  ✓ populated canonical_source_id: {n_populated} rows  (null: {n_null})")
    except Exception:
        con.execute("ROLLBACK")
        raise

    # Post-state determinism check
    post_md5 = _verdict_set_md5(con)
    post_support = dict(con.execute(
        "SELECT support_state, COUNT(*) FROM claim_verdicts WHERE review_status='current' GROUP BY 1 ORDER BY 1"
    ).fetchall())
    if pre_md5 != post_md5:
        print(f"HALT: verdict_id set MD5 changed (pre={pre_md5} post={post_md5})", file=sys.stderr)
        con.close()
        return 1
    if pre_support != post_support:
        print(f"HALT: support_state distribution changed (pre={pre_support} post={post_support})", file=sys.stderr)
        con.close()
        return 1
    print(f"  ✓ verdict_set_md5 unchanged  support_state unchanged")

    # 5B: corpus annotation backfill
    sys.path.insert(
        0,
        str(Path.home() / "Projects" / "agent-infra" / "scripts" / "corpus" / "packages" / "corpus-core"),
    )
    from corpus_core.annotate import annotate as corpus_annotate
    from corpus_core.store import paper_path

    # Re-query with canonical_source_id directly
    backfill_rows = con.execute("""
        SELECT cv.verdict_id, cv.model_version, cv.prompt_template_hash,
               cv.verdict_projection_hash, cv.asserted_at,
               (SELECT so.canonical_source_id
                FROM evidence_bindings eb
                JOIN source_observations so ON eb.observation_id = so.observation_id
                WHERE eb.verdict_id = cv.verdict_id
                ORDER BY eb.binding_id LIMIT 1) AS canonical_source_id
        FROM claim_verdicts cv
        WHERE cv.review_status = 'current'
    """).fetchall()

    backfilled = 0
    skipped_no_binding = 0
    errors: list[str] = []
    for vid, model_version, prompt_hash, vp_hash, asserted, canon_sid in backfill_rows:
        if not canon_sid:
            skipped_no_binding += 1
            continue
        try:
            paper_path(canon_sid).mkdir(parents=True, exist_ok=True)
            asserted_dt: datetime | str | None
            if isinstance(asserted, datetime):
                asserted_dt = asserted
            elif isinstance(asserted, str):
                asserted_dt = asserted
            else:
                asserted_dt = datetime.now(timezone.utc)
            is_stub = (not model_version) or model_version == "direction-d-router-stub"
            actor_type = "service" if is_stub else "model"
            actor_id = (
                f"urn:agent:service:direction-d-router-stub"
                if is_stub
                else f"urn:agent:model:{model_version}"
            )
            # Schema regex on hash fields is ^([0-9a-f]{8,64}|)$ — drop
            # non-hex placeholders (the router stub used during the seed
            # drain) by passing None.
            safe_prompt_hash: str | None = prompt_hash
            if prompt_hash and not re.fullmatch(r"[0-9a-f]{8,64}", prompt_hash):
                safe_prompt_hash = None
            corpus_annotate(
                canon_sid,
                repo="genomics",
                actor_type=actor_type,
                actor_id=actor_id,
                scope="verdict",
                output_uri=f"genomics://verdicts/{vid}",
                output_hash=vp_hash,
                prompt_template_hash=safe_prompt_hash,
                asserted_at=asserted_dt,
            )
            backfilled += 1
        except Exception as exc:
            errors.append(f"{vid} → {canon_sid}: {exc}")

    print(f"  ✓ corpus annotations backfilled: {backfilled}  (skipped no-binding: {skipped_no_binding})")
    if errors:
        print(f"  ! errors: {len(errors)}")
        for e in errors[:5]:
            print(f"    - {e}")

    con.close()
    print()
    print("=== Phase 5 complete ===")
    print(f"  source_observations.canonical_source_id populated: {n_populated}")
    print(f"  corpus annotations backfilled: {backfilled}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
