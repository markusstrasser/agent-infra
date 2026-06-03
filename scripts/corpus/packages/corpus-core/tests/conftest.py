"""Test fixtures — every test gets an explicit temp CorpusStore."""
from __future__ import annotations

from pathlib import Path

import pytest

from corpus_core.store import CorpusStore


@pytest.fixture
def corpus_root(tmp_path) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    return root


@pytest.fixture
def corpus_store(corpus_root: Path) -> CorpusStore:
    return CorpusStore(corpus_root)


@pytest.fixture
def tiny_pdf(tmp_path) -> Path:
    """A 1-page minimal valid PDF (~200 bytes)."""
    pdf = tmp_path / "tiny.pdf"
    pdf.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000053 00000 n \n0000000102 00000 n \n"
        b"trailer<< /Size 4 /Root 1 0 R >>\nstartxref\n164\n%%EOF\n"
    )
    return pdf


@pytest.fixture
def tiny_pdf_v2(tmp_path) -> Path:
    """A slightly different 1-page PDF for revision tests."""
    pdf = tmp_path / "tiny_v2.pdf"
    pdf.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>endobj\n"
        b"4 0 obj<< /Length 0 >>stream\nendstream endobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000053 00000 n \n0000000102 00000 n \n0000000200 00000 n \n"
        b"trailer<< /Size 5 /Root 1 0 R >>\nstartxref\n250\n%%EOF\n"
    )
    return pdf
