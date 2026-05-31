"""Content-addressed identity primitives for the corpus.

Every hash in the substrate is `sha256_hex(canonical_json(...))`. This module
defines `canonical_json`, `sha256_hex`, source_id derivation rules, and the
annotation_id stable-tuple → id derivation.

`canonical_json` is byte-compatible with `phenome/identity/canonicalize.py`
on the inputs both projects emit (no non-BMP unicode in slot values, no
control chars). The byte-compat property is asserted by paired test fixtures
in both repos and (transitively) against `rfc8785.py`'s RFC 8785 JCS reference
implementation as a dev-dep.

NO UUID5 — round-2 reversal of phenome alignment. UUID5 uses SHA-1 truncated
to 122 bits (deprecated). For source-grade content-addressing, sha256-prefix
ids are what every other scientific corpus tool emits.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

# ---------------------------------------------------------------------------
# Canonical JSON + sha256
# ---------------------------------------------------------------------------


def canonical_json(value: Any) -> bytes:
    """Stable canonical bytes for hashing.

    Sorted keys, compact separators, UTF-8 (no escape). Matches
    `phenome/identity/canonicalize.py:canonical_json` byte-for-byte.

    NB: does NOT recursively normalize semantic content (string casing,
    unit normalization, etc.) — that belongs to higher slot canonicalization.
    """
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_hex(payload: bytes | str) -> str:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Source id derivation
# ---------------------------------------------------------------------------


_SLUG_NONALNUM = re.compile(r"[^a-z0-9]+")
_SLUG_REPEATED = re.compile(r"_+")
_DOI_BARE = re.compile(r"^10\.\d{4,9}/")
_PMID_BARE = re.compile(r"^\d{6,9}$")
_PMCID_BARE = re.compile(r"^PMC\d+$", re.IGNORECASE)


def slug_doi(doi: str) -> str:
    """DOI → filesystem slug. Lowercase, non-alnum → `_`, collapse, strip.

    >>> slug_doi("10.1097/FPC.0000000000000456")
    '10_1097_fpc_0000000000000456'
    """
    s = doi.strip().lower()
    s = _SLUG_NONALNUM.sub("_", s)
    s = _SLUG_REPEATED.sub("_", s)
    return s.strip("_")


def derive_source_id(
    *,
    doi: str | None = None,
    pmid: str | None = None,
    pmcid: str | None = None,
    content_sha256: str | None = None,
) -> str:
    """Deterministic source_id. Precedence: DOI > PMID > PMCID > content_sha256.

    Raises ValueError if no input is supplied.
    """
    if doi:
        return f"doi_{slug_doi(doi)}"
    if pmid:
        clean = str(pmid).strip()
        if not clean.isdigit():
            raise ValueError(f"PMID must be numeric, got {pmid!r}")
        return f"pmid_{clean}"
    if pmcid:
        clean = pmcid.strip().upper()
        if not clean.startswith("PMC"):
            clean = f"PMC{clean}"
        return f"pmcid_{clean.lower()}"
    if content_sha256:
        prefix = content_sha256.replace("sha256:", "")[:16]
        if len(prefix) < 16:
            raise ValueError("content_sha256 must be at least 16 hex chars")
        return f"sha_{prefix}"
    raise ValueError("derive_source_id requires at least one of doi, pmid, pmcid, content_sha256")


def parse_source_identifier(raw: str) -> dict[str, str | None]:
    """Parse a free-form identifier into typed components.

    Accepts: 'doi:10.x/y', '10.x/y', 'pmid:123', '123', 'PMC123', 'pmcid:PMC123'.
    Returns dict with keys: doi, pmid, pmcid, raw, source_id (canonical form).
    """
    out: dict[str, str | None] = {
        "doi": None, "pmid": None, "pmcid": None, "raw": raw, "source_id": None,
    }
    s = raw.strip()
    low = s.lower()
    if low.startswith("doi:"):
        out["doi"] = s[4:].strip()
    elif _DOI_BARE.match(s):
        out["doi"] = s
    elif low.startswith("pmid:"):
        out["pmid"] = s[5:].strip()
    elif low.startswith("pmcid:"):
        rest = s[6:].strip().upper()
        out["pmcid"] = rest if rest.startswith("PMC") else f"PMC{rest}"
    elif _PMCID_BARE.match(s):
        out["pmcid"] = s.upper()
    elif _PMID_BARE.match(s):
        out["pmid"] = s
    if out["doi"] or out["pmid"] or out["pmcid"]:
        out["source_id"] = derive_source_id(
            doi=out["doi"], pmid=out["pmid"], pmcid=out["pmcid"]
        )
    return out


# ---------------------------------------------------------------------------
# Annotation id (stable-tuple → ann_<sha16>)
# ---------------------------------------------------------------------------


def annotation_stable_tuple(
    *,
    source_id: str,
    repo: str,
    scope: str,
    agent_id: str,
    prompt_template_hash: str | None,
    output_hash: str | None,
    output_uri: str | None = None,
) -> dict[str, str | None]:
    """Build the stable tuple used for annotation idempotency + id derivation.

    Order is fixed (alphabetic via canonical_json sort) — DO NOT include
    asserted_at, recorded_at, instrument, or any field the agent may legitimately
    re-emit at a later time without changing semantic content.

    `output_uri` is included so each addressable output (e.g. distinct
    `genomics://verdicts/<vid>` URIs) gets its own annotation even when the
    content projection (output_hash) is shared with another output. Without
    this, two verdicts with the same support_state + review_status + …
    collapse to one annotation, hiding the second attestation event.
    Idempotent retries (same agent re-calling with the same output_uri)
    remain no-ops.
    """
    return {
        "agent_id": agent_id,
        "output_hash": output_hash,
        "output_uri": output_uri,
        "prompt_template_hash": prompt_template_hash,
        "repo": repo,
        "scope": scope,
        "source_id": source_id,
    }


def annotation_idempotency_key(stable_tuple: dict[str, str | None]) -> str:
    """Canonical-JSON of the stable tuple as the idempotency key."""
    return canonical_json(stable_tuple).decode("utf-8")


def annotation_id_from_tuple(stable_tuple: dict[str, str | None]) -> str:
    """ann_ + first 16 hex chars of sha256_hex(canonical_json(stable_tuple))."""
    return f"ann_{sha256_hex(canonical_json(stable_tuple))[:16]}"


# ---------------------------------------------------------------------------
# Claim relation identity (epistemic core)
# ---------------------------------------------------------------------------


def relation_content_sha(
    *,
    relation_class: str,
    subject_refs: list[str],
    object_refs: list[str],
    detector: str,
) -> str:
    """Content sha (64 hex) over a claim relation's identity-bearing core.

    Identity = (relation_class, sorted subject_refs, sorted object_refs,
    detector). Endpoint order is irrelevant (sorted), spans/weight/home ids are
    NOT in identity — re-grounding the same relation with a richer span set does
    not fork it. `relation_id` is the 16-hex prefix; the full sha doubles as the
    annotation's output_hash so re-emitting the same relation stays idempotent.
    """
    core = {
        "relation_class": relation_class,
        "subject_refs": sorted(subject_refs),
        "object_refs": sorted(object_refs),
        "detector": detector,
    }
    return sha256_hex(canonical_json(core))
