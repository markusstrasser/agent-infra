#!/usr/bin/env python3
"""Four-surface governance dedup — grep before minting rules/skills/findings.

Surfaces: CLAUDE.md, AGENTS.md, .claude/rules/, decisions/, improvement-log,
skills/**/SKILL.md (+ canonical ~/Projects/skills).

Usage:
    uv run python3 scripts/dedup_surfaces.py check --text "candidate rule text"
    uv run python3 scripts/dedup_surfaces.py check --file proposal.md --project .
    uv run python3 scripts/dedup_surfaces.py files --project ~/Projects/intel
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import con
from common.surface_gates import governance_files, search_governance


def main() -> int:
    ap = argparse.ArgumentParser(description="Governance surface dedup")
    sub = ap.add_subparsers(dest="cmd", required=True)

    chk = sub.add_parser("check", help="search for overlapping governance")
    chk.add_argument("--text", help="candidate text to dedup-check")
    chk.add_argument("--file", type=Path, help="read candidate from file")
    chk.add_argument("--project", type=Path, default=Path.cwd())
    chk.add_argument("--json", action="store_true")

    lst = sub.add_parser("files", help="list governance files in scope")
    lst.add_argument("--project", type=Path, default=Path.cwd())
    lst.add_argument("--json", action="store_true")

    args = ap.parse_args()
    project = args.project.expanduser().resolve()

    if args.cmd == "files":
        files = governance_files(project)
        if args.json:
            print(json.dumps([str(p) for p in files], indent=2))
        else:
            con.header(f"Governance files ({project.name})")
            for p in files:
                print(f"  {p}")
            con.kv("count", str(len(files)))
        return 0

    text = args.text or ""
    if args.file:
        text = args.file.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        con.fail("provide --text or --file")
        return 2

    hits = search_governance(text, project)
    if args.json:
        print(json.dumps({"hits": hits, "duplicate_risk": bool(hits)}, indent=2))
        return 1 if hits else 0

    con.header("Dedup check")
    if not hits:
        con.ok("no overlap in governance surfaces")
        return 0
    con.warn(f"{len(hits)} potential overlap(s) — sharpen existing, do not mint")
    for h in hits:
        loc = h["path"]
        if h.get("line"):
            loc += f":{h['line']}"
        print(f"  {loc} [{h['match']}]")
        if h.get("text"):
            print(f"    {h['text'][:120]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
