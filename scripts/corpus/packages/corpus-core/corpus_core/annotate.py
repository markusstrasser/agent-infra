"""Sole writer for ``<corpus-root>/<source_id>/annotations.jsonl``.

Every cross-repo annotation flows through `annotate(...)`. Per-repo MCPs and
external callers MUST NOT write annotations.jsonl directly — repos enqueue
attestation intent in their mutation gateway's transactional outbox
(`pending_corpus_attestations`), which drains via `corpus_core.outbox.drain`
into this function. (The v1 `record_verdict` + `corpus_attest` MCP ritual was
retired 2026-05-26 per substrate-v2 — 0 invocations in 9 months.)

Guarantees:
    - Schema-validated against schemas/v1/annotation.v1.json (jsonschema)
    - 16KB serialized record ceiling (a claim_relation rides inline; genuinely
      large outputs like parses still go to output_uri sidecars)
    - annotation_id = "ann_" + sha256(canonical_json(stable_tuple))[:16]
    - Idempotent: re-append with same stable_tuple is a no-op (read-tail check)
    - Atomic append via os.open(O_APPEND) + single os.write (local POSIX only)
    - JSONL format: one record per line, sorted-keys + compact-separators

Failure-mode contract (with Phase 2's graph.duckdb projection):
    JSONL append succeeds, DB insert fails → JSONL has truth; rebuild catches up.
    The reverse (DB insert before JSONL) is forbidden.

## PROV-AGENT mapping (informative; ORNL arXiv:2508.02866)

The annotation shape is isomorphic to prov:Activity:

    source_id          → prov:used (Entity, content-addressed)
    agent              → prov:wasAssociatedWith → prov:Agent
    output_uri         → URI of the prov:Entity generated (no direct
                         property; the relation is prov:wasGeneratedBy)
    output_hash        → content hash of the generated Entity
    asserted_at        → prov:atTime
    valid_from         → informational; PROV has no direct equivalent
                         (Phase A bitemporal extension)
    scope              → custom property
    idempotency_key    → stable_tuple hash; PROV has no equivalent

We adopt the PROV-AGENT vocabulary in documentation. We do NOT serialize
to RDF or import the PROV-O stack. JSONL with the right shape buys what
RDF would at our scale (Phase D decision record).

We do NOT rename `output_uri` → `generated_uri` at the schema level:
output_uri is in annotation_stable_tuple — renaming would mutate
annotation_id for every replayed record (rename-risks memo move #2).
Also `generated_uri` is not blessed PROV; `prov:wasGeneratedBy` is a
relation, not a property name (move #4).

Phase E of .claude/plans/2026-05-27-knowledge-infra-next-foundations.md.
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
from .schema_version import SchemaVersionMismatch, verify_graph_schema
from .store import CorpusStore
from .uri import KNOWN_PROJECT_SCHEMES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Inline ceiling. Raised from 4096 for the epistemic core: a claim_relation
# rides INLINE on the annotation (references spans by id, not full text), so a
# single atomic O_APPEND carries the whole record — no sidecar, no two-write
# non-atomicity. 16 KiB is generous headroom for a multi-party relation while
# still bounding pathological inlining (the original reason a ceiling exists).
ANNOTATION_RECORD_CEILING_BYTES = 16384

# SchemaVer (MODEL-REVISION-ADDITION). Provenance-only annotations stay 1-0-0;
# relation-bearing annotations advance the ADDITION digit to 1-0-1. The
# validator accepts both, and schema_version is NOT in annotation_stable_tuple,
# so the bump never mutates an annotation_id.
SCHEMA_VERSION = "1-0-0"
SCHEMA_VERSION_RELATION = "1-0-1"
CONFORMS_TO = "https://schema.local/corpus/annotation/v1.0.0"
CONFORMS_TO_RELATION = "https://schema.local/corpus/annotation/v1.0.1"
CLAIM_RELATION_SCOPE = "claim_relation"

ActorType = Literal["model", "human", "service", "cli"]
Status = Literal["active", "superseded", "retracted"]


class AnnotationError(Exception):
    """Base for annotation write errors."""


class AnnotationTooLargeError(AnnotationError):
    """Record exceeds ANNOTATION_RECORD_CEILING_BYTES. Reference genuinely
    large outputs via an output_uri sidecar (a claim_relation rides inline)."""


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


def validate_relation_body(relation: dict[str, Any]) -> None:
    """Validate a claim-relation body against the SAME closed schema
    ``annotate`` enforces at write time — but EAGERLY, so a malformed relation
    fails where it is constructed/enqueued, not hours later inside the
    cross-process drain. ``relation_id`` is excluded from the required set
    because the substrate derives it at drain (callers must not set it).

    Raises :class:`AnnotationSchemaError`. This is the single source of truth a
    relation enqueuer should call before persisting a relation_json row.
    """
    try:
        import jsonschema
    except ImportError as e:
        raise AnnotationError(
            "corpus-core: jsonschema not installed (add as a runtime dep)"
        ) from e
    rel_schema = dict(_load_schema("annotation.v1.json")["properties"]["relation"])
    # Derived at drain — don't require it eagerly (and callers must not set it).
    rel_schema["required"] = [r for r in rel_schema.get("required", []) if r != "relation_id"]
    if "relation_id" in relation:
        raise AnnotationSchemaError(
            "relation must NOT carry relation_id — the substrate derives it at drain"
        )
    try:
        jsonschema.validate(relation, rel_schema)
    except jsonschema.ValidationError as e:
        raise AnnotationSchemaError(f"relation failed schema: {e.message}") from e


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------


def _annotations_path(store: CorpusStore, source_id: str) -> Path:
    return store.paper_path(source_id) / "annotations.jsonl"


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


def _existing_annotation_record(
    store: CorpusStore, source_id: str, annotation_id: str
) -> dict[str, Any] | None:
    """Scan annotations.jsonl for the record with the given annotation_id.

    Returns the parsed record (the last one, if duplicates ever exist), or None.
    Idempotency is content-keyed: same stable_tuple → same annotation_id. The
    CALLER must still compare lifecycle fields (status / supersedes /
    source_content_hash) that are excluded from the id, so a same-content
    correction is not silently swallowed as a no-op.
    """
    path = _annotations_path(store, source_id)
    if not path.exists():
        return None
    needle = f'"annotation_id":"{annotation_id}"'
    # Annotations files are small; full read is fine until graph.duckdb
    # projection (Phase 2) handles reverse lookups.
    found: dict[str, Any] | None = None
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if needle not in line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("annotation_id") == annotation_id:
                    found = rec
    except OSError:
        return None
    return found


# Lifecycle fields deliberately EXCLUDED from annotation_stable_tuple (so a
# replayed record keeps its id). A re-append that changes any of these but
# nothing else is a same-content CORRECTION — it must not be silently dropped.
_LIFECYCLE_DISCRIMINATORS = ("status", "supersedes_annotation_id", "source_content_hash")


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
    store: CorpusStore,
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
    valid_from: datetime | str | None = None,
    relation: dict[str, Any] | None = None,
) -> str:
    """Append one annotation to ``store/<source_id>/annotations.jsonl``.

    Args:
        source_id: canonical corpus source_id (`doi_…`, `pmid_…`, `sha_…`).
        store: explicit corpus store handle.
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

    # Epistemic core: the substrate owns relation identity. Content-address the
    # relation, stamp its relation_id, and derive the annotation's output_hash
    # from the same sha so a re-emit of the identical relation is idempotent
    # (the producer supplies only the semantic body).
    if relation is not None:
        from .identity import relation_content_sha
        rel_sha = relation_content_sha(
            relation_class=relation.get("relation_class", ""),
            subject_refs=relation.get("subject_refs", []) or [],
            object_refs=relation.get("object_refs", []) or [],
            detector=relation.get("detector", "") or "",
        )
        relation = {**relation, "relation_id": f"rel_{rel_sha[:16]}"}
        if output_hash is None:
            output_hash = rel_sha

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

    # Idempotency: re-append of the SAME content is a no-op — but only if the
    # lifecycle fields excluded from the id (status / supersedes /
    # source_content_hash) ALSO match. If they differ, this is a same-content
    # correction (e.g. a same-actor retraction, or re-attesting a verdict
    # against a re-parsed source). Silently dropping it would let the
    # append-only trail swallow a correction; fail loud instead and tell the
    # caller to fork the id (new output_uri/output_hash) for a genuine new event.
    existing = _existing_annotation_record(store, source_id, annotation_id)
    if existing is not None:
        incoming = {
            "status": status,
            "supersedes_annotation_id": supersedes_annotation_id,
            "source_content_hash": source_content_hash,
        }
        for field in _LIFECYCLE_DISCRIMINATORS:
            old = existing.get(field) if field != "status" else existing.get("status", "active")
            if incoming[field] != old:
                raise AnnotationError(
                    f"annotation_id {annotation_id} already exists for {source_id} "
                    f"with identical content, but this call changes {field!r} "
                    f"({old!r} → {incoming[field]!r}) — a field excluded from the "
                    "content-addressed id. A same-content correction must NOT be "
                    "dropped as an idempotent no-op. To record it, fork the id with "
                    "a new output_uri/output_hash (a distinct attestation event)."
                )
        return annotation_id

    # Time stamps.
    def _to_iso_z(v: datetime | str) -> str:
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return v  # caller-provided ISO string

    if asserted_at is None:
        asserted_at_iso = _utc_now_iso()
    else:
        asserted_at_iso = _to_iso_z(asserted_at)
    recorded_at_iso = _utc_now_iso()
    # Phase A: informational bitemporal field. Defaults to asserted_at
    # so writers that don't care about world-time vs. record-time get
    # a sensible value, while writers that DO care (verdicts coming
    # from a published-on-2026-01-01 paper) can pass it explicitly.
    if valid_from is None:
        valid_from_iso = asserted_at_iso
    else:
        valid_from_iso = _to_iso_z(valid_from)

    # Build the record. A relation-bearing record advances to schema 1-0-1.
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION_RELATION if relation is not None else SCHEMA_VERSION,
        "conformsTo": CONFORMS_TO_RELATION if relation is not None else CONFORMS_TO,
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
    # Phase A: emit valid_from to JSONL. NOT in stable_tuple — does
    # not mutate annotation_id (idempotency preserved on replay).
    record["valid_from"] = valid_from_iso
    if output_uri or output_hash or output_size_bytes is not None:
        result: dict[str, Any] = {}
        if output_uri is not None:
            result["uri"] = output_uri
        if output_hash is not None:
            result["hash"] = output_hash
        if output_size_bytes is not None:
            result["size_bytes"] = output_size_bytes
        record["result"] = result
    # Epistemic core: inline the structured claim relation (validated as part
    # of the closed annotation schema). Callers route distinct relations to
    # distinct annotation_ids by passing output_hash = the relation content
    # sha (relation_id is its 16-hex prefix), so re-emit stays idempotent.
    if relation is not None:
        record["relation"] = relation

    _validate_annotation(record)
    payload = _serialize_record(record)
    _atomic_append(_annotations_path(store, source_id), payload)

    # Phase G0 preflight: raise loudly on schema skew BEFORE attempting the
    # projection. SchemaVersionMismatch must propagate — the bare-Exception
    # swallow below is for transient DB errors that the rebuild script can
    # backfill, not for permanent version-skew that needs operator action.
    verify_graph_schema(store.graph_db_path())

    # Phase 2 projection: best-effort insert into graph.duckdb. JSONL is the
    # source of truth — DB failure logs and continues; rebuild catches up.
    try:
        from .index import index_annotation
        index_annotation(record, store=store)
    except SchemaVersionMismatch:
        raise
    except Exception:  # pragma: no cover — never break a JSONL append
        pass

    return annotation_id


__all__ = [
    "ANNOTATION_RECORD_CEILING_BYTES",
    "CLAIM_RELATION_SCOPE",
    "CONFORMS_TO",
    "CONFORMS_TO_RELATION",
    "SCHEMA_VERSION",
    "SCHEMA_VERSION_RELATION",
    "AnnotationError",
    "AnnotationSchemaError",
    "AnnotationTooLargeError",
    "annotate",
]
