"""Retrieval @tool wrappers for claim-verification benchmark.

Phase 1 ships one tool only: `exa_search()`. Phase 2+ may add scite,
Semantic Scholar, Perplexity, Brave. Keeping this module narrow on
purpose — the point of Phase 1 is to validate the adapter pattern works
end-to-end, not to expose every possible search engine.

Implementation notes:
- Uses `exa_py.AsyncExa` directly (not MCP) — MCPs are for interactive
  tool use, not programmatic adapter code.
- Budget counter enforces a hard call cap per Python process to keep
  dev runs cheap. Phase 0 worst-case math: 4 cases × 5 queries × ~$0.005
  per call = ~$0.10 per full run.
- Returns compact JSON strings so the model sees structured results
  without blowing its context. Trim content aggressively — default is
  1500 chars per result, 5 results per call.
"""

from __future__ import annotations

import json
import os
from typing import Any

from inspect_ai.tool import Tool, ToolError, tool

# Hard budget per process. Phase 1 dev runs should never exceed this.
MAX_EXA_CALLS_PER_PROCESS = 50

_exa_call_count = 0


def _check_budget() -> None:
    global _exa_call_count
    if _exa_call_count >= MAX_EXA_CALLS_PER_PROCESS:
        raise ToolError(
            f"exa_search budget exhausted ({MAX_EXA_CALLS_PER_PROCESS} calls). "
            "Raise MAX_EXA_CALLS_PER_PROCESS in tools.py if intentional."
        )
    _exa_call_count += 1


def exa_call_count() -> int:
    """Inspect the Exa call count for the current process (for scorers/tests)."""
    return _exa_call_count


def _format_result(result: Any, max_chars: int) -> dict[str, Any]:
    """Normalize one Exa result into a compact dict.

    Exa's result objects expose attributes via dataclass; we pull the
    fields the model actually needs for adjudication.
    """
    text = getattr(result, "text", "") or ""
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return {
        "title": getattr(result, "title", None),
        "url": getattr(result, "url", None),
        "published_date": getattr(result, "published_date", None),
        "author": getattr(result, "author", None),
        "text": text,
    }


@tool
def exa_search() -> Tool:
    """Exa web search adapter.

    Returns top-k results as a JSON string. Supports optional date
    filtering for post-cutoff queries — critical for claims whose
    gold evidence was published after the model's training cutoff.
    """

    async def execute(
        query: str,
        num_results: int = 5,
        start_published_date: str | None = None,
        end_published_date: str | None = None,
    ) -> str:
        """Search the web via Exa neural search and return top results.

        Args:
            query: Search query. Use specific terms — Exa is neural, not keyword.
            num_results: Number of results to return. 3-5 is typical for claim
                verification; higher burns context without helping.
            start_published_date: Optional ISO date (YYYY-MM-DD). Restricts
                results to sources published on or after this date. Use this
                when you need to find recent evidence, e.g. for claims about
                2025-2026 events.
            end_published_date: Optional ISO date (YYYY-MM-DD). Upper bound.

        Returns:
            JSON string with a list of results. Each result has title, url,
            published_date, author, and a text excerpt (up to 1500 chars).
        """
        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            raise ToolError(
                "EXA_API_KEY not set in environment — cannot call Exa search."
            )

        _check_budget()

        # Import lazily so module import doesn't require exa_py at parse time.
        from exa_py import AsyncExa

        client = AsyncExa(api_key=api_key)

        try:
            response = await client.search_and_contents(
                query,
                num_results=num_results,
                start_published_date=start_published_date,
                end_published_date=end_published_date,
                text={"max_characters": 1500},
            )
        except Exception as exc:
            raise ToolError(f"Exa search failed: {type(exc).__name__}: {exc}") from exc

        results = [
            _format_result(r, max_chars=1500) for r in (response.results or [])
        ]
        return json.dumps(
            {"query": query, "count": len(results), "results": results},
            ensure_ascii=False,
        )

    return execute
