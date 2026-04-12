"""Phase 2 unit tests for claim-bench process_metrics.

Covers the pure-logic parts of process_metrics.py:
- _extract_dois_from_text       (DOI regex + trim)
- _extract_urls_from_text       (URL regex)
- _classify_url                 (publisher/preprint/mirror)
- _interpret_crossref_message   (Crossref message → currency flags)
- _parse_currency_judge         (judge output parsing)
- _classify_hedge               (hedged/confident/neutral classifier)
- _normalize_url_for_match      (URL canonicalization for fuzzy match)
- joint_success_per_sample      (the canonical headline definition)

Network-dependent tests (Crossref API, judge model calls) are NOT covered
here — they require live APIs and would couple unit tests to remote state.
The full eval run is the integration test.

Run:
    uv run pytest experiments/claim-bench/test_phase2.py -v
"""

from __future__ import annotations

import pytest

from claim_bench.process_metrics import (
    _classify_hedge,
    _classify_url,
    _extract_dois_from_text,
    _extract_urls_from_text,
    _interpret_crossref_message,
    _normalize_url_for_match,
    _parse_currency_judge,
    joint_success_per_sample,
)


# ─── _extract_dois_from_text ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, expected",
    [
        ("see DOI 10.1038/s41586-026-10359-0 for details", {"10.1038/s41586-026-10359-0"}),
        # Trailing punctuation must be trimmed
        ("(10.1056/NEJMoa1809944).", {"10.1056/nejmoa1809944"}),
        # Multiple DOIs in one text
        (
            "10.1038/s41586-025-09726-0 and 10.1056/NEJMoa1809944",
            {"10.1038/s41586-025-09726-0", "10.1056/nejmoa1809944"},
        ),
        # Mixed case is normalized to lower
        ("DOI: 10.1093/IJE/dyt148", {"10.1093/ije/dyt148"}),
        # No DOI in text
        ("just some text without a DOI", set()),
        # Empty
        ("", set()),
    ],
)
def test_extract_dois(text: str, expected: set[str]) -> None:
    assert _extract_dois_from_text(text) == expected


def test_extract_dois_dedupes() -> None:
    text = "10.1038/x and 10.1038/x and 10.1038/x"
    assert _extract_dois_from_text(text) == {"10.1038/x"}


# ─── URL fragment stripping (regression for over-extraction bug) ─────────────


@pytest.mark.parametrize(
    "text, expected_doi",
    [
        # /fulltext.html getting appended (observed on case 001)
        ("DOI: 10.1007/s13238-015-0153-5/fulltext.html", "10.1007/s13238-015-0153-5"),
        # /pdf appended (observed on case 003)
        ("Reference 10.3847/1538-4357/ae17af/pdf", "10.3847/1538-4357/ae17af"),
        # /full appended (observed on case 007)
        (
            "10.3389/fgene.2024.1375481/full was the source",
            "10.3389/fgene.2024.1375481",
        ),
        # /abstract appended
        ("10.1038/s41586-024-07219-0/abstract", "10.1038/s41586-024-07219-0"),
        # /epdf appended
        ("10.1056/NEJMoa1809944/epdf", "10.1056/nejmoa1809944"),
    ],
)
def test_extract_dois_strips_url_fragments(text: str, expected_doi: str) -> None:
    """Regression for the Phase 2 first-eval-run finding: DOIs inside URLs
    were over-matched to include /fulltext.html, /pdf, /full path components,
    causing Crossref queries to 404 and silently disabling currency_scorer.
    """
    dois = _extract_dois_from_text(text)
    assert expected_doi in dois, f"expected {expected_doi}, got {dois}"


# ─── Publisher URL → DOI extraction ──────────────────────────────────────────


@pytest.mark.parametrize(
    "text, expected_doi",
    [
        # Nature: nature.com/articles/sNNNNN-...
        (
            "see https://www.nature.com/articles/s41586-024-07219-0 for the paper",
            "10.1038/s41586-024-07219-0",
        ),
        (
            "https://nature.com/articles/s41586-026-10359-0",
            "10.1038/s41586-026-10359-0",
        ),
        # NEJM: nejm.org/doi/10.1056/...
        (
            "https://www.nejm.org/doi/10.1056/NEJMoa1809944",
            "10.1056/nejmoa1809944",
        ),
        (
            "https://nejm.org/doi/full/10.1056/NEJMoa1809944",
            "10.1056/nejmoa1809944",
        ),
        # Science: science.org/doi/10.1126/...
        (
            "https://www.science.org/doi/10.1126/science.abc1234",
            "10.1126/science.abc1234",
        ),
        # doi.org resolver
        (
            "https://doi.org/10.1056/NEJMoa1809944",
            "10.1056/nejmoa1809944",
        ),
    ],
)
def test_extract_dois_from_publisher_urls(text: str, expected_doi: str) -> None:
    """Regression for case-004 failure mode: the model retrieved the Nature
    paper page but the DOI string was past the 1500-char text excerpt cap.
    Currency_scorer reported not_applicable and silently failed to detect
    the retraction. This test pins the publisher URL → DOI extraction that
    catches the DOI from the URL itself, even when text excerpt doesn't
    contain it.
    """
    dois = _extract_dois_from_text(text)
    assert expected_doi in dois, f"expected {expected_doi}, got {dois}"


