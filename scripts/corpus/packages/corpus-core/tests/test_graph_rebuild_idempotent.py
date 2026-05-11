"""Rebuilding the graph twice produces the same edge set."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from papers import ingest, paper_store as ps
from papers.maintain import cmd_rebuild_graph


class _Args:
    pass


def test_graph_rebuild_idempotent(papers_root, tiny_pdf):
    meta_a = ingest.ingest_pdf(tiny_pdf, doi="10.test/a", skip_parse=True)
    pid_a = meta_a["paper_id"]
    # Make a second paper via SHA path
    pdf_b = papers_root.parent / "b.pdf"
    pdf_b.write_bytes(tiny_pdf.read_bytes() + b"\n%diff\n")
    meta_b = ingest.ingest_pdf(pdf_b, doi="10.test/b", skip_parse=True)
    pid_b = meta_b["paper_id"]

    # Manually drop a citance: B cites A
    citance = {
        "citance_id": "abc123",
        "citing_paper_id": pid_b,
        "cited_paper_id": pid_a,
        "stance_class": "supporting",
        "stance_cito": "http://purl.org/spar/cito/supports",
        "stance_confidence": 0.9,
        "stance_source": "scite",
        "snippet": "B supports A.",
        "citing_section": "Discussion",
        "citing_page": 3,
        "providers": ["scite"],
        "fetched_at": "2026-05-11T10:00:00Z",
    }
    (papers_root / pid_b / "citances_out.jsonl").write_text(json.dumps(citance) + "\n")
    (papers_root / pid_a / "citances_in.jsonl").write_text(json.dumps(citance) + "\n")

    args = _Args()
    cmd_rebuild_graph(args)
    con = duckdb.connect(str(ps.graph_db_path()), read_only=True)
    rows1 = con.execute("SELECT * FROM edges ORDER BY citing_paper_id, cited_paper_id, citance_id").fetchall()
    n1_papers = con.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    con.close()

    cmd_rebuild_graph(args)
    con = duckdb.connect(str(ps.graph_db_path()), read_only=True)
    rows2 = con.execute("SELECT * FROM edges ORDER BY citing_paper_id, cited_paper_id, citance_id").fetchall()
    n2_papers = con.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    con.close()

    assert rows1 == rows2
    assert n1_papers == n2_papers == 2
    # Edge dedupe: appears in both citances_in (A) and citances_out (B) but same citance_id
    assert len(rows1) == 1
