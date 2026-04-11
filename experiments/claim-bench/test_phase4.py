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
