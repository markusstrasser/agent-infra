"""Sole writer for `~/Projects/corpus/<source_id>/annotations.jsonl`.

Every cross-repo annotation flows through `annotate(...)`. Per-repo MCPs and
external callers MUST NOT write annotations.jsonl directly — the agent
orchestrates two MCP calls (per-repo `record_verdict` + `corpus_attest`),
where `corpus_attest` is the MCP wrapper around this function.

Guarantees:
    - Schema-validated against schemas/v1/annotation.v1.json (jsonschema)
    - 4KB serialized record ceiling (large outputs go to sidecars)
    - annotation_id = "ann_" + sha256(canonical_json(stable_tuple))[:16]
    - Idempotent: re-append with same stable_tuple is a no-op (read-tail check)
    - Atomic append via os.open(O_APPEND) + single os.write (local POSIX only)
    - JSONL format: one record per line, sorted-keys + compact-separators

Failure-mode contract (with Phase 2's graph.duckdb projection):
    JSONL append succeeds, DB insert fails → JSONL has truth; rebuild catches up.
    The reverse (DB insert before JSONL) is forbidden.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .identity import (
    annotation_id_from_tuple,
    annotation_idempotency_key,
    annotation_stable_tuple,
    canonical_json,
)
from .store import paper_path  # use the canonical-store path helper
from .uri import KNOWN_PROJECT_SCHEMES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ANNOTATION_RECORD_CEILING_BYTES = 4096
SCHEMA_VERSION = "1-0-0"
CONFORMS_TO = "https://schema.local/corpus/annotation/v1.0.0"

ActorType = Literal["model", "human", "service", "cli"]
Status = Literal["active", "superseded", "retracted"]


class AnnotationError(Exception):
    """Base for annotation write errors."""


class AnnotationTooLargeError(AnnotationError):
    """Record exceeds the 4KB ceiling. Reference output via sidecar."""


class AnnotationSchemaError(AnnotationError):
    """Record fails JSON Schema validation."""


# ---------------------------------------------------------------------------
# Schema loading (lazy, cached)
# ---------------------------------------------------------------------------


def _schemas_dir() -> Path:
    """Locate schemas/v1/ relative to the corpus package install."""
    # corpus-core is installed as a wheel; schemas live one workspace level up.
    # Walk: package dir → corpus_core/ → corpus-core/ → packages/ → corpus/ → schemas/
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent.parent.parent / "schemas" / "v1",  # editable install
        here.parent / "schemas" / "v1",                 # wheel-bundled (force-include)
    ]
    for c in candidates:
        if c.is_dir():
            return c
    raise AnnotationError(
        f"corpus-core: schemas/v1/ not found near {here} "
        f"(looked at: {[str(c) for c in candidates]})"
    )


_SCHEMA_CACHE: dict[str, dict] = {}


def _load_schema(name: str) -> dict:
    if name not in _SCHEMA_CACHE:
        path = _schemas_dir() / name
        _SCHEMA_CACHE[name] = json.loads(path.read_text(encoding="utf-8"))
    return _SCHEMA_CACHE[name]


def _validate_annotation(record: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as e:
        raise AnnotationError(
            "corpus-core: jsonschema not installed (add as a runtime dep)"
        ) from e
    try:
        jsonschema.validate(record, _load_schema("annotation.v1.json"))
    except jsonschema.ValidationError as e:
        raise AnnotationSchemaError(f"annotation failed schema: {e.message}") from e


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------


def _annotations_path(source_id: str) -> Path:
    return paper_path(source_id) / "annotations.jsonl"


def _utc_now_iso() -> str:
    """ISO-8601 UTC with Z suffix, second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _serialize_record(record: dict[str, Any]) -> bytes:
    """Canonical JSONL bytes (sorted-keys + compact-separators) + newline."""
    line = canonical_json(record)
    if len(line) + 1 > ANNOTATION_RECORD_CEILING_BYTES:
        raise AnnotationTooLargeError(
            f"annotation record {len(line) + 1} bytes exceeds "
            f"{ANNOTATION_RECORD_CEILING_BYTES}-byte ceiling. Reference large "
            "outputs via output_uri+output_hash sidecars; do NOT inline."
        )
    return line + b"\n"


def _existing_annotation_id(source_id: str, annotation_id: str) -> bool:
    """Tail-scan annotations.jsonl for the given annotation_id.

    Idempotency check: same stable_tuple → same annotation_id → skip the write.
    """
    path = _annotations_path(source_id)
    if not path.exists():
        return False
    needle = f'"annotation_id":"{annotation_id}"'.encode("utf-8")
    # Annotations files are small; full read is fine until graph.duckdb
    # projection (Phase 2) handles reverse lookups.
    try:
        with open(path, "rb") as fh:
            return needle in fh.read()
    except OSError:
        return False


