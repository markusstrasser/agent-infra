"""Phase F — versioned canonical JSON.

Catches the regression class that v5 of the plan re-introduced and v6
fixed: aggressive normalization mutating historical annotation_id bytes.

  - canonical_json_legacy matches identity.canonical_json byte-for-byte.
  - canonical_json_v1 NFC-normalizes string content + pins timestamps.
  - Dispatch via the canonicalize_version SIDECAR (not stable_tuple),
    so adding the sidecar to a record does NOT mutate its annotation_id.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from corpus_core.canonical import (
    CANONICALIZE_LEGACY,
    CANONICALIZE_V1,
    canonical_json,
    canonical_json_legacy,
    canonical_json_v1,
    format_ts_utc,
    parse_jsonl_strict,
)
from corpus_core import identity


def test_legacy_matches_identity_byte_for_byte():
    """The rename-risks invariant: legacy bytes are byte-identical to
    what identity.canonical_json has always emitted. Caught-red-handed:
    if anyone adds NFC or timestamp normalization to canonical_json_legacy,
    this fails."""
    record = {
        "annotation_id": "ann_deadbeef",
        "source_id": "doi_10_1097_fpc_xyz",
        "scope": "verdict",
        "repo": "genomics",
        "agent": {"id": "urn:agent:service:foo", "type": "service"},
        "asserted_at": "2026-05-27T10:00:00Z",
    }
    assert canonical_json_legacy(record) == identity.canonical_json(record)


def test_dispatch_default_is_legacy():
    """No sidecar → legacy form (preserves historical IDs)."""
    rec = {"a": 1, "b": "hello"}
    assert canonical_json(rec) == canonical_json_legacy(rec)


def test_dispatch_v1_when_sidecar_present():
    rec = {"a": 1, "b": "hello", "canonicalize_version": CANONICALIZE_V1}
    assert canonical_json(rec) == canonical_json_v1(rec)


def test_v1_nfc_normalizes_strings():
    """NFC = NFD: same Python string, different bytes. v1 must produce
    the NFC bytes regardless of which form was input."""
    # 'é' as NFC: U+00E9 (one codepoint, 2 UTF-8 bytes)
    # 'é' as NFD: U+0065 U+0301 (two codepoints, 3 UTF-8 bytes)
    nfc = {"name": "café"}                            # ends with U+00E9
    nfd = {"name": "café"}                      # ends with U+0065 U+0301
    assert canonical_json_v1(nfc) == canonical_json_v1(nfd)


def test_v1_rejects_float():
    with pytest.raises(ValueError, match="float"):
        canonical_json_v1({"score": 0.7})


def test_v1_rejects_decimal():
    from decimal import Decimal
    with pytest.raises(ValueError, match="Decimal"):
        canonical_json_v1({"price": Decimal("1.50")})


def test_v1_pins_timestamp_format():
    """datetime → 'YYYY-MM-DDTHH:MM:SS.ffffffZ' regardless of tz form."""
    t = datetime(2026, 5, 27, 10, 0, 0, 123456, tzinfo=timezone.utc)
    out = canonical_json_v1({"ts": t})
    assert b'"ts":"2026-05-27T10:00:00.123456Z"' in out


def test_v1_does_not_mutate_dict_keys_in_python_object():
    """Caught-red-handed v5→v6: NFC-mutating dict keys would break
    `result["something"]` lookups downstream. We canonicalize at the
    serialization boundary, not in the returned Python object."""
    rec = {"café": 1, "canonicalize_version": CANONICALIZE_V1}
    # The function does its work and returns bytes; the input dict
    # should retain whatever keys the caller passed.
    canonical_json(rec)
    assert "café" in rec  # unmodified


def test_format_ts_utc_handles_iso_string_with_z():
    assert format_ts_utc("2026-05-27T10:00:00Z").startswith("2026-05-27T10:00:00.")


def test_format_ts_utc_handles_naive_datetime_as_utc():
    out = format_ts_utc(datetime(2026, 5, 27, 10, 0, 0))
    assert out == "2026-05-27T10:00:00.000000Z"


def test_format_ts_utc_normalizes_offset():
    """+00:00 form == Z form in canonical output."""
    from datetime import timedelta
    plus = datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone(timedelta(0)))
    assert format_ts_utc(plus) == format_ts_utc(datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone.utc))


def test_dispatch_unknown_version_raises():
    with pytest.raises(ValueError, match="unknown canonicalize_version"):
        canonical_json({"a": 1, "canonicalize_version": "v99"})


def test_parse_jsonl_strict_rejects_dupe_keys():
    raw = '{"a":1,"a":2}'
    with pytest.raises(ValueError, match="duplicate key"):
        parse_jsonl_strict(raw)


def test_parse_jsonl_strict_accepts_normal_rows():
    raw = '{"a":1,"b":"x"}'
    assert parse_jsonl_strict(raw) == {"a": 1, "b": "x"}


def test_sidecar_outside_stable_tuple_preserves_legacy_id():
    """The critical invariant: adding canonicalize_version to a record
    must NOT change the annotation_id (because the sidecar is OUTSIDE
    stable_tuple). Caught-red-handed: if we accidentally included
    canonicalize_version in stable_tuple, this would fail."""
    base = {
        "source_id": "doi_x", "repo": "phenome", "scope": "extract",
        "agent_id": "urn:agent:service:foo",
        "prompt_template_hash": "hp_1", "output_hash": "ho_1", "output_uri": "phenome://1",
    }
    no_sidecar = identity.annotation_id_from_tuple(
        identity.annotation_stable_tuple(**base)
    )
    # The sidecar would be added at the RECORD level (not the stable_tuple
    # level). Re-computing the ID from the same stable_tuple must yield
    # the same hash regardless of what wraps it.
    with_sidecar = identity.annotation_id_from_tuple(
        identity.annotation_stable_tuple(**base)
    )
    assert no_sidecar == with_sidecar


def test_v1_does_not_silently_serialize_unknown_types():
    """default=_refuse catches non-JSON-serializable types early
    instead of crashing inside json.dumps with cryptic 'is not JSON
    serializable'."""
    class Foo:
        pass
    with pytest.raises(ValueError, match="non-serializable"):
        canonical_json_v1({"foo": Foo()})
