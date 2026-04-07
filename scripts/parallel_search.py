"""Parallel Task API — CLI wrapper for deep web research.

Usage:
    uv run python3 scripts/parallel_search.py "query" [--processor lite|core|ultra|ultra2x|ultra4x|ultra8x]
    uv run python3 scripts/parallel_search.py "query" --json  # structured output
"""

import argparse
import json
import time

import parallel


def run_task(query: str, processor: str = "lite", json_output: bool = False) -> dict:
    client = parallel.Client()  # reads PARALLEL_API_KEY from env

    t0 = time.time()
    result = client.task_run.execute(input=query, processor=processor)
    elapsed = time.time() - t0

    data = result.model_dump()
    output = data.get("output", {})
    run_info = data.get("run", {})

    if json_output:
        data["_elapsed_s"] = round(elapsed, 1)
        print(json.dumps(data, indent=2, default=str))
        return data

    # Extract answer — structure varies by output type
    content = output.get("content", {})
    if isinstance(content, dict):
        text = content.get("output", "") or content.get("text", "")
    else:
        text = str(content) if content else ""
    if not text:
        text = output.get("text", "")

    print(f"\n[Parallel {processor}] ({elapsed:.1f}s)")
    print(f"{'─' * 60}")
    print(text or "(no text output)")

    # Citations
    basis = output.get("basis", [])
    if basis:
        print(f"\n{'─' * 60}")
        print(f"Sources ({sum(len(b.get('citations', [])) for b in basis)}):")
        for b in basis:
            for c in b.get("citations", []):
                title = c.get("title", "")
                url = c.get("url", "")
                print(f"  • {title[:60]}")
                print(f"    {url}")

    # Run metadata
    if run_info:
        rid = run_info.get("id", "?")
        status = run_info.get("status", "?")
        print(f"\nRun: {rid} | Status: {status}")

    return data


def main():
    parser = argparse.ArgumentParser(description="Parallel Task API query")
    parser.add_argument("query", help="Research question")
    parser.add_argument(
        "--processor",
        "-p",
        default="lite",
        choices=["lite", "core", "core2x", "ultra", "ultra2x", "ultra4x", "ultra8x"],
        help="Processor tier (default: lite)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    run_task(args.query, args.processor, args.json)


if __name__ == "__main__":
    main()
