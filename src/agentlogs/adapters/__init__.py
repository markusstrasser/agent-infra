"""Vendor-specific parsers for session transcripts.

Each adapter module exports:
  - PARSER_NAME, PARSER_VERSION
  - parser_identity() -> (name, version)
  - discover_sources(root: Path | None) -> list[DiscoveredSource]
  - parse_source(source: DiscoveredSource) -> ParsedSource
"""

from __future__ import annotations

from . import claude, codex, gemini

ADAPTERS = {
    "claude": claude,
    "codex": codex,
    "gemini": gemini,
}

__all__ = ["ADAPTERS", "claude", "codex", "gemini"]
