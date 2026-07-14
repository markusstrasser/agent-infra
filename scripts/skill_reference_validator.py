#!/usr/bin/env python3
"""Validate skill reference closure across hooks, rules, docs, and prompts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
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

# --- Doc-reference closure: relative/bare file refs in routing docs ---
# The absolute-path arm above misses the rot that actually recurs: a LIVE routing
# doc (CLAUDE.md, cockpit.md, README) pointing at a deleted/moved file via a bare
# (`runlog.md`) or repo-relative (`docs/x/INDEX.md`) reference. Those are not
# absolute paths, so PATH_RE never sees them.
DOC_EXT = (".md", ".py", ".sh", ".json", ".jsonl", ".toml", ".yaml", ".yml", ".sql")
# Only the routing surface is checked for relative-ref closure — the docs an agent
# loads to decide what to read. SKILL.md / research memos / .context aggregates
# reference consumer-project or example paths by design and would flood the gate.
ROUTING_DOC_NAMES = frozenset({"CLAUDE.md", "AGENTS.md", "GEMINI.md", "README.md"})
# Refs whose first segment is a sibling repo/skill are cross-context, not this
# repo's closure (they resolve where the skill/repo is consumed). The meta→agent-infra
# rename husk is fully cleaned (refs repointed, old ~/Projects/meta deleted 2026-06-13),
# so meta/ no longer needs special flagging.
LIVE_SIBLINGS = frozenset({"agent-infra", "intel", "intel-harness", "genomics", "personal", "publishing", "research-mcp", "skills", "modal"})
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s#]+)")
_CODE_RE = re.compile(r"`([^`\n]+?)`")


def _git_tracked_names(root: Path) -> set[str]:
    """Basenames of all git-tracked files — for resolving bare references."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            capture_output=True, text=True, timeout=20, check=True,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return set()
    return {line.rsplit("/", 1)[-1] for line in out.splitlines() if line}


def _doc_refs(text: str) -> set[str]:
    """Path-shaped references: markdown link targets + backtick'd file paths."""
    body = _FENCE_RE.sub("", text)  # drop fenced code blocks (example paths)
    refs: set[str] = set()
    for target in _LINK_RE.findall(body):
        if not target.startswith(("http://", "https://", "mailto:", "#")):
            refs.add(target)
    for span in _CODE_RE.findall(body):
        span = span.strip()
        if span and "/" in span and span.endswith(DOC_EXT) and not any(c in span for c in " *$<>{}|[]"):
            refs.add(span)  # path-shaped only; bare `foo.md` is usually a prose mention
    return refs


def _is_routing_doc(path: Path) -> bool:
    """A doc agents load to route: top-level agent files + .claude/rules/*.md."""
    if path.name in ROUTING_DOC_NAMES:
        return True
    return path.suffix == ".md" and "rules" in path.parts and ".claude" in path.parts


def _dangling_doc_refs(text: str, path: Path, repo_root: Path, names: set[str]) -> list[str]:
    """Refs in `text` (located at `path`) resolving to no file on disk or in git."""
    out: list[str] = []
    for ref in _doc_refs(text):
        norm = ref[2:] if ref.startswith("./") else ref  # strip leading "./" only, not ".claude"
        if norm.startswith(("~", "/")):
            continue  # absolute — handled by the PATH_RE arm
        if norm.split("/", 1)[0] in LIVE_SIBLINGS:
            continue  # cross-repo / cross-skill reference
        if (repo_root / norm).exists() or (path.parent / norm).exists():
            continue  # resolves repo-root-relative or file-relative (incl. ../)
        if "/" not in norm and norm in names:
            continue  # bare basename exists somewhere in the repo
        out.append(ref)
    return out


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
    parser.add_argument("--strict-refs", action="store_true", help="Fail on dangling relative/bare doc refs in routing docs")
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
        if root.project != "skills":  # skills already scans "." (whole tree)
            scan_paths.extend(sorted(root.repo_root.glob("*.md")))  # root routing docs
        tracked_names = _git_tracked_names(root.repo_root)
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
            if root.project != "skills" and _is_routing_doc(path):
                for ref in _dangling_doc_refs(text, path, root.repo_root, tracked_names):
                    bucket = findings if args.strict_refs else warnings
                    bucket.append({
                        "type": "dangling_doc_ref",
                        "repo": root.project,
                        "file": str(path),
                        "reference": ref,
                    })

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
            dangling = sum(1 for w in warnings if w["type"] == "dangling_doc_ref")
            paths = len(warnings) - dangling
            parts = []
            if paths:
                parts.append(f"{paths} missing absolute path(s) [--strict-paths]")
            if dangling:
                parts.append(f"{dangling} dangling doc ref(s) [--strict-refs]")
            print("advisory: " + "; ".join(parts))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
