#!/usr/bin/env python3
"""Validate skill reference closure across hooks, rules, docs, and prompts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common.project_registry import SKILL_REPOS
from common.skill_objects import collect_skill_objects, iter_default_roots


SCAN_DIRS = [
    ".claude/rules",
    ".claude/agents",
    ".claude/prompts",
    ".claude/skills",
    "docs/workflows",
    "scripts/hooks",
]
SCAN_FILES = [
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".codex/hooks.json",
    ".codex/config.toml",
    ".mcp.json",
]
PATH_RE = re.compile(r"(?:~/Projects/[A-Za-z0-9_./-]+|/Users/[A-Za-z0-9_-]+/Projects/[A-Za-z0-9_./-]+)")


def _scan_dirs_for(project: str) -> list[str]:
    if project == "skills":
        return ["."]
    return SCAN_DIRS


def _expand(path_text: str) -> Path:
    return Path(path_text.replace("~", str(Path.home()), 1))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill path/reference closure")
    parser.add_argument("--repo", action="append", choices=list(SKILL_REPOS))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict-paths", action="store_true", help="Fail on all missing absolute/~/Projects paths")
    args = parser.parse_args()

    roots = iter_default_roots(args.repo)
    rows = [obj.to_json() for obj in collect_skill_objects(roots)]
    known_ids = {row["object_id"] for row in rows}
    known_names = {row["name"] for row in rows}
    findings: list[dict] = []
    warnings: list[dict] = []

    for root in roots:
        for row in rows:
            if row.get("project") != root.project:
                continue
            if row.get("status", "active") == "active":
                target = Path(row["repo_root"].replace("${PROJECTS_ROOT}", str(Path.home() / "Projects"))) / row["path"]
                if not target.exists():
                    findings.append({
                        "type": "manifest_path_missing",
                        "repo": root.project,
                        "file": f"{root.repo_root}/skill_manifest.jsonl",
                        "reference": row["path"],
                    })
        scan_paths: list[Path] = []
        for scan in _scan_dirs_for(root.project):
            directory = root.repo_root / scan
            if not directory.exists():
                continue
            scan_paths.extend(path for path in directory.rglob("*") if path.is_file() and not path.is_symlink())
        scan_paths.extend(root.repo_root / scan for scan in SCAN_FILES)
        for path in scan_paths:
            if not path.is_file() or path.is_symlink():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for match in PATH_RE.findall(text):
                expanded = _expand(match)
                if not expanded.exists():
                    warnings.append({
                        "type": "missing_path",
                        "repo": root.project,
                        "file": str(path),
                        "reference": match,
                    })
            for skill_ref in re.findall(r"`([A-Za-z0-9_.:-]+)`", text):
                if skill_ref.startswith(root.project + ":") and skill_ref not in known_ids:
                    findings.append({
                        "type": "unknown_manifest_id",
                        "repo": root.project,
                        "file": str(path),
                        "reference": skill_ref,
                    })
                elif skill_ref.endswith((".md", ".py", ".sh")):
                    continue
                elif "-" in skill_ref and skill_ref not in known_names and skill_ref.split(":")[-1] not in known_names:
                    # Advisory only: many markdown code spans are not skills.
                    pass

    if args.strict_paths:
        findings.extend(warnings)

    result = {
        "checked_repos": [r.project for r in roots],
        "findings": findings,
        "warnings": warnings if not args.strict_paths else [],
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if not findings:
            print("Reference closure OK.")
        for finding in findings:
            print(f"{finding['type']}: {finding['file']} -> {finding['reference']}")
        if warnings:
            print(f"{len(warnings)} advisory missing path warning(s); pass --strict-paths to fail on them.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
