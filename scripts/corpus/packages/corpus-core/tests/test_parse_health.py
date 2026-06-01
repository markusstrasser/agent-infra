"""Parse-state (C0) + parse-health (C2) seed tests.

Constructs an isolated corpus with one source in each state and asserts the
report classifies every case — including the two that matter most: the
flat-dump paper (`no_sections`, the silent-false-not_supported class) and the
empty parse (`empty_or_tiny`). Non-paper sources must NOT be flagged
`no_sections`, and an unparsed source is a state, not a health defect.
"""
from __future__ import annotations

import json
from pathlib import Path

from corpus_core import parse_health, store

# A real, healthy parse: ATX headings + a non-trivial body.
HEALTHY = (
    "# Title\n\n## Introduction\n\n"
    + ("Lorem ipsum dolor sit amet. " * 80)
    + "\n\n## Methods\n\nMore text follows."
)
# A flat dump: long body, NO headings — the section parser sees an empty body.
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
    _write_source(root, "db_gnomad", parser="manual", page_md=FLAT_DUMP)  # non-paper

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
    assert states["doi_flatdump"]["flags"] == ["no_sections"]
    assert states["doi_tiny"]["flags"] == ["empty_or_tiny"]
    assert states["doi_unparsed"]["parsed"] is False
    assert states["doi_unparsed"]["flags"] == []
    # non-paper source with no headings is healthy (no_sections does NOT apply)
    assert states["db_gnomad"]["flags"] == []

    # C2 — unhealthy = parsed-but-broken; the unparsed source is NOT "unhealthy"
    assert report["unhealthy_count"] == 2
    assert {r["source_id"] for r in report["unhealthy"]} == {"doi_flatdump", "doi_tiny"}


def test_is_paper_shaped():
    assert parse_health.is_paper_shaped("doi_10_1038_ng_456")
    assert parse_health.is_paper_shaped("pmid_12345")
    assert parse_health.is_paper_shaped("sha_abc")
    assert not parse_health.is_paper_shaped("db_gnomad_r4")
    assert not parse_health.is_paper_shaped("tool_hirisplex_s")
    assert not parse_health.is_paper_shaped("repo_gene_panel")
