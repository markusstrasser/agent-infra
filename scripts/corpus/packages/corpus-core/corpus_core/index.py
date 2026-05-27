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

from .store import iter_papers, paper_path, store_root


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
    finally:
        con.close()


def rebuild_annotations_index(graph_db_path: Path | None = None) -> dict[str, int]:
    """Walk every source dir with an annotations.jsonl, replace the annotations
    table.

    Idempotent: TRUNCATE + bulk INSERT. Returns {sources_scanned, rows_written}.

    Source discovery walks the corpus root directly (one level deep) and
    selects any subdir containing annotations.jsonl — NOT just dirs with
    metadata.json. Synthetic annotation-only sources (e.g. genomics' verdict
    sources `pubmed_asof`, `pubmed_conflict` written by the substrate-v2
    backfill without ingest) are valid attestation targets even without a
    metadata.json. Using iter_papers() here previously dropped these
    annotations on rebuild — the per-call index_annotation path inserted
    them, then the rebuild nuked them.
    """
    from .store import store_root

    con = _connect(graph_db_path)
    try:
        # TRUNCATE first so removed entries (theoretical — JSONL is append-only)
        # don't linger.
        con.execute("DELETE FROM annotations")
        sources_scanned = 0
        rows_written = 0
        root = store_root()
        if not root.is_dir():
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
        return {"sources_scanned": sources_scanned, "rows_written": rows_written}
    finally:
        con.close()


__all__ = ["index_annotation", "rebuild_annotations_index"]
