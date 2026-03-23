#!/usr/bin/env python3
"""Model-review dispatch — context assembly + parallel llmx dispatch + output collection.

Replaces the 10-tool-call manual ceremony in the model-review skill with one script call.
Agent provides context + topic + question; script handles plumbing; agent reads outputs.

Usage:
    # Standard review (2 queries: arch + formal)
    model-review.py --context plan.md --topic "hook architecture" "Review for gaps"

    # Simple review (1 query: combined)
    model-review.py --context plan.md --topic "config tweak" --axes simple "Review this change"

    # Deep review (4 queries: arch + formal + domain + mechanical)
    model-review.py --context plan.md --topic "classification logic" --axes arch,formal,domain,mechanical "Review this"

    # With project dir for constitution discovery
    model-review.py --context plan.md --topic "data wiring" --project ~/Projects/intel "Review this plan"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

# --- Axis definitions: model + prompt + llmx flags ---

AXES = {
    "arch": {
        "label": "Gemini (architecture/patterns)",
        "model": "gemini-3.1-pro-preview",
        "flags": ["--timeout", "300"],
        "prompt": """\
<system>
You are reviewing a codebase. Be concrete. No platitudes. Reference specific code, configs, and findings. It is {date}.
Budget: ~2000 words. Dense tables and lists over prose.
</system>

{question}

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Assessment of Strengths and Weaknesses
What holds up and what doesn't. Reference actual code/config. Be specific about errors AND what's correct.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, architectural gaps.

## 3. Better Approaches
For each recommendation, either: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Your ranked list of the 5 most impactful changes, with testable verification criteria.

## 5. Constitutional Alignment
{constitution_instruction}

## 6. Blind Spots In My Own Analysis
What am I (Gemini) likely getting wrong? Where should you distrust my assessment?""",
    },
    "formal": {
        "label": "GPT-5.4 (quantitative/formal)",
        "model": "gpt-5.4",
        "flags": ["--stream", "--reasoning-effort", "high", "--timeout", "600", "--max-tokens", "32768"],
        "prompt": """\
<system>
You are performing QUANTITATIVE and FORMAL analysis. Other reviewers handle qualitative pattern review. Focus on what they can't do well. Be precise. Show your reasoning. No hand-waving.
Budget: ~2000 words. Tables over prose. Source-grade claims.
</system>

{question}

RESPOND WITH EXACTLY:

## 1. Logical Inconsistencies
Formal contradictions, unstated assumptions, invalid inferences. If math is involved, verify it.

## 2. Cost-Benefit Analysis
For each proposed change: expected impact, maintenance burden, composability, risk. Rank by value adjusted for ongoing cost (not creation effort — dev time is ~free).

## 3. Testable Predictions
Convert vague claims into falsifiable predictions with success criteria. If a claim can't be made testable, flag it.

## 4. Constitutional Alignment (Quantified)
{constitution_instruction}

## 5. My Top 5 Recommendations (different from the originals)
Ranked by measurable impact. Each must have: (a) what, (b) why with quantitative justification, (c) how to verify with specific metrics.

## 6. Where I'm Likely Wrong
What am I (GPT-5.4) probably getting wrong? Known biases to flag: overconfidence in fabricated specifics, overcautious scope-limiting, production-grade recommendations for personal projects.""",
    },
    "domain": {
        "label": "Gemini Pro (domain correctness)",
        "model": "gemini-3.1-pro-preview",
        "flags": ["--timeout", "300"],
        "prompt": """\
<system>
You are verifying DOMAIN-SPECIFIC CLAIMS in this plan. Other reviewers handle architecture and formal logic.
Focus exclusively on: are the domain facts correct? Are citations real? Are API endpoints, database schemas,
biological claims, financial numbers accurate? Check every specific claim against your knowledge.
Budget: ~1500 words. Flat list of claims with verdict (CORRECT / WRONG / UNVERIFIABLE).
</system>

{question}

For each domain-specific claim in the reviewed material:
1. State the claim
2. Verdict: CORRECT / WRONG / UNVERIFIABLE
3. If WRONG: what's actually true
4. If UNVERIFIABLE: what would you need to check

