#!/usr/bin/env python3
"""Context budget analyzer.

Measures the token cost of everything Claude Code auto-loads per session:
CLAUDE.md, rules, memory index, skill descriptions, global context.

Distinguishes always-loaded vs path-scoped vs on-demand.

Usage:
    uv run python3 scripts/context-budget.py                # current project
    uv run python3 scripts/context-budget.py ~/Projects/selve
    uv run python3 scripts/context-budget.py --compare       # all 3 projects
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import yaml

from common import con

PROJECTS_ROOT = Path.home() / "Projects"
DEFAULT_PROJECTS = ["meta", "selve", "genomics"]
GLOBAL_CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
GLOBAL_RULES_DIR = Path.home() / ".claude" / "rules"
SKILLS_DIR = PROJECTS_ROOT / "skills"
MEMORY_BASE = Path.home() / ".claude" / "projects"


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def file_tokens(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return estimate_tokens(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return 0


def parse_paths_scope(path: Path) -> list[str] | None:
    """Extract paths: frontmatter from a rule file. Returns None if no scope."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    try:
        fm = yaml.safe_load(text[4:end])
        if isinstance(fm, dict) and "paths" in fm:
            return fm["paths"]
    except Exception:
        pass
    return None


def project_memory_dir(project_path: Path) -> Path:
    """Resolve the memory directory for a project."""
    slug = str(project_path.resolve()).replace("/", "-")
    return MEMORY_BASE / slug / "memory"


def collect_rules(rules_dir: Path) -> tuple[list[dict], list[dict]]:
    """Return (always_loaded, path_scoped) rule entries."""
    always = []
    scoped = []
    if not rules_dir.is_dir():
        return always, scoped
    for f in sorted(rules_dir.glob("*.md")):
        tok = file_tokens(f)
        paths = parse_paths_scope(f)
        entry = {"name": f.name, "path": str(f), "tokens": tok}
        if paths:
            entry["scope"] = paths
            scoped.append(entry)
        else:
            always.append(entry)
    return always, scoped


def collect_skills() -> tuple[int, int, int]:
    """Return (description_tokens, body_tokens, count) for shared skills."""
    desc_total = 0
    body_total = 0
    count = 0
    if not SKILLS_DIR.is_dir():
        return 0, 0, 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        count += 1
        # Parse frontmatter for description
        if text.startswith("---\n"):
            end = text.find("\n---\n", 4)
            if end != -1:
                try:
                    fm = yaml.safe_load(text[4:end])
                    desc = fm.get("description", "") if isinstance(fm, dict) else ""
                    desc_total += estimate_tokens(str(desc))
                    body_total += estimate_tokens(text[end + 5 :])
                except Exception:
                    body_total += estimate_tokens(text)
            else:
                body_total += estimate_tokens(text)
        else:
            body_total += estimate_tokens(text)
    return desc_total, body_total, count


def collect_project_skills(project_path: Path) -> tuple[int, int, int]:
    """Return (desc_tokens, body_tokens, count) for project-local skills."""
    skills_dir = project_path / ".claude" / "skills"
    desc_total = 0
    body_total = 0
    count = 0
    if not skills_dir.is_dir():
        return 0, 0, 0
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        count += 1
        if text.startswith("---\n"):
            end = text.find("\n---\n", 4)
            if end != -1:
                try:
                    fm = yaml.safe_load(text[4:end])
                    desc = fm.get("description", "") if isinstance(fm, dict) else ""
                    desc_total += estimate_tokens(str(desc))
                    body_total += estimate_tokens(text[end + 5 :])
                except Exception:
                    body_total += estimate_tokens(text)
            else:
                body_total += estimate_tokens(text)
        else:
            body_total += estimate_tokens(text)
    return desc_total, body_total, count


