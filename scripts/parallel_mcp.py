"""Parallel Task API — MCP server for deep web research.

Tools:
  parallel_task     — execute a research task (any processor tier)
  parallel_search   — lightweight web search via lite processor

Reads PARALLEL_API_KEY from environment.
"""

import logging
import os
import time

from fastmcp import FastMCP

log = logging.getLogger(__name__)

mcp = FastMCP(
    "parallel",
    instructions=(
        "Deep web research via Parallel Task API. Use parallel_task for complex "
        "multi-step research questions requiring cross-referencing multiple sources. "
        "Use parallel_search for quick factual lookups. "
        "Processor tiers: lite ($0.005/q) for simple lookups, core ($0.05/q) for "
        "standard research, ultra ($0.30/q) through ultra8x ($2.40/q) for hard "
        "multi-step research. Default to 'core' unless the query clearly needs "
        "deeper research or is trivially simple."
    ),
)


def _get_client():
    import parallel

    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        raise ValueError("PARALLEL_API_KEY not set")
    return parallel.Client(api_key=api_key)


def _format_result(data: dict, elapsed: float, processor: str) -> str:
    """Format Parallel result into readable text with citations."""
    output = data.get("output", {})
    content = output.get("content", {})

    # Extract answer text
    if isinstance(content, dict):
        text = content.get("output", "") or content.get("text", "")
    else:
        text = str(content) if content else ""
    if not text:
        text = output.get("text", "(no text output)")

    lines = [text, ""]

    # Citations
    basis = output.get("basis", [])
    for b in basis:
        confidence = b.get("confidence", "")
        if confidence:
            lines.append(f"Confidence: {confidence}")
        reasoning = b.get("reasoning", "")
        if reasoning:
            lines.append(f"Reasoning: {reasoning[:500]}")
        for c in b.get("citations", []):
            title = c.get("title", "")
            url = c.get("url", "")
            excerpts = c.get("excerpts", [])
            lines.append(f"  • {title}")
            lines.append(f"    {url}")
            for e in excerpts[:2]:
                lines.append(f"    > {e[:200]}")

    # Metadata
    run_info = data.get("run", {})
    interaction_id = run_info.get("interaction_id", "")
    lines.append(f"\n[Parallel {processor} | {elapsed:.1f}s | {interaction_id}]")

    return "\n".join(lines)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
    },
)
def parallel_task(
    query: str,
    processor: str = "core",
) -> str:
    """Execute a deep web research task via Parallel Task API.

    Use for complex multi-step research questions that require cross-referencing
    multiple web sources, resolving causal chains, or synthesizing across domains.

    Processor tiers (higher = more compute, better on hard questions):
      lite ($0.005/q) — simple factual lookups
      core ($0.05/q) — standard web research (default)
      core2x ($0.10/q) — extended standard research
      ultra ($0.30/q) — deep multi-step research
      ultra2x ($0.60/q) — harder research with more paths explored
      ultra4x ($1.20/q) — very hard research
      ultra8x ($2.40/q) — maximum depth, 82% on DeepSearchQA

    Args:
        query: The research question in natural language.
        processor: Processor tier. Default 'core'.
    """
    valid = {"lite", "core", "core2x", "ultra", "ultra2x", "ultra4x", "ultra8x"}
    if processor not in valid:
        return f"Invalid processor '{processor}'. Valid: {', '.join(sorted(valid))}"

    client = _get_client()
    t0 = time.time()
    result = client.task_run.execute(input=query, processor=processor)
    elapsed = time.time() - t0

    data = result.model_dump()
    return _format_result(data, elapsed, processor)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
    },
)
def parallel_search(query: str) -> str:
    """Quick web search via Parallel lite processor.

    Use for simple factual lookups where you need web-grounded answers with
    citations. Costs $0.005/query. For complex research, use parallel_task
    with a higher processor tier instead.

    Args:
        query: A simple factual question.
    """
    client = _get_client()
    t0 = time.time()
    result = client.task_run.execute(input=query, processor="lite")
    elapsed = time.time() - t0

    data = result.model_dump()
    return _format_result(data, elapsed, "lite")


def main():
    mcp.run()


if __name__ == "__main__":
    main()