def test_extract_dois_combines_text_and_url_extraction() -> None:
    """A trace with BOTH a text DOI and a publisher URL DOI should yield both."""
    text = (
        "Result 1: see DOI 10.1186/s12889-023-17229-8\n"
        "Result 2: https://www.nature.com/articles/s41586-024-07219-0"
    )
    dois = _extract_dois_from_text(text)
    assert "10.1186/s12889-023-17229-8" in dois
    assert "10.1038/s41586-024-07219-0" in dois


# ─── _extract_urls_from_text ─────────────────────────────────────────────────


def test_extract_urls_basic() -> None:
    text = "see https://nature.com/article and http://example.com for context"
    urls = _extract_urls_from_text(text)
    assert "https://nature.com/article" in urls
    assert "http://example.com" in urls


def test_extract_urls_strips_trailing_punctuation() -> None:
    text = "Reference: https://nature.com/article."
    urls = _extract_urls_from_text(text)
    # Trailing period must not be part of the URL
    assert all(not u.endswith(".") for u in urls)


def test_extract_urls_empty() -> None:
    assert _extract_urls_from_text("") == []
    assert _extract_urls_from_text("no urls at all") == []


# ─── _classify_url ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url, expected",
    [
        # Publishers
        ("https://www.nature.com/articles/s41586-026-10359-0", "publisher"),
        ("https://nejm.org/doi/10.1056/NEJMoa1809944", "publisher"),
        ("https://www.science.org/doi/10.1126/science.abc1234", "publisher"),
        ("https://doi.org/10.1056/NEJMoa1809944", "publisher"),
        # Preprints
        ("https://arxiv.org/abs/2509.04151", "preprint"),
        ("https://www.biorxiv.org/content/10.1101/2024.01.01.123456v1", "preprint"),
        # Institutional / personal mirrors
        ("https://pik-potsdam.de/~kotz/papers/climate2024.pdf", "institutional_mirror"),
        ("https://stanford.edu/people/researcher/paper.pdf", "institutional_mirror"),
        # Generic / unknown
        ("https://blog.example.com/news/", "other"),
    ],
)
def test_classify_url(url: str, expected: str) -> None:
    assert _classify_url(url) == expected


def test_classify_url_handles_malformed() -> None:
    # No protocol → not a real URL but should not crash
    assert _classify_url("nature.com") == "other"
    assert _classify_url("") == "other"


# ─── _interpret_crossref_message ─────────────────────────────────────────────


def test_interpret_empty() -> None:
    flags = _interpret_crossref_message({})
    assert flags["is_retraction"] is False
    assert flags["has_update"] is False
    assert flags["is_retracted"] is False
    assert flags["is_corrected"] is False
    assert flags["update_labels"] == []


def test_interpret_none() -> None:
    flags = _interpret_crossref_message(None)
    assert flags["is_retracted"] is False


def test_interpret_record_is_retraction_notice() -> None:
    """A Crossref record with subtype='retraction' is itself a retraction notice."""
    msg = {"subtype": "retraction", "title": ["Retraction Note: ..."]}
    flags = _interpret_crossref_message(msg)
    assert flags["is_retraction"] is True
    assert flags["is_retracted"] is False  # The notice itself is not retracted
    assert flags["has_update"] is False


def test_interpret_paper_with_retraction_update() -> None:
    """A paper that has been retracted has update-to entries with 'Retraction' labels."""
    msg = {
        "update-to": [
            {
                "DOI": "10.1038/s41586-025-09726-0",
                "label": "Retraction",
                "type": "retraction",
            }
        ]
    }
    flags = _interpret_crossref_message(msg)
    assert flags["has_update"] is True
    assert flags["is_retracted"] is True
    assert flags["update_labels"] == ["Retraction"]


