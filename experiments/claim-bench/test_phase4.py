"""Phase 4 unit tests for cards.py.

Covers the pure-logic parts:
- _ci95_from_values        (normal-approximation CI)
- _safe_value              (Score → float | None)
- derive_independence_card (synthetic EvalLog → independence card)
- derive_adequacy_card     (synthetic EvalLog → adequacy card)
- render_independence_md   (smoke test only)
- render_adequacy_md       (smoke test only)

The CLI is not tested — it's a thin wrapper around derive_*.

Run:
    uv run python -m pytest experiments/claim-bench/test_phase4.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

THIS_DIR = str(Path(__file__).resolve().parent)
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

from cards import (  # noqa: E402
    _ci95_from_values,
    _safe_value,
    derive_adequacy_card,
    derive_independence_card,
    render_adequacy_md,
    render_independence_md,
)


# ─── _ci95_from_values ───────────────────────────────────────────────────────


def test_ci95_empty() -> None:
    mean, lo, hi = _ci95_from_values([])
    assert (mean, lo, hi) == (0.0, 0.0, 0.0)


def test_ci95_single_value() -> None:
    """N=1 has no variance — CI is just the value."""
    mean, lo, hi = _ci95_from_values([0.5])
    assert mean == 0.5
    assert lo == 0.5
    assert hi == 0.5


def test_ci95_zero_variance() -> None:
    """Identical values → CI width = 0. (Floating-point precision via approx.)"""
    mean, lo, hi = _ci95_from_values([0.7, 0.7, 0.7])
    assert mean == pytest.approx(0.7)
    assert lo == pytest.approx(0.7)
    assert hi == pytest.approx(0.7)
    assert hi - lo == pytest.approx(0.0)


def test_ci95_normal_case() -> None:
    """Mixed values → meaningful CI bracketing the mean."""
    mean, lo, hi = _ci95_from_values([0.0, 0.5, 1.0])
    assert mean == pytest.approx(0.5, abs=0.01)
    assert lo < mean < hi
    assert lo >= 0.0
    assert hi <= 1.0


def test_ci95_clamps_to_unit_interval() -> None:
    """Even if normal-approx would exceed [0, 1], CI is clamped."""
    mean, lo, hi = _ci95_from_values([1.0] * 10)
    assert mean == 1.0
    assert hi <= 1.0
    assert lo >= 0.0


# ─── _safe_value ─────────────────────────────────────────────────────────────


def test_safe_value_none() -> None:
    assert _safe_value(None) is None


def test_safe_value_float() -> None:
    s = SimpleNamespace(value=0.75)
    assert _safe_value(s) == 0.75


def test_safe_value_int() -> None:
    s = SimpleNamespace(value=1)
    assert _safe_value(s) == 1.0


def test_safe_value_string() -> None:
    """A string Score.value is not coercible — return None."""
    s = SimpleNamespace(value="aware")
    assert _safe_value(s) is None


# ─── Synthetic EvalLog fixture ───────────────────────────────────────────────


def _make_score(value: float, metadata: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(value=value, metadata=metadata or {})


def _make_sample(
    sid: str,
    target: str,
    metadata: dict,
    scores: dict[str, SimpleNamespace],
) -> SimpleNamespace:
    return SimpleNamespace(id=sid, target=target, metadata=metadata, scores=scores)


def _make_log(samples: list, model: str = "test/model") -> SimpleNamespace:
    return SimpleNamespace(
        samples=samples,
        eval=SimpleNamespace(
            run_id="test_run_id",
            task="claim_verification_probe",
            model=model,
            created="2026-04-11T00:00:00+00:00",
        ),
    )


# ─── derive_independence_card ────────────────────────────────────────────────


def test_independence_empty_log() -> None:
    log = _make_log([])
    card = derive_independence_card(log)
    assert card["card_type"] == "independence"
    assert card["n_cases"] == 0
    # Single-author threat is always added
    threat_names = [t["name"] for t in card["major_threats"]]
    assert "single_author_corpus" in threat_names


def test_independence_easy_cases_flagged() -> None:
    samples = [
        _make_sample(
            "001_easy_a",
            "supported",
            {"difficulty": "easy", "domain": "bio"},
            {},
        ),
        _make_sample(
            "002_easy_b",
            "contradicted",
            {"difficulty": "easy", "domain": "bio"},
            {},
        ),
    ]
    log = _make_log(samples)
    card = derive_independence_card(log)
    threats = {t["name"]: t for t in card["major_threats"]}
    assert "memorizable_cases" in threats
    assert threats["memorizable_cases"]["severity"] == "medium"  # 2/2 easy
    assert "001_easy_a" in threats["memorizable_cases"]["affected_cases"]


def test_independence_post_cutoff_coverage() -> None:
    """Cases citing post-2025 evidence count toward post_cutoff_case_count."""
    samples = [
        _make_sample(
            "001",
            "supported",
            {
                "gold_sources": [{"published_date": "2026-04-01"}],
                "difficulty": "hard",
            },
            {},
        ),
        _make_sample(
            "002",
            "contradicted",
            {
                "gold_contradict_sources": [{"published_date": "2025-12-03"}],
                "difficulty": "hard",
            },
            {},
        ),
    ]
    log = _make_log(samples)
    card = derive_independence_card(log)
    assert card["post_cutoff_case_count"] == 2


def test_independence_low_post_cutoff_coverage_flagged() -> None:
    """If <25% of cases have post-cutoff evidence, threat fires."""
    samples = [
        _make_sample(
            f"{i:03d}",
            "supported",
            {"gold_sources": [{"published_date": "2020-01-01"}]},
            {},
        )
        for i in range(8)
    ]
    log = _make_log(samples)
    card = derive_independence_card(log)
    threat_names = [t["name"] for t in card["major_threats"]]
    assert "low_post_cutoff_coverage" in threat_names


def test_independence_domain_concentration() -> None:
    """If one domain >50% of cases, domain_concentration threat fires."""
    samples = [
        _make_sample(f"{i:03d}", "supported", {"domain": "bio"}, {})
        for i in range(5)
    ]
    samples.append(
        _make_sample("099", "contradicted", {"domain": "physics"}, {})
    )
    log = _make_log(samples)
    card = derive_independence_card(log)
    threat_names = [t["name"] for t in card["major_threats"]]
    assert "domain_concentration" in threat_names


def test_independence_distributions_populated() -> None:
    samples = [
        _make_sample("a", "supported", {"difficulty": "easy", "domain": "bio"}, {}),
        _make_sample("b", "contradicted", {"difficulty": "hard", "domain": "phys"}, {}),
    ]
    log = _make_log(samples)
    card = derive_independence_card(log)
    assert card["case_difficulty_distribution"]["easy"] == 1
    assert card["case_difficulty_distribution"]["hard"] == 1
    assert card["case_domain_distribution"]["bio"] == 1
    assert card["case_domain_distribution"]["phys"] == 1


# ─── derive_adequacy_card ────────────────────────────────────────────────────


def test_adequacy_empty_log() -> None:
    log = _make_log([])
    card = derive_adequacy_card(log)
    assert card["card_type"] == "adequacy"
    assert card["n_cases"] == 0
    assert card["epochs_per_case"] == 0
    assert card["decision_grade"] == "exploratory"


def test_adequacy_per_scorer_means() -> None:
    samples = [
        _make_sample(
            "a",
            "supported",
            {},
            {
                "verdict_enum_scorer": _make_score(1.0),
                "groundedness_scorer": _make_score(0.5),
            },
        ),
        _make_sample(
            "b",
            "contradicted",
            {},
            {
                "verdict_enum_scorer": _make_score(0.0),
                "groundedness_scorer": _make_score(1.0),
            },
        ),
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    assert card["per_scorer"]["verdict_enum_scorer"]["mean"] == 0.5
    assert card["per_scorer"]["groundedness_scorer"]["mean"] == 0.75


def test_adequacy_consistency_perfect() -> None:
    """3 epochs, model gave the same verdict each time → consistency 1.0"""
    samples = [
        _make_sample(
            "a",
            "supported",
            {},
            {
                "verdict_enum_scorer": _make_score(
                    1.0, metadata={"predicted": "supported"}
                )
            },
        )
        for _ in range(3)
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    assert card["consistency_per_case"]["a"] == 1.0
    assert card["mean_consistency"] == 1.0


def test_adequacy_consistency_partial() -> None:
    """3 epochs, 2 supported and 1 mixed → consistency 2/3 ≈ 0.667"""
    metadata_options = ["supported", "supported", "mixed"]
    samples = [
        _make_sample(
            "a",
            "supported",
            {},
            {
                "verdict_enum_scorer": _make_score(
                    1.0 if pred == "supported" else 0.0,
                    metadata={"predicted": pred},
                )
            },
        )
        for pred in metadata_options
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    assert card["consistency_per_case"]["a"] == pytest.approx(0.6667, abs=0.01)


def test_adequacy_joint_success_passes() -> None:
    """Sample with verdict=1, grounded=1, currency=1 → joint pass."""
    samples = [
        _make_sample(
            "a",
            "supported",
            {},
            {
                "verdict_enum_scorer": _make_score(1.0),
                "groundedness_scorer": _make_score(1.0),
                "currency_scorer": _make_score(
                    1.0, metadata={"currency_status": "all_current"}
                ),
            },
        ),
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    assert card["joint_success"]["n_passes"] == 1
    assert card["joint_success"]["n_total"] == 1
    assert card["joint_success"]["rate"] == 1.0


def test_adequacy_joint_success_fails_on_currency_unaware() -> None:
    """The case-004 failure mode: verdict=1, grounded=1, currency=0 → joint fail."""
    samples = [
        _make_sample(
            "a",
            "contradicted",
            {},
            {
                "verdict_enum_scorer": _make_score(1.0),
                "groundedness_scorer": _make_score(1.0),
                "currency_scorer": _make_score(
                    0.0, metadata={"currency_status": "unaware"}
                ),
            },
        ),
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    assert card["joint_success"]["n_passes"] == 0
    assert card["joint_success"]["rate"] == 0.0


def test_adequacy_decision_grade_exploratory_for_small_corpus() -> None:
    """8 cases × 3 epochs = 24 samples, well below 30 → exploratory."""
    samples = [
        _make_sample(
            f"case_{i}",
            "supported",
            {},
            {"verdict_enum_scorer": _make_score(1.0, metadata={"predicted": "supported"})},
        )
        for i in range(8)
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    assert card["decision_grade"] == "exploratory"


def test_adequacy_decision_grade_bounded_for_30_plus_cases() -> None:
    samples = [
        _make_sample(
            f"case_{i}",
            "supported",
            {},
            {"verdict_enum_scorer": _make_score(1.0, metadata={"predicted": "supported"})},
        )
        for i in range(35)
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    assert card["decision_grade"] == "bounded"


def test_adequacy_gold_distribution() -> None:
    samples = [
        _make_sample("a", "supported", {}, {}),
        _make_sample("b", "supported", {}, {}),
        _make_sample("c", "contradicted", {}, {}),
        _make_sample("d", "mixed", {}, {}),
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    assert card["gold_distribution"]["supported"] == 2
    assert card["gold_distribution"]["contradicted"] == 1
    assert card["gold_distribution"]["mixed"] == 1


def test_adequacy_atomic_claim_excludes_not_applicable() -> None:
    """Regression for plan-close finding F1.

    atomic_claim_scorer returns value=1.0 with answer='not_applicable' for
    samples lacking gold claims (e.g. case 007 GWAS not_verifiable). inspect_ai's
    raw mean() includes these in the denominator, inflating the atomic_claim
    mean. cards.py is the headline path — must filter them out.

    Setup: 3 samples.
      - sample_a: atomic_claim=0.2, status=scored       → included
      - sample_b: atomic_claim=1.0, status=not_applicable → EXCLUDED
      - sample_c: atomic_claim=0.4, status=scored       → included

    Raw mean (wrong): (0.2 + 1.0 + 0.4) / 3 = 0.533
    Effective mean (correct): (0.2 + 0.4) / 2 = 0.300
    """
    samples = [
        _make_sample(
            "sample_a",
            "supported",
            {},
            {
                "atomic_claim_scorer": _make_score(
                    0.2, metadata={"atomic_status": "scored"}
                )
            },
        ),
        _make_sample(
            "sample_b",
            "not_verifiable",
            {},
            {
                "atomic_claim_scorer": _make_score(
                    1.0, metadata={"atomic_status": "not_applicable"}
                )
            },
        ),
        _make_sample(
            "sample_c",
            "contradicted",
            {},
            {
                "atomic_claim_scorer": _make_score(
                    0.4, metadata={"atomic_status": "scored"}
                )
            },
        ),
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    ac = card["per_scorer"]["atomic_claim_scorer"]
    # n excludes the not_applicable sample
    assert ac["n"] == 2
    # mean is over scored samples only
    assert ac["mean"] == pytest.approx(0.3, abs=0.0001)
    # excluded count surfaced in metadata
    assert ac["excluded_not_applicable"] == 1


def test_adequacy_atomic_claim_only_not_applicable_samples() -> None:
    """Edge case: if ALL atomic_claim samples are not_applicable, the scorer
    should not appear in per_scorer at all (no valid values).
    """
    samples = [
        _make_sample(
            "a",
            "not_verifiable",
            {},
            {
                "atomic_claim_scorer": _make_score(
                    1.0, metadata={"atomic_status": "not_applicable"}
                )
            },
        ),
        _make_sample(
            "b",
            "not_verifiable",
            {},
            {
                "atomic_claim_scorer": _make_score(
                    1.0, metadata={"atomic_status": "not_applicable"}
                )
            },
        ),
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    # Either the scorer is entirely absent OR it has n=0 (neither is reported
    # as a valid mean). Current implementation drops it entirely.
    assert "atomic_claim_scorer" not in card["per_scorer"]


def test_adequacy_other_scorers_not_affected_by_atomic_filter() -> None:
    """The F1 fix is narrowly scoped to atomic_claim_scorer. currency_scorer
    and calibration_scorer have their own 'N/A' semantics but the fix does
    NOT filter them — verify they still include all samples in their mean.
    """
    samples = [
        _make_sample(
            "a",
            "supported",
            {},
            {
                "currency_scorer": _make_score(
                    1.0, metadata={"currency_status": "not_applicable"}
                ),
                "calibration_scorer": _make_score(
                    1.0, metadata={"calibration_label": "abstention_consistent"}
                ),
            },
        ),
        _make_sample(
            "b",
            "supported",
            {},
            {
                "currency_scorer": _make_score(
                    0.5, metadata={"currency_status": "partial"}
                ),
                "calibration_scorer": _make_score(
                    0.5, metadata={"calibration_label": "neutral"}
                ),
            },
        ),
    ]
    log = _make_log(samples)
    card = derive_adequacy_card(log)
    assert card["per_scorer"]["currency_scorer"]["n"] == 2
    assert card["per_scorer"]["currency_scorer"]["mean"] == 0.75
    assert card["per_scorer"]["calibration_scorer"]["n"] == 2
    assert card["per_scorer"]["calibration_scorer"]["mean"] == 0.75


# ─── Markdown rendering smoke tests ──────────────────────────────────────────


def test_render_independence_md_smoke() -> None:
    log = _make_log([])
    card = derive_independence_card(log)
    md = render_independence_md(card)
    assert "# Independence Card" in md
    assert "Major threats" in md


def test_render_adequacy_md_smoke() -> None:
    log = _make_log([])
    card = derive_adequacy_card(log)
    md = render_adequacy_md(card)
    assert "# Adequacy Card" in md
    assert "Decision grade" in md
    assert "EXPLORATORY" in md  # default for empty log
