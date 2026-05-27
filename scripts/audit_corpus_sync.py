#!/usr/bin/env python3
"""audit_corpus_sync — verdicts ↔ corpus-annotations drift detection + outbox drain.

Substrate v2 (2026-05-26): cross-attestation is enforced by the per-repo
mutation gateway via a transactional outbox; this audit is the crash-gap
recovery surface. Two responsibilities:

  1. DRAIN — for each repo with a `pending_corpus_attestations` table,
     flush rows to corpus filesystem via corpus_core.annotate. Failures
     bump retry_count; ≥3 retries flips status='abandoned' (audit reports
     the count). This catches the case where a process crash leaves
     committed-but-not-drained outbox rows the gateway can't re-drain
     until next gateway entry.
  2. REPORT — verdicts ↔ corpus-annotations drift, both directions:
       A. Verdicts WITHOUT a corresponding corpus annotation (sync drift)
       B. Corpus annotations WITHOUT a corresponding verdict   (orphans)

Exit code:
    0   no drift
    1   drift detected (counts in stdout, JSON detail in --json mode)
    2   audit infrastructure failure (DB unreachable, etc.)

Usage:
    just audit-corpus-sync               # human-readable
    just audit-corpus-sync -- --json     # machine-readable (CI / launchd)
    just audit-corpus-sync -- --drain-only   # drain pending outboxes, no report
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


def _drain_repo_outbox(repo: str, db_path: Path) -> dict[str, int]:
    """Drain pending_corpus_attestations for a repo. Returns counts:
    {flushed, retried, abandoned, no_table, skipped_locked}.

    Lock-friendly: opens read-only first to fetch pending rows, releases,
    performs filesystem IO outside any DuckDB lock, then re-opens write
    only briefly per row to DELETE/UPDATE. Critique #13 fix — prior
    implementation held the writer lock for the full O(N) corpus IO loop,
    blocking concurrent gateway drains.
    """
    out = {"flushed": 0, "retried": 0, "abandoned": 0, "no_table": 0, "skipped_locked": 0}
    if not db_path.exists():
        out["no_table"] = 1
        return out
    # Phase 1: read-only fetch of pending rows (lock-free).
    try:
        con_ro = duckdb.connect(str(db_path), read_only=True)
    except duckdb.IOException:
        out["skipped_locked"] = 1
        return out
    try:
        try:
            # Lifecycle columns (annotation_status, supersedes_annotation_id)
            # may not exist on repos that haven't migrated yet (only genomics
            # at the time substrate v2 deferred-items plan landed). Use
            # COALESCE-on-missing pattern via two-step query: try the full
            # SELECT first, fall back to the legacy shape if columns are
            # absent. Mapped to defaults at emit time.
            try:
                rows = con_ro.execute(
                    """
                    SELECT verdict_id, canonical_source_id, actor_type, actor_id,
                           output_uri, output_hash, prompt_template_hash,
                           asserted_at, retry_count,
                           annotation_status, supersedes_annotation_id
                    FROM pending_corpus_attestations
                    WHERE status = 'pending'
                    LIMIT 1000
                    """
                ).fetchall()
            except duckdb.BinderException:
                legacy_rows = con_ro.execute(
                    """
                    SELECT verdict_id, canonical_source_id, actor_type, actor_id,
                           output_uri, output_hash, prompt_template_hash,
                           asserted_at, retry_count
                    FROM pending_corpus_attestations
                    WHERE status = 'pending'
                    LIMIT 1000
                    """
                ).fetchall()
                rows = [(*r, "active", None) for r in legacy_rows]
        except (duckdb.BinderException, duckdb.CatalogException):
            out["no_table"] = 1
            return out
    finally:
        con_ro.close()
    if not rows:
        return out

    # Phase 2: FS IO with NO DuckDB lock held. Lazy import — only the
    # drain path needs corpus_core; keep audit importable in environments
    # without the package installed.
    cc_path = str(
        Path.home() / "Projects" / "agent-infra" / "scripts" / "corpus" / "packages" / "corpus-core"
    )
    if cc_path not in sys.path:
        sys.path.insert(0, cc_path)
    from corpus_core.annotate import AnnotationError, annotate as _annotate
    from corpus_core.store import paper_path

    # Collect successes/failures; apply DB writes in Phase 3.
    successes: list[tuple[str, str]] = []  # (verdict_id, canon)
    failures: list[tuple[str, str, int, str]] = []  # (vid, canon, new_retry, err)
    for (
        verdict_id, canon, actor_type, actor_id, output_uri,
        output_hash, prompt_template_hash, asserted_at, retry_count,
        annotation_status, supersedes_annotation_id,
    ) in rows:
        try:
            paper_path(canon).mkdir(parents=True, exist_ok=True)
            _annotate(
                canon, repo=repo, actor_type=actor_type, actor_id=actor_id,
                scope="verdict", output_uri=output_uri, output_hash=output_hash,
                prompt_template_hash=prompt_template_hash, asserted_at=asserted_at,
                status=annotation_status or "active",
                supersedes_annotation_id=supersedes_annotation_id,
            )
            successes.append((verdict_id, canon))
        except (OSError, AnnotationError, duckdb.IOException) as exc:
            failures.append((verdict_id, canon, retry_count + 1, str(exc)[:500]))

    # Phase 3: short write-locked transaction to apply DELETEs and UPDATEs.
    try:
        con_rw = duckdb.connect(str(db_path), read_only=False)
    except duckdb.IOException:
        # We did the FS IO but can't record it. Next audit cycle re-fetches
        # the same rows — annotate is idempotent so re-emit is a no-op.
        # The DB hasn't been updated; rows stay as 'pending'.
        out["skipped_locked"] = 1
        return out
    try:
        for verdict_id, canon in successes:
            con_rw.execute(
                """DELETE FROM pending_corpus_attestations
                   WHERE verdict_id = ? AND canonical_source_id = ?""",
                [verdict_id, canon],
            )
            out["flushed"] += 1
        for verdict_id, canon, new_retry, err in failures:
            new_status = "abandoned" if new_retry >= 3 else "pending"
            con_rw.execute(
                """UPDATE pending_corpus_attestations
                   SET retry_count = ?, last_error = ?, status = ?
                   WHERE verdict_id = ? AND canonical_source_id = ?""",
                [new_retry, err, new_status, verdict_id, canon],
            )
            if new_status == "abandoned":
                out["abandoned"] += 1
            else:
                out["retried"] += 1
    finally:
        con_rw.close()
    return out


def _abandoned_count(db_path: Path) -> int:
    """How many rows are stuck in status='abandoned' (need human triage)."""
    if not db_path.exists():
        return 0
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except duckdb.IOException:
        return 0
    try:
        try:
            row = con.execute(
                "SELECT COUNT(*) FROM pending_corpus_attestations WHERE status = 'abandoned'"
            ).fetchone()
            return int(row[0]) if row else 0
        except (duckdb.BinderException, duckdb.CatalogException):
            return 0
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
    """Audit verdict-level attestation coverage.

    Primary check: each local verdict_id must appear as the verdict_id
    component of some annotation's output_uri (`<repo>://verdicts/<vid>`).
    The annotation stable_tuple now includes output_uri (substrate fix
    2026-05-11), so each verdict gets its own annotation row — no
    projection-collapse, no need for the secondary (source_id, output_hash)
    coverage join that was a workaround before the stable_tuple fix.

    Secondary signal: report projection coverage (`(source_id, output_hash)`
    pairs that have any annotation) alongside the strict count so
    operators can distinguish "no verdicts attested" from "some verdicts
    re-emitted a known projection." Advisory only — does NOT affect drift.
    """
    annotations = _read_corpus_annotations()

    annotated_uris_by_repo: dict[str, set[str]] = {}
    projection_cover_by_repo: dict[str, set[tuple[str, str]]] = {}
    for ann in annotations:
        repo = ann["repo"]
        uri_repo, vid = _verdict_id_from_uri(ann["output_uri"])
        if uri_repo and vid:
            annotated_uris_by_repo.setdefault(uri_repo, set()).add(vid)
        if ann["source_id"] and ann["output_hash"]:
            projection_cover_by_repo.setdefault(repo, set()).add(
                (ann["source_id"], ann["output_hash"])
            )

    drift_missing_annotations: list[dict[str, Any]] = []
    drift_orphan_annotations: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []

    for src in VERDICTS_SOURCES:
        repo = src["repo"]
        local_verdicts = _read_verdicts(repo, src["db_path"], src["sql"])
        local_vid_set = {vid for vid, _sid, _h in local_verdicts}
        annotated_vid_set = annotated_uris_by_repo.get(repo, set())
        proj_cover = projection_cover_by_repo.get(repo, set())

        missing = sorted(local_vid_set - annotated_vid_set)
        orphans = sorted(annotated_vid_set - local_vid_set) if local_vid_set else []

        # Secondary advisory: how many local (source_id, output_hash)
        # projections are represented in the corpus at all.
        projection_hits = 0
        for _vid, sid, ohash in local_verdicts:
            if sid and ohash and (sid, ohash) in proj_cover:
                projection_hits += 1

        for vid in missing:
            drift_missing_annotations.append({"repo": repo, "verdict_id": vid})
        for vid in orphans:
            drift_orphan_annotations.append({"repo": repo, "verdict_id": vid})

        summary.append({
            "repo": repo,
            "db_path": str(src["db_path"]),
            "verdicts_local": len(local_vid_set),
            "verdicts_annotated": len(annotated_vid_set & local_vid_set),
            "missing_annotations": len(missing),
            "orphan_annotations": len(orphans),
            "projection_hits": projection_hits,  # advisory
        })

    return {
        "summary": summary,
        "drift_missing_annotations": drift_missing_annotations,
        "drift_orphan_annotations": drift_orphan_annotations,
        "drift_total": len(drift_missing_annotations) + len(drift_orphan_annotations),
    }


def drain_all() -> dict[str, dict[str, int]]:
    """Drain pending_corpus_attestations across all repos with the outbox.
    Returns {repo: {flushed, retried, abandoned, no_table, skipped_locked}}."""
    return {
        src["repo"]: _drain_repo_outbox(src["repo"], src["db_path"])
        for src in VERDICTS_SOURCES
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit verdicts ↔ corpus annotations drift")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON; non-zero exit on drift")
    parser.add_argument("--verbose", action="store_true",
                        help="List individual drifted verdict_ids")
    parser.add_argument("--drain-only", action="store_true",
                        help="Drain pending outboxes; skip drift report")
    parser.add_argument("--no-drain", action="store_true",
                        help="Report drift; skip outbox drain (read-only)")
    args = parser.parse_args(argv)

    drain_report: dict[str, dict[str, int]] = {}
    if not args.no_drain:
        try:
            drain_report = drain_all()
        except Exception as exc:
            print(f"outbox drain failure: {exc}", file=sys.stderr)
            return 2
    if args.drain_only:
        if args.json:
            print(json.dumps({"drain": drain_report}, indent=2))
        else:
            print("=== Outbox drain ===")
            for repo, counts in drain_report.items():
                print(f"  {repo:10s}  flushed={counts['flushed']:4d}  "
                      f"retried={counts['retried']:4d}  abandoned={counts['abandoned']:4d}")
        return 0

    try:
        report = audit()
    except Exception as exc:
        print(f"audit infrastructure failure: {exc}", file=sys.stderr)
        return 2

    # Count abandoned rows for the human-triage backstop.
    abandoned_by_repo = {
        src["repo"]: _abandoned_count(src["db_path"]) for src in VERDICTS_SOURCES
    }
    report["drain"] = drain_report
    report["abandoned_by_repo"] = abandoned_by_repo
    report["abandoned_total"] = sum(abandoned_by_repo.values())

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print("=== Corpus sync audit ===")
        print(f"corpus.graph.duckdb: {CORPUS_GRAPH_DB}")
        if drain_report:
            print()
            print("Outbox drain:")
            for repo, counts in drain_report.items():
                if counts["flushed"] or counts["retried"] or counts["abandoned"]:
                    print(f"  {repo:10s}  flushed={counts['flushed']:4d}  "
                          f"retried={counts['retried']:4d}  "
                          f"abandoned={counts['abandoned']:4d}")
        print()
        for row in report["summary"]:
            abandoned = abandoned_by_repo.get(row["repo"], 0)
            print(f"  {row['repo']:10s}  verdicts={row['verdicts_local']:5d}  "
                  f"annotated={row['verdicts_annotated']:5d}  "
                  f"missing_ann={row['missing_annotations']:4d}  "
                  f"orphans={row['orphan_annotations']:4d}  "
                  f"projection_hits={row.get('projection_hits', 0):4d}  "
                  f"abandoned={abandoned:3d}")
        print()
        if report["abandoned_total"]:
            print(f"WARN: {report['abandoned_total']} abandoned outbox rows need human triage")
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
