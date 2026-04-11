"""Phase 3 unit tests for atomic_claim.py.

Covers the pure-logic parts:
- _strip_code_fences         (markdown fence removal)
- _parse_claim_list          (decomposer JSON output → list[str])
- _parse_match_result        (matcher JSON output → label arrays)
- _compute_p_r_f1            (label arrays → P/R/F1)
- _gold_text_from_metadata   (case JSON → gold evidence text blob)

The decomposer LLM calls are NOT covered here — they require the live
Gemini API. The full eval run is the integration test for those.

Run:
    uv run python -m pytest experiments/claim-bench/test_phase3.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

THIS_DIR = str(Path(__file__).resolve().parent)
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

from atomic_claim import (  # noqa: E402
    _compute_p_r_f1,
    _gold_text_from_metadata,
    _parse_claim_list,
    _parse_match_result,
    _strip_code_fences,
)


# ─── _strip_code_fences ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('["a", "b"]', '["a", "b"]'),
        ('```json\n["a", "b"]\n```', '["a", "b"]'),
        ('```\n["a", "b"]\n```', '["a", "b"]'),
        ('```JSON\n["a"]\n```', '["a"]'),
        ('  ```json\n  ["a"]\n  ```  ', '["a"]'),
        ("", ""),
    ],
)
def test_strip_code_fences(raw: str, expected: str) -> None:
    assert _strip_code_fences(raw) == expected


# ─── _parse_claim_list ───────────────────────────────────────────────────────


def test_parse_claim_list_basic() -> None:
    raw = '["Earth orbits the Sun.", "Earth has one moon."]'
    claims = _parse_claim_list(raw)
    assert claims == ["Earth orbits the Sun.", "Earth has one moon."]


def test_parse_claim_list_with_fences() -> None:
    raw = '```json\n["claim 1", "claim 2"]\n```'
    assert _parse_claim_list(raw) == ["claim 1", "claim 2"]


def test_parse_claim_list_strips_whitespace() -> None:
    raw = '["  claim with whitespace  ", "another"]'
    assert _parse_claim_list(raw) == ["claim with whitespace", "another"]


def test_parse_claim_list_filters_empty_and_non_strings() -> None:
    # Decomposer might output mixed types or empty strings
    raw = '["valid claim", "", null, 42, "another valid"]'
    claims = _parse_claim_list(raw)
    assert "valid claim" in claims
    assert "another valid" in claims
    assert "" not in claims
    assert len(claims) == 2


def test_parse_claim_list_invalid_json_returns_empty() -> None:
    raw = "not json at all"
    assert _parse_claim_list(raw) == []


def test_parse_claim_list_dict_returns_empty() -> None:
    """Decomposer might mistakenly output a dict — must not crash."""
    raw = '{"claims": ["a", "b"]}'
    assert _parse_claim_list(raw) == []


def test_parse_claim_list_caps_at_max() -> None:
    """Defends against pathological 200-claim decomposer outputs."""
    huge = "[" + ",".join(f'"claim {i}"' for i in range(100)) + "]"
    claims = _parse_claim_list(huge)
    assert len(claims) <= 30  # MAX_CLAIMS_PER_SIDE


# ─── _parse_match_result ─────────────────────────────────────────────────────


def test_parse_match_basic() -> None:
    raw = '{"set_a": ["SUPPORTED", "NEW"], "set_b": ["FOUND", "MISSED"]}'
    a, b = _parse_match_result(raw, n_a=2, n_b=2)
    assert a == ["SUPPORTED", "NEW"]
    assert b == ["FOUND", "MISSED"]


def test_parse_match_with_fences() -> None:
    raw = '```json\n{"set_a": ["SUPPORTED"], "set_b": ["FOUND"]}\n```'
    a, b = _parse_match_result(raw, n_a=1, n_b=1)
    assert a == ["SUPPORTED"]
    assert b == ["FOUND"]


def test_parse_match_pads_short_arrays() -> None:
    """Matcher truncated its response — must pad to expected length with safe defaults."""
    raw = '{"set_a": ["SUPPORTED"], "set_b": ["FOUND"]}'
    a, b = _parse_match_result(raw, n_a=3, n_b=3)
    assert len(a) == 3
    assert len(b) == 3
    assert a[0] == "SUPPORTED"
    assert a[1] == "NEW"  # padded
    assert a[2] == "NEW"
    assert b[0] == "FOUND"
    assert b[1] == "MISSED"  # padded
    assert b[2] == "MISSED"


def test_parse_match_truncates_long_arrays() -> None:
    """Matcher returned more entries than expected — truncate."""
    raw = (
        '{"set_a": ["SUPPORTED", "SUPPORTED", "SUPPORTED"], '
        '"set_b": ["FOUND", "FOUND", "FOUND"]}'
    )
    a, b = _parse_match_result(raw, n_a=2, n_b=2)
    assert len(a) == 2
    assert len(b) == 2


def test_parse_match_invalid_json_returns_all_miss() -> None:
    """Parse failure scores as all NEW / MISSED — total miss, not silent half-pass."""
    a, b = _parse_match_result("not json", n_a=2, n_b=3)
    assert a == ["NEW", "NEW"]
    assert b == ["MISSED", "MISSED", "MISSED"]


def test_parse_match_normalizes_label_case() -> None:
    raw = '{"set_a": ["supported", "new"], "set_b": ["found", "missed"]}'
    a, b = _parse_match_result(raw, n_a=2, n_b=2)
    assert a == ["SUPPORTED", "NEW"]
    assert b == ["FOUND", "MISSED"]


def test_parse_match_unknown_label_treated_as_negative() -> None:
    """Unknown label in set_a → NEW, in set_b → MISSED. Conservative."""
    raw = '{"set_a": ["UNKNOWN", "MAYBE"], "set_b": ["?", "WHATEVER"]}'
    a, b = _parse_match_result(raw, n_a=2, n_b=2)
    assert a == ["NEW", "NEW"]
    assert b == ["MISSED", "MISSED"]


def test_parse_match_missing_keys_returns_all_miss() -> None:
    raw = '{"foo": "bar"}'
    a, b = _parse_match_result(raw, n_a=1, n_b=1)
    assert a == ["NEW"]
    assert b == ["MISSED"]


# ─── _compute_p_r_f1 ─────────────────────────────────────────────────────────


def test_compute_perfect_match() -> None:
    """All claims match → P=R=F1=1.0"""
    p, r, f1 = _compute_p_r_f1(
        set_a=["SUPPORTED", "SUPPORTED"],
        set_b=["FOUND", "FOUND"],
        n_a=2,
        n_b=2,
    )
    assert p == 1.0
    assert r == 1.0
    assert f1 == 1.0


def test_compute_total_miss() -> None:
    """Nothing matches → P=R=F1=0.0"""
    p, r, f1 = _compute_p_r_f1(
        set_a=["NEW", "NEW"],
        set_b=["MISSED", "MISSED"],
        n_a=2,
        n_b=2,
    )
    assert p == 0.0
    assert r == 0.0
    assert f1 == 0.0


def test_compute_high_precision_low_recall() -> None:
    """1 of 1 model claim is supported (P=1.0) but only 1 of 4 gold claims found (R=0.25)."""
    p, r, f1 = _compute_p_r_f1(
        set_a=["SUPPORTED"],
        set_b=["FOUND", "MISSED", "MISSED", "MISSED"],
        n_a=1,
        n_b=4,
    )
    assert p == 1.0
    assert r == 0.25
    # Harmonic mean
    assert 0.39 < f1 < 0.41


def test_compute_low_precision_high_recall() -> None:
    """4 model claims, 1 supported (P=0.25); 1 gold claim, found (R=1.0)."""
    p, r, f1 = _compute_p_r_f1(
        set_a=["SUPPORTED", "NEW", "NEW", "NEW"],
        set_b=["FOUND"],
        n_a=4,
        n_b=1,
    )
    assert p == 0.25
    assert r == 1.0
    assert 0.39 < f1 < 0.41


def test_compute_zero_model_claims() -> None:
    """No model claims → P=0 by definition."""
    p, r, f1 = _compute_p_r_f1(set_a=[], set_b=["MISSED"], n_a=0, n_b=1)
    assert p == 0.0
    assert r == 0.0
    assert f1 == 0.0


def test_compute_zero_gold_claims() -> None:
    """No gold claims → R=0 to avoid div-by-zero noise."""
    p, r, f1 = _compute_p_r_f1(set_a=["NEW"], set_b=[], n_a=1, n_b=0)
    assert p == 0.0  # 0 SUPPORTED out of 1 model claim
    assert r == 0.0
    assert f1 == 0.0


# ─── _gold_text_from_metadata ────────────────────────────────────────────────


def test_gold_text_from_supports_field() -> None:
    metadata = {
        "gold_sources": [
            {
                "doi": "10.x/y",
                "supports": "The vitamin C study found no effect on cold incidence.",
            }
        ]
    }
    text = _gold_text_from_metadata(metadata)
    assert "no effect on cold incidence" in text


def test_gold_text_from_contradicts_field() -> None:
    metadata = {
        "gold_contradict_sources": [
            {
                "doi": "10.x/y",
                "contradicts": "The retraction notice invalidates the original 19% claim.",
            }
        ]
    }
    text = _gold_text_from_metadata(metadata)
    assert "retraction notice" in text


def test_gold_text_combines_both_lists() -> None:
    metadata = {
        "gold_sources": [{"supports": "claim A"}],
        "gold_contradict_sources": [{"contradicts": "claim B"}],
    }
    text = _gold_text_from_metadata(metadata)
    assert "claim A" in text
    assert "claim B" in text


def test_gold_text_falls_back_to_citation() -> None:
    metadata = {
        "gold_sources": [{"doi": "10.x/y", "citation": "Smith et al. 2020 Nature"}]
    }
    text = _gold_text_from_metadata(metadata)
    assert "Smith et al" in text


def test_gold_text_falls_back_to_note() -> None:
    metadata = {
        "gold_contradict_sources": [
            {"note": "No paper claiming sub-2 Å exists as of late 2025"}
        ]
    }
    text = _gold_text_from_metadata(metadata)
    assert "sub-2" in text


def test_gold_text_empty_for_missing_metadata() -> None:
    assert _gold_text_from_metadata({}) == ""
    assert _gold_text_from_metadata({"gold_sources": []}) == ""


def test_gold_text_skips_non_dict_entries() -> None:
    """Defensive: case JSON might have a string in the sources array."""
    metadata = {"gold_sources": ["not a dict", {"supports": "real claim"}]}
    text = _gold_text_from_metadata(metadata)
    assert "real claim" in text
    assert "not a dict" not in text
