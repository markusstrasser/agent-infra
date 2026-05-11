"""`papers` console script entry point.

Subcommands:
    papers ingest --pdf <path> [--doi ... | --pmid ...]
    papers ingest --revise --pdf <new> --paper-id <id>
    papers resolve-references --paper-id <id> [--online]
    papers extract-citances --paper-id <id> [--enrich-cito]
    papers sync --from <manifest.json> [--dry-run]
    papers stats
    papers show <paper_id> [--depth full]
    papers maintain --verify | --rebuild-indexes | --rebuild-citances | --rebuild-graph | --gc
    papers cites|cited-by|contradictions|ego|path|similar|cluster|collection|table  ...
"""
from __future__ import annotations

import argparse
import sys

from . import ingest as _ingest
from . import resolve_references as _refs
from . import extract_citances as _cites
from . import sync as _sync
from . import maintain as _maintain
from . import graph_cli as _graph


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="papers", description="Canonical papers store CLI")
    subs = parser.add_subparsers(dest="cmd", required=True)
    _ingest.add_cli(subs)
    _refs.add_cli(subs)
    _cites.add_cli(subs)
    _sync.add_cli(subs)
    _maintain.add_cli(subs)
    _graph.add_cli(subs)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
