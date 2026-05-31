"""Reference-section + entry extraction against marker's real markdown dialects."""
from corpus_core.resolve_references import (
    extract_inline_doi,
    extract_reference_section,
    extract_entries,
)


def test_header_plain():
    md = "# Intro\nbody text\n\n## References\n\n- 1. Foo B. A title long enough here. J 2020;1:2."
    assert extract_reference_section(md) is not None


def test_header_bold_emphasis():
    # marker renders `# **References**` (markdown emphasis inside the header)
    md = "body\n\n# **References**\n\n- 1. Smith J. A study of things. Nature 2021;1:2-3."
    sec = extract_reference_section(md)
    assert sec is not None and extract_entries(sec)


def test_header_span_tagged():
    md = '## <span id="page-6-0"></span>REFERENCES\n\n- 1. Moffat DA. A title here. J Otol 1977;91:279.'
    assert extract_entries(extract_reference_section(md) or "")


def test_bulleted_numbered_entries():
    sec = ("- 9. Buss DM. 1989 Sex differences in mate preferences. Behav Brain Sci 12, 1-14.\n"
           "- 10. Smith J. Another title long enough for the filter. Nature 2020;1:2.")
    e = extract_entries(sec)
    assert len(e) == 2 and e[0]["ref_label"] == "[9]"


def test_unnumbered_vancouver_entries():
    sec = ("- Zhang Z, Long J, Li W. Cerebral venous sinus thrombosis study. Chin Med J 2000;113:1043.\n"
           "- Arac A, Lee M. Efficacy of stenting in venous sinus stenosis. Neurosurg Focus 2009;27:E14.")
    e = extract_entries(sec)
    assert len(e) == 2 and e[0]["ref_label"] == "[1]"  # sequential when unnumbered


def test_doi_pulled_from_link_href():
    # marker hides the full DOI in the href; the visible text is truncated
    sec = "- 1. Buss DM. A title long enough here. ([doi:10.1017/](http://dx.doi.org/10.1017/S0140525X00023992))"
    e = extract_entries(sec)
    assert extract_inline_doi(e[0]["raw_text"]) == "10.1017/s0140525x00023992"


def test_no_blank_line_garbage():
    # acknowledgment/copyright text with stray digits must NOT become "references"
    sec = "We thank the 3 reviewers and grant 12345 for support.\n\nThe authors declare no conflict."
    assert extract_entries(sec) == []


def test_llm_fallback_gate():
    # gate keeps the gemini fallback off reference-less docs; fires on ref-dense ones
    from corpus_core.resolve_references import _has_strong_ref_signals
    assert _has_strong_ref_signals("ref 10.1234/abc def " * 12)      # >=10 inline DOIs
    assert _has_strong_ref_signals("Smith J et al. 2020. " * 25)     # >=20 "et al"
    assert not _has_strong_ref_signals("A short news item with no reference list at all.")


def test_section_header_ends_the_bullet_list():
    sec = ("- 1. Real reference entry long enough to count here. J 2020;1:2.\n"
           "## Appendix\n- not a reference, this is an appendix bullet item")
    e = extract_entries(sec)
    assert len(e) == 1