def test_interpret_paper_with_correction() -> None:
    """A corrected paper has update-to with 'Correction' label, not retraction."""
    msg = {
        "update-to": [
            {"DOI": "10.1038/s41586-024-07732-2", "label": "Correction", "type": "correction"}
        ]
    }
    flags = _interpret_crossref_message(msg)
    assert flags["has_update"] is True
    assert flags["is_retracted"] is False
    assert flags["is_corrected"] is True


def test_interpret_relation_is_retracted_by() -> None:
    """Crossref also uses relation.is-retracted-by for some retractions."""
    msg = {"relation": {"is-retracted-by": [{"id": "10.1038/x", "id-type": "doi"}]}}
    flags = _interpret_crossref_message(msg)
    assert flags["is_retracted"] is True


def test_interpret_title_says_retracted_article() -> None:
    """Regression for case 004: Nature prepends 'RETRACTED ARTICLE:' to titles
    of retracted papers but does NOT populate update-to or relation. The title
    is the most reliable cross-publisher signal — _interpret_crossref_message
    must check it.

    Empirically: querying https://api.crossref.org/works/10.1038/s41586-024-07219-0
    on 2026-04-11 returned exactly this shape — title with RETRACTED ARTICLE
    prefix, update-to=null, relation only contains has-preprint.
    """
    msg = {
        "title": ["RETRACTED ARTICLE: The economic commitment of climate change"],
        "subtype": None,
        "update-to": None,
        "relation": {"has-preprint": [{"id": "10.x/y", "id-type": "doi"}]},
    }
    flags = _interpret_crossref_message(msg)
    assert flags["is_retracted"] is True
    assert flags["retraction_signal"] == "title"


@pytest.mark.parametrize(
    "title_prefix",
    [
        "RETRACTED ARTICLE: ",
        "Retracted: ",
        "WITHDRAWN: ",
        "withdrawn article: ",
    ],
)
def test_interpret_title_prefix_variants(title_prefix: str) -> None:
    """Title prefixes that mark a RETRACTED paper (not a retraction notice).

    Note: 'Retraction Note: ...' titles are NOT in this list — those are
    the notices themselves, signaled by subtype='retraction', and the
    notice itself is not is_retracted (see test_interpret_record_is_retraction_notice).
    """
    msg = {"title": [title_prefix + "Some paper title"]}
    flags = _interpret_crossref_message(msg)
    assert flags["is_retracted"] is True


def test_interpret_retraction_notice_title_not_flagged_as_retracted() -> None:
    """A 'Retraction Note: ...' titled record with subtype='retraction' is the
    notice — it should be is_retraction=True, is_retracted=False. The notice
    is current and authoritative; only the paper IT refers to is retracted.
    """
    msg = {
        "subtype": "retraction",
        "title": ["Retraction Note: The economic commitment of climate change"],
    }
    flags = _interpret_crossref_message(msg)
    assert flags["is_retraction"] is True
    assert flags["is_retracted"] is False


def test_interpret_title_string_not_list() -> None:
    """Crossref usually returns title as a list, but defensive: handle string."""
    msg = {"title": "RETRACTED ARTICLE: foo"}
    flags = _interpret_crossref_message(msg)
    assert flags["is_retracted"] is True


def test_interpret_signal_priority_title_first() -> None:
    """When multiple signals fire, retraction_signal records the first hit
    in priority order: title → subtype → update-to → relation.
    """
    msg = {
        "title": ["RETRACTED ARTICLE: foo"],
        "update-to": [{"label": "Retraction"}],
    }
    flags = _interpret_crossref_message(msg)
    assert flags["retraction_signal"] == "title"


def test_interpret_normal_paper_no_retraction_signal() -> None:
    msg = {
        "title": ["A normal scientific paper"],
        "subtype": None,
        "update-to": None,
        "relation": {"has-preprint": [{"id": "10.x/y"}]},
    }
    flags = _interpret_crossref_message(msg)
    assert flags["is_retracted"] is False
    assert flags["retraction_signal"] == "none"


# ─── _parse_currency_judge ───────────────────────────────────────────────────


def test_parse_aware() -> None:
    label, value = _parse_currency_judge("aware\nThe model surfaced the retraction")
    assert label == "aware"
    assert value == 1.0


def test_parse_partial_currency() -> None:
    label, value = _parse_currency_judge("partial\nCited but did not address staleness")
    assert label == "partial"
    assert value == 0.5


def test_parse_unaware() -> None:
    label, value = _parse_currency_judge("unaware\nTreated retracted source as current")
    assert label == "unaware"
    assert value == 0.0


def test_parse_unaware_variant() -> None:
    label, value = _parse_currency_judge("not aware\nMissed it completely")
    assert label == "unaware"
    assert value == 0.0


