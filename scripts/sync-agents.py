#!/usr/bin/env python3
"""Generate AGENTS.md from CLAUDE.md by stripping Claude-specific sections.

AGENTS.md is the Codex-readable derivative of CLAUDE.md. This script strips
XML-tagged Claude-specific sections and inline references so Codex gets clean
project instructions without hooks, session forensics, or Claude internals.

Usage:
    python3 scripts/sync-agents.py [--all] [--dry-run] [project_dir]
"""

import argparse
import os
import re
import sys
from pathlib import Path

PROJECTS = [
    "~/Projects/meta",
    "~/Projects/intel",
    "~/Projects/selve",
    "~/Projects/genomics",
    "~/Projects/trading",
    "~/Projects/sean",
    "~/Projects/research",
    "~/Projects/people",
]

# XML tags whose entire content (including the tags) gets stripped
STRIP_TAGS = [
    "constitution",
    "session_forensics",
    "cockpit",
    "reference_data",
    "subagent_usage",
    "context_management",
    "execution",
    "ai_text_policy",
    "environment",
    "communication",
    "technical_pushback",
    "git_rules",
]

# Inline patterns to remove (lines containing these)
STRIP_LINE_PATTERNS = [
    r"\.claude/",
    r"claude -p",
    r"hooks?/",  # hook paths
    r"hook[_-]telemetry",
    r"session-analyst",
    r"precompact",
    r"compaction",
    r"subagent",
    r"MEMORY\.md",
]


def strip_claude_sections(text: str) -> str:
    """Remove XML-tagged sections and codex-exclude blocks."""
    # Strip XML-tagged sections
    for tag in STRIP_TAGS:
        text = re.sub(
            rf"<{tag}>.*?</{tag}>\n?",
            "",
            text,
            flags=re.DOTALL,
        )

    # Strip <!-- codex-exclude-start --> ... <!-- codex-exclude-end --> blocks
    text = re.sub(
        r"<!-- codex-exclude-start -->.*?<!-- codex-exclude-end -->\n?",
        "",
        text,
        flags=re.DOTALL,
    )

    return text


def strip_claude_line_refs(text: str) -> str:
    """Remove lines containing Claude-specific references.

    Only strips lines that are purely reference/config lines, not substantive
    content that happens to mention a pattern.
    """
    lines = text.split("\n")
    filtered = []
    compiled = [re.compile(p, re.IGNORECASE) for p in STRIP_LINE_PATTERNS]

    for line in lines:
        stripped = line.strip()
        # Only strip lines that look like config/reference lines, not prose
        # Skip stripping if the line is a heading or table header
        if stripped.startswith("#") or stripped.startswith("|"):
            filtered.append(line)
            continue
        # Skip stripping in code blocks
        if stripped.startswith("```"):
            filtered.append(line)
            continue

        # Check non-substantive lines (bullets, bare refs, key-value)
        if any(p.search(stripped) for p in compiled):
            # Only strip short reference-style lines, not long prose
            if len(stripped) < 120 and (
                stripped.startswith("-")
                or stripped.startswith("*")
                or ":" in stripped[:40]
                or stripped.startswith("`")
            ):
                continue
        filtered.append(line)

    return "\n".join(filtered)


def clean_whitespace(text: str) -> str:
    """Collapse runs of 3+ blank lines to 2."""
    return re.sub(r"\n{3,}", "\n\n", text)


def generate_agents_md(claude_md_path: Path) -> str:
    """Read CLAUDE.md and produce clean AGENTS.md content."""
    text = claude_md_path.read_text()
    text = strip_claude_sections(text)
    text = strip_claude_line_refs(text)
    text = clean_whitespace(text)
    return text.strip() + "\n"


def sync_project(project_dir: Path, dry_run: bool = False) -> bool:
    """Sync one project. Returns True if changes were made."""
    claude_md = project_dir / "CLAUDE.md"
    agents_md = project_dir / "AGENTS.md"

    if not claude_md.exists():
        print(f"  SKIP {project_dir.name}: no CLAUDE.md")
        return False

    # Remove symlink if present
    if agents_md.is_symlink():
        if dry_run:
            print(f"  Would remove symlink: {agents_md}")
        else:
            agents_md.unlink()
            print(f"  Removed symlink: {agents_md}")

    new_content = generate_agents_md(claude_md)
    old_content = agents_md.read_text() if agents_md.exists() and not agents_md.is_symlink() else ""

    if new_content == old_content:
        print(f"  OK {project_dir.name}: unchanged")
        return False

    if dry_run:
        print(f"  Would write {agents_md} ({len(new_content)} bytes)")
        # Show first diff
        if old_content:
            import difflib
            diff = difflib.unified_diff(
                old_content.splitlines(), new_content.splitlines(),
                fromfile="AGENTS.md (old)", tofile="AGENTS.md (new)", lineterm=""
            )
            for line in list(diff)[:30]:
                print(f"    {line}")
        return True

    agents_md.write_text(new_content)
    print(f"  WROTE {project_dir.name}/AGENTS.md ({len(new_content)} bytes)")
    return True


def ensure_gitignore(project_dir: Path, dry_run: bool = False) -> None:
    """Add AGENTS.md to .gitignore if not already present."""
    gitignore = project_dir / ".gitignore"

    if gitignore.exists():
        content = gitignore.read_text()
        if "AGENTS.md" in content:
            return
        if dry_run:
            print(f"  Would add AGENTS.md to {project_dir.name}/.gitignore")
            return
        with open(gitignore, "a") as f:
            if not content.endswith("\n"):
                f.write("\n")
            f.write("AGENTS.md\n")
        print(f"  Added AGENTS.md to {project_dir.name}/.gitignore")
    else:
        if dry_run:
            print(f"  Would create {project_dir.name}/.gitignore with AGENTS.md")
            return
        gitignore.write_text("AGENTS.md\n")
        print(f"  Created {project_dir.name}/.gitignore with AGENTS.md")


def main():
    parser = argparse.ArgumentParser(description="Generate AGENTS.md from CLAUDE.md")
    parser.add_argument("project_dir", nargs="?", help="Single project directory")
    parser.add_argument("--all", action="store_true", help="Sync all configured projects")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    args = parser.parse_args()

    if not args.all and not args.project_dir:
        # Default: sync current directory
        args.project_dir = "."

    if args.all:
        dirs = [Path(p).expanduser() for p in PROJECTS]
    else:
        dirs = [Path(args.project_dir).resolve()]

    changed = 0
    for d in dirs:
        if not d.exists():
            print(f"  SKIP {d}: directory not found")
            continue
        print(f"Syncing {d.name}...")
        if sync_project(d, dry_run=args.dry_run):
            changed += 1
        ensure_gitignore(d, dry_run=args.dry_run)

    action = "would change" if args.dry_run else "changed"
    print(f"\nDone: {changed} projects {action}")


if __name__ == "__main__":
    main()
