"""Regression tests for concrete paths synthesized from guard regexes."""

from scripts.guard_doctor import _sample_for


def test_sample_for_grouped_personal_protected_paths() -> None:
    assert _sample_for("(^|/)(data|private)/") == "data/sample.dat"


def test_sample_for_nested_personal_append_only_paths() -> None:
    pattern = "(^|/)(admin/(tax|immigration)|health/(research|entities|self-reports)|apps/phenome/docs/research)/"
    assert _sample_for(pattern) == "admin/tax/sample.dat"


def test_sample_for_preserves_existing_flat_patterns() -> None:
    assert _sample_for("(^|/)datasets/|\\.parquet$") == "datasets/sample.dat"
    assert _sample_for("(^|/)improvement-log\\.md$|^decisions/") == "improvement-log.md"
