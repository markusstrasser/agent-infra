"""Parse-state derivation + an empty-parse health flag over the corpus.

- **C0 — parse-state**: is a source parsed, and against which parser? Derivable as
  ONE call (`parse_health_report`), so parse-count claims stop being ungrounded.
  (The roadmap's "130/157 parsed; 52 unparsed" was unreproducible — 157-130≠52 —
  precisely because no single derivation existed; this is it.)

- **Health**: one deterministic, high-signal flag — ``empty_or_tiny`` (the active
  ``page.md`` is below a sane floor = a failed or near-empty parse).

ADVISORY by construction: this never changes an audit's exit code. It reports
counts; the operator acts on the backlog.

Parse access goes through ``PaperRecord.parsed_markdown_path()`` (the sole entry
point) — never a hand-built path.

History: a ``no_sections`` heading-structure check was dropped 2026-06-01. The
flat-dump failure mode it guarded (a paper parse with no ``##`` headings →
section-aware extractor sees an empty body → silent false ``not_supported``) is
solved for all FUTURE ingests — DEFAULT_PARSER for papers/preprints is
marker-modal, which emits headings. The only residual was 26 legacy
trafilatura-parsed papers, all currently healthy and cheaply re-ingestable via
marker-modal if one ever goes flat — not worth the heading-regex + code-fence
machinery. Restore from git (commit 08ff904) if non-marker paper parses become a
live problem again.
"""

from __future__ import annotations

from typing import Any

from . import store
from .store import CorpusStore

# Source-id prefixes that denote a scientific *paper* (vs non-paper corpus
# entries: db_/tool_/repo_/guideline_/…). Used as the parse-coverage denominator.
# Case-insensitive (corpus ids are slugified lowercase, but guard an upstream
# that records e.g. `DOI_…`). Includes the preprint servers search_preprints
# ingests (bioRxiv/medRxiv/arXiv).
_PAPER_PREFIXES = (
    "doi_", "pmid_", "pmcid_", "pmc_", "sha_", "pubmed",
    "arxiv_", "biorxiv_", "medrxiv_",
)

# A real paper parse is far larger than this; below it the parse is empty/failed.
EMPTY_BODY_THRESHOLD = 500  # characters (stripped)


def is_paper_shaped(source_id: str) -> bool:
    """True if the source_id denotes a scientific paper (the parse-coverage
    denominator). Case-insensitive."""
    return source_id.lower().startswith(_PAPER_PREFIXES)


def parse_state(record: store.PaperRecord) -> dict[str, Any]:
    """Parse-state + health for ONE source.

    Returns ``{source_id, parsed: bool, parser: str|None, chars: int,
    flags: list[str]}``. ``flags`` is ``["empty_or_tiny"]`` for a parsed source
    whose ``page.md`` is below the floor, else empty. An unparsed source has
    ``parsed=False`` and no flags (being unparsed is a state, not a defect).
    """
    md_path = record.parsed_markdown_path()
    if md_path is None:
        return {
            "source_id": record.paper_id,
            "parsed": False,
            "parser": None,
            "chars": 0,
            "flags": [],
        }
    active = record.parsed_dir_active()
    parser = active.name.removeprefix("parsed.") if active is not None else None
    text = md_path.read_text(errors="replace")
    flags = ["empty_or_tiny"] if len(text.strip()) < EMPTY_BODY_THRESHOLD else []
    return {
        "source_id": record.paper_id,
        "parsed": True,
        "parser": parser,
        "chars": len(text),  # code points, not bytes — a size proxy only
        "flags": flags,
    }


def parse_health_report(corpus_store: CorpusStore) -> dict[str, Any]:
    """Aggregate parse-state + health across every source in the corpus.

    Single-call derivation (C0) plus the health rollup. Paper-shaped sources are
    the denominator for parse-coverage; non-paper entries are counted for
    parser-mix but excluded from ``papers_unparsed``.
    """
    rows = [parse_state(corpus_store.get(pid)) for pid in corpus_store.iter_papers()]
    papers = [r for r in rows if is_paper_shaped(r["source_id"])]
    papers_unparsed = [r for r in papers if not r["parsed"]]

    by_parser: dict[str, int] = {}
    for r in rows:
        if r["parsed"] and r["parser"]:
            by_parser[r["parser"]] = by_parser.get(r["parser"], 0) + 1

    unhealthy = [r for r in rows if r["flags"]]
    return {
        "sources_total": len(rows),
        "papers_total": len(papers),
        "papers_parsed": len(papers) - len(papers_unparsed),
        "papers_unparsed": len(papers_unparsed),
        "parsed_by_parser": dict(sorted(by_parser.items())),
        "unhealthy": sorted(unhealthy, key=lambda r: r["source_id"]),
        "unhealthy_count": len(unhealthy),
    }
