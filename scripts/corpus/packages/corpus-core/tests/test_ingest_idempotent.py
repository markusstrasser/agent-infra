"""Ingest is a no-op on re-run with same PDF + parser."""
from __future__ import annotations

import json

from papers import ingest, paper_store as ps


def test_ingest_idempotent(papers_root, tiny_pdf):
    meta1 = ingest.ingest_pdf(tiny_pdf, doi="10.test/idem", skip_parse=True)
    assert meta1["pdf_sha256"]
    pid = meta1["paper_id"]
    assert pid == "doi_10_test_idem"
    assert (papers_root / pid / "paper.pdf").exists()

    # Re-run same PDF, same args — should not error and should keep same hash
    meta2 = ingest.ingest_pdf(tiny_pdf, doi="10.test/idem", skip_parse=True)
    assert meta2["pdf_sha256"] == meta1["pdf_sha256"]


def test_ingest_different_pdf_same_doi_refuses(papers_root, tiny_pdf, tiny_pdf_v2):
    """A different PDF under the same DOI must fail without --revise."""
    ingest.ingest_pdf(tiny_pdf, doi="10.test/refuse", skip_parse=True)
    import pytest
    with pytest.raises(ps.PaperStoreError):
        ingest.ingest_pdf(tiny_pdf_v2, doi="10.test/refuse", skip_parse=True)
