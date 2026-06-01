"""Derived `annotations` table in graph.duckdb.

Per-source `~/Projects/corpus/<source_id>/annotations.jsonl` files remain the
SOURCE OF TRUTH. This module projects them into a DuckDB table for reverse
queries (e.g. "all phenome activity yesterday", "all sources processed by X").

Failure-mode contract (Phase 2 of substrate-migration plan):
    JSONL append succeeds, DB insert fails  → JSONL has truth; rebuild catches up.
    DB insert before JSONL append           → forbidden (annotate.py enforces order).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, Optional

from .store import paper_path, store_root


# Columns in the order INSERT expects.
_COLS = (
    "annotation_id",
    "source_id",
    "source_type",
    "repo",
    "actor_type",
    "actor_id",
    "scope",
    "tool",
    "prompt_template_hash",
    "output_uri",
    "output_hash",
    "source_content_hash",
    "supersedes_annotation_id",
    "status",
    "asserted_at",
    "recorded_at",
    "schema_version",
    "valid_from",
)

# claim_relations projection columns (epistemic core), in INSERT order.
_REL_COLS = (
    "relation_id",
    "annotation_id",
    "anchor_source_id",
    "relation_class",
    "kind",
    "grade_weight",
    "detector",
    "home_pair_id",
    "home_verdict_id",
    "repo",
    "status",
    "asserted_at",
    "recorded_at",
)


def _connect(graph_db_path: Path | None = None):
    """Open the graph.duckdb (read-write); ensure schema is applied."""
    import duckdb  # type: ignore

    db_path = graph_db_path or (store_root() / "graph.duckdb")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    schema_sql = (Path(__file__).parent / "graph_schema.sql").read_text()
    con.execute(schema_sql)
    return con


def _row_from_record(record: dict[str, Any], *, source_type: Optional[str]) -> tuple:
    """Project a JSONL record + source_type to the column tuple INSERT expects."""
    agent = record.get("agent") or {}
    return (
        record["annotation_id"],
        record["source_id"],
        source_type,
        _derive_repo(record),
        agent.get("type"),
        agent.get("id"),
        record["scope"],
        record.get("tool"),
        record.get("prompt_template_hash"),
        record.get("output_uri"),
        record.get("output_hash"),
        record.get("source_content_hash"),
        record.get("supersedes_annotation_id"),
        record.get("status", "active"),
        record["asserted_at"],
        record["recorded_at"],
        record["schema_version"],
        # Phase A: valid_from is informational; pre-A records lack it,
        # so we fall back to asserted_at (matches the annotate() default).
        record.get("valid_from") or record["asserted_at"],
    )


def _derive_repo(record: dict[str, Any]) -> str:
    """Recover the writer repo from the idempotency_key (canonical-JSON of stable tuple).

    The annotation schema doesn't carry `repo` as a top-level field — it's
    embedded in idempotency_key (which preserves it via the canonical-tuple).
    """
    key = record.get("idempotency_key", "")
    try:
        tup = json.loads(key)
    except (json.JSONDecodeError, TypeError):
        return "unknown"
    repo = tup.get("repo")
    return repo if isinstance(repo, str) else "unknown"


def _read_metadata_source_type(source_id: str) -> Optional[str]:
    meta_path = paper_path(source_id) / "metadata.json"
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    val = meta.get("source_type")
    return val if isinstance(val, str) else None


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _relation_rows(
    record: dict[str, Any],
) -> Optional[tuple[tuple, list[tuple[str, str, str]]]]:
    """Project a claim_relation-bearing annotation record into
    (claim_relations row, endpoint rows). Returns None for non-relation records
    or malformed relation bodies (missing relation_id / endpoints).

    The anchor endpoint is namespaced `corpus:<source_id>` so a single
    endpoint_ref lookup catches anchored relations AND object/subject mentions
    of the same paper.
    """
    rel = record.get("relation")
    if not isinstance(rel, dict):
        return None
    rid = rel.get("relation_id")
    subjects = rel.get("subject_refs") or []
    objects = rel.get("object_refs") or []
    if not rid or not rel.get("relation_class") or not subjects or not objects:
        return None
    source_id = record["source_id"]
    rrow = (
        rid,
        record["annotation_id"],
        source_id,
        rel["relation_class"],
        rel.get("kind"),
        rel.get("grade_weight"),
        rel.get("detector") or "",
        rel.get("home_pair_id"),
        rel.get("home_verdict_id"),
        _derive_repo(record),
        record.get("status", "active"),
        record.get("asserted_at"),
        record.get("recorded_at"),
    )
    # Endpoints are a SET per role (dedup): a duplicate ref must not produce a
    # duplicate endpoint row and must match the set-based relation_id identity.
    eps: list[tuple[str, str, str]] = []
    for ref in dict.fromkeys(subjects):
        eps.append((rid, ref, "subject"))
    for ref in dict.fromkeys(objects):
        eps.append((rid, ref, "object"))
    eps.append((rid, f"corpus:{source_id}", "anchor"))
    return rrow, eps


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def index_annotation(record: dict[str, Any], graph_db_path: Path | None = None) -> None:
    """Insert (or replace) one annotation row into graph.duckdb.

    Called from `corpus_core.annotate.annotate()` AFTER a successful JSONL
    append. Failures bubble to the caller — annotate() will swallow them since
    JSONL is the source of truth and the rebuild script can backfill.
    """
    con = _connect(graph_db_path)
    try:
        source_type = _read_metadata_source_type(record["source_id"])
        row = _row_from_record(record, source_type=source_type)
        # INSERT OR REPLACE — idempotent on annotation_id (the primary key).
        placeholders = ",".join(["?"] * len(_COLS))
        con.execute(
            f"INSERT OR REPLACE INTO annotations ({','.join(_COLS)}) "
            f"VALUES ({placeholders})",
            row,
        )
        _index_relation(con, record)
    finally:
        con.close()


def _index_relation(con, record: dict[str, Any]) -> None:
    """Best-effort per-write projection of a claim_relation into
    claim_relations + claim_relation_endpoints. A superseding relation drops
    the relation(s) carried by the annotation it supersedes (current-leaf
    semantics). No-op for non-relation records. The authoritative idempotent
    rebuild is `rebuild_claim_relations`; this keeps the projection fresh on
    each write without a full rescan."""
    rows = _relation_rows(record)
    if rows is None:
        return
    rrow, eps = rows
    sup = record.get("supersedes_annotation_id")
    if sup:
        # Tombstone the superseded annotation_id FIRST (order-independent), then
        # drop its projected relation. The tombstone persists even if the
        # superseded relation has not been indexed yet.
        con.execute(
            "INSERT OR IGNORE INTO claim_relation_tombstones "
            "(superseded_annotation_id) VALUES (?)",
            [sup],
        )
        con.execute(
            "DELETE FROM claim_relation_endpoints WHERE relation_id IN "
            "(SELECT relation_id FROM claim_relations WHERE annotation_id = ?)",
            [sup],
        )
        con.execute("DELETE FROM claim_relations WHERE annotation_id = ?", [sup])
    # If THIS relation's annotation was already superseded by an earlier-arriving
    # retraction (out-of-order drain), project it as 'superseded' — never as a
    # stale-active leaf. This makes the incremental path agree with rebuild.
    ann_id = rrow[1]
    if rrow[10] == "active" and con.execute(
        "SELECT 1 FROM claim_relation_tombstones WHERE superseded_annotation_id = ?",
        [ann_id],
    ).fetchone():
        rrow = (*rrow[:10], "superseded", *rrow[11:])
    placeholders = ",".join(["?"] * len(_REL_COLS))
    con.execute(
        f"INSERT OR REPLACE INTO claim_relations ({','.join(_REL_COLS)}) "
        f"VALUES ({placeholders})",
        rrow,
    )
    con.execute(
        "DELETE FROM claim_relation_endpoints WHERE relation_id = ?", [rrow[0]]
    )
    con.executemany(
        "INSERT OR REPLACE INTO claim_relation_endpoints "
        "(relation_id, endpoint_ref, role) VALUES (?,?,?)",
        eps,
    )


def rebuild_annotations_index(graph_db_path: Path | None = None) -> dict[str, int]:
    """Walk every source dir with an annotations.jsonl, replace the annotations
    table.

    Idempotent: TRUNCATE + bulk INSERT. Returns {sources_scanned, rows_written}.

    Source discovery walks the corpus root directly (one level deep) and
    selects any subdir containing annotations.jsonl — NOT just dirs with
    metadata.json. A legitimate annotation-only synthetic source (one written
    by a substrate backfill without a separate ingest, hence no metadata.json)
    is still a valid attestation target. Using iter_papers() here previously
    dropped such sources on rebuild — the per-call index_annotation path
    inserted them, then the rebuild nuked them.

    NOTE: the earlier version of this docstring cited `pubmed_asof` /
    `pubmed_conflict` as examples of legitimate synthetic sources. Those were
    actually test-fixture pollution (actor `urn:agent:model:m1`, verdict_ids
    absent from genomics' claim_verdicts) that leaked into the live corpus
    before the test-isolation autouse fixtures landed; they were removed
    2026-06-01 (E1). The iterdir-not-iter_papers behaviour above is still
    correct as a general invariant — it just had a mislabeled example.
    """
    from .store import store_root

    con = _connect(graph_db_path)
    try:
        # Plan-close finding #3 (CONFIRMED): rebuild is now wrapped in
        # an explicit transaction. Pre-fix, a crash between DELETE and
        # the bulk INSERT left the index empty until the next rebuild.
        # BEGIN/COMMIT scopes the DELETE+INSERT atomically; ROLLBACK
        # on any exception preserves the prior projection state.
        con.execute("BEGIN TRANSACTION")
        # TRUNCATE first so removed entries (theoretical — JSONL is append-only)
        # don't linger.
        con.execute("DELETE FROM annotations")
        sources_scanned = 0
        rows_written = 0
        root = store_root()
        if not root.is_dir():
            con.execute("COMMIT")
            return {"sources_scanned": 0, "rows_written": 0}
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            jsonl = entry / "annotations.jsonl"
            if not jsonl.exists():
                continue
            sid = entry.name
            sources_scanned += 1
            # source_type lookup tolerates missing metadata.json — returns
            # the default ('paper') in that case. Annotations carry their
            # own scope; the source_type is index-side metadata.
            source_type = _read_metadata_source_type(sid)
            batch = []
            for record in _iter_jsonl(jsonl):
                try:
                    batch.append(_row_from_record(record, source_type=source_type))
                except (KeyError, TypeError):
                    # Skip malformed records — surfaced as a row-count delta.
                    continue
            if batch:
                placeholders = ",".join(["?"] * len(_COLS))
                con.executemany(
                    f"INSERT OR REPLACE INTO annotations ({','.join(_COLS)}) "
                    f"VALUES ({placeholders})",
                    batch,
                )
                rows_written += len(batch)
        con.execute("COMMIT")
        return {"sources_scanned": sources_scanned, "rows_written": rows_written}
    except Exception:
        # Rollback on any failure mid-rebuild — leaves the projection at
        # its prior state instead of a partial (DELETE'd but not yet
        # repopulated) intermediate.
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        con.close()


def active_annotations_for_source(
    source_id: str, *, db_path: Path | None = None
) -> list[dict[str, Any]]:
    """Active (current-leaf) annotations for a source — the read-loop primitive.

    An agent about to act on a source uses this to SEE what's already been
    attested about it (active verdicts, retractions) before re-deriving. This is
    the READ half of the attestation ledger; without it the ledger is write-only
    (the substrate-v1 ritual got ~0 read invocations in 9 months because no read
    path was wired into agent context). Surfaced by `corpus_lookup` so the verdict
    rides along the lookup an agent already does.

    Queries the `annotations_current` view (annotations with no successor).
    Fail-soft: returns [] if duckdb or graph.duckdb is unavailable.
    """
    from .store import graph_db_path
    path = Path(db_path) if db_path else graph_db_path()
    if not path.exists():
        return []
    try:
        import duckdb
    except ImportError:
        return []
    try:
        con = duckdb.connect(str(path), read_only=True)
        rows = con.execute(
            "SELECT annotation_id, repo, scope, output_uri, status, recorded_at "
            "FROM annotations_current WHERE source_id = ? ORDER BY recorded_at DESC",
            [source_id],
        ).fetchall()
        con.close()
    except Exception:
        return []
    return [
        {"annotation_id": r[0], "repo": r[1], "scope": r[2],
         "output_uri": r[3], "status": r[4], "recorded_at": r[5]}
        for r in rows
    ]


def rebuild_claim_relations(graph_db_path: Path | None = None) -> dict[str, int]:
    """Rebuild claim_relations + claim_relation_endpoints from the JSONL ledger.

    Authoritative + idempotent: TRUNCATE both tables, scan every
    annotations.jsonl, keep only CURRENT-LEAF relation records (annotation_id
    not superseded by any other record) and drop retracted/superseded ones from
    the active surface. Returns a health report so a standing audit can catch
    projection drift (the substrate's measure-before-trust discipline).

    Cross-repo participant liveness is NOT introspected here — the home repo
    emits a superseding relation when a participant dies, which this rebuild
    then honours via the supersession chain.
    """
    con = _connect(graph_db_path)
    try:
        con.execute("BEGIN TRANSACTION")
        con.execute("DELETE FROM claim_relation_endpoints")
        con.execute("DELETE FROM claim_relations")
        con.execute("DELETE FROM claim_relation_tombstones")
        root = store_root()
        report = {
            "sources_scanned": 0,
            "relations_seen": 0,
            "relations_active": 0,
            "relations_retracted": 0,
            "relations_superseded": 0,
            "relations_malformed": 0,
            "endpoints_written": 0,
            "participants_unresolved": 0,
        }
        if not root.is_dir():
            con.execute("COMMIT")
            return report

        records: list[dict[str, Any]] = []
        superseded: set[str] = set()
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            jsonl = entry / "annotations.jsonl"
            if not jsonl.exists():
                continue
            has_relation = False
            for record in _iter_jsonl(jsonl):
                if not record.get("relation"):
                    continue
                has_relation = True
                records.append(record)
                sup = record.get("supersedes_annotation_id")
                if sup:
                    superseded.add(sup)
            if has_relation:
                report["sources_scanned"] += 1

        report["relations_seen"] = len(records)
        # Repopulate tombstones so the incremental path stays order-independent
        # after a rebuild (every superseded annotation_id is recorded, even if
        # its relation record is absent/not-yet-arrived).
        if superseded:
            con.executemany(
                "INSERT OR IGNORE INTO claim_relation_tombstones "
                "(superseded_annotation_id) VALUES (?)",
                [(s,) for s in superseded],
            )
        rel_placeholders = ",".join(["?"] * len(_REL_COLS))
        for record in records:
            if record.get("annotation_id") in superseded:
                report["relations_superseded"] += 1
                continue
            rows = _relation_rows(record)
            if rows is None:
                report["relations_malformed"] += 1
                continue
            rrow, eps = rows
            con.execute(
                f"INSERT OR REPLACE INTO claim_relations ({','.join(_REL_COLS)}) "
                f"VALUES ({rel_placeholders})",
                rrow,
            )
            con.executemany(
                "INSERT OR REPLACE INTO claim_relation_endpoints "
                "(relation_id, endpoint_ref, role) VALUES (?,?,?)",
                eps,
            )
            report["endpoints_written"] += len(eps)
            if rrow[10] == "retracted":
                report["relations_retracted"] += 1
            elif rrow[10] == "active":
                report["relations_active"] += 1
            for _rid, ref, role in eps:
                if role in ("subject", "object") and ref.startswith("corpus:"):
                    sid = ref[len("corpus:"):]
                    if not (root / sid).is_dir():
                        report["participants_unresolved"] += 1
        con.execute("COMMIT")
        return report
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        con.close()


def active_relations_for_source(
    source_id: str, *, db_path: Path | None = None
) -> list[dict[str, Any]]:
    """Active claim_relations touching a source — the conflict read-loop primitive.

    Returns every ACTIVE relation in which `source_id` participates as anchor,
    subject, or object (discovered through the namespaced `corpus:<source_id>`
    endpoint). Each relation carries its class, grounded detector, originating
    repo, round-trip ids, and its subject/object endpoints. An agent about to
    reuse a paper/claim calls this (via corpus_lookup) to SEE active refutations
    or qualifications before acting. Fail-soft: [] if duckdb/graph.duckdb absent.
    """
    from .store import graph_db_path
    path = Path(db_path) if db_path else graph_db_path()
    if not path.exists():
        return []
    try:
        import duckdb
    except ImportError:
        return []
    ref = f"corpus:{source_id}"
    try:
        con = duckdb.connect(str(path), read_only=True)
    except Exception:
        return []
    try:
        try:
            rel_rows = con.execute(
                "SELECT relation_id, relation_class, kind, grade_weight, detector, "
                "repo, home_pair_id, home_verdict_id, anchor_source_id "
                "FROM claim_relations_active "
                "WHERE relation_id IN ("
                "  SELECT relation_id FROM claim_relation_endpoints WHERE endpoint_ref = ?"
                ") ORDER BY recorded_at DESC",
                [ref],
            ).fetchall()
            ep_rows = con.execute(
                "SELECT e.relation_id, e.endpoint_ref, e.role "
                "FROM claim_relation_endpoints e "
                "JOIN claim_relations_active a ON a.relation_id = e.relation_id "
                "WHERE a.relation_id IN ("
                "  SELECT relation_id FROM claim_relation_endpoints WHERE endpoint_ref = ?"
                ")",
                [ref],
            ).fetchall()
        except Exception:
            return []
    finally:
        con.close()
    endpoints: dict[str, dict[str, list[str]]] = {}
    for rid, eref, role in ep_rows:
        slot = endpoints.setdefault(rid, {"subject": [], "object": [], "anchor": []})
        slot.setdefault(role, []).append(eref)
    out = []
    for r in rel_rows:
        rid = r[0]
        eps = endpoints.get(rid, {"subject": [], "object": [], "anchor": []})
        out.append({
            "relation_id": rid,
            "relation_class": r[1],
            "kind": r[2],
            "grade_weight": r[3],
            "detector": r[4],
            "repo": r[5],
            "home_pair_id": r[6],
            "home_verdict_id": r[7],
            "anchor_source_id": r[8],
            "subjects": eps.get("subject", []),
            "objects": eps.get("object", []),
        })
    return out


def support_balance_for_source(
    source_id: str, *, db_path: Path | None = None
) -> dict[str, Any] | None:
    """The linear support_balance row for a corpus source (keyed by its
    namespaced `corpus:<source_id>` ref). Returns None when the source has no
    active relations. The scalar is a transparent sign-weighted tally — NOT a
    probability. Fail-soft: None if duckdb/graph.duckdb/view absent."""
    from .store import graph_db_path
    path = Path(db_path) if db_path else graph_db_path()
    if not path.exists():
        return None
    try:
        import duckdb
    except ImportError:
        return None
    try:
        con = duckdb.connect(str(path), read_only=True)
    except Exception:
        return None
    try:
        try:
            row = con.execute(
                "SELECT support_balance, relation_count, n_refute, n_support, "
                "n_qualify, n_extend FROM support_balance WHERE claim_ref = ?",
                [f"corpus:{source_id}"],
            ).fetchone()
        except Exception:
            return None
    finally:
        con.close()
    if row is None:
        return None
    return {
        "support_balance": row[0],
        "relation_count": row[1],
        "n_refute": row[2],
        "n_support": row[3],
        "n_qualify": row[4],
        "n_extend": row[5],
    }


def epistemic_surface(
    source_id: str,
    *,
    retraction_status: str = "unknown",
    db_path: Path | None = None,
) -> dict[str, Any]:
    """The read-loop epistemic surface for a source — active verdicts AND active
    claim relations it participates in (the conflict half) AND the linear
    support_balance. This is what an agent SEES when it looks a source up before
    reusing it (the architectural read loop; extends the shipped retraction-only
    surface to full conflict). Pure + fail-soft — the home of the read-loop
    logic so it is testable without the MCP layer; corpus_mcp just exposes it.
    """
    active_ann = active_annotations_for_source(source_id, db_path=db_path)
    active_rels = active_relations_for_source(source_id, db_path=db_path)
    balance = support_balance_for_source(source_id, db_path=db_path)
    # Conflict fires only when THIS source is the OBJECT of a refute/qualify
    # (it is being refuted) — NOT when it is the subject (the refuter). A
    # gold-standard db_source used to refute a wrong claim must not show
    # conflict=true on its own lookup (close-review: cross-model).
    own_ref = f"corpus:{source_id}"
    refuting = [
        r for r in active_rels
        if r.get("relation_class") == "refute" and own_ref in (r.get("objects") or [])
    ]
    qualifying = [
        r for r in active_rels
        if r.get("relation_class") == "qualify" and own_ref in (r.get("objects") or [])
    ]
    return {
        "active_annotations": active_ann,
        "active_relations": active_rels,
        "epistemic": {
            "paper_retraction_status": retraction_status,
            "active_verdict_count": len(active_ann),
            "attesting_repos": sorted({a["repo"] for a in active_ann if a.get("repo")}),
            "retracted_annotations": [a for a in active_ann if a.get("status") == "retracted"],
            "conflict": len(refuting) > 0,
            "active_relation_count": len(active_rels),
            "refuting_relations": refuting,
            "qualifying_relations": qualifying,
            "support_balance": balance,  # linear tally, NOT a probability; None if no relations
        },
    }


__all__ = [
    "index_annotation",
    "rebuild_annotations_index",
    "rebuild_claim_relations",
    "active_annotations_for_source",
    "active_relations_for_source",
    "support_balance_for_source",
    "epistemic_surface",
]
