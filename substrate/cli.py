"""Knowledge substrate CLI.

Usage:
    uv run python3 -m substrate stats [--db PATH]
    uv run python3 -m substrate stale [--db PATH]
    uv run python3 -m substrate changes [--db PATH] [--limit N]
    uv run python3 -m substrate get ID [--db PATH]
    uv run python3 -m substrate dependents ID [--db PATH]
    uv run python3 -m substrate mark-stale ID [--reason R] [--db PATH]
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


if __name__ == "__main__":
    main()
