#!/usr/bin/env python3
"""Generate and validate cross-project skill manifests.

The manifest is the single object model for skill entrypoints, planned modules,
lenses, role-agent contracts, aliases, symlinks, and export boundaries. It is
read-only by default; pass ``--write`` to persist `skill_manifest.jsonl` in each
selected repo.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from common.skill_objects import (
    DEFAULT_ROOTS,
    SkillObject,
    collect_skill_objects,
    iter_default_roots,
    load_object_content,
    load_manifest,
    resolve_object_path,
    resolve_portable_path,
    write_manifest,
)


REQUIRED_FIELDS = {
    "object_id",
    "object_type",
    "project",
    "package",
    "name",
    "path",
    "repo_root",
    "primary_category",
}

OBJECT_TYPES = {
    "SkillEntrypoint",
    "ModuleDoc",
    "LensDoc",
    "ReferenceDoc",
    "ArtifactBuilder",
    "HookContract",
    "RoleAgentContract",
}

CATEGORIES = {
    "workflow",
    "module",
    "lens",
    "reference",
    "artifact",
    "alias",
    "role-agent",
}


def _case_sensitive_path_exists(path: Path) -> bool:
    if not path.exists():
        return False
    current = Path(path.anchor) if path.is_absolute() else Path(".")
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for part in parts:
        if part in ("", "."):
            continue
        try:
            names = {child.name for child in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current = current / part
    return True


def _validate_readable_symlink_target(target: Path) -> str | None:
    try:
        resolved = target.resolve(strict=True)
    except OSError as exc:
        return f"symlink target does not resolve strictly: {exc}"
    if resolved.is_dir():
        skill_file = next((resolved / name for name in ("SKILL.md", "skill.md") if (resolved / name).is_file()), None)
        if skill_file is None:
            return "symlink target directory has no SKILL.md or skill.md"
        try:
            skill_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "symlink target skill file is not UTF-8 readable"
        return None
    if resolved.is_file():
        try:
            resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "symlink target file is not UTF-8 readable"
        return None
    return "symlink target is neither file nor directory"


def _shared_shadow_exists(object_id: str) -> bool:
    prefix = "skills:skill."
    if not object_id.startswith(prefix):
        return False
    skill_name = object_id.removeprefix(prefix)
    shared_skill_dir = DEFAULT_ROOTS["skills"].root / skill_name
    return (shared_skill_dir / "SKILL.md").exists() or (shared_skill_dir / "skill.md").exists()


def _validate_row(row: dict[str, Any], *, strict: bool = False, object_ids: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(row))
    if missing:
        errors.append(f"missing required fields: {missing}")
    if row.get("object_type") not in OBJECT_TYPES:
        errors.append(f"invalid object_type: {row.get('object_type')}")
    if row.get("primary_category") not in CATEGORIES:
        errors.append(f"invalid primary_category: {row.get('primary_category')}")
    if row.get("exportable") and row.get("private"):
        errors.append("exportable object cannot be private")
    if row.get("is_symlink") and not row.get("symlink_target"):
        errors.append("symlink row missing symlink_target")
    if row.get("status") not in (None, "active", "planned", "deprecated"):
        errors.append(f"invalid status: {row.get('status')}")
    if row.get("replaced_by") and not row.get("boundary"):
        errors.append("alias/replaced row missing boundary")
    if row.get("replaced_by") and not row.get("sunset_after"):
        errors.append("alias/replaced row missing sunset_after")
    if row.get("primary_category") == "alias" and not row.get("boundary"):
        errors.append("alias row missing boundary")
    if row.get("side_effectful") and not row.get("boundary"):
        errors.append("side-effectful row missing invocation boundary")
    if row.get("side_effectful") and not (row.get("user_invocable") or row.get("disable_model_invocation")):
        errors.append("side-effectful row missing explicit invocation policy")
    if strict:
        repo_root_text = row.get("repo_root")
        path_text = row.get("path")
        if repo_root_text:
            repo_root = resolve_portable_path(repo_root_text)
            if not repo_root.exists():
                errors.append(f"repo_root does not resolve: {repo_root_text}")
            elif path_text and row.get("status", "active") == "active":
                target = resolve_object_path(row)
                if not _case_sensitive_path_exists(target):
                    errors.append(f"active path does not exist: {path_text}")
                elif target.is_file():
                    try:
                        target.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        errors.append(f"active path is not UTF-8 readable: {path_text}")
        if row.get("replaced_by") and object_ids and row["replaced_by"] not in object_ids:
            errors.append(f"replaced_by target not found: {row['replaced_by']}")
        if row.get("shadows"):
            for shadow in row["shadows"]:
                if object_ids and shadow not in object_ids and not _shared_shadow_exists(shadow):
                    errors.append(f"shadow target not found: {shadow}")
        symlink_target = row.get("symlink_target")
        if symlink_target:
            target = resolve_portable_path(symlink_target)
            if not target.exists():
                errors.append(f"symlink target does not resolve: {symlink_target}")
            else:
                symlink_error = _validate_readable_symlink_target(target)
                if symlink_error:
                    errors.append(symlink_error)
        if row.get("status", "active") == "active":
            content = load_object_content(row, max_chars=1)
            if not content.get("available"):
                reason = content.get("error") or "content unavailable"
                errors.append(f"active content not loadable: {reason}")
    return errors


def validate_rows(rows: list[dict[str, Any]], *, strict: bool = False) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    object_ids = {row.get("object_id", "") for row in rows}
    for row in rows:
        object_id = row.get("object_id", "<missing>")
        row_errors = _validate_row(row, strict=strict, object_ids=object_ids)
        if object_id in seen:
            row_errors.append("duplicate object_id")
        seen.add(object_id)
        if row_errors:
            errors.append({"object_id": object_id, "errors": row_errors})
    return {"rows": len(rows), "errors": errors}


def _objects_to_rows(objects: list[SkillObject]) -> list[dict[str, Any]]:
    return [obj.to_json() for obj in objects]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate/validate skill manifests")
    parser.add_argument(
        "--repo",
        action="append",
        choices=["skills", "agent-infra", "genomics", "phenome", "intel"],
        help="Repo to include. Repeatable. Default: all known repos.",
    )
    parser.add_argument("--no-planned", action="store_true", help="Only discovered skill dirs")
    parser.add_argument("--write", action="store_true", help="Write skill_manifest.jsonl per repo")
    parser.add_argument("--output", type=Path, help="Write combined JSONL here")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of JSONL")
    parser.add_argument("--validate", type=Path, help="Validate an existing JSONL manifest")
    parser.add_argument("--strict", action="store_true", help="Validate semantic path/reference correctness")
    args = parser.parse_args()

    if args.validate:
        rows = load_manifest(args.validate)
        result = validate_rows(rows, strict=args.strict)
        print(json.dumps(result, indent=2))
        return 1 if result["errors"] else 0

    roots = iter_default_roots(args.repo)
    objects = collect_skill_objects(roots, include_planned=not args.no_planned)
    rows = _objects_to_rows(objects)
    result = validate_rows(rows, strict=args.strict)
    if result["errors"]:
        print(json.dumps(result, indent=2), file=sys.stderr)
        return 1

    if args.write:
        by_project: dict[str, list[SkillObject]] = {}
        for obj in objects:
            by_project.setdefault(obj.project, []).append(obj)
        for root in roots:
            write_manifest(root.repo_root / "skill_manifest.jsonl", by_project.get(root.project, []))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
            encoding="utf-8",
        )

    if args.json:
        print(json.dumps({"rows": rows, "summary": {"total": len(rows)}}, indent=2))
    elif not args.output:
        for row in rows:
            print(json.dumps(row, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
