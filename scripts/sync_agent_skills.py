#!/usr/bin/env python3
"""Sync agent skill mounts across vendors from ~/.claude/skills canonical set.

Mirrors Claude global skill symlinks into Codex discovery:
  ~/.agents/skills  (open agent skills standard)

Do not mirror into ~/.codex/skills — that path is Codex's bundled/.system store
only; managed skills live under ~/.agents/skills (+ per-repo .agents/skills).

Per-repo parity remains codex_parity_sync.py (.agents/skills -> .claude/skills).

Honors `skillOverrides: off` from ~/.claude/settings.json: a skill the operator
switched off for Claude is not mirrored into Codex's ambient index either (Codex
has no per-skill disable, so the mirror is the only place parity can be kept).
2026-09-01: 16 off skills were mirrored, pushing the Codex index to 9,362 chars
against its 8,000 ceiling.

Usage:
    uv run python3 scripts/sync_agent_skills.py
    uv run python3 scripts/sync_agent_skills.py --check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import con
from common.surface_gates import claude_disabled_skills, sync_skill_symlinks


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync global skill symlinks across vendors")
    ap.add_argument("--check", action="store_true", help="report drift only")
    args = ap.parse_args()

    home = Path.home()
    src = home / ".claude" / "skills"
    off = claude_disabled_skills(home / ".claude" / "settings.json")
    targets = [
        ("codex_agents", home / ".agents" / "skills"),
    ]

    con.header("Agent skills sync" + (" (check)" if args.check else ""))
    exit_code = 0
    for label, dst in targets:
        result = sync_skill_symlinks(src, dst, check=args.check, exclude=off)
        if result["errors"]:
            for err in result["errors"]:
                con.fail(f"{label}: {err}")
            exit_code = 1
            continue
        verb = "would" if args.check else ""
        con.kv(
            label,
            f"{verb} +{result['created']} ~{result['updated']} -{result['removed']} "
            f"from {src}; {result['excluded']} skipped (skillOverrides=off)",
        )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
