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
For each proposed change: expected impact, maintenance burden, composability, risk. Rank by value adjusted for ongoing cost. Creation effort is irrelevant (agents build everything). Only ongoing drag matters: maintenance, supervision, complexity budget.

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
4. Maintenance burden and complexity cost (not implementation effort — agents build everything)

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

GEMINI_PRO_MODEL = "gemini-3.1-pro-preview"
GEMINI_FLASH_MODEL = "gemini-3-flash-preview"
GEMINI_RATE_LIMIT_MARKERS = (
    "503",
    "rate limit",
    "rate-limit",
    "resource_exhausted",
    "overloaded",
    "429",
)


def slugify(text: str, max_len: int = 40) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:max_len]


def build_llmx_cmd(
    model: str,
    flags: list[str],
    context_path: Path,
    output_path: Path,
    prompt: str,
) -> list[str]:
    return [
        "llmx", "chat",
        "-m", model,
        *flags,
        "-f", str(context_path),
        "-o", str(output_path),
        prompt,
    ]


def read_process_stderr(proc: subprocess.Popen) -> str:
    _, stderr = proc.communicate()
    return stderr.decode(errors="replace").strip() if stderr else ""


def is_gemini_rate_limit_failure(model: str, exit_code: int, stderr: str, output_size: int) -> bool:
    if model != GEMINI_PRO_MODEL:
        return False
    if exit_code == 0 and output_size > 0:
        return False
    stderr_lower = stderr.lower()
    return exit_code == 3 or any(marker in stderr_lower for marker in GEMINI_RATE_LIMIT_MARKERS)


def rerun_axis_with_flash(
    axis: str,
    axis_def: dict[str, object],
    review_dir: Path,
    ctx_file: Path,
    prompt: str,
    env: dict[str, str],
) -> tuple[int, str, Path]:
    out_path = review_dir / f"{axis}-output.md"
    cmd = build_llmx_cmd(
        GEMINI_FLASH_MODEL,
        list(axis_def["flags"]),
        ctx_file,
        out_path,
        prompt,
    )
    print(
        f"warning: {axis} hit Gemini Pro rate limits; retrying once with Gemini Flash",
        file=sys.stderr,
    )
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderr = read_process_stderr(proc)
    return proc.returncode, stderr, out_path


def find_constitution(project_dir: Path) -> tuple[str, str | None]:
    """Find constitution text and GOALS.md path in project dir."""
    constitution = ""
    goals_path = None

    # Check .claude/rules/constitution.md first (genomics, projects with standalone file)
    rules_const = project_dir / ".claude" / "rules" / "constitution.md"
    if rules_const.exists():
        constitution = rules_const.read_text().strip()

    # Fall back to CLAUDE.md <constitution> tag or ## Constitution heading
    if not constitution:
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

    # Agent economics framing — always included so reviewers don't
    # recommend trading quality for dev time (which is ~free with agents)
    preamble += "# DEVELOPMENT CONTEXT\n"
    preamble += "All code, plans, and features in this project are developed by AI agents, not human developers. "
    preamble += "Dev creation time is effectively zero. Therefore:\n"
    preamble += "- NEVER recommend trading stability, composability, or robustness for dev time savings\n"
    preamble += "- NEVER recommend simpler/hacky approaches because they're 'faster to implement'\n"
    preamble += "- Cost-benefit analysis should filter on: maintenance burden, supervision cost, complexity budget, blast radius — not creation effort\n"
    preamble += "- 'Effort to implement' is not a meaningful cost dimension — only ongoing drag matters\n\n"

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
    prompts = {}
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
        prompts[axis] = prompt

        # Auto-escalate Gemini Pro to API transport for large context.
        # CLI transport (free) times out on thinking models above ~15KB context
        # within the 300s window. --stream forces API transport (paid but reliable).
        axis_flags = list(axis_def["flags"])
        ctx_size = ctx_files[axis].stat().st_size if ctx_files[axis].exists() else 0
        model_name = str(axis_def["model"])
        if model_name == GEMINI_PRO_MODEL and ctx_size > 15_000 and "--stream" not in axis_flags:
            axis_flags.append("--stream")

        cmd = build_llmx_cmd(
            model_name,
            axis_flags,
            ctx_files[axis],
            out_path,
            prompt,
        )

        procs[axis] = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    # Wait for all
    results = {"review_dir": str(review_dir), "axes": axis_names, "queries": len(axis_names)}
    gemini_rate_limited = False
    for axis in axis_names:
        proc = procs[axis]
        stderr = read_process_stderr(proc)
        rc = proc.returncode
        out_path = outputs[axis]
        requested_model = str(AXES[axis]["model"])
        output_size = out_path.stat().st_size if out_path.exists() else 0
        transient_gemini_failure = is_gemini_rate_limit_failure(
            requested_model,
            rc,
            stderr,
            output_size,
        )
        should_fallback = requested_model == GEMINI_PRO_MODEL and (
            transient_gemini_failure
            or (gemini_rate_limited and (rc != 0 or output_size == 0))
        )
        if transient_gemini_failure:
            gemini_rate_limited = True

        entry = {
            "label": AXES[axis]["label"],
            "requested_model": requested_model,
            "model": requested_model,
            "exit_code": rc,
            "output": str(out_path),
            "size": output_size,
        }
        if should_fallback:
            entry["fallback_from"] = requested_model
            entry["fallback_reason"] = (
                "gemini_rate_limit" if transient_gemini_failure else "gemini_session_rate_limit"
            )
            entry["initial_exit_code"] = rc
            entry["initial_size"] = output_size
            if stderr:
                entry["initial_stderr"] = stderr[-500:]

            rc, stderr, out_path = rerun_axis_with_flash(
                axis,
                AXES[axis],
                review_dir,
                ctx_files[axis],
                prompts[axis],
                env,
            )
            output_size = out_path.stat().st_size if out_path.exists() else 0
            entry["model"] = GEMINI_FLASH_MODEL
            entry["exit_code"] = rc
            entry["size"] = output_size
        if rc != 0:
            entry["stderr"] = stderr[-500:] if stderr else ""

        results[axis] = entry

    results["elapsed_seconds"] = round(time.time() - t0, 1)
    return results


