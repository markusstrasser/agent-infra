#!/usr/bin/env python3
"""Allowlisted public export for shared skills.

Default is dry-run. The exporter refuses rows marked private and rejects known
private path tokens in exported content.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common.skill_objects import collect_skill_objects, iter_default_roots, resolve_object_path


BLOCKED_TOKENS = ("/Users/alien", "Markus", "phenome", "genomics", "intel")
BLOCKED_PROJECT_PATH_PATTERNS = (
    "../intel",
    "../phenome",
    "../genomics",
    "~/Projects/intel",
    "~/Projects/phenome",
    "~/Projects/genomics",
    "$HOME/Projects/intel",
    "$HOME/Projects/phenome",
    "$HOME/Projects/genomics",
)


def _contains_blocked_token(path: Path) -> str | None:
    if path.is_symlink():
        return f"{path}: symlink exports are not allowed"
    for file in path.rglob("*"):
        if file.is_symlink():
            return f"{file}: symlink exports are not allowed"
        if not file.is_file():
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token in BLOCKED_TOKENS:
            if token in text:
                return f"{file}: {token}"
        for pattern in BLOCKED_PROJECT_PATH_PATTERNS:
            if pattern in text:
                return f"{file}: {pattern}"
    return None


def _export_block_reason(row: dict) -> str | None:
    if row.get("private"):
        return "row is private"
    if not row.get("exportable"):
        return "row is not marked exportable"
    if row.get("is_symlink"):
        return "symlink skill rows are not exportable"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Export allowlisted public shared skills")
    parser.add_argument("--allow", action="append", required=True, help="Skill name to export. Repeatable.")
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="Actually copy files")
    args = parser.parse_args()

    rows = [obj.to_json() for obj in collect_skill_objects(iter_default_roots(["skills"]), include_planned=False)]
    by_name = {row["name"]: row for row in rows if row.get("object_type") == "SkillEntrypoint"}
    errors: list[str] = []
    planned: list[tuple[Path, Path]] = []

    for name in args.allow:
        row = by_name.get(name)
        if not row:
            errors.append(f"unknown skill: {name}")
            continue
        block_reason = _export_block_reason(row)
        if block_reason:
            errors.append(f"not exportable: {name} ({block_reason})")
            continue
        source_file = resolve_object_path(row)
        source_dir = source_file.parent if source_file.is_file() else source_file
        blocked = _contains_blocked_token(source_dir)
        if blocked:
            errors.append(f"blocked token in {name}: {blocked}")
            continue
        planned.append((source_dir, args.dest / name))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    for source, dest in planned:
        print(f"{source} -> {dest}")
        if args.execute:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest, symlinks=False)
    if not args.execute:
        print("dry-run only; pass --execute to copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
