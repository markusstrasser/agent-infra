"""Extractor dispatch for the corpus.

Each extractor returns an ExtractResult with `parser_id`, `parsed_markdown`,
and config-determined metadata. Outputs land in immutable
`parsed.<parser_id>/` directories per the SCHEMA.md immutability rule —
re-parses with different parser/config never mutate an existing dir.

Tool picks (per research/prior-art-2026-05-11/01-pdf-html-extractors.md):

| source_type        | default parser    | license       |
|--------------------|-------------------|---------------|
| paper, preprint    | marker-modal      | GPL-3.0 †     |
| database_release   | pymupdf4llm       | AGPL-3.0 *    |
| regulatory_filing  | pymupdf4llm       | AGPL-3.0 *    |
| tool_output        | pymupdf4llm       | AGPL-3.0 *    |
| webpage / blog /   | trafilatura       | Apache-2.0    |
|   news             |                   |               |
| other              | pymupdf4llm       | AGPL-3.0 *    |

* AGPL is OK for local-only personal use (per SCHEMA.md license invariant).
  Must NOT be deployed behind a public network endpoint.
† marker is GPL-3.0 and runs on your own Modal account (T4 GPU). Default
  for papers/preprints per ~/.claude/rules/marker-modal-default.md (local
  marker is MPS-broken on this Mac; mineru lacks LLM table/equation/figure
  fidelity). Needs network — pass `--parser mineru` for offline / local ingest.

Opt-in parsers (NOT in DEFAULT_PARSER; pass via `--parser <name>`):
  - `marker`             GPL-3.0; LLM-enhanced + figure crops. Mac MPS bugs
                         (#993/#967/#960). Chunked-by-default workaround.
                         Install: `uv tool install marker-pdf`.
  - `gemini-flash-lite`  Cloud LLM fallback for PDFs the local parsers fail.
  - `liteparse`          Apache-2.0; Rust, model-free. Flat text only (no
                         structure) — fast text-layer extraction + office docs,
                         and a cheap scan-vs-digital preflight (extras
                         .has_text_layer). NOT a markdown parser for papers.
                         Install: `pip install liteparse`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class ExtractResult:
    parser_id: str
    parsed_markdown: str
    parser_config_md5: str
    page_count: Optional[int] = None
    char_count: Optional[int] = None
    extras: Optional[dict[str, Any]] = None


DEFAULT_PARSER: dict[str, str] = {
    "paper":             "marker-modal",
    "preprint":          "marker-modal",
    "database_release":  "pymupdf4llm",
    "regulatory_filing": "pymupdf4llm",
    "tool_output":       "pymupdf4llm",
    "webpage":           "trafilatura",
    "blog_post":         "trafilatura",
    "news":              "trafilatura",
    "other":             "pymupdf4llm",
}


def _registry() -> dict[str, Callable[..., ExtractResult]]:
    """Lazy import — keeps optional deps optional."""
    from . import (
        html_trafilatura,
        pdf_lightweight,
        pdf_liteparse,
        pdf_llm,
        pdf_marker,
        pdf_marker_modal,
        pdf_mineru,
    )
    return {
        "mineru":            pdf_mineru.extract,
        "pymupdf4llm":       pdf_lightweight.extract,
        "trafilatura":       html_trafilatura.extract_from_bytes,
        "marker":            pdf_marker.extract,         # opt-in; GPL-3.0, local CPU
        "marker-modal":      pdf_marker_modal.extract,   # DEFAULT (paper/preprint); GPL-3.0, T4 GPU on Modal
        "liteparse":         pdf_liteparse.extract,      # opt-in; Apache-2.0, Rust, flat text
        "gemini-flash-lite": pdf_llm.extract,
    }


def extract(
    *,
    content: Any,
    source_type: str,
    parser: Optional[str] = None,
    parser_config: Optional[dict] = None,
) -> ExtractResult:
    """Dispatch to the appropriate extractor.

    Args:
        content: bytes (HTML), Path (PDF), or str URL — type depends on parser.
        source_type: see DEFAULT_PARSER keys.
        parser: optional override. Must be a key of EXTRACTORS.
        parser_config: tool-specific config dict (frozen + md5'd into parser_id).
    """
    chosen = parser or DEFAULT_PARSER.get(source_type, "pymupdf4llm")
    extractors = _registry()
    if chosen not in extractors:
        raise ValueError(
            f"unknown parser {chosen!r}; available: {sorted(extractors)}"
        )
    return extractors[chosen](content, parser_config=parser_config)


__all__ = ["DEFAULT_PARSER", "ExtractResult", "extract"]
