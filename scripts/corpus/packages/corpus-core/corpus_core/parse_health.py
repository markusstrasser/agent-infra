"""Parse-state + parse-health derivation over the corpus.

Two roadmap items, one module (both enumerate the active parse of every source):

- **C0 — parse-state**: is a source parsed, and against which parser? Derivable as
  ONE call (`parse_health_report`), so parse-count claims stop being ungrounded.
  (The roadmap's "130/157 parsed; 52 unparsed" was unreproducible — 157-130≠52 —
  precisely because no single derivation existed; this is it.)

- **C2 — parse-health**: flag an active parse that will silently break downstream
  claim extraction. Two deterministic, high-signal checks:
    * ``empty_or_tiny`` — the active ``page.md`` is below a sane floor (a failed or
      near-empty parse).
    * ``no_sections`` — a *paper-shaped* source whose parse has no markdown section
      headings. This is the flat-dump class: the section-aware claim extractor sees
      an empty body and emits a silent false ``not_supported``. marker-modal (the
      default parser since agent-infra@09dbba6) produces ``##`` headings; a flagged
      paper is a re-ingest candidate.

ADVISORY by construction: this never changes an audit's exit code. A large
pre-marker-modal backlog of flat-dump parses must NOT re-red the audit (that is
exactly the desensitization E1 just removed). It reports counts; the operator
acts on the re-ingest backlog.

Parse access goes through ``PaperRecord.parsed_markdown_path()`` (the sole entry
point) — never a hand-built path.

Known limitations (close-review 2026-06-01, deferred as out-of-scope for an
advisory check): heading detection is markdown-ATX only (not Setext/HTML — every
current parser emits ATX); ``no_sections`` strips *fenced* code blocks but not
indented ones; it does not detect scraper gatekeeping/paywall pages that happen
to carry headings (a content-authenticity concern, distinct from structural
health). See the review disposition for rationale.
"""

from __future__ import annotations

import re
from typing import Any

from . import store

# ATX markdown heading at line start, tolerating up to 3 leading spaces
# (CommonMark allows 0-3). Stricter indentation than that is a code block.
_HEADING_RE = re.compile(r"^[ ]{0,3}#{1,6}\s+\S", re.MULTILINE)

# Source-id prefixes that denote a scientific *paper* (where section headings are
# expected). Non-paper corpus entries (db_/tool_/repo_/guideline_/…) legitimately
# lack headings, so ``no_sections`` does not apply to them. Includes the preprint
# servers that research-mcp's search_preprints ingests (bioRxiv/medRxiv/arXiv).
_PAPER_PREFIXES = (
    "doi_", "pmid_", "pmcid_", "pmc_", "sha_", "pubmed",
    "arxiv_", "biorxiv_", "medrxiv_",
)

# A real paper parse is far larger than this; below it the parse is empty/failed.
EMPTY_BODY_THRESHOLD = 500  # characters (stripped)


def is_paper_shaped(source_id: str) -> bool:
    """True if the source_id denotes a scientific paper (heading-expected).

    Case-insensitive: corpus ids are slugified lowercase, but guard against an
    upstream that records e.g. ``DOI_…`` so it is not silently skipped.
    """
    return source_id.lower().startswith(_PAPER_PREFIXES)


def _strip_code_fences(text: str) -> str:
    """Drop fenced code blocks (``` or ~~~) so a ``# comment`` inside code is not
    mistaken for a markdown heading (close-review convergent finding). Line-based
    and language-tag tolerant. Does NOT strip indented code blocks (rare in parser
    output; documented limitation)."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def _health_flags(text: str, source_id: str) -> list[str]:
    """Health flags for an active parse's markdown. Empty list == healthy."""
    flags: list[str] = []
    if len(text.strip()) < EMPTY_BODY_THRESHOLD:
        flags.append("empty_or_tiny")
    elif is_paper_shaped(source_id) and not _HEADING_RE.search(_strip_code_fences(text)):
        # Only meaningful once the body is non-trivial (the elif): a tiny parse is
        # already the dominant, actionable flag (re-parse) and need not also carry
        # no_sections. A flat-dump paper with real text but no headings (outside
        # code fences) is the silent-false-not_supported case.
        flags.append("no_sections")
    return flags


def parse_state(record: store.PaperRecord) -> dict[str, Any]:
    """Parse-state + health for ONE source.

    Returns: ``{source_id, parsed: bool, parser: str|None, chars: int,
    flags: list[str]}``. ``flags`` are HEALTH problems on a *parsed* source
    (empty_or_tiny / no_sections); an unparsed source has ``parsed=False`` and
    no flags (being unparsed is a state, not a health defect).
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
    return {
        "source_id": record.paper_id,
        "parsed": True,
        "parser": parser,
        "chars": len(text),  # code points, not bytes — used as a size proxy only
        "flags": _health_flags(text, record.paper_id),
    }


def parse_health_report() -> dict[str, Any]:
    """Aggregate parse-state + health across every source in the corpus.

    Single-call derivation (C0) plus the health rollup (C2). Paper-shaped
    sources are the denominator for parse-coverage; non-paper entries are
    counted for parser-mix but excluded from ``papers_unparsed``.
    """
    rows = [parse_state(store.get(pid)) for pid in store.iter_papers()]
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