def analyze_project(project_path: Path) -> dict:
    """Analyze a single project's context budget."""
    project_path = project_path.resolve()
    result = {"name": project_path.name, "path": str(project_path)}

    # 1. Global CLAUDE.md
    result["global_claude_md"] = file_tokens(GLOBAL_CLAUDE_MD)

    # 2. Global rules
    g_always, g_scoped = collect_rules(GLOBAL_RULES_DIR)
    result["global_rules_always"] = g_always
    result["global_rules_scoped"] = g_scoped

    # 3. Project CLAUDE.md
    result["project_claude_md"] = file_tokens(project_path / "CLAUDE.md")

    # 4. Project rules
    p_always, p_scoped = collect_rules(project_path / ".claude" / "rules")
    result["project_rules_always"] = p_always
    result["project_rules_scoped"] = p_scoped

    # 5. Memory (MEMORY.md index only — individual files are on-demand)
    mem_dir = project_memory_dir(project_path)
    mem_index = mem_dir / "MEMORY.md"
    result["memory_index_tokens"] = file_tokens(mem_index)
    mem_files = list(mem_dir.glob("*.md")) if mem_dir.is_dir() else []
    mem_other = [f for f in mem_files if f.name != "MEMORY.md"]
    result["memory_file_count"] = len(mem_other)
    result["memory_files_total"] = sum(file_tokens(f) for f in mem_other)

    # 6. Overviews
    overview_dir = project_path / ".claude" / "overviews"
    overviews = []
    if overview_dir.is_dir():
        for f in sorted(overview_dir.glob("*.md")):
            overviews.append({"name": f.name, "tokens": file_tokens(f)})
    result["overviews"] = overviews

    # 7. Skills (shared + project-local)
    s_desc, s_body, s_count = collect_skills()
    result["shared_skills"] = {
        "count": s_count,
        "description_tokens": s_desc,
        "body_tokens": s_body,
    }
    p_desc, p_body, p_count = collect_project_skills(project_path)
    result["project_skills"] = {
        "count": p_count,
        "description_tokens": p_desc,
        "body_tokens": p_body,
    }

    return result


def print_report(data: dict) -> int:
    """Print formatted report. Returns grand total always-loaded tokens."""
    name = data["name"]
    con.header(f"Context Budget: {name}")

    always_total = 0

    # Global section
    print("\n  GLOBAL (every project, every session)")
    tok = data["global_claude_md"]
    print(f"    {'Global CLAUDE.md':<40} {tok:>6} tok")
    always_total += tok

    g_always_total = sum(r["tokens"] for r in data["global_rules_always"])
    g_scoped_total = sum(r["tokens"] for r in data["global_rules_scoped"])
    n = len(data["global_rules_always"])
    print(f"    {'Global rules (always, ' + str(n) + ')':<40} {g_always_total:>6} tok")
    always_total += g_always_total
    for r in sorted(data["global_rules_always"], key=lambda x: -x["tokens"])[:3]:
        print(f"      {r['name']:<38} {r['tokens']:>6}")

    if data["global_rules_scoped"]:
        n = len(data["global_rules_scoped"])
        print(f"    {'Global rules (scoped, ' + str(n) + ')':<40} {g_scoped_total:>6} tok  (conditional)")
        for r in sorted(data["global_rules_scoped"], key=lambda x: -x["tokens"])[:3]:
            scope = ", ".join(r.get("scope", []))
            print(f"      {r['name']:<30} {r['tokens']:>6}  [{scope}]")

    # Shared skills
    sd = data["shared_skills"]
    print(f"    {'Skill descriptions (' + str(sd['count']) + ' shared)':<40} {sd['description_tokens']:>6} tok")
    always_total += sd["description_tokens"]

    # Project section
    print(f"\n  PROJECT: {name}")
    tok = data["project_claude_md"]
    print(f"    {'Project CLAUDE.md':<40} {tok:>6} tok")
    always_total += tok

    p_always_total = sum(r["tokens"] for r in data["project_rules_always"])
    p_scoped_total = sum(r["tokens"] for r in data["project_rules_scoped"])
    n = len(data["project_rules_always"])
    print(f"    {'Project rules (always, ' + str(n) + ')':<40} {p_always_total:>6} tok")
    always_total += p_always_total
    for r in sorted(data["project_rules_always"], key=lambda x: -x["tokens"])[:5]:
        print(f"      {r['name']:<38} {r['tokens']:>6}")

    if data["project_rules_scoped"]:
        n = len(data["project_rules_scoped"])
        print(f"    {'Project rules (scoped, ' + str(n) + ')':<40} {p_scoped_total:>6} tok  (conditional)")
        for r in sorted(data["project_rules_scoped"], key=lambda x: -x["tokens"])[:5]:
            scope = ", ".join(r.get("scope", []))
            print(f"      {r['name']:<30} {r['tokens']:>6}  [{scope}]")

    # Memory
    mem_idx = data["memory_index_tokens"]
    print(f"    {'Memory index (MEMORY.md)':<40} {mem_idx:>6} tok")
    always_total += mem_idx
    n = data["memory_file_count"]
    mem_total = data["memory_files_total"]
    print(f"    {'Memory files (' + str(n) + ', on-demand)':<40} {mem_total:>6} tok  (not auto-loaded)")

    # Overviews
    if data["overviews"]:
        ov_total = sum(o["tokens"] for o in data["overviews"])
        n = len(data["overviews"])
        print(f"    {'Overviews (' + str(n) + ')':<40} {ov_total:>6} tok")
        always_total += ov_total

    # Project-local skills
    pd = data["project_skills"]
    if pd["count"] > 0:
        print(f"    {'Project skill descs (' + str(pd['count']) + ')':<40} {pd['description_tokens']:>6} tok")
        always_total += pd["description_tokens"]

    # Totals
    scoped_total = g_scoped_total + p_scoped_total
    print(f"\n  {'─' * 55}")
    print(f"    {'ALWAYS LOADED':<40} {always_total:>6} tok")
    print(f"    {'+ PATH-SCOPED (conditional)':<40} {scoped_total:>6} tok")
    print(f"    {'= MAX LOADED':<40} {always_total + scoped_total:>6} tok")

    on_invoke = sd["body_tokens"] + pd["body_tokens"]
    print(f"    {'ON-INVOKE (skill bodies)':<40} {on_invoke:>6} tok")

    return always_total


