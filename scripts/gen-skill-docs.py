#!/usr/bin/env python3
"""Generate SKILL.md from .tmpl templates with live infrastructure data.

Templates use {{PLACEHOLDER}} syntax. Resolvers pull from live config.

Usage:
    gen-skill-docs.py              # generate all templated skills
    gen-skill-docs.py --dry-run    # exit 1 if generated differs from committed
    gen-skill-docs.py --check      # report which skills are templated vs hand-authored
    gen-skill-docs.py --skill NAME # generate single skill
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

SKILLS_DIR = Path.home() / "Projects" / "skills"
META_DIR = Path.home() / "Projects" / "agent-infra"
HOOKS_DIR = SKILLS_DIR / "hooks"


def resolve_mcp_tools() -> str:
    """Generate MCP tools table from all .mcp.json configs."""
    servers: dict[str, list[str]] = {}  # server -> list of projects

    for mcp_file in sorted(Path.home().glob("Projects/*/.mcp.json")):
        project = mcp_file.parent.name
        try:
            data = json.loads(mcp_file.read_text())
            for server in data.get("mcpServers", {}):
                servers.setdefault(server, []).append(project)
        except (json.JSONDecodeError, KeyError):
            pass

    # Also check user-scope
    from common.paths import CLAUDE_DIR
    user_mcp = CLAUDE_DIR / ".mcp.json"
    if user_mcp.exists():
        try:
            data = json.loads(user_mcp.read_text())
            for server in data.get("mcpServers", {}):
                servers.setdefault(server, []).append("(user-scope)")
        except (json.JSONDecodeError, KeyError):
            pass

    lines = ["| MCP Server | Available In |", "|------------|-------------|"]
    for server in sorted(servers):
        projects = ", ".join(sorted(set(servers[server])))
        lines.append(f"| `{server}` | {projects} |")

    return "\n".join(lines)


def resolve_meta_scripts() -> str:
    """Generate agent-infra scripts table from docstrings."""
    scripts_dir = META_DIR / "scripts"
    if not scripts_dir.exists():
        return "(no scripts found)"

    lines = ["| Script | Description |", "|--------|-------------|"]
    for py_file in sorted(scripts_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            tree = ast.parse(py_file.read_text())
            docstring = ast.get_docstring(tree) or ""
            # First line only
            desc = docstring.split("\n")[0].strip() if docstring else ""
            if not desc:
                desc = "(no docstring)"
            # Truncate
            if len(desc) > 80:
                desc = desc[:77] + "..."
            lines.append(f"| `{py_file.name}` | {desc} |")
        except SyntaxError:
            lines.append(f"| `{py_file.name}` | (parse error) |")

    return "\n".join(lines)


def resolve_hook_list() -> str:
    """Generate hook inventory from skills/hooks/."""
    if not HOOKS_DIR.exists():
        return "(no hooks directory)"

    hooks = sorted(HOOKS_DIR.glob("*.sh"))
    lines = ["| Hook | Size |", "|------|------|"]
    for hook in hooks:
        size = hook.stat().st_size
        lines.append(f"| `{hook.name}` | {size:,} bytes |")

    return "\n".join(lines)


RESOLVERS = {
    "MCP_TOOLS": resolve_mcp_tools,
    "META_SCRIPTS": resolve_meta_scripts,
    "HOOK_LIST": resolve_hook_list,
}


def render_template(tmpl_path: Path) -> str:
    """Render a .tmpl file by substituting placeholders."""
    content = tmpl_path.read_text()

    def replacer(match: re.Match) -> str:
        name = match.group(1)
        resolver = RESOLVERS.get(name)
        if resolver is None:
            return match.group(0)  # leave unknown placeholders
        return resolver()

    return re.sub(r"\{\{(\w+)\}\}", replacer, content)


def find_templated_skills() -> list[tuple[Path, Path]]:
    """Find all skills with .tmpl files. Returns [(tmpl_path, output_path)]."""
    results = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        tmpl = skill_dir / "SKILL.md.tmpl"
        if tmpl.exists():
            results.append((tmpl, skill_dir / "SKILL.md"))
    return results


def main():
    parser = argparse.ArgumentParser(description="Generate skill docs from templates")
    parser.add_argument("--dry-run", action="store_true", help="Check for drift without writing")
    parser.add_argument("--check", action="store_true", help="Report templated vs hand-authored")
    parser.add_argument("--skill", help="Generate single skill by name")
    args = parser.parse_args()

    if args.check:
        all_skills = sorted(
            p.name for p in SKILLS_DIR.iterdir()
            if p.is_dir() and (p / "SKILL.md").exists()
            and p.name not in ("hooks", "archive", ".claude", ".git")
        )
        templated = [p.parent.name for p, _ in find_templated_skills()]
        hand_authored = [s for s in all_skills if s not in templated]

        print(f"Templated ({len(templated)}):")
        for s in templated:
            print(f"  {s}")
        print(f"\nHand-authored ({len(hand_authored)}):")
        for s in hand_authored:
            print(f"  {s}")
        return

    # Find templates to process
    if args.skill:
        tmpl = SKILLS_DIR / args.skill / "SKILL.md.tmpl"
        if not tmpl.exists():
            print(f"No template found: {tmpl}", file=sys.stderr)
            sys.exit(1)
        pairs = [(tmpl, SKILLS_DIR / args.skill / "SKILL.md")]
    else:
        pairs = find_templated_skills()

    if not pairs:
        print("No templated skills found. Create SKILL.md.tmpl files to use templates.")
        return

    drift_found = False
    for tmpl_path, output_path in pairs:
        skill_name = tmpl_path.parent.name
        rendered = render_template(tmpl_path)

        if args.dry_run:
            if output_path.exists():
                current = output_path.read_text()
                if current != rendered:
                    print(f"DRIFT {skill_name}: generated differs from committed")
                    drift_found = True
                else:
                    print(f"OK    {skill_name}: up to date")
            else:
                print(f"MISS  {skill_name}: SKILL.md missing (template exists)")
                drift_found = True
        else:
            output_path.write_text(rendered)
            print(f"Generated {skill_name}/SKILL.md")

    if args.dry_run and drift_found:
        sys.exit(1)


if __name__ == "__main__":
    main()