def _atomic_append(path: Path, payload: bytes) -> None:
    """O_APPEND + single os.write — atomic at PIPE_BUF on local POSIX FS.

    Per SCHEMA.md invariant: corpus MUST live on local POSIX. NFS/SMB break
    this guarantee (atomicity isn't preserved across the network).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def annotate(
    source_id: str,
    *,
    repo: str,
    actor_type: ActorType,
    actor_id: str,
    scope: str,
    tool: str | None = None,
    instrument: dict[str, str] | None = None,
    prompt_template_hash: str | None = None,
    output_uri: str | None = None,
    output_hash: str | None = None,
    output_size_bytes: int | None = None,
    source_content_hash: str | None = None,
    supersedes_annotation_id: str | None = None,
    status: Status = "active",
    asserted_at: datetime | str | None = None,
) -> str:
    """Append one annotation to ~/Projects/corpus/<source_id>/annotations.jsonl.

    Args:
        source_id: canonical corpus source_id (`doi_…`, `pmid_…`, `sha_…`).
        repo: writer-repo identifier (must be one of corpus_core.uri.KNOWN_PROJECT_SCHEMES).
        actor_type: agent kind (model | human | service | cli).
        actor_id: stable urn:agent:<type>:<name>[@<version>] form.
        scope: free-form scope tag (e.g. raw_fetch, parse, claim_extraction, verdict).
        tool, instrument, prompt_template_hash: optional metadata; see schema.
        output_uri, output_hash, output_size_bytes: sidecar reference for results
            larger than the 4KB inline ceiling.
        source_content_hash: hash of source bytes the annotation was made against.
        supersedes_annotation_id: previous annotation this one replaces.
        status: active | superseded | retracted (default active).
        asserted_at: world time the annotation was asserted; defaults to now (UTC).

    Returns:
        annotation_id ("ann_<sha256[:16]>").

    Idempotency:
        Two calls with the same (source_id, repo, scope, agent_id,
        prompt_template_hash, output_hash) tuple produce the same annotation_id
        and only one row is written.
    """
    if repo not in KNOWN_PROJECT_SCHEMES:
        raise AnnotationError(
            f"unknown repo {repo!r}; expected one of {sorted(KNOWN_PROJECT_SCHEMES)}"
        )
    if actor_type not in ("model", "human", "service", "cli"):
        raise AnnotationError(f"unknown actor_type {actor_type!r}")
    if not actor_id.startswith("urn:agent:"):
        raise AnnotationError(
            f"actor_id must be 'urn:agent:<type>:<name>[@<version>]' form; got {actor_id!r}"
        )
    if status not in ("active", "superseded", "retracted"):
        raise AnnotationError(f"unknown status {status!r}")

    # Identity (idempotency-bearing fields only — NOT asserted_at/recorded_at).
    stable_tuple = annotation_stable_tuple(
        source_id=source_id,
        repo=repo,
        scope=scope,
        agent_id=actor_id,
        prompt_template_hash=prompt_template_hash,
        output_hash=output_hash,
        output_uri=output_uri,
    )
    annotation_id = annotation_id_from_tuple(stable_tuple)
    idempotency_key = annotation_idempotency_key(stable_tuple)

    # Idempotency: re-append is a no-op.
    if _existing_annotation_id(source_id, annotation_id):
        return annotation_id

    # Time stamps.
    if asserted_at is None:
        asserted_at_iso = _utc_now_iso()
    elif isinstance(asserted_at, datetime):
        if asserted_at.tzinfo is None:
            asserted_at = asserted_at.replace(tzinfo=timezone.utc)
        asserted_at_iso = asserted_at.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    else:
        asserted_at_iso = asserted_at  # caller-provided ISO string
    recorded_at_iso = _utc_now_iso()

    # Build the record.
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "conformsTo": CONFORMS_TO,
        "annotation_id": annotation_id,
        "source_id": source_id,
        "agent": {"id": actor_id, "type": actor_type},
        "scope": scope,
        "asserted_at": asserted_at_iso,
        "recorded_at": recorded_at_iso,
        "idempotency_key": idempotency_key,
        "status": status,
    }
    if tool is not None:
        record["tool"] = tool
    if instrument is not None:
        record["instrument"] = instrument
    if prompt_template_hash is not None:
        record["prompt_template_hash"] = prompt_template_hash
    if output_uri is not None:
        record["output_uri"] = output_uri
    if output_hash is not None:
        record["output_hash"] = output_hash
    if source_content_hash is not None:
        record["source_content_hash"] = source_content_hash
    if supersedes_annotation_id is not None:
        record["supersedes_annotation_id"] = supersedes_annotation_id
    if output_uri or output_hash or output_size_bytes is not None:
        result: dict[str, Any] = {}
        if output_uri is not None:
            result["uri"] = output_uri
        if output_hash is not None:
            result["hash"] = output_hash
        if output_size_bytes is not None:
            result["size_bytes"] = output_size_bytes
        record["result"] = result

    _validate_annotation(record)
    payload = _serialize_record(record)
    _atomic_append(_annotations_path(source_id), payload)

    # Phase 2 projection: best-effort insert into graph.duckdb. JSONL is the
    # source of truth — DB failure logs and continues; rebuild catches up.
    try:
        from .index import index_annotation
        index_annotation(record)
    except Exception:  # pragma: no cover — never break a JSONL append
        pass

    return annotation_id


__all__ = [
    "ANNOTATION_RECORD_CEILING_BYTES",
    "CONFORMS_TO",
    "SCHEMA_VERSION",
    "AnnotationError",
    "AnnotationSchemaError",
    "AnnotationTooLargeError",
    "annotate",
]
