#!/usr/bin/env python3
"""Model-review dispatch — context assembly + parallel llmx dispatch + output collection.

Replaces the 10-tool-call manual ceremony in the model-review skill with one script call.
Agent provides context + topic + question; script handles plumbing; agent reads outputs.

Usage:
    # Narrow review (agent provides context file)
    model-review.py --context plan.md --topic "hook architecture" "Review for gaps"

    # Broad review (script picks .context/ views)
    model-review.py --broad src --topic "auth flow" "Review the auth flow"

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

GEMINI_MODEL = "gemini-3.1-pro-preview"
GPT_MODEL = "gpt-5.4"

GEMINI_PROMPT = """\
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
What am I (Gemini) likely getting wrong? Where should you distrust my assessment?"""

GPT_PROMPT = """\
<system>
You are performing QUANTITATIVE and FORMAL analysis. Gemini is handling qualitative pattern review separately. Focus on what Gemini can't do well. Be precise. Show your reasoning. No hand-waving.
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
What am I (GPT-5.4) probably getting wrong? Known biases to flag: overconfidence in fabricated specifics, overcautious scope-limiting, production-grade recommendations for personal projects."""


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
        # Extract <constitution>...</constitution> section
        m = re.search(r"<constitution>(.*?)</constitution>", text, re.DOTALL)
        if m:
            constitution = m.group(1).strip()
        # Fallback: ## Constitution heading
        elif "## Constitution" in text:
            idx = text.index("## Constitution")
            # Take until next ## heading or end
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
    broad_view: str | None,
) -> tuple[Path, Path]:
    """Assemble gemini-context.md and gpt-context.md with constitutional preamble."""
    gemini_ctx = review_dir / "gemini-context.md"
    gpt_ctx = review_dir / "gpt-context.md"

    constitution, goals_path = find_constitution(project_dir)

    # Write constitutional preamble
    preamble = ""
    if constitution:
        preamble += "# PROJECT CONSTITUTION\nReview against these principles, not your own priors.\n\n"
        preamble += constitution + "\n\n"
    if goals_path:
        preamble += "# PROJECT GOALS\n\n"
        preamble += Path(goals_path).read_text() + "\n\n"

    if context_file:
        # Narrow review — same content for both
        content = context_file.read_text()
        gemini_ctx.write_text(preamble + content)
        gpt_ctx.write_text(preamble + content)
    elif broad_view:
        # Broad review — use .context/ views
        ctx_dir = project_dir / ".context"
        gemini_view = ctx_dir / f"{broad_view}.xml"
        gpt_view = ctx_dir / "signatures.xml"

        if not gemini_view.exists():
            print(f"error: {gemini_view} not found", file=sys.stderr)
            sys.exit(1)
        if not gpt_view.exists():
            gpt_view = gemini_view  # Fall back to same view

        gemini_ctx.write_text(preamble + gemini_view.read_text())
        gpt_ctx.write_text(preamble + gpt_view.read_text())

    size_g = gemini_ctx.stat().st_size
    size_p = gpt_ctx.stat().st_size
    if size_g > 15_000 or size_p > 15_000:
        print(
            f"warning: context size (gemini={size_g}, gpt={size_p}) > 15KB — consider summarizing",
            file=sys.stderr,
        )

    return gemini_ctx, gpt_ctx


def dispatch(
    review_dir: Path,
    gemini_ctx: Path,
    gpt_ctx: Path,
    question: str,
    has_constitution: bool,
) -> dict:
    """Fire both llmx processes in parallel, wait, return results."""
    # Clean env to avoid nested session detection
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CLAUDECODE", "CLAUDE_SESSION_ID")
    }

    today = date.today().isoformat()

    const_gemini = (
        "Where does the reviewed work violate or neglect stated principles? Which principles are well-served?"
        if has_constitution
        else "No constitution provided — assess internal consistency only."
    )
    const_gpt = (
        "For each constitutional principle: coverage score (0-100%), specific gaps, suggested fixes."
        if has_constitution
        else "No constitution provided — assess internal logical consistency."
    )

    gemini_prompt = GEMINI_PROMPT.format(
        date=today, question=question, constitution_instruction=const_gemini
    )
    gpt_prompt = GPT_PROMPT.format(
        date=today, question=question, constitution_instruction=const_gpt
    )

    gemini_out = review_dir / "gemini-output.md"
    gpt_out = review_dir / "gpt-output.md"

    # Gemini: --stream required (hangs without it on thinking models with -f)
    gemini_cmd = [
        "llmx", "chat",
        "-m", GEMINI_MODEL,
        "--stream", "--timeout", "300",
        "-f", str(gemini_ctx),
        "-o", str(gemini_out),
        gemini_prompt,
    ]

    # GPT: --stream + --reasoning-effort high + long timeout
    gpt_cmd = [
        "llmx", "chat",
        "-m", GPT_MODEL,
        "--stream", "--reasoning-effort", "high",
        "--timeout", "600", "--max-tokens", "16384",
        "-f", str(gpt_ctx),
        "-o", str(gpt_out),
        gpt_prompt,
    ]

    t0 = time.time()

    gemini_proc = subprocess.Popen(
        gemini_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    gpt_proc = subprocess.Popen(
        gpt_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Wait for both
    gemini_rc = gemini_proc.wait()
    gpt_rc = gpt_proc.wait()
    elapsed = time.time() - t0

    gemini_stderr = (gemini_proc.stderr.read().decode(errors="replace").strip()
                      if gemini_proc.stderr else "")
    gpt_stderr = (gpt_proc.stderr.read().decode(errors="replace").strip()
                  if gpt_proc.stderr else "")

    result = {
        "review_dir": str(review_dir),
        "elapsed_seconds": round(elapsed, 1),
        "gemini": {
            "exit_code": gemini_rc,
            "output": str(gemini_out),
            "size": gemini_out.stat().st_size if gemini_out.exists() else 0,
        },
        "gpt": {
            "exit_code": gpt_rc,
            "output": str(gpt_out),
            "size": gpt_out.stat().st_size if gpt_out.exists() else 0,
        },
    }

    # Surface errors
    if gemini_rc != 0:
        result["gemini"]["stderr"] = gemini_stderr[-500:] if gemini_stderr else ""
    if gpt_rc != 0:
        result["gpt"]["stderr"] = gpt_stderr[-500:] if gpt_stderr else ""

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Model-review dispatch: context assembly + parallel llmx + output collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--context", type=Path, help="Context file for narrow review")
    group.add_argument("--broad", metavar="VIEW", help=".context/ view name for broad review (src, full, infra, docs)")
    parser.add_argument("--topic", required=True, help="Short topic label (used in output dir name)")
    parser.add_argument("--project", type=Path, help="Project dir for constitution discovery (default: cwd)")
    parser.add_argument("question", nargs="?", default="Review this for logical gaps, missed edge cases, and constitutional alignment.",
                        help="Review question for both models")

    args = parser.parse_args()

    project_dir = args.project or Path.cwd()
    if not project_dir.is_dir():
        print(f"error: project dir {project_dir} not found", file=sys.stderr)
        return 1

    if args.context and not args.context.exists():
        print(f"error: context file {args.context} not found", file=sys.stderr)
        return 1

    # Create output directory
    slug = slugify(args.topic)
    hex_id = os.urandom(3).hex()
    review_dir = Path(f".model-review/{date.today().isoformat()}-{slug}-{hex_id}")
    review_dir.mkdir(parents=True, exist_ok=True)

    # Assemble context
    gemini_ctx, gpt_ctx = build_context(
        review_dir, project_dir, args.context, args.broad
    )

    constitution, _ = find_constitution(project_dir)

    # Dispatch and wait
    result = dispatch(review_dir, gemini_ctx, gpt_ctx, args.question, bool(constitution))

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
