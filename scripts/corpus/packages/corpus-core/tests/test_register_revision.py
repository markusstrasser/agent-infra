"""Revision flow archives prior PDF + parsed/, updates metadata."""
from __future__ import annotations

import json

from corpus_core import ingest, store as ps


def test_register_revision_archives(corpus_root, tiny_pdf, tiny_pdf_v2):
    meta = ingest.ingest_pdf(tiny_pdf, doi="10.test/rev", skip_parse=True)
    pid = meta["paper_id"]
    paper_dir = corpus_root / pid

    # Fake a parsed/ to ensure it gets archived
    parsed = paper_dir / "parsed"
    parsed.mkdir()
    (parsed / "paper.md").write_text("# fake old parse\n")
    (parsed / "parsed.sha256").write_text("oldsha\n")
    ps.update_metadata(pid, parsed_sha256="oldsha",
                       parser={"parser_id": "marker-1.0+surya-0.4+llm-none+cfg-deadbeef",
                               "config_md5": "deadbeefdeadbeef"})

    prior_sha = meta["pdf_sha256"]
    res = ps.register_revision(pid, tiny_pdf_v2)
    assert res.prior_pdf_sha256 == prior_sha
    assert res.new_pdf_sha256 != prior_sha
    assert res.archived_pdf.exists()
    assert res.archived_parsed is not None and res.archived_parsed.exists()

    rec = ps.get(pid)
    assert rec.metadata["pdf_sha256"] == res.new_pdf_sha256
    assert len(rec.metadata["revisions"]) == 1
    assert rec.metadata["revisions"][0]["prior_pdf_sha256"] == prior_sha
    # parsed_sha256 cleared until reparse
    assert "parsed_sha256" not in rec.metadata
