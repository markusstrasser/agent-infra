#!/usr/bin/env python3
"""Skill Validator — static checks for ~/Projects/skills/*/SKILL.md.

Zero LLM cost. Catches drift, broken references, malformed frontmatter.

Usage:
    skill-validator.py                  # validate all skills
    skill-validator.py --changed-only   # validate only git-changed skills
    skill-validator.py --json           # JSON output
    skill-validator.py --skill NAME     # validate single skill
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

import yaml

from common.skill_objects import (
    DEFAULT_ROOTS,
    collect_skill_objects,
    iter_default_roots,
    stored_skill_filename,
)

SKILLS_DIR = Path.home() / "Projects" / "skills"
HOOKS_DIR = SKILLS_DIR / "hooks"

# Known Claude Code tool names (native + MCP prefix pattern)
NATIVE_TOOLS = {
    "Agent", "AskUserQuestion", "Bash", "Edit", "Glob", "Grep",
    "Read", "Write", "Skill", "Task", "TaskCreate", "TaskGet",
    "TaskList", "TaskUpdate", "TaskOutput", "TaskStop",
    "NotebookEdit", "WebFetch", "WebSearch",
    "EnterPlanMode", "ExitPlanMode",
    "EnterWorktree", "ExitWorktree",
    "SendMessage", "TeamCreate", "TeamDelete",
    "CronCreate", "CronDelete", "CronList",
}

# Known frontmatter fields
KNOWN_FIELDS = {
    "name", "description", "argument-hint", "allowed-tools",
    "user-invocable", "hooks", "model", "license", "context",
    "disable-model-invocation", "effort", "agent",
}

PRIVATE_EXPORT_PATTERNS = (
    "/Users/alien",
    "Markus",
    "phenome",
    "genomics",
    "intel",
)


def collect_mcp_servers() -> set[str]:
    """Gather all configured MCP server names from global + project configs."""
    servers: set[str] = set()

    # Global settings
    from common.paths import CLAUDE_DIR
    global_settings = CLAUDE_DIR / "settings.json"
    if global_settings.exists():
        try:
            data = json.loads(global_settings.read_text())
            servers.update(data.get("mcpServers", {}).keys())
        except (json.JSONDecodeError, KeyError):
            pass

    # User-scope .mcp.json
    user_mcp = CLAUDE_DIR / ".mcp.json"
    if user_mcp.exists():
        try:
            data = json.loads(user_mcp.read_text())
            servers.update(data.get("mcpServers", {}).keys())
        except (json.JSONDecodeError, KeyError):
            pass

    # Per-project .mcp.json files
    for mcp_file in Path.home().glob("Projects/*/.mcp.json"):
        try:
            data = json.loads(mcp_file.read_text())
            servers.update(data.get("mcpServers", {}).keys())
        except (json.JSONDecodeError, KeyError):
            pass

    return servers


def parse_frontmatter(path: Path) -> tuple[dict | None, str, list[str]]:
    """Parse YAML frontmatter from SKILL.md. Returns (frontmatter, body, errors)."""
    errors = []
    text = path.read_text()

    if not text.startswith("---\n"):
        errors.append("Missing YAML frontmatter (must start with ---)")
        return None, text, errors

    end = text.find("\n---\n", 4)
    if end == -1:
        errors.append("Unterminated YAML frontmatter (no closing ---)")
        return None, text, errors

    fm_text = text[4:end]
    body = text[end + 5:]

    try:
        fm = yaml.safe_load(fm_text)
        if not isinstance(fm, dict):
            errors.append(f"Frontmatter is not a mapping (got {type(fm).__name__})")
            return None, body, errors
    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
        return None, body, errors

    return fm, body, errors


def validate_skill(
    skill_dir: Path,
    mcp_servers: set[str],
    *,
    project: str = "skills",
    repo_root: Path | None = None,
    require_canonical_case: bool = False,
    exportable: bool = False,
    max_lines: int = 500,
) -> dict:
    """Validate a single skill. Returns {name, path, errors[], warnings[]}."""
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    stored_filename = stored_skill_filename(skill_dir)
    result = {
        "name": name,
        "project": project,
        "path": str(skill_dir),
        "stored_filename": stored_filename,
        "is_symlink": skill_dir.is_symlink(),
        "symlink_target": os.readlink(skill_dir) if skill_dir.is_symlink() else None,
        "errors": [],
        "warnings": [],
    }

    if require_canonical_case and stored_filename != "SKILL.md":
        result["errors"].append(
            f"Non-canonical skill filename: {stored_filename or '<missing>'} (expected SKILL.md)"
        )

    if not skill_md.exists():
        result["errors"].append("SKILL.md not found")
        return result

    # Parse frontmatter
    fm, body, parse_errors = parse_frontmatter(skill_md)
    result["errors"].extend(parse_errors)

    if fm is None:
        return result

    # Check required fields
    if "name" not in fm:
        result["errors"].append("Missing required field: name")
    elif fm["name"] != name:
        result["errors"].append(
            f"name field '{fm['name']}' doesn't match directory '{name}'"
        )

    if "description" not in fm:
        result["errors"].append("Missing required field: description")
    elif isinstance(fm["description"], str) and len(fm["description"]) > 1024:
        result["warnings"].append(
            f"Long description ({len(fm['description'])} chars, >1024)"
        )

    # Check for unknown frontmatter fields
    unknown = set(fm.keys()) - KNOWN_FIELDS
    if unknown:
        result["warnings"].append(f"Unknown frontmatter fields: {sorted(unknown)}")

    # Validate allowed-tools
    if "allowed-tools" in fm:
        tools = fm["allowed-tools"]
        if isinstance(tools, str):
            tools = [tool.strip() for tool in tools.split(",") if tool.strip()]
            result["warnings"].append("allowed-tools should be a YAML list, parsed comma string")
        elif not isinstance(tools, list):
            result["errors"].append("allowed-tools must be a list or comma-separated string")
            tools = []
        if tools:
            for tool in tools:
                if not isinstance(tool, str):
                    result["errors"].append(f"allowed-tools entries must be strings: {tool!r}")
                    continue
                if tool not in NATIVE_TOOLS and not tool.startswith("mcp__"):
                    result["errors"].append(f"Unknown tool in allowed-tools: {tool}")
                if tool.startswith("mcp__"):
                    # Extract server name: mcp__SERVER__tool_name
                    parts = tool.split("__")
                    if len(parts) >= 2:
                        server = parts[1]
                        if server not in mcp_servers:
                            result["warnings"].append(
                                f"MCP server '{server}' in allowed-tools not found in any .mcp.json"
                            )

    # Validate embedded hooks
    if "hooks" in fm:
        hooks = fm["hooks"]
        if not isinstance(hooks, dict):
            result["errors"].append("hooks must be a mapping")
        else:
            for event, hook_list in hooks.items():
                if not isinstance(hook_list, list):
                    result["errors"].append(f"hooks.{event} must be a list")
                    continue
                for hook_entry in hook_list:
                    if not isinstance(hook_entry, dict):
                        continue
                    for h in hook_entry.get("hooks", []):
                        cmd = h.get("command", "")
                        # Check if referenced scripts exist
                        for match in re.findall(
                            r"~/Projects/[^\s\"']+|/Users/\w+/Projects/[^\s\"']+", cmd
                        ):
                            expanded = os.path.expanduser(match)
                            if not Path(expanded).exists():
                                result["errors"].append(
                                    f"Hook references missing file: {match}"
                                )

    # Check MCP tool references in body
    mcp_refs = set(re.findall(r"mcp__(\w+)__\w+", body))
    for server in mcp_refs:
        if server not in mcp_servers:
            result["warnings"].append(
                f"Body references MCP server '{server}' not found in any .mcp.json"
            )

    # Check file path references in body
    path_refs = re.findall(r"~/Projects/[\w/._-]+", body)
    for ref in path_refs:
        expanded = os.path.expanduser(ref)
        if not Path(expanded).exists():
            result["warnings"].append(f"Body references missing path: {ref}")
        if exportable and any(pattern in ref for pattern in PRIVATE_EXPORT_PATTERNS):
            result["errors"].append(f"Exportable skill references private path/token: {ref}")

    if exportable:
        for pattern in PRIVATE_EXPORT_PATTERNS:
            if pattern in body:
                result["errors"].append(
                    f"Exportable skill body contains private token: {pattern}"
                )

    # Check hook script references in body
    hook_refs = re.findall(r"skills/hooks/[\w._-]+\.sh", body)
    for ref in hook_refs:
        hook_path = Path.home() / "Projects" / ref
        if not hook_path.exists():
            result["errors"].append(f"Body references missing hook: {ref}")

    # Size (line count)
    line_count = len(skill_md.read_text().splitlines())
    result["lines"] = line_count
    if line_count > max_lines:
        result["warnings"].append(f"Large skill ({line_count} lines, >{max_lines})")

    return result


def get_changed_skills() -> list[str]:
    """Get skill names changed in the last commit (for post-commit use)."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(SKILLS_DIR), "diff", "--name-only", "HEAD~1", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        changed = set()
        for line in out.strip().splitlines():
            parts = line.split("/")
            if parts and parts[0] not in ("hooks", "archive", ".claude"):
                changed.add(parts[0])
        return sorted(changed)
    except subprocess.CalledProcessError:
        return []


