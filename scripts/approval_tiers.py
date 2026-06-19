#!/usr/bin/env python3
"""Approval-tier manifest — Eve needsApproval analog for pretool hooks.

Loads config/approval-tiers.json and validates:
  - every listed hook file exists under skills/hooks or ~/.claude/hooks
  - global PreToolUse pretool-* commands are covered by the manifest

Used by doctor.py and scripts/tests/test_approval_tiers.py.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from common.paths import CLAUDE_DIR

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "config" / "approval-tiers.json"
SKILLS_HOOKS = Path.home() / "Projects" / "skills" / "hooks"
LOCAL_HOOKS = CLAUDE_DIR / "hooks"
GLOBAL_SETTINGS = CLAUDE_DIR / "settings.json"

# Inject tier + optional per-project — not required in global coverage check.
_SKIP_COVERAGE = {"inject"}


@dataclass
class TierCheck:
    ok: bool
    missing_files: list[str]
    uncovered_global: list[str]
    orphan_manifest: list[str]


def load_manifest(path: Path = MANIFEST) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def manifest_hooks(data: dict | None = None) -> dict[str, str]:
    """hook_basename -> tier action (block|predicate|warn|inject)."""
    data = data or load_manifest()
    out: dict[str, str] = {}
    for tier in data.get("tiers", []):
        action = tier.get("action", "warn")
        for hook in tier.get("hooks", []):
            out[hook] = action
    return out


def hook_search_paths() -> list[Path]:
    return [SKILLS_HOOKS, LOCAL_HOOKS]


def resolve_hook_file(name: str) -> Path | None:
    for root in hook_search_paths():
        p = root / name
        if p.is_file():
            return p
    return None


def global_pretool_hooks() -> list[str]:
    if not GLOBAL_SETTINGS.is_file():
        return []
    data = json.loads(GLOBAL_SETTINGS.read_text())
    names: list[str] = []
    for matcher_entry in data.get("hooks", {}).get("PreToolUse", []):
        if not isinstance(matcher_entry, dict):
            continue
        for entry in matcher_entry.get("hooks", []):
            if not isinstance(entry, dict):
                continue
            cmd = entry.get("command", "")
            m = re.search(r"(pretool-[\w.-]+)", cmd)
            if m:
                names.append(m.group(1))
    return sorted(set(names))


def validate_manifest(path: Path = MANIFEST) -> TierCheck:
    data = load_manifest(path)
    listed = manifest_hooks(data)
    missing: list[str] = []
    for name in listed:
        if resolve_hook_file(name) is None:
            missing.append(name)

    global_hooks = global_pretool_hooks()
    covered = set(listed)
    inject_hooks = {
        h for tier in data.get("tiers", [])
        if tier.get("action") in _SKIP_COVERAGE
        for h in tier.get("hooks", [])
    }
    uncovered = [
        h for h in global_hooks
        if h not in covered and h not in inject_hooks
    ]

    # Manifest entries that aren't global pretools and missing on disk
    orphan = [h for h in missing]

    return TierCheck(
        ok=not missing and not uncovered,
        missing_files=missing,
        uncovered_global=uncovered,
        orphan_manifest=orphan,
    )


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Validate approval-tier manifest")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    chk = validate_manifest()
    payload = {
        "ok": chk.ok,
        "missing_files": chk.missing_files,
        "uncovered_global": chk.uncovered_global,
        "manifest_hooks": len(manifest_hooks()),
        "global_pretools": len(global_pretool_hooks()),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        if chk.ok:
            print(f"OK: {payload['manifest_hooks']} hooks, {payload['global_pretools']} global pretools covered")
        else:
            if chk.missing_files:
                print("MISSING:", ", ".join(chk.missing_files))
            if chk.uncovered_global:
                print("UNCOVERED:", ", ".join(chk.uncovered_global))
    return 0 if chk.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
