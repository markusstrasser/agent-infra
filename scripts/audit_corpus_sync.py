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

# Each per-repo verdicts source declares:
#   repo     — corpus_core.uri scheme + audit grouping key
#   db_path  — DuckDB containing the domain tables AND the outbox
#   scope    — corpus annotation scope (close-review #14: per-repo, not hardcoded)
#   natural_key_cols — outbox PK shape for that repo (close-review #21)
#   sql      — query producing (entity_id, source_id, output_hash) triples
#              for the verdicts↔annotations drift report. Missing-table is
#              tolerated (BinderException-swallowed); repos that don't write
#              the domain table yet appear as verdicts=0.
VERDICTS_SOURCES: list[dict[str, Any]] = [
    {
        "repo": "genomics",
        "db_path": PROJECTS_ROOT / "genomics" / "data" / "knowledge" / "knowledge.duckdb",
        "scope": "verdict",
        "natural_key_cols": ("verdict_id",),
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
        "scope": "cert_event",
        "natural_key_cols": ("cert_event_id",),
        # Phenome's verdict surface is the cert stack (Phase 3 of substrate-
        # v2-deferred shipped 2026-05-27). Each `issued` claim_certificate_event
        # bound to assertion_evidence with a canonical_source_id becomes one
        # attestation. DISTINCT collapses the same cert_event_id appearing
        # against multiple sources to one drift row per (event_id, source_id).
        # The output_hash is the SHA-256 hex digest of the cert (strip
        # phenome's `sha256:` prefix to match what corpus annotations carry).
        "sql": """
            SELECT DISTINCT
                cce.event_id AS verdict_id,
                ae.canonical_source_id AS source_id,
                CASE
                    WHEN cce.certificate_hash LIKE 'sha256:%'
                    THEN substr(cce.certificate_hash, 8)
                    ELSE cce.certificate_hash
                END AS output_hash
            FROM claim_certificate_events cce
            JOIN assertion_evidence ae
              ON ae.assertion_id = TRY_CAST(cce.target_id AS UUID)
            WHERE cce.event_kind = 'issued'
              AND cce.target_kind = 'assertion'
              AND ae.canonical_source_id IS NOT NULL
        """,
    },
    {
        "repo": "intel",
        "db_path": PROJECTS_ROOT / "intel" / "intel" / "indexed" / "theses.duckdb",
        # Phase I: contradiction events attest via the crosswalk. Audit
        # compares intel's local event_ids against the verdict_id slot of
        # `intel://contradiction_events/<vid>` corpus URIs.
        # source_id + output_hash are advisory (projection coverage); the
        # primary drift check is event_id presence in URIs.
        "scope": "contradiction_resolution",
        "natural_key_cols": ("contradiction_event_id",),
        "sql": (
            "SELECT crl.event_id::VARCHAR AS verdict_id, "
            "       '' AS source_id, "
            "       '' AS output_hash "
            "FROM contradiction_resolutions_log crl"
        ),
    },
]


_URI_RE = re.compile(r"^([a-z-]+)://(?:verdicts|cert_events|contradiction_events)/(.+)$")


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


def _ensure_corpus_core_importable() -> None:
    """corpus_core is an editable install in this monorepo. The audit script
    can run from cron / launchd / a thin venv that doesn't have it on
    sys.path; prepend the package dir so the import resolves."""
    cc_path = str(
        Path.home() / "Projects" / "agent-infra" / "scripts" / "corpus" / "packages" / "corpus-core"
    )
    if cc_path not in sys.path:
        sys.path.insert(0, cc_path)


def _drain_repo_outbox(src: dict[str, Any]) -> dict[str, int]:
    """Drain a per-repo outbox via corpus_core.outbox.drain (substrate-v2
    shared primitive). Lock-friendly drain owns its own connection pair —
    RO fetch, unlocked FS IO, RW DELETE/UPDATE. Drain stats normalized to
    the audit's existing reporting shape.

    Per-repo config (scope, natural_key_cols) comes from VERDICTS_SOURCES,
    not hardcoded — close-review #14/#21 resolution. Adding a new repo
    means appending one dict to VERDICTS_SOURCES.
    """
    _ensure_corpus_core_importable()
    from corpus_core.outbox import drain

    stats = drain(
        src["db_path"],
        repo=src["repo"],
        scope=src["scope"],
        natural_key_cols=src["natural_key_cols"],
    )
    return {
        "flushed": stats.flushed,
        "retried": stats.retried,
        "abandoned": stats.abandoned,
        # `no_table` / `skipped_locked` flags were used by the prior bespoke
        # drainer to distinguish steady-state cases from active progress.
        # The shared drain treats both as "drained zero rows"; the audit
        # consumer downstream only cares about positive activity counts.
        "no_table": 0,
        "skipped_locked": 0,
    }


def _abandoned_count(db_path: Path) -> int:
    """Delegate to corpus_core.outbox.abandoned_count — graceful on missing
    DB / missing table / locked DB."""
    _ensure_corpus_core_importable()
    from corpus_core.outbox import abandoned_count

    return abandoned_count(db_path)


def _read_corpus_annotations() -> list[dict[str, Any]]:
    """All annotations from any per-repo emission scope in VERDICTS_SOURCES.

    Scope filter is derived from per-repo config (close-review #14/#21):
    each VERDICTS_SOURCES entry declares its scope (e.g. 'verdict',
    'cert_event'). Previously hardcoded to 'verdict', which made phenome's
    cert_event annotations invisible to the audit even when the emission
    pipeline was working end-to-end.
    """
    if not CORPUS_GRAPH_DB.exists():
        return []
    scopes = sorted({src["scope"] for src in VERDICTS_SOURCES if src.get("scope")})
    if not scopes:
        return []
    placeholders = ",".join(["?"] * len(scopes))
    con = duckdb.connect(str(CORPUS_GRAPH_DB), read_only=True)
    try:
        # Phase A: read annotations_current (chain-aware view) so
        # superseded attestations don't inflate the drift count.
        rows = con.execute(
            "SELECT annotation_id, source_id, repo, output_uri, output_hash, "
            "       recorded_at, scope "
            f"FROM annotations_current WHERE scope IN ({placeholders})",
            scopes,
        ).fetchall()
    finally:
        con.close()
    return [
        {"annotation_id": r[0], "source_id": r[1], "repo": r[2],
         "output_uri": r[3], "output_hash": r[4] or "", "recorded_at": r[5],
         "scope": r[6]}
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
    return {src["repo"]: _drain_repo_outbox(src) for src in VERDICTS_SOURCES}


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