def print_comparison(projects: list[dict]) -> None:
    """Print cross-project comparison table."""
    con.header("Cross-Project Comparison")

    headers = ["Category"] + [p["name"] for p in projects]
    rows = []

    rows.append(("Global CLAUDE.md", *[p["global_claude_md"] for p in projects]))
    rows.append((
        "Global rules (always)",
        *[sum(r["tokens"] for r in p["global_rules_always"]) for p in projects],
    ))
    rows.append((
        "Global rules (scoped)",
        *[sum(r["tokens"] for r in p["global_rules_scoped"]) for p in projects],
    ))
    rows.append(("Skill descriptions", *[p["shared_skills"]["description_tokens"] for p in projects]))
    rows.append(("Project CLAUDE.md", *[p["project_claude_md"] for p in projects]))
    rows.append((
        "Project rules (always)",
        *[sum(r["tokens"] for r in p["project_rules_always"]) for p in projects],
    ))
    rows.append((
        "Project rules (scoped)",
        *[sum(r["tokens"] for r in p["project_rules_scoped"]) for p in projects],
    ))
    rows.append(("Memory index", *[p["memory_index_tokens"] for p in projects]))
    rows.append(("Overviews", *[sum(o["tokens"] for o in p["overviews"]) for p in projects]))
    rows.append((
        "Project skill descs",
        *[p["project_skills"]["description_tokens"] for p in projects],
    ))

    # Print table
    w_label = 24
    w_col = 10
    header_line = f"  {'':>{w_label}}"
    for p in projects:
        header_line += f"  {p['name']:>{w_col}}"
    print(header_line)
    print(f"  {'─' * (w_label + (w_col + 2) * len(projects))}")

    for row in rows:
        line = f"  {row[0]:>{w_label}}"
        for val in row[1:]:
            line += f"  {val:>{w_col},}"
        print(line)

    # Totals
    print(f"  {'─' * (w_label + (w_col + 2) * len(projects))}")

    always_totals = []
    for p in projects:
        t = (
            p["global_claude_md"]
            + sum(r["tokens"] for r in p["global_rules_always"])
            + p["shared_skills"]["description_tokens"]
            + p["project_claude_md"]
            + sum(r["tokens"] for r in p["project_rules_always"])
            + p["memory_index_tokens"]
            + sum(o["tokens"] for o in p["overviews"])
            + p["project_skills"]["description_tokens"]
        )
        always_totals.append(t)

    line = f"  {'ALWAYS LOADED':>{w_label}}"
    for t in always_totals:
        line += f"  {t:>{w_col},}"
    print(line)

    scoped_totals = []
    for p in projects:
        t = sum(r["tokens"] for r in p["global_rules_scoped"]) + sum(
            r["tokens"] for r in p["project_rules_scoped"]
        )
        scoped_totals.append(t)

    line = f"  {'+ SCOPED':>{w_label}}"
    for t in scoped_totals:
        line += f"  {t:>{w_col},}"
    print(line)

    line = f"  {'= MAX':>{w_label}}"
    for a, s in zip(always_totals, scoped_totals):
        line += f"  {a + s:>{w_col},}"
    print(line)


def main():
    parser = argparse.ArgumentParser(description="Context budget analyzer")
    parser.add_argument("project", nargs="?", default=".", help="Project path (default: cwd)")
    parser.add_argument("--compare", action="store_true", help="Compare meta/selve/genomics")
    args = parser.parse_args()

    if args.compare:
        projects = []
        for name in DEFAULT_PROJECTS:
            p = PROJECTS_ROOT / name
            if p.is_dir():
                projects.append(analyze_project(p))
            else:
                print(f"  ! Skipping {name} (not found at {p})")
        for p in projects:
            print_report(p)
            print()
        if len(projects) > 1:
            print_comparison(projects)
    else:
        project_path = Path(args.project).resolve()
        data = analyze_project(project_path)
        print_report(data)


if __name__ == "__main__":
    main()
