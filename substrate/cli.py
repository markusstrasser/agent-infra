"""Knowledge substrate CLI.

Usage:
    uv run python3 -m substrate stats [--db PATH]
    uv run python3 -m substrate stale [--db PATH]
    uv run python3 -m substrate changes [--db PATH] [--limit N]
    uv run python3 -m substrate get ID [--db PATH]
    uv run python3 -m substrate dependents ID [--db PATH]
    uv run python3 -m substrate mark-stale ID [--reason R] [--db PATH]
    uv run python3 -m substrate reflect QUERY [--db PATH] [--model M] [--dry-run] [--raw]
    uv run python3 -m substrate provenance ID [--db PATH] [--max-depth N]
    uv run python3 -m substrate impact ID [--db PATH] [--max-depth N]
    uv run python3 -m substrate shared-evidence ID [--db PATH]
    uv run python3 -m substrate contradictions ID [--db PATH]
    uv run python3 -m substrate orphans [--db PATH]
    uv run python3 -m substrate search QUERY [--db PATH] [--max-results N]
"""

import argparse
import json
import sys
from pathlib import Path

from .core import KnowledgeDB

DEFAULT_DB = Path.home() / ".claude" / "knowledge" / "meta.db"


def main():
    parser = argparse.ArgumentParser(description="Knowledge substrate CLI")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help=f"Database path (default: {DEFAULT_DB})")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("stats", help="Show summary statistics")
    sub.add_parser("stale", help="List stale objects")

    changes_p = sub.add_parser("changes", help="Recent changelog")
    changes_p.add_argument("--limit", type=int, default=20)

    get_p = sub.add_parser("get", help="Get object by ID")
    get_p.add_argument("id")

    deps_p = sub.add_parser("dependents", help="Find dependents of an object")
    deps_p.add_argument("id")

    stale_p = sub.add_parser("mark-stale", help="Mark object and downstream as stale")
    stale_p.add_argument("id")
    stale_p.add_argument("--reason", default=None)

    reflect_p = sub.add_parser("reflect", help="LLM synthesis over recalled knowledge")
    reflect_p.add_argument("query")
    reflect_p.add_argument("--model", default="claude-haiku-4-5-20251001")
    reflect_p.add_argument("--max-results", type=int, default=20)
    reflect_p.add_argument("--raw", action="store_true",
                           help="Dump full recalled objects")
    reflect_p.add_argument("--dry-run", action="store_true",
                           help="Show recalled objects without LLM call")

    search_p = sub.add_parser("search", help="Search objects by query")
    search_p.add_argument("query")
    search_p.add_argument("--max-results", type=int, default=20)

    prov_p = sub.add_parser("provenance", help="Downstream provenance chain")
    prov_p.add_argument("id")
    prov_p.add_argument("--max-depth", type=int, default=10)

    impact_p = sub.add_parser("impact", help="Upstream impact radius")
    impact_p.add_argument("id")
    impact_p.add_argument("--max-depth", type=int, default=5)

    shared_p = sub.add_parser("shared-evidence", help="Assertions sharing evidence")
    shared_p.add_argument("id")

    contra_p = sub.add_parser("contradictions", help="Contradictory assertions")
    contra_p.add_argument("id")

    sub.add_parser("orphans", help="Find objects with zero relations")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    with KnowledgeDB(args.db) as db:
        if args.command == "stats":
            s = db.stats()
            for k, v in s.items():
                print(f"  {k}: {v}")

        elif args.command == "stale":
            items = db.stale_objects()
            if not items:
                print("  No stale objects.")
            for item in items:
                print(f"  [{item['type']}] {item['id']} — {item.get('title', '(no title)')}")

        elif args.command == "changes":
            for entry in db.recent_changes(args.limit):
                ts = entry["timestamp"][:16]
                print(f"  {ts}  {entry['action']:20s}  {entry['object_type']:10s}  {entry['object_id']}")
                if entry.get("reason"):
                    print(f"             reason: {entry['reason']}")

        elif args.command == "get":
            obj = db.get(args.id)
            if obj:
                print(json.dumps(obj, indent=2))
            else:
                print(f"  Not found: {args.id}")
                sys.exit(1)

        elif args.command == "dependents":
            deps = db.dependents(args.id)
            if not deps:
                print(f"  No dependents of {args.id}")
            for d in deps:
                print(f"  [{d['type']}] {d['id']} via {d['via']} ({d.get('relation', d.get('derivation_id', ''))})")

        elif args.command == "mark-stale":
            staled = db.mark_stale(args.id, reason=args.reason)
            print(f"  Marked {len(staled)} object(s) stale:")
            for s in staled:
                print(f"    {s}")

        elif args.command == "search":
            results = db.search_objects(args.query, max_results=args.max_results)
            if not results:
                print(f"  No results for: {args.query}")
            for obj in results:
                score = obj.get("_score", 0)
                print(f"  [{obj['_type']}] {obj['id']} (score={score}) — {obj.get('title') or '(no title)'}")

        elif args.command == "reflect":
            results = db.search_objects(args.query, max_results=args.max_results)
            if not results:
                print(f"  No results for: {args.query}")
                sys.exit(0)

            if args.raw:
                print(json.dumps(results, indent=2))
                sys.exit(0)

            if args.dry_run:
                print(f"  Recalled {len(results)} object(s):")
                for obj in results:
                    print(f"    [{obj['_type']}] {obj['id']} (score={obj.get('_score', 0)}) — {obj.get('title') or '(no title)'}")
                sys.exit(0)

            result = db.reflect(args.query, max_results=args.max_results,
                                model=args.model)
            print(result.text)
            print(f"\n--- Reflect metadata ---")
            print(f"  Model: {result.model}")
            print(f"  Recalled: {len(result.recalled_ids)} objects")
            print(f"  Cited: {result.cited_ids}")
            if result.hallucinated_ids:
                print(f"  Hallucinated IDs: {result.hallucinated_ids}")
            print(f"  Tokens: {result.input_tokens} in / {result.output_tokens} out")

        elif args.command == "provenance":
            chain = db.provenance_chain(args.id, max_depth=args.max_depth)
            if not chain:
                print(f"  No downstream provenance for {args.id}")
            else:
                print(f"  Provenance chain from {args.id} ({len(chain)} objects):")
                for item in chain:
                    indent = "  " * (item["depth"] + 1)
                    print(f"{indent}[{item['type']}] {item['id']} via {item['relation']}")

        elif args.command == "impact":
            chain = db.impact_radius(args.id, max_depth=args.max_depth)
            if not chain:
                print(f"  No upstream impact for {args.id}")
            else:
                print(f"  Impact radius of {args.id} ({len(chain)} objects):")
                for item in chain:
                    indent = "  " * (item["depth"] + 1)
                    print(f"{indent}[{item['type']}] {item['id']} via {item['relation']}")

        elif args.command == "shared-evidence":
            shared = db.shared_evidence(args.id)
            if not shared:
                print(f"  No shared evidence for {args.id}")
            else:
                print(f"  Assertions sharing evidence with {args.id}:")
                for item in shared:
                    print(f"    [{item['type']}] {item['id']} — shared: {item['shared_evidence_id']} ({item['relation']})")

        elif args.command == "contradictions":
            contras = db.contradictory_assertions(args.id)
            if not contras:
                print(f"  No contradictions for {args.id}")
            else:
                print(f"  Contradictions involving {args.id}:")
                for item in contras:
                    print(f"    [{item['type']}] {item['id']} ({item['direction']})")

        elif args.command == "orphans":
            orphans = db.orphans()
            if not orphans:
                print("  No orphan objects.")
            else:
                print(f"  {len(orphans)} orphan(s):")
                for item in orphans:
                    print(f"    [{item['_type']}] {item['id']} ({item['type']}, {item['status']}) — {item.get('title') or '(no title)'}")


if __name__ == "__main__":
    main()
