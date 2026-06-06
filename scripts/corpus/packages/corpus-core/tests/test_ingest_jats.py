"""JATS full-text ingest preserves paper identity and writes a parsed bundle."""
from __future__ import annotations

from corpus_core import ingest
from corpus_core.extract import ExtractResult


def test_ingest_jats_uses_doi_identity(corpus_root, corpus_store, tmp_path, monkeypatch):
    jats = tmp_path / "paper.xml"
    jats.write_text(
        "<article><front><article-meta><title-group>"
        "<article-title>Example JATS Paper</article-title>"
        "</title-group></article-meta></front><body><p>"
        "This is enough source text to stand in for a real JATS paper in the "
        "unit test without invoking pandoc."
        "</p></body></article>",
        encoding="utf-8",
    )

    def fake_extract(path, *, parser_config):
        return ExtractResult(
            parser_id="jats-pandoc@test+cfg-d41d8cd9",
            parsed_markdown="# Example JATS Paper\n\nThis parsed markdown came from JATS.\n",
            parser_config_md5="d41d8cd98f00b204e9800998ecf8427e",
            char_count=58,
            extras={"jats_path": str(path)},
        )

    monkeypatch.setattr(ingest, "_extract_jats_with_pandoc", fake_extract)

    meta = ingest.ingest_jats(
        corpus_store,
        jats,
        doi="10.test/jats",
        pmid="12345",
        source_url="https://example.test/jats.xml",
    )

    assert meta["paper_id"] == "doi_10_test_jats"
    assert meta["doi"] == "10.test/jats"
    assert meta["pmid"] == "12345"
    assert meta["pdf_sha256"] is None
    source_dir = corpus_root / "doi_10_test_jats"
    assert (source_dir / "source.jats.xml").exists()
    assert (source_dir / "parsed.jats-pandoc@test+cfg-d41d8cd9" / "page.md").exists()
    assert meta["parsed_sha256"]


def test_ingest_jats_is_idempotent(corpus_store, tmp_path, monkeypatch):
    jats = tmp_path / "paper.xml"
    jats.write_text("<article><body><p>" + ("x" * 120) + "</p></body></article>")

    calls = 0

    def fake_extract(path, *, parser_config):
        nonlocal calls
        calls += 1
        return ExtractResult(
            parser_id="jats-pandoc@test+cfg-d41d8cd9",
            parsed_markdown="# Parsed\n\n" + ("x" * 120) + "\n",
            parser_config_md5="d41d8cd98f00b204e9800998ecf8427e",
            char_count=130,
        )

    monkeypatch.setattr(ingest, "_extract_jats_with_pandoc", fake_extract)

    meta1 = ingest.ingest_jats(corpus_store, jats, doi="10.test/jats-idem")
    meta2 = ingest.ingest_jats(corpus_store, jats, doi="10.test/jats-idem")

    assert meta2["content_hash"] == meta1["content_hash"]
    assert calls == 1