Flag any URLs, API endpoints, or version numbers that should be probed before implementation.""",
    },
    "mechanical": {
        "label": "Gemini Flash (mechanical audit)",
        "model": "gemini-3-flash-preview",
        "flags": ["--timeout", "120"],
        "prompt": """\
<system>
Mechanical audit only. No analysis, no recommendations. Fast and precise.
</system>

Find in the reviewed material:
- Stale references (wrong versions, deprecated APIs, broken links)
- Inconsistent naming (model names, paths, conventions that don't match)
- Missing cross-references between related documents
- Duplicated content
- Paths or file references that look wrong
Output as a flat numbered list. One issue per line.""",
    },
    "alternatives": {
        "label": "Kimi K2.5 (alternative approaches)",
        "model": "kimi-k2.5",
        "flags": ["--stream", "--timeout", "300"],
        "prompt": """\
<system>
You are generating ALTERNATIVE APPROACHES to the proposed plan. Other reviewers check correctness.
Your job: what ELSE could be done? Different mechanisms, not variations.
Budget: ~1500 words.
</system>

{question}

Generate 3-5 genuinely different approaches to the same problem. For each:
1. Core mechanism (how it works differently)
2. What it's better at than the proposed approach
3. What it's worse at
4. Rough effort to implement

Do NOT critique the existing plan — generate alternatives. Different mechanisms, not tweaks.""",
    },
    "simple": {
        "label": "Gemini Pro (combined review)",
        "model": "gemini-3.1-pro-preview",
        "flags": ["--timeout", "300"],
        "prompt": """\
<system>
Quick combined review. Be concrete. It is {date}. Budget: ~1000 words.
</system>

{question}

Check for: (1) anything that breaks existing functionality, (2) wrong assumptions, (3) missing edge cases.
If everything looks correct, say so concisely.""",
    },
}

# Presets map a single name to a list of axes
PRESETS = {
    "simple": ["simple"],
    "standard": ["arch", "formal"],
    "deep": ["arch", "formal", "domain", "mechanical"],
    "full": ["arch", "formal", "domain", "mechanical", "alternatives"],
}


def slugify(text: str, max_len: int = 40) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:max_len]


def find_constitution(project_dir: Path) -> tuple[str, str | None]:
    """Find constitution text and GOALS.md path in project dir."""
    constitution = ""
    goals_path = None

    claude_md = project_dir / "CLAUDE.md"
    if claude_md.exists():
        text = claude_md.read_text()
        m = re.search(r"<constitution>(.*?)</constitution>", text, re.DOTALL)
        if m:
            constitution = m.group(1).strip()
        elif "## Constitution" in text:
            idx = text.index("## Constitution")
            rest = text[idx:]
            end = re.search(r"\n## (?!Constitution)", rest)
            constitution = rest[: end.start()].strip() if end else rest.strip()

    for gp in [project_dir / "GOALS.md", project_dir / "docs" / "GOALS.md"]:
        if gp.exists():
            goals_path = str(gp)
            break

    return constitution, goals_path


def build_context(
    review_dir: Path,
    project_dir: Path,
    context_file: Path | None,
    axis_names: list[str],
) -> dict[str, Path]:
    """Assemble per-axis context files with constitutional preamble."""
    constitution, goals_path = find_constitution(project_dir)

    preamble = ""
    if constitution:
        preamble += "# PROJECT CONSTITUTION\nReview against these principles, not your own priors.\n\n"
        preamble += constitution + "\n\n"
    if goals_path:
        preamble += "# PROJECT GOALS\n\n"
        preamble += Path(goals_path).read_text() + "\n\n"

    content = context_file.read_text() if context_file else ""

    ctx_files = {}
    for axis in axis_names:
        ctx_path = review_dir / f"{axis}-context.md"
        ctx_path.write_text(preamble + content)
        ctx_files[axis] = ctx_path

    # Warn on size
    for axis, path in ctx_files.items():
        size = path.stat().st_size
        if size > 15_000:
            print(f"warning: {axis} context {size} bytes > 15KB — consider summarizing", file=sys.stderr)

    return ctx_files


def dispatch(
    review_dir: Path,
    ctx_files: dict[str, Path],
    axis_names: list[str],
    question: str,
    has_constitution: bool,
) -> dict:
    """Fire N llmx processes in parallel (one per axis), wait, return results."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CLAUDECODE", "CLAUDE_SESSION_ID")
    }

    today = date.today().isoformat()

    const_instruction = {
        "arch": (
            "Where does the reviewed work violate or neglect stated principles? Which principles are well-served?"
            if has_constitution
            else "No constitution provided — assess internal consistency only."
        ),
        "formal": (
            "For each constitutional principle: coverage score (0-100%), specific gaps, suggested fixes."
            if has_constitution
            else "No constitution provided — assess internal logical consistency."
        ),
    }

    procs = {}
    outputs = {}
    t0 = time.time()

    for axis in axis_names:
        axis_def = AXES[axis]
        out_path = review_dir / f"{axis}-output.md"
        outputs[axis] = out_path

        prompt = axis_def["prompt"].format(
            date=today,
            question=question,
            constitution_instruction=const_instruction.get(axis, ""),
        )

        cmd = [
            "llmx", "chat",
            "-m", axis_def["model"],
            *axis_def["flags"],
            "-f", str(ctx_files[axis]),
            "-o", str(out_path),
            prompt,
        ]

        procs[axis] = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    # Wait for all
    results = {"review_dir": str(review_dir), "axes": axis_names, "queries": len(axis_names)}
    for axis in axis_names:
        proc = procs[axis]
        rc = proc.wait()
        stderr = proc.stderr.read().decode(errors="replace").strip() if proc.stderr else ""
        out_path = outputs[axis]

        entry = {
            "label": AXES[axis]["label"],
            "model": AXES[axis]["model"],
            "exit_code": rc,
            "output": str(out_path),
            "size": out_path.stat().st_size if out_path.exists() else 0,
        }
        if rc != 0:
            entry["stderr"] = stderr[-500:] if stderr else ""

        results[axis] = entry

    results["elapsed_seconds"] = round(time.time() - t0, 1)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Model-review dispatch: context assembly + parallel llmx + output collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Presets: {', '.join(PRESETS.keys())}. Axes: {', '.join(AXES.keys())}.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--context", type=Path, help="Context file for narrow review")
    parser.add_argument("--topic", required=True, help="Short topic label (used in output dir name)")
    parser.add_argument("--project", type=Path, help="Project dir for constitution discovery (default: cwd)")
    parser.add_argument(
        "--axes", default="standard",
        help="Comma-separated axes or preset name (simple, standard, deep, full). Default: standard",
    )
    parser.add_argument(
        "question", nargs="?",
        default="Review this for logical gaps, missed edge cases, and constitutional alignment.",
        help="Review question for all models",
    )

    args = parser.parse_args()

    project_dir = args.project or Path.cwd()
    if not project_dir.is_dir():
        print(f"error: project dir {project_dir} not found", file=sys.stderr)
        return 1

    if args.context and not args.context.exists():
        print(f"error: context file {args.context} not found", file=sys.stderr)
        return 1

    # Resolve axes
    if args.axes in PRESETS:
        axis_names = PRESETS[args.axes]
    else:
        axis_names = [a.strip() for a in args.axes.split(",")]
        for a in axis_names:
            if a not in AXES:
                print(f"error: unknown axis '{a}'. Available: {', '.join(AXES.keys())}", file=sys.stderr)
                return 1

    print(f"Dispatching {len(axis_names)} queries: {', '.join(axis_names)}", file=sys.stderr)

    # Create output directory
    slug = slugify(args.topic)
    hex_id = os.urandom(3).hex()
    review_dir = Path(f".model-review/{date.today().isoformat()}-{slug}-{hex_id}")
    review_dir.mkdir(parents=True, exist_ok=True)

    # Assemble context
    ctx_files = build_context(review_dir, project_dir, args.context, axis_names)

    constitution, _ = find_constitution(project_dir)

    # Dispatch and wait
    result = dispatch(review_dir, ctx_files, axis_names, args.question, bool(constitution))

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
