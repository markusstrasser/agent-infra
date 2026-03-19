#!/usr/bin/env python3
"""Prompt Archaeology — feed entire instruction surface into Gemini 3.1 Pro,
extract the system's implied beliefs, contradictions, and unstated assumptions.

Usage:
    uv run python3 scripts/prompt-archaeology.py [--dry-run] [-o OUTPUT]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import date

PROJECTS_DIR = Path.home() / "Projects"
SKILLS_DIR = PROJECTS_DIR / "skills"
from common.paths import CLAUDE_DIR as GLOBAL_CLAUDE

# Core projects (skip throwaway/demo dirs)
CORE_PROJECTS = [
    "meta", "intel", "selve", "genomics", "skills",
    "arc-agi", "evo", "research", "people", "trading",
    "anki", "phys-1", "sean", "scripting", "clipper",
]


def gather_files() -> list[tuple[str, str]]:
    """Collect all instruction surface files. Returns [(label, content), ...]."""
    files = []

    # Global CLAUDE.md + settings
    for name in ["CLAUDE.md", "settings.json"]:
        p = GLOBAL_CLAUDE / name
        if p.exists():
            files.append((f"GLOBAL/{name}", p.read_text()))

    # Global rules
    rules_dir = GLOBAL_CLAUDE / "rules"
    if rules_dir.is_dir():
        for f in sorted(rules_dir.glob("*.md")):
            files.append((f"GLOBAL/rules/{f.name}", f.read_text()))

    # Per-project CLAUDE.md + GOALS.md
    for proj in CORE_PROJECTS:
        proj_dir = PROJECTS_DIR / proj
        if not proj_dir.exists():
            continue

        claude_md = proj_dir / "CLAUDE.md"
        if claude_md.exists():
            files.append((f"{proj}/CLAUDE.md", claude_md.read_text()))

        # GOALS.md in root or docs/
        for goals_path in [proj_dir / "GOALS.md", proj_dir / "docs" / "GOALS.md"]:
            if goals_path.exists():
                files.append((f"{proj}/GOALS.md", goals_path.read_text()))
                break

    # Hooks
    hooks_dir = SKILLS_DIR / "hooks"
    if hooks_dir.is_dir():
        for f in sorted(hooks_dir.glob("*.sh")):
            files.append((f"hooks/{f.name}", f.read_text()))

    # Skills (SKILL.md only)
    if SKILLS_DIR.is_dir():
        for f in sorted(SKILLS_DIR.glob("*/SKILL.md")):
            skill_name = f.parent.name
            files.append((f"skills/{skill_name}/SKILL.md", f.read_text()))

    return files


def build_context(files: list[tuple[str, str]]) -> str:
    """Build the full context document."""
    parts = []
    for label, content in files:
        parts.append(f"{'='*60}\n## FILE: {label}\n{'='*60}\n{content}\n")
    return "\n".join(parts)


SYSTEM_PROMPT = """\
You are performing a metacognitive audit of an agent system's instruction surface.
You have the COMPLETE set of instructions, hooks, skills, goals, and settings
that govern this system across all projects. No session ever sees all of this
simultaneously — you are the first to hold the entire surface in context.

Your task: identify what this system IMPLICITLY BELIEVES about itself,
where those beliefs contradict reality, and what assumptions are unstated.

This is NOT a consistency check (find contradictions between files).
This IS an archaeology of the implied mental model — the ghost in the instructions."""

USER_PROMPT = """\
Analyze the complete instruction surface above. Produce a structured report:

## 1. Implied Beliefs
What does this system believe about itself? Extract 10-15 core beliefs implied
by the totality of instructions — not what any single file says, but what the
SYSTEM believes when you read everything together. For each:
- The belief (one sentence)
- Evidence (which files/sections imply this)
- Confidence that this belief is actually true (high/medium/low)
- If low/medium: what's actually true instead

## 2. Unstated Assumptions
Things the system assumes but never writes down. These are the gaps —
the load-bearing implicit knowledge that would break things if wrong. 10+.
For each:
- The assumption
- Where it's load-bearing (what breaks if false)
- Whether it's actually true

## 3. Contradictions (not surface-level)
NOT "file A says X, file B says Y." Instead: structural contradictions where
the system's architecture implies one thing but its instructions demand another.
Or where two goals are in genuine tension and the system has no resolution mechanism.

## 4. Power Map
Which files/rules actually control behavior vs which are decorative?
What's the real hierarchy of authority when instructions conflict?
Which hooks actually fire and block vs which are advisory noise?

## 5. Evolutionary Fossils
Instructions that made sense in a previous era but no longer serve a purpose.
Rules that were responses to specific incidents and have outlived the problem.
Patterns that got cargo-culted across projects without the original reason.

## 6. The System's Blind Spots
What CAN'T this system see about itself? What failure modes exist that
no hook, skill, or instruction addresses? Where is the metacognitive gap?

Be specific. Reference files and line-level evidence. No platitudes."""


def main():
    parser = argparse.ArgumentParser(description="Prompt Archaeology")
    parser.add_argument("--dry-run", action="store_true", help="Print context stats, don't call LLM")
    parser.add_argument("-o", "--output", default=None, help="Output file (default: artifacts/prompt-archaeology/YYYY-MM-DD.md)")
    parser.add_argument("--model", default="gemini-3.1-pro-preview", help="Model to use")
    args = parser.parse_args()

    files = gather_files()
    context = build_context(files)

    print(f"Gathered {len(files)} files, {len(context):,} chars (~{len(context)//4:,} tokens)", file=sys.stderr)

    if args.dry_run:
        print("\nFiles included:", file=sys.stderr)
        for label, content in files:
            print(f"  {label}: {len(content):,} chars", file=sys.stderr)
        print(f"\nTotal context: {len(context):,} chars", file=sys.stderr)
        return

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        out_dir = Path("artifacts/prompt-archaeology")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{date.today()}.md"

    # Build prompt
    full_prompt = f"{context}\n\n---\n\n{USER_PROMPT}"

    # Call via llmx — use --max-tokens to force API route (Gemini CLI caps at 8K)
    cmd = [
        "llmx", "chat",
        "-m", args.model,
        "--max-tokens", "65536",
        "--stream", "--timeout", "300",
        "-s", SYSTEM_PROMPT,
        "-o", str(out_path),
    ]

    print(f"Calling {args.model} via API (--max-tokens forces API route)...", file=sys.stderr)
    print(f"Output: {out_path}", file=sys.stderr)

    result = subprocess.run(
        cmd,
        input=full_prompt,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode == 0:
        print(f"Done. Output written to {out_path}", file=sys.stderr)
    elif result.returncode == 3:
        print(f"Rate limited. stderr: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    elif result.returncode == 4:
        print(f"Timeout. stderr: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Error (exit {result.returncode}). stderr: {result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