def test_parse_currency_strips_decoration() -> None:
    label, value = _parse_currency_judge("**aware**\nGood")
    assert label == "aware"
    assert value == 1.0


def test_parse_currency_error_returns_zero() -> None:
    """Parse failure must score 0.0, never 0.5 — same fix as Phase 1 groundedness."""
    label, value = _parse_currency_judge("???\nunclear")
    assert label == "parse_error"
    assert value == 0.0


def test_parse_currency_empty() -> None:
    label, value = _parse_currency_judge("")
    assert label == "parse_error"
    assert value == 0.0


# ─── _classify_hedge ─────────────────────────────────────────────────────────


def test_classify_hedge_strong_hedge() -> None:
    text = (
        "This claim is unclear and the evidence appears to be insufficient. "
        "It seems to be ambiguous whether this is supported, and the data may "
        "not be reliable."
    )
    assert _classify_hedge(text) == "hedged"


def test_classify_hedge_strong_confidence() -> None:
    text = (
        "Evidence directly supports this. The claim has been definitively "
        "demonstrated by clearly established trials, and the result is "
        "unambiguous."
    )
    assert _classify_hedge(text) == "confident"


def test_classify_hedge_neutral() -> None:
    text = "The model retrieved one paper and concluded the verdict."
    assert _classify_hedge(text) == "neutral"


def test_classify_hedge_empty() -> None:
    assert _classify_hedge("") == "neutral"


def test_classify_hedge_one_hedge_one_confident() -> None:
    """Borderline case: needs ≥2 dominant hits to break neutral."""
    text = "may be clearly true"  # one hedge, one confident
    assert _classify_hedge(text) == "neutral"


# ─── _normalize_url_for_match ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.nature.com/articles/abc/", "nature.com/articles/abc"),
        ("http://NATURE.com/abc?q=1", "nature.com/abc"),
        ("https://nature.com/abc#section", "nature.com/abc"),
        ("https://nature.com/abc#section?bad=1", "nature.com/abc"),
        ("", ""),
    ],
)
def test_normalize_url_for_match(url: str, expected: str) -> None:
    assert _normalize_url_for_match(url) == expected


# ─── joint_success_per_sample ────────────────────────────────────────────────


def test_joint_success_all_pass() -> None:
    assert joint_success_per_sample(
        verdict_match=1.0, groundedness_value=1.0, currency_value=1.0
    ) is True


def test_joint_success_grounded_partial_passes() -> None:
    """Groundedness 0.5 (partial) is enough for joint success — only 0 fails."""
    assert joint_success_per_sample(
        verdict_match=1.0, groundedness_value=0.5, currency_value=1.0
    ) is True


def test_joint_success_grounded_zero_fails() -> None:
    assert joint_success_per_sample(
        verdict_match=1.0, groundedness_value=0.0, currency_value=1.0
    ) is False


def test_joint_success_verdict_miss_fails() -> None:
    assert joint_success_per_sample(
        verdict_match=0.0, groundedness_value=1.0, currency_value=1.0
    ) is False


def test_joint_success_currency_unaware_fails() -> None:
    assert joint_success_per_sample(
        verdict_match=1.0, groundedness_value=1.0, currency_value=0.0
    ) is False


def test_joint_success_currency_not_applicable_passes() -> None:
    """If no DOIs were checkable, currency is not_applicable and doesn't block."""
    assert joint_success_per_sample(
        verdict_match=1.0,
        groundedness_value=1.0,
        currency_value=1.0,
        currency_label="not_applicable",
    ) is True


def test_joint_success_currency_none_passes() -> None:
    """If currency wasn't measured at all, it doesn't block."""
    assert joint_success_per_sample(
        verdict_match=1.0, groundedness_value=1.0, currency_value=None
    ) is True


def test_joint_success_partial_currency_passes() -> None:
    """Currency 0.5 (partial) is enough for joint — only 0.0 unaware fails."""
    assert joint_success_per_sample(
        verdict_match=1.0, groundedness_value=1.0, currency_value=0.5
    ) is True


def test_joint_success_case_004_failure_mode() -> None:
    """The Phase 1 case 004 failure: verdict wrong, grounded partial, currency unaware.

    The whole point of Phase 2 — this case should fail joint success regardless
    of which scorer triggered first. Documents the canonical failure path.
    """
    assert joint_success_per_sample(
        verdict_match=0.0,  # gold contradicted, predicted supported
        groundedness_value=0.5,  # judge said partial
        currency_value=0.0,  # Crossref flagged retraction, model unaware
    ) is False
