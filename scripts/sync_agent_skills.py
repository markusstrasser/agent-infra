#!/usr/bin/env python3
"""Sync agent skill mounts across vendors from ~/.claude/skills canonical set.

Mirrors Claude global skill symlinks into Codex discovery paths:
  ~/.agents/skills  (primary, open agent skills standard)
  ~/.codex/skills   (legacy user path, kept in sync)

Per-repo parity remains codex_parity_sync.py (.agents/skills -> .claude/skills).

Usage:
    uv run python3 scripts/sync_agent_skills.py
    uv run python3 scripts/sync_agent_skills.py --check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import con
from common.surface_gates import sync_skill_symlinks


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync global skill symlinks across vendors")
    ap.add_argument("--check", action="store_true", help="report drift only")
    args = ap.parse_args()

    home = Path.home()
    src = home / ".claude" / "skills"
    targets = [
        ("codex_agents", home / ".agents" / "skills"),
        ("codex_legacy", home / ".codex" / "skills"),
    ]

    con.header("Agent skills sync" + (" (check)" if args.check else ""))
    exit_code = 0
    for label, dst in targets:
        result = sync_skill_symlinks(src, dst, check=args.check)
        if result["errors"]:
            for err in result["errors"]:
                con.fail(f"{label}: {err}")
            exit_code = 1
            continue
        verb = "would" if args.check else ""
        con.kv(
            label,
            f"{verb} +{result['created']} ~{result['updated']} -{result['removed']} "
            f"from {src}",
        )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
