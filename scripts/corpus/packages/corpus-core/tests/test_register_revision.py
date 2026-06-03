"""Revision flow archives prior PDF + active parse, updates metadata."""
from __future__ import annotations

import json

from corpus_core import ingest, store as ps


def test_register_revision_archives(corpus_root, corpus_store, tiny_pdf, tiny_pdf_v2):
    meta = ingest.ingest_pdf(corpus_store, tiny_pdf, doi="10.test/rev", skip_parse=True)
    pid = meta["paper_id"]
    paper_dir = corpus_root / pid

    # Fake an active parser-addressed parse to ensure it gets archived
    parser_id = "marker-1.0+surya-0.4+llm-none+cfg-deadbeef"
    parsed = paper_dir / f"parsed.{parser_id}"
    parsed.mkdir()
    (parsed / "page.md").write_text("# fake old parse\n")
    (parsed / "parsed.sha256").write_text("oldsha\n")
    corpus_store.update_metadata(pid, parsed_sha256="oldsha",
                       parser={"parser_id": parser_id,
                               "config_md5": "deadbeefdeadbeef"})

    prior_sha = meta["pdf_sha256"]
    res = corpus_store.register_revision(pid, tiny_pdf_v2)
    assert res.prior_pdf_sha256 == prior_sha
    assert res.new_pdf_sha256 != prior_sha
    assert res.archived_pdf.exists()
    assert res.archived_parsed is not None and res.archived_parsed.exists()

    rec = corpus_store.get(pid)
    assert rec.metadata["pdf_sha256"] == res.new_pdf_sha256
    assert len(rec.metadata["revisions"]) == 1
    assert rec.metadata["revisions"][0]["prior_pdf_sha256"] == prior_sha
    # parsed_sha256 cleared until reparse
    assert "parsed_sha256" not in rec.metadata
