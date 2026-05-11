"""DOI > PMID > SHA precedence, slug normalization, collision detection."""
from __future__ import annotations

import json

import pytest

from corpus_core import store as ps


def test_doi_precedence(corpus_root):
    pid = ps.derive_paper_id(doi="10.1234/abc", pmid="999", pdf_sha="a" * 64)
    assert pid == "doi_10_1234_abc"


def test_pmid_when_no_doi(corpus_root):
    pid = ps.derive_paper_id(pmid="12345", pdf_sha="a" * 64)
    assert pid == "pmid_12345"


def test_sha_fallback(corpus_root):
    pid = ps.derive_paper_id(pdf_sha="deadbeef" * 8)
    assert pid == "sha_deadbeefdeadbeef"


def test_doi_slug_punctuation(corpus_root):
    pid = ps.derive_paper_id(doi="10.1097/FPC.0000000000000456")
    assert pid == "doi_10_1097_fpc_0000000000000456"


def test_doi_collision_raises(corpus_root):
    pid = "doi_10_1234_abc"
    p = corpus_root / pid
    p.mkdir()
    (p / "metadata.json").write_text(json.dumps({"doi": "10.1234/abc", "paper_id": pid}))

    with pytest.raises(ps.DOICollisionError):
        ps.derive_paper_id(doi="10.1234/ABC!")  # different DOI, same slug


def test_doi_match_no_collision(corpus_root):
    pid = "doi_10_1234_abc"
    p = corpus_root / pid
    p.mkdir()
    (p / "metadata.json").write_text(json.dumps({"doi": "10.1234/abc", "paper_id": pid}))
    # Same DOI re-derives cleanly
    assert ps.derive_paper_id(doi="10.1234/abc") == pid


def test_invalid_pmid(corpus_root):
    with pytest.raises(ps.PaperStoreError):
        ps.derive_paper_id(pmid="not-numeric")


def test_no_inputs(corpus_root):
    with pytest.raises(ps.PaperStoreError):
        ps.derive_paper_id()
