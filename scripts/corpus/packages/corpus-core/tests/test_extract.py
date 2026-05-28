"""Extractor dispatch + per-tool smoke tests.

The MinerU and pdf_llm tests are kept minimal — they exercise the *dispatch
shape*, not the model output. End-to-end PDF parsing is validated manually
when source documents land.
"""
from __future__ import annotations

import pytest

from corpus_core.extract import DEFAULT_PARSER, extract


def test_default_parser_routing():
    assert DEFAULT_PARSER["paper"] == "mineru"
    assert DEFAULT_PARSER["preprint"] == "mineru"
    assert DEFAULT_PARSER["webpage"] == "trafilatura"
    assert DEFAULT_PARSER["regulatory_filing"] == "pymupdf4llm"
    assert DEFAULT_PARSER["other"] == "pymupdf4llm"


def test_extract_unknown_parser_rejected():
    with pytest.raises(ValueError, match="unknown parser"):
        extract(content=b"", source_type="webpage", parser="bogus")


def test_trafilatura_extracts_html_to_markdown():
    html = b"""<html><body>
        <h1>Title</h1>
        <p>First paragraph with <a href="https://x.test">a link</a>.</p>
        <h2>Section</h2>
        <p>Second paragraph.</p>
    </body></html>"""
    result = extract(content=html, source_type="webpage")
    assert result.parser_id.startswith("trafilatura@")
    assert result.char_count and result.char_count > 0
    md = result.parsed_markdown.lower()
    assert "first paragraph" in md
    assert "second paragraph" in md


def test_trafilatura_deterministic_for_fixed_input():
    html = b"<html><body><p>Hello world.</p></body></html>"
    a = extract(content=html, source_type="blog_post").parsed_markdown
    b = extract(content=html, source_type="blog_post").parsed_markdown
    assert a == b


def test_mineru_resolver_smoke():
    """Just verify the binary resolver finds the installed mineru CLI.

    Full extraction would require a real PDF + run mineru (slow) — out of
    unit-test scope. End-to-end smoke happens in `corpus ingest --pdf …`.
    """
    from corpus_core.extract import pdf_mineru
    bin_path = pdf_mineru._find_mineru_bin()
    assert bin_path
    assert "mineru" in bin_path


def test_pymupdf4llm_extracts_real_pdf(tmp_path):
    """Smoke: pymupdf4llm should extract a tiny PDF without crashing.

    Generates a 1-page PDF on the fly via pypdf so we don't depend on a
    fixture file."""
    pypdf = pytest.importorskip("pypdf")
    pdf_path = tmp_path / "tiny.pdf"
    # Build a minimal 1-page PDF
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    with open(pdf_path, "wb") as f:
        w.write(f)
    result = extract(content=pdf_path, source_type="other")  # → pymupdf4llm
    assert result.parser_id.startswith("pymupdf4llm@")
    # Empty page → empty markdown is fine; we're testing shape, not content
    assert result.char_count is not None


def test_liteparse_dispatch_shape(tmp_path):
    """Smoke: opt-in liteparse parser returns a well-formed ExtractResult.

    Skips when the optional `liteparse` extra isn't installed. A blank page has
    no text layer, so extras.has_text_layer must be False — the preflight signal
    we route scanned/image PDFs on."""
    pytest.importorskip("liteparse")
    pypdf = pytest.importorskip("pypdf")
    pdf_path = tmp_path / "tiny.pdf"
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    with open(pdf_path, "wb") as f:
        w.write(f)
    result = extract(content=pdf_path, source_type="other", parser="liteparse")
    assert result.parser_id.startswith("liteparse@")
    assert result.page_count == 1
    assert result.extras is not None
    assert result.extras["has_text_layer"] is False
