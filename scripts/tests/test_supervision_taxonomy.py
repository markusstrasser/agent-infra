"""Verifier for the supervision taxonomy (Gov-ID lib:supervision-taxonomy).

Ground-truth anchored on REAL corrections, including this session's (2026-06-14):
"why ask" and "why not build it now?" must classify as over_caution / RAISE_AUTONOMY —
the type the old scalar SLI was structurally blind to. Also pins the single-source
invariant: the consumers must NOT re-state the regexes (epistemic principle #9).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import supervision_taxonomy as tax  # noqa: E402

# (message, expected_type or None, expected_direction or None)
CASES = [
    # over_caution / RAISE_AUTONOMY — the new, previously-invisible class (this session's real flags)
    ("why ask", "over_caution", "raise_autonomy"),
    ("why not build it now?", "over_caution", "raise_autonomy"),
    ("b) is the answer, given the principle of VOI right? #f why ask", "over_caution", "raise_autonomy"),
    ("just do it now", "over_caution", "raise_autonomy"),
    ("why are you deferring this, see it through", "over_caution", "raise_autonomy"),
    ("you don't need to ask me, go ahead", "over_caution", "raise_autonomy"),
    # rediscovery / GROW_COVERAGE — the prior "blindspot" class
    ("SOOO why didn't you find this bug?", "rediscovery", "grow_coverage"),
    ("did you check the git log first", "rediscovery", "grow_coverage"),
    ("we already discussed this", "rediscovery", "grow_coverage"),
    ("you should have looked at the prior decisions", "rediscovery", "grow_coverage"),
    # error_correction / REDUCE_ERROR — blunt corrections (start-anchored)
    ("no, that's wrong", "error_correction", "reduce_error"),
    ("revert that change", "error_correction", "reduce_error"),
    ("stop, undo that", "error_correction", "reduce_error"),
    # NOT corrections — ordinary task instructions must NOT flag (precision guard)
    ("add a test for the parser", None, None),
    ("run the tests and commit this", None, None),
    ("implement the feature and open a PR", None, None),
    ("what model are you using?", None, None),
]


@pytest.mark.parametrize("text,exp_type,exp_dir", CASES)
def test_regex_classification(text, exp_type, exp_dir):
    m = tax.classify_regex(text)
    if exp_type is None:
        assert m is None, f"{text!r} should not classify, got {m}"
    else:
        assert m is not None, f"{text!r} should classify as {exp_type}, got None"
        assert m.type_id == exp_type, f"{text!r}: expected {exp_type}, got {m.type_id} (evidence {m.evidence})"
        assert m.direction.value == exp_dir
        assert m.evidence  # inspectable: every classification cites why


def test_priority_specific_before_blunt():
    """A message that is both blunt AND substantive classifies by the substantive type."""
    m = tax.classify_regex("no, why didn't you check the existing tool first")
    assert m is not None and m.type_id == "rediscovery"  # not error_correction — rediscovery is the real signal


def test_direction_vector_accumulation():
    vec = tax.empty_vector()
    tax.add_to_vector(vec, "over_caution", 2)
    tax.add_to_vector(vec, "rediscovery", 1)
    tax.add_to_vector(vec, "denial", 3)  # structural → reduce_error
    assert vec["raise_autonomy"] == 2
    assert vec["grow_coverage"] == 1
    assert vec["reduce_error"] == 3
    assert vec["amplify_taste"] == 0


def test_taxonomy_is_closed_and_complete():
    # every type maps to a real Direction; every Direction has at least one type
    dirs_used = {t.direction for t in tax.TAXONOMY}
    assert dirs_used == set(tax.Direction), "every Direction must have a type and vice versa"
    assert {t.id for t in tax.TAXONOMY} >= {"over_caution", "rediscovery", "error_correction", "taste_steer", "denial", "repeated_instruction"}


def test_single_source_no_duplicated_regex_in_consumers():
    """epistemic principle #9: the correction regexes live ONLY in the taxonomy. The consumers
    must import it, not re-state CORRECTION_PATTERNS / BLINDSPOT_PATTERNS / BLIND_SEEDS."""
    for fname in ("supervision-kpi.py", "blindspot_miner.py"):
        src = (REPO / "scripts" / fname).read_text()
        assert "import supervision_taxonomy" in src, f"{fname} must load the taxonomy"
        for banned in ("BLINDSPOT_PATTERNS", "CORRECTION_PATTERNS", "BLIND_SEEDS", "NORMAL_SEEDS ="):
            assert banned not in src, f"{fname} re-states {banned} — must load it from the taxonomy"


def test_gross_load_is_weighted():
    counts = {"over_caution": 1, "denial": 1}  # weights 3 + 2
    assert tax.gross_load(counts, by_type=True) == 5
