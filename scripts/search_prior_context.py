#!/usr/bin/env python3
"""Search the active turn-level prior-context index and return source handles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_INDEX = Path.home() / ".cache" / "agent-infra" / "prior-context" / "index"


def source_rows(results: list[dict]) -> list[dict]:
    rows = []
    for rank, result in enumerate(results, start=1):
        metadata = result["metadata"]
        session_uuid = metadata["session_uuid"]
        rows.append(
            {
                "rank": rank,
                "similarity": result["similarity"],
                "session_uuid": session_uuid,
                "vendor_session_id": metadata.get("vendor_session_id"),
                "project": metadata.get("project"),
                "vendor": metadata.get("vendor"),
                "date": result.get("date"),
                "role": metadata.get("role"),
                "event_id": metadata.get("event_id"),
                "source_handle": f"agentlogs show {session_uuid}",
                "snippet": result["text"],
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="+", help="semantic prior-context query")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--project")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not (args.index / "current.json").is_file():
        parser.error(
            f"no active index at {args.index}; run scripts/prior-context-index build"
        )

    from emb.search import SearchEngine

    engine = SearchEngine(args.index)
    results = engine.search(
        " ".join(args.query),
        top_k=args.top_k,
        entry_filter=(
            (lambda entry: entry.metadata.get("project") == args.project)
            if args.project
            else None
        ),
        dedup_key=lambda result: result["entry"].metadata.get("session_uuid"),
    )
    rows = source_rows(results)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    for row in rows:
        print(
            f"{row['rank']}. {row['similarity']:.3f} {row['project']}/{row['vendor']} "
            f"{row['date'] or '-'} {row['source_handle']} event={row['event_id']}"
        )
        print(f"   {row['snippet']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