EXTRACTION_PROMPT = (
    "Extract every discrete recommendation, finding, or claimed bug as a numbered list. "
    "One item per line. Include the specific file/code/concept referenced. "
    "SKIP confirmatory observations that merely describe existing correct behavior "
    "(e.g. 'X correctly groups Y', 'Z is well-designed'). "
    "Only extract items that propose a change, flag a problem, or claim something is wrong/missing."
)


def extract_claims(
    review_dir: Path,
    dispatch_result: dict,
) -> str | None:
    """Cross-family extraction: Flash extracts GPT outputs, GPT-Instant extracts Gemini outputs.

    Returns path to disposition.md, or None if no outputs to extract.
    """
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CLAUDECODE", "CLAUDE_SESSION_ID")
    }

    extraction_procs: dict[str, tuple[subprocess.Popen, Path]] = {}
    skip_keys = {"review_dir", "axes", "queries", "elapsed_seconds"}

    for axis, info in dispatch_result.items():
        if axis in skip_keys or not isinstance(info, dict):
            continue
        if info.get("size", 0) == 0:
            continue

        output_path = Path(info["output"])
        if not output_path.exists():
            continue

        extraction_path = review_dir / f"{axis}-extraction.md"
        model = info.get("model", "")

        # Cross-family: Gemini outputs → GPT extraction, GPT outputs → Gemini Flash extraction
        if "gemini" in model.lower():
            extract_model = "gpt-5.3-chat-latest"
            extract_flags = ["--stream", "--timeout", "120"]
        else:
            extract_model = "gemini-3-flash-preview"
            extract_flags = ["--timeout", "120"]

        cmd = build_llmx_cmd(
            extract_model, extract_flags, output_path, extraction_path, EXTRACTION_PROMPT,
        )
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        extraction_procs[axis] = (proc, extraction_path)

    if not extraction_procs:
        return None

    print(
        f"Extracting claims from {len(extraction_procs)} outputs...",
        file=sys.stderr,
    )

    # Wait for all extractions and merge
    extractions: list[str] = []
    for axis, (proc, path) in extraction_procs.items():
        stderr = read_process_stderr(proc)
        label = dispatch_result[axis].get("label", axis)
        if proc.returncode != 0:
            print(f"warning: extraction for {axis} failed (exit {proc.returncode})", file=sys.stderr)
            if stderr:
                print(f"  stderr: {stderr[:200]}", file=sys.stderr)
            continue
        if path.exists() and path.stat().st_size > 0:
            extractions.append(f"## {label}\n\n{path.read_text().strip()}")

    if not extractions:
        return None

    disposition = review_dir / "disposition.md"
    disposition.write_text(
        f"# Extracted Claims — {date.today().isoformat()}\n\n" + "\n\n---\n\n".join(extractions) + "\n"
    )
    return str(disposition)


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
        "--extract", action="store_true",
        help="After dispatch, auto-extract claims from each output into disposition.md",
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

    # Optional extraction phase
    if args.extract:
        disposition_path = extract_claims(review_dir, result)
        if disposition_path:
            result["disposition"] = disposition_path
            print(f"Disposition written to {disposition_path}", file=sys.stderr)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
