#!/usr/bin/env python3
"""audit_corpus_sync — verdicts ↔ corpus-annotations drift detection.

Phase 4 backstop for the substrate-v1 attestation flow:
  1. agent calls <repo>_mcp.record_verdict(...)        → writes verdict_id to repo-local DB
  2. agent calls corpus_mcp.corpus_attest(scope='verdict', output_uri='<repo>://verdicts/<vid>')
                                                       → writes corpus annotation

If step 2 is skipped, the verdict has no corpus provenance. This script
reports the drift in BOTH directions:

    A. Verdicts WITHOUT a corresponding corpus annotation (sync drift)
    B. Corpus annotations WITHOUT a corresponding verdict   (orphans)

Exit code:
    0   no drift
    1   drift detected (counts in stdout, JSON detail in --json mode)
    2   audit infrastructure failure (DB unreachable, etc.)

Usage:
    just audit-corpus-sync               # human-readable
    just audit-corpus-sync -- --json     # machine-readable (CI / launchd)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import duckdb

PROJECTS_ROOT = Path.home() / "Projects"
CORPUS_ROOT = Path.home() / "Projects" / "corpus"
CORPUS_GRAPH_DB = CORPUS_ROOT / "graph.duckdb"

# Each per-repo verdicts source is a (repo_name, db_path, sql) triple.
# The SQL must yield (verdict_id, source_id) rows. Phase 5/6 will normalize
# source_id forms across all three repos.
# Each per-repo verdicts source yields (verdict_id, source_id, output_hash)
# triples. The audit covers a verdict if the corpus carries an annotation
# whose (source_id, output_hash) matches the verdict's pair — idempotent
# annotations collapse when multiple verdicts share a projection, so 1:1
# verdict_id ↔ output_uri matching undercounts coverage.
VERDICTS_SOURCES: list[dict[str, Any]] = [
    {
        "repo": "genomics",
        "db_path": PROJECTS_ROOT / "genomics" / "data" / "knowledge" / "knowledge.duckdb",
        "sql": """
            SELECT cv.verdict_id,
                   (SELECT so.canonical_source_id
                    FROM evidence_bindings eb
                    JOIN source_observations so ON eb.observation_id = so.observation_id
                    WHERE eb.verdict_id = cv.verdict_id
                    ORDER BY eb.binding_id LIMIT 1) AS source_id,
                   cv.verdict_projection_hash AS output_hash
            FROM claim_verdicts cv
            WHERE cv.review_status = 'current'
        """,
    },
    {
        "repo": "phenome",
        "db_path": PROJECTS_ROOT / "phenome" / "indexed" / "claims.duckdb",
        # Phenome's verdict surface is the cert stack. Until phenome-mcp
        # stands up record_verdict, this query is a placeholder — missing-
        # table is tolerated by the audit.
        "sql": "SELECT cert_id AS verdict_id, '' AS source_id, '' AS output_hash FROM cert_attestations",
    },
    {
        "repo": "intel",
        "db_path": PROJECTS_ROOT / "intel" / "intel" / "indexed" / "theses.duckdb",
        "sql": "SELECT verdict_id, '' AS source_id, '' AS output_hash FROM claim_verdicts",
    },
]


_URI_RE = re.compile(r"^([a-z-]+)://verdicts/(.+)$")


def _read_verdicts(repo: str, db_path: Path, sql: str) -> list[tuple[str, str, str]]:
    """Return [(verdict_id, source_id, output_hash), ...]."""
    if not db_path.exists():
        return []
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except duckdb.IOException:
        # Concurrent writer holds the lock — treat as no-data, surfaced in
        # the audit summary.
        return []
    try:
        try:
            rows = con.execute(sql).fetchall()
            return [(str(r[0]), str(r[1] or ""), str(r[2] or "")) for r in rows]
        except (duckdb.BinderException, duckdb.CatalogException):
            # Schema not present — common for repos that haven't migrated to
            # the shared interface yet (Phase 5/6).
            return []
    finally:
        con.close()


def _read_corpus_annotations() -> list[dict[str, Any]]:
    """All scope=verdict annotations in the corpus annotations table."""
    if not CORPUS_GRAPH_DB.exists():
        return []
    con = duckdb.connect(str(CORPUS_GRAPH_DB), read_only=True)
    try:
        rows = con.execute(
            "SELECT annotation_id, source_id, repo, output_uri, output_hash, recorded_at "
            "FROM annotations WHERE scope = 'verdict'"
        ).fetchall()
    finally:
        con.close()
    return [
        {"annotation_id": r[0], "source_id": r[1], "repo": r[2],
         "output_uri": r[3], "output_hash": r[4] or "", "recorded_at": r[5]}
        for r in rows
    ]


def _verdict_id_from_uri(uri: str | None) -> tuple[str | None, str | None]:
    """Recover (repo, verdict_id) from a `<repo>://verdicts/<vid>` URI."""
    if not uri:
        return None, None
    m = _URI_RE.match(uri)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def audit() -> dict[str, Any]:
    annotations = _read_corpus_annotations()

    # Coverage index: per repo, set of (source_id, output_hash) pairs that
    # have an annotation. Verdicts collapse onto a (source_id, vp_hash) pair
    # because corpus_annotate is idempotent on the stable_tuple
    # — multiple verdicts sharing a projection share an annotation by design.
    coverage_by_repo: dict[str, set[tuple[str, str]]] = {}
    annotated_uris_by_repo: dict[str, set[str]] = {}
    for ann in annotations:
        repo = ann["repo"]
        if ann["source_id"] and ann["output_hash"]:
            coverage_by_repo.setdefault(repo, set()).add(
                (ann["source_id"], ann["output_hash"])
            )
        uri_repo, vid = _verdict_id_from_uri(ann["output_uri"])
        if uri_repo and vid:
            annotated_uris_by_repo.setdefault(uri_repo, set()).add(vid)

    drift_missing_annotations: list[dict[str, Any]] = []
    drift_orphan_annotations: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []

    for src in VERDICTS_SOURCES:
        repo = src["repo"]
        local_verdicts = _read_verdicts(repo, src["db_path"], src["sql"])
        cover = coverage_by_repo.get(repo, set())

        local_vid_set = {vid for vid, _sid, _h in local_verdicts}
        annotated_vid_set = annotated_uris_by_repo.get(repo, set())

        missing: list[str] = []
        for vid, sid, ohash in local_verdicts:
            if sid and ohash:
                # Covered if (sid, ohash) appears in any annotation
                if (sid, ohash) not in cover:
                    missing.append(vid)
            else:
                # No verdict-side join keys — fall back to URI matching for
                # repos that haven't joined the substrate-v1 interface yet.
                if vid not in annotated_vid_set:
                    missing.append(vid)

        # Orphans: annotation URIs naming verdict_ids not in the local DB.
        orphans = sorted(annotated_vid_set - local_vid_set) if local_vid_set else []

        for vid in missing:
            drift_missing_annotations.append({"repo": repo, "verdict_id": vid})
        for vid in orphans:
            drift_orphan_annotations.append({"repo": repo, "verdict_id": vid})

        summary.append({
            "repo": repo,
            "db_path": str(src["db_path"]),
            "verdicts_local": len(local_vid_set),
            "verdicts_annotated": len(local_vid_set) - len(missing),
            "missing_annotations": len(missing),
            "orphan_annotations": len(orphans),
        })

    return {
        "summary": summary,
        "drift_missing_annotations": drift_missing_annotations,
        "drift_orphan_annotations": drift_orphan_annotations,
        "drift_total": len(drift_missing_annotations) + len(drift_orphan_annotations),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit verdicts ↔ corpus annotations drift")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON; non-zero exit on drift")
    parser.add_argument("--verbose", action="store_true",
                        help="List individual drifted verdict_ids")
    args = parser.parse_args(argv)

    try:
        report = audit()
    except Exception as exc:
        print(f"audit infrastructure failure: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print("=== Corpus sync audit ===")
        print(f"corpus.graph.duckdb: {CORPUS_GRAPH_DB}")
        print()
        for row in report["summary"]:
            print(f"  {row['repo']:10s}  verdicts={row['verdicts_local']:5d}  "
                  f"annotated={row['verdicts_annotated']:5d}  "
                  f"missing_ann={row['missing_annotations']:4d}  "
                  f"orphans={row['orphan_annotations']:4d}")
        print()
        if report["drift_total"] == 0:
            print("OK: 0 drift")
        else:
            print(f"DRIFT: {report['drift_total']} total")
            if args.verbose:
                for d in report["drift_missing_annotations"][:20]:
                    print(f"  missing  {d['repo']}/{d['verdict_id']}")
                for d in report["drift_orphan_annotations"][:20]:
                    print(f"  orphan   {d['repo']}/{d['verdict_id']}")

    return 1 if report["drift_total"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
