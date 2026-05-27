"""Versioned canonical JSON for the corpus substrate.

Two canonical forms coexist:

  - ``canonical_json_legacy(record)`` — preserves historical bytes for
    annotation_id stability across replay. NO Unicode normalization,
    NO timestamp reformatting; matches the byte form that
    ``corpus_core.identity.canonical_json`` has emitted from day one.

  - ``canonical_json_v1(record)`` — for NEW records only. NFC-normalizes
    string content at the serialization boundary; pinned UTC ISO-8601
    timestamp form via ``format_ts_utc``; rejects ``float`` / ``Decimal``
    / non-serializable types up-front.

Records dispatch via the ``canonicalize_version`` SIDECAR — never via
the stable-tuple — so adding the sidecar to a record does NOT mutate
its annotation_id. Absent sidecar = legacy.

Why the split: aggressive normalization on historical records would
mutate every annotation_id on replay. The rename-risks memo killed
Phase J for this; v5 of the plan re-introduced the same bug via NFC
+ microsecond timestamps; v6 explicitly separates the two.

Storage:
  - Canonical JSON stored as VARCHAR, never DuckDB JSON type — JSON
    type normalizes to STRUCT and loses key order.

Phase F of .claude/plans/2026-05-27-knowledge-infra-next-foundations.md.
"""
from __future__ import annotations

import json
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


CANONICALIZE_V1 = "v1"
CANONICALIZE_LEGACY = "legacy"


def format_ts_utc(t: datetime | str) -> str:
    """Single canonical timestamp form for v1 records.

    YYYY-MM-DDTHH:MM:SS.ffffffZ — microsecond precision, Z suffix.

    Why: ``datetime.isoformat`` uses a 'T' separator; DuckDB's JSON cast
    uses a space; both serialize the SAME timestamp to DIFFERENT bytes.
    Pinning the format prevents that divergence.

    Naive datetimes are interpreted as UTC. ISO strings round-trip
    through ``fromisoformat`` (accepting either ``+00:00`` or ``Z``).
    """
    if isinstance(t, str):
        t = datetime.fromisoformat(t.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    t = t.astimezone(timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _nfc(s: str) -> str:
    """Unicode NFC normalization.

    macOS APFS stores HFS-origin filenames in NFD; bytes that round-trip
    through readdir on a different filesystem will look different. NFC
    is the canonical form on the wire.
    """
    return unicodedata.normalize("NFC", s)


def _canonicalize_value_v1(v: Any) -> Any:
    """Transform a value for v1 serialization WITHOUT mutating the input.

    Returns a new structure. Dict keys are NOT NFC-normalized here
    (that happens at ``json.dumps`` boundary below) so that downstream
    ``returned["something"]`` lookups remain consistent with the
    caller's strings.

    Rejects float and Decimal up-front: scientific records must be
    pre-stringified to avoid floating-point divergence across
    re-serializations (Datomic / Datascript lesson).
    """
    if isinstance(v, str):
        return _nfc(v)
    if isinstance(v, datetime):
        return format_ts_utc(v)
    if isinstance(v, bool):
        # bool is a subclass of int; check before int handling to avoid
        # bool → True/False stringification surprises.
        return v
    if isinstance(v, (int,)):
        return v
    if isinstance(v, float):
        raise ValueError(
            "float in canonical_json_v1: use Decimal-string or fixed-precision string"
        )
    if isinstance(v, Decimal):
        raise ValueError(
            "Decimal in canonical_json_v1: pre-stringify to fixed-precision string"
        )
    if v is None:
        return v
    if isinstance(v, dict):
        return {k: _canonicalize_value_v1(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_canonicalize_value_v1(x) for x in v]
    if isinstance(v, tuple):
        return [_canonicalize_value_v1(x) for x in v]
    raise ValueError(
        f"non-serializable type {type(v).__name__} in canonical_json_v1"
    )


def _refuse(o: Any) -> Any:
    raise ValueError(
        f"non-serializable {type(o).__name__} in canonical_json"
    )


def canonical_json_v1(record: dict) -> bytes:
    """v1 canonical bytes. ONLY for new records being hashed for the
    first time. Records produced by this form should carry the
    ``canonicalize_version='v1'`` sidecar (OUTSIDE stable_tuple) so
    future readers dispatch correctly.
    """
    canonicalized = _canonicalize_value_v1(record)
    return json.dumps(
        canonicalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_refuse,
    ).encode("utf-8")


def canonical_json_legacy(record: dict) -> bytes:
    """Legacy canonical bytes — preserves byte-for-byte stability of
    annotation_id across replay of pre-v6 JSONL files.

    Matches ``corpus_core.identity.canonical_json`` byte-for-byte on
    every annotation record currently in the corpus (no NaN, no Decimal,
    no datetime — records always carry string ISO timestamps). The
    ``allow_nan=False`` guard is a safety net: real records would raise
    rather than emit invalid JSON.
    """
    return json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json(record: dict) -> bytes:
    """Dispatch on ``canonicalize_version`` sidecar (default legacy).

    The sidecar lives OUTSIDE ``annotation_stable_tuple`` so adding it
    to a record does NOT mutate the annotation_id.
    """
    version = record.get("canonicalize_version", CANONICALIZE_LEGACY)
    if version == CANONICALIZE_LEGACY:
        return canonical_json_legacy(record)
    if version == CANONICALIZE_V1:
        return canonical_json_v1(record)
    raise ValueError(f"unknown canonicalize_version: {version!r}")


def parse_jsonl_strict(line: str) -> dict:
    """Parse one JSONL row in strict mode — duplicate keys are rejected.

    RFC 8259 leaves duplicate-key behavior implementation-defined; we
    choose strict because a JSONL row with duplicate keys is almost
    certainly a writer bug. Tolerant mode is opt-in elsewhere (e.g.
    ``replay_tolerant=True``).
    """
    def _no_dupes(pairs):
        d: dict[str, Any] = {}
        for k, v in pairs:
            if k in d:
                raise ValueError(f"duplicate key {k!r} in JSONL row")
            d[k] = v
        return d
    return json.loads(line, object_pairs_hook=_no_dupes)


__all__ = [
    "CANONICALIZE_V1",
    "CANONICALIZE_LEGACY",
    "canonical_json",
    "canonical_json_legacy",
    "canonical_json_v1",
    "format_ts_utc",
    "parse_jsonl_strict",
]