def main():
    parser = argparse.ArgumentParser(description="Validate Claude Code skills")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--changed-only", action="store_true", help="Only git-changed skills")
    parser.add_argument("--skill", help="Validate single skill by name")
    parser.add_argument(
        "--repo",
        action="append",
        choices=["skills", "agent-infra", "genomics", "phenome", "intel"],
        help="Repo skill root to validate. Repeatable. Default: skills.",
    )
    parser.add_argument("--all-projects", action="store_true", help="Validate all known skill roots")
    parser.add_argument(
        "--require-canonical-case",
        action="store_true",
        help="Fail discovered skills not stored as SKILL.md",
    )
    parser.add_argument("--max-lines", type=int, default=500)
    parser.add_argument(
        "--manifest",
        action="store_true",
        help="Include manifest-style discovered object summary in JSON output",
    )
    parser.add_argument(
        "--check-export-leaks",
        action="store_true",
        help="Treat selected shared skills as export candidates and fail on private tokens",
    )
    args = parser.parse_args()

    mcp_servers = collect_mcp_servers()
    roots = iter_default_roots(None if args.all_projects else (args.repo or ["skills"]))

    # Collect skills to validate
    if args.skill:
        skill_dirs = []
        for root in roots:
            candidate = root.root / args.skill
            if candidate.exists():
                skill_dirs.append((root, candidate))
        if not skill_dirs:
            print(f"Skill not found in selected roots: {args.skill}", file=sys.stderr)
            sys.exit(1)
    elif args.changed_only:
        changed = get_changed_skills()
        if not changed:
            if args.json:
                print(json.dumps({"skills": [], "summary": "No changed skills"}))
            else:
                print("No changed skills to validate.")
            return
        skill_dirs = [(DEFAULT_ROOTS["skills"], SKILLS_DIR / name) for name in changed]
    else:
        skill_dirs = []
        for root in roots:
            if not root.root.exists():
                continue
            skill_dirs.extend(
                (root, p)
                for p in sorted(root.root.iterdir(), key=lambda x: x.name)
                if p.is_dir()
                and p.name not in ("hooks", "archive", ".claude", ".git", "__pycache__")
                and stored_skill_filename(p)
            )

    # Validate
    results = [
        validate_skill(
            d,
            mcp_servers,
            project=root.project,
            repo_root=root.repo_root,
            require_canonical_case=args.require_canonical_case,
            exportable=args.check_export_leaks and root.shared,
            max_lines=args.max_lines,
        )
        for root, d in skill_dirs
    ]

    # Size anomaly detection (only when validating all)
    if not args.skill and not args.changed_only:
        line_counts = [r["lines"] for r in results if "lines" in r]
        if line_counts:
            median = statistics.median(line_counts)
            for r in results:
                lines = r.get("lines", 0)
                if lines < 10:
                    r["warnings"].append(f"Very small skill ({lines} lines, <10)")
                elif median > 0 and lines > 2 * median:
                    r["warnings"].append(
                        f"Large skill ({lines} lines, >{2 * median:.0f} = 2x median)"
                    )

    # Output
    total_errors = sum(len(r["errors"]) for r in results)
    total_warnings = sum(len(r["warnings"]) for r in results)

    if args.json:
        output = {
            "skills": results,
            "summary": {
                "total": len(results),
                "errors": total_errors,
                "warnings": total_warnings,
                "mcp_servers_found": sorted(mcp_servers),
            },
        }
        if args.manifest:
            output["manifest_objects"] = [
                obj.to_json()
                for obj in collect_skill_objects(roots, include_planned=True)
            ]
        print(json.dumps(output, indent=2))
    else:
        for r in results:
            if not r["errors"] and not r["warnings"]:
                continue
            print(f"\n{'ERROR' if r['errors'] else 'WARN '} {r['name']}")
            for e in r["errors"]:
                print(f"  ✗ {e}")
            for w in r["warnings"]:
                print(f"  ⚠ {w}")

        print(f"\n{'─' * 50}")
        print(f"Skills: {len(results)}  Errors: {total_errors}  Warnings: {total_warnings}")

        if total_errors == 0:
            print("All skills valid.")
        else:
            print(f"{total_errors} error(s) found.")

    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
