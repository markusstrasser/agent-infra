"""Parse-state (C0) + empty-parse health seed tests.

Constructs an isolated corpus with one source in each state and asserts the
report classifies them. Note (2026-06-01): the `no_sections` heading check was
dropped, so a long structureless paper is now HEALTHY — only `empty_or_tiny`
(a failed/near-empty parse) and unparsed remain.
"""
from __future__ import annotations

import json
from pathlib import Path

from corpus_core import parse_health, store

# A real, healthy parse (non-trivial body).
HEALTHY = "# Title\n\n## Introduction\n\n" + ("Lorem ipsum dolor sit amet. " * 80)
# A long body with no headings — healthy now that no_sections is gone.
FLAT_DUMP = "Lorem ipsum dolor sit amet consectetur adipiscing. " * 80
# A failed/near-empty parse.
TINY = "abstract only"


def _write_source(
    root: Path, source_id: str, *, parser: str | None = None, page_md: str | None = None
) -> None:
    d = root / source_id
    d.mkdir(parents=True)
    (d / "metadata.json").write_text(json.dumps({"paper_id": source_id}))
    if parser is not None and page_md is not None:
        pdir = d / f"parsed.{parser}"
        pdir.mkdir()
        (pdir / "page.md").write_text(page_md)


def test_parse_health_classifies_each_state(corpus_root):
    root = corpus_root
    _write_source(root, "doi_healthy", parser="marker-modal", page_md=HEALTHY)
    _write_source(root, "doi_flatdump", parser="pymupdf", page_md=FLAT_DUMP)
    _write_source(root, "doi_tiny", parser="pymupdf", page_md=TINY)
    _write_source(root, "doi_unparsed")  # metadata only, no parse
    _write_source(root, "db_gnomad", parser="manual", page_md=TINY)  # non-paper, tiny

    report = parse_health.parse_health_report()

    # C0 — parse-state coverage (paper-shaped denominator; db_ excluded)
    assert report["sources_total"] == 5
    assert report["papers_total"] == 4
    assert report["papers_unparsed"] == 1
    assert report["papers_parsed"] == 3
    assert report["parsed_by_parser"] == {"manual": 1, "marker-modal": 1, "pymupdf": 2}

    # per-source flags
    states = {r["source_id"]: r for r in (parse_health.parse_state(store.get(p)) for p in store.iter_papers())}
    assert states["doi_healthy"]["flags"] == []
    assert states["doi_healthy"]["parser"] == "marker-modal"
    assert states["doi_healthy"]["chars"] > 500  # size proxy is 'chars', not 'bytes'
    # a long structureless paper is HEALTHY (no_sections dropped 2026-06-01)
    assert states["doi_flatdump"]["flags"] == []
    assert states["doi_tiny"]["flags"] == ["empty_or_tiny"]
    assert states["doi_unparsed"]["parsed"] is False
    assert states["doi_unparsed"]["flags"] == []

    # empty_or_tiny applies to ANY parsed source, paper or not
    assert {r["source_id"] for r in report["unhealthy"]} == {"doi_tiny", "db_gnomad"}
    assert report["unhealthy_count"] == 2


def test_is_paper_shaped():
    assert parse_health.is_paper_shaped("doi_10_1038_ng_456")
    assert parse_health.is_paper_shaped("pmid_12345")
    assert parse_health.is_paper_shaped("sha_abc")
    assert parse_health.is_paper_shaped("biorxiv_2026_01_01_123456")
    assert parse_health.is_paper_shaped("medrxiv_abc")
    assert parse_health.is_paper_shaped("arxiv_2601_01234")
    assert parse_health.is_paper_shaped("DOI_10.1016/abc")  # case-insensitive
    assert not parse_health.is_paper_shaped("db_gnomad_r4")
    assert not parse_health.is_paper_shaped("tool_hirisplex_s")
    assert not parse_health.is_paper_shaped("repo_gene_panel")
