"""Identity primitives: byte-stable canonical_json + sha256 + slug + id derivations."""
from __future__ import annotations

import hashlib

import pytest

from corpus_core.identity import (
    annotation_id_from_tuple,
    annotation_idempotency_key,
    annotation_stable_tuple,
    canonical_json,
    derive_source_id,
    parse_source_identifier,
    sha256_hex,
    slug_doi,
)


# --- canonical_json ---


def test_canonical_json_sorts_keys():
    a = canonical_json({"b": 2, "a": 1})
    b = canonical_json({"a": 1, "b": 2})
    assert a == b == b'{"a":1,"b":2}'


def test_canonical_json_compact():
    assert canonical_json({"x": [1, 2]}) == b'{"x":[1,2]}'


def test_canonical_json_utf8_no_escape():
    assert canonical_json({"k": "café"}) == b'{"k":"caf\xc3\xa9"}'


def test_canonical_json_nested_sorting():
    out = canonical_json({"z": {"b": 2, "a": 1}, "x": [{"k": 2, "j": 1}]})
    assert out == b'{"x":[{"j":1,"k":2}],"z":{"a":1,"b":2}}'


def test_sha256_hex_known_vector():
    # Empty JSON object → '{}' (UTF-8) sha256
    h = sha256_hex(canonical_json({}))
    assert h == hashlib.sha256(b"{}").hexdigest()


# --- DOI slug ---


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("10.1097/FPC.0000000000000456", "10_1097_fpc_0000000000000456"),
        ("10.1038/s41586-021-03491-6", "10_1038_s41586_021_03491_6"),
        (" 10.1234/test  ", "10_1234_test"),
        ("10.1101/2026.04.10.26350624", "10_1101_2026_04_10_26350624"),
    ],
)
def test_slug_doi(raw, expected):
    assert slug_doi(raw) == expected


# --- derive_source_id ---


def test_derive_source_id_doi_precedence():
    sid = derive_source_id(doi="10.1234/test", pmid="999")
    assert sid == "doi_10_1234_test"


def test_derive_source_id_pmid():
    assert derive_source_id(pmid="12345678") == "pmid_12345678"


def test_derive_source_id_pmid_must_be_numeric():
    with pytest.raises(ValueError):
        derive_source_id(pmid="abc")


def test_derive_source_id_pmcid():
    assert derive_source_id(pmcid="PMC12345") == "pmcid_pmc12345"


def test_derive_source_id_sha_fallback():
    h = "a" * 64
    assert derive_source_id(content_sha256=h) == f"sha_{'a' * 16}"


def test_derive_source_id_no_inputs():
    with pytest.raises(ValueError):
        derive_source_id()


# --- parse_source_identifier ---


def test_parse_doi_bare():
    out = parse_source_identifier("10.1234/test")
    assert out["doi"] == "10.1234/test"
    assert out["source_id"] == "doi_10_1234_test"


def test_parse_doi_prefixed():
    out = parse_source_identifier("doi:10.1234/test")
    assert out["doi"] == "10.1234/test"


def test_parse_pmid_bare():
    out = parse_source_identifier("12345678")
    assert out["pmid"] == "12345678"
    assert out["source_id"] == "pmid_12345678"


def test_parse_pmcid():
    out = parse_source_identifier("PMC123")
    assert out["pmcid"] == "PMC123"


# --- annotation_id derivation ---


def test_annotation_stable_tuple_no_timestamp():
    t = annotation_stable_tuple(
        source_id="doi_x", repo="genomics", scope="verdict",
        agent_id="urn:agent:human:markus", prompt_template_hash=None, output_hash=None,
    )
    assert "asserted_at" not in t
    assert "recorded_at" not in t


def test_annotation_id_format():
    t = annotation_stable_tuple(
        source_id="doi_x", repo="genomics", scope="verdict",
        agent_id="urn:agent:human:markus", prompt_template_hash=None, output_hash=None,
    )
    aid = annotation_id_from_tuple(t)
    assert aid.startswith("ann_")
    assert len(aid) == len("ann_") + 16
    assert all(c in "0123456789abcdef" for c in aid[len("ann_"):])


def test_annotation_id_deterministic():
    t1 = annotation_stable_tuple(
        source_id="doi_x", repo="genomics", scope="verdict",
        agent_id="urn:agent:human:markus", prompt_template_hash=None, output_hash=None,
    )
    t2 = annotation_stable_tuple(
        source_id="doi_x", repo="genomics", scope="verdict",
        agent_id="urn:agent:human:markus", prompt_template_hash=None, output_hash=None,
    )
    assert annotation_id_from_tuple(t1) == annotation_id_from_tuple(t2)


def test_annotation_id_differs_on_scope():
    t1 = annotation_stable_tuple(
        source_id="doi_x", repo="genomics", scope="verdict",
        agent_id="urn:agent:human:markus", prompt_template_hash=None, output_hash=None,
    )
    t2 = annotation_stable_tuple(
        source_id="doi_x", repo="genomics", scope="claim_extraction",
        agent_id="urn:agent:human:markus", prompt_template_hash=None, output_hash=None,
    )
    assert annotation_id_from_tuple(t1) != annotation_id_from_tuple(t2)


def test_annotation_idempotency_key_stable_string():
    t = annotation_stable_tuple(
        source_id="doi_x", repo="genomics", scope="verdict",
        agent_id="urn:agent:human:markus", prompt_template_hash=None, output_hash=None,
    )
    k = annotation_idempotency_key(t)
    # Sorted keys → predictable order
    assert k.startswith('{"agent_id":')
    assert '"source_id":"doi_x"' in k


# --- canonical_json byte-compat with rfc8785 (RFC 8785 JCS reference impl) ---


def test_canonical_json_matches_rfc8785_on_our_inputs():
    """Our canonical_json must produce the same bytes as RFC 8785 JCS reference
    implementation for the input shapes we actually emit (UTF-8 BMP keys,
    integers, no control chars, no non-BMP unicode in slot values).

    NOT a runtime dep — strictly test-only (per plan §G round-2 finding 4).
    """
    rfc8785 = pytest.importorskip("rfc8785")
    cases = [
        {"a": 1, "b": [2, 3]},
        {"agent_id": "urn:agent:human:markus", "source_id": "doi_x", "scope": "verdict"},
        {"k": "café", "n": 42},
        {"nested": {"z": [{"b": 2, "a": 1}]}},
    ]
    for case in cases:
        ours = canonical_json(case)
        # rfc8785.dumps returns bytes already
        theirs = rfc8785.dumps(case)
        if isinstance(theirs, str):
            theirs = theirs.encode("utf-8")
        assert ours == theirs, f"divergence on {case!r}: ours={ours!r} theirs={theirs!r}"
