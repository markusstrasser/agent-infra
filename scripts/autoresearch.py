#!/usr/bin/env python3
"""Autoresearch — evolutionary code search with LLM-as-mutator.

Adapted from karpathy/autoresearch. Runs an autonomous loop:
  1. LLM edits code in a sandboxed worktree
  2. Deterministic eval runs
  3. Keep (metric improved) or discard (git reset)
  4. Repeat

Usage:
    autoresearch.py run --config experiments/foo/config.json [--tag mar8] [--max-experiments 50]
    autoresearch.py results --config experiments/foo/config.json [--last 20] [--status keep]
    autoresearch.py progress --config experiments/foo/config.json  # ASCII progress chart
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_MAX_EXPERIMENTS = 200
DEFAULT_STALL_THRESHOLD = 3  # consecutive discards with similar diffs
LEARNINGS_UPDATE_INTERVAL = 10  # summarize every N experiments
MAX_RESULTS_IN_PROMPT = 30  # last N results shown to agent
MAX_KEPT_DIFFS_IN_PROMPT = 3  # last N kept diffs shown to agent


def load_config(path: str) -> dict:
    """Load and validate experiment config."""
    with open(path) as f:
        cfg = json.load(f)

    required = ["eval_command", "metric_name", "metric_direction", "editable_files"]
    for key in required:
        if key not in cfg:
            print(f"ERROR: config missing required key: {key}", file=sys.stderr)
            sys.exit(1)

    cfg.setdefault("type", "autoresearch")
    cfg.setdefault("time_budget_seconds", 300)
    cfg.setdefault("readonly_context", [])
    cfg.setdefault("program_md", None)
    cfg.setdefault("holdout_eval_command", None)
    cfg.setdefault("holdout_every_k_keeps", 5)
    cfg.setdefault("model", "sonnet")
    cfg.setdefault("max_budget_usd", 2.0)
    cfg.setdefault("max_turns", 10)
    return cfg


# ---------------------------------------------------------------------------
# Worktree management
# ---------------------------------------------------------------------------

def setup_worktree(repo_root: Path, tag: str) -> Path:
    """Create a disposable git worktree for the experiment run."""
    branch = f"autoresearch/{tag}"
    worktree_path = repo_root / ".autoresearch-worktrees" / tag

    # Clean up stale worktree if it exists
    if worktree_path.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=repo_root, capture_output=True,
        )

    # Create branch if it doesn't exist
    result = subprocess.run(
        ["git", "branch", "--list", branch],
        cwd=repo_root, capture_output=True, text=True,
    )
    if not result.stdout.strip():
        subprocess.run(
            ["git", "branch", branch],
            cwd=repo_root, capture_output=True, check=True,
        )

    # Create worktree
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "worktree", "add", str(worktree_path), branch],
        cwd=repo_root, capture_output=True, check=True,
    )

    return worktree_path


def cleanup_worktree(repo_root: Path, worktree_path: Path):
    """Remove the worktree."""
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_path)],
        cwd=repo_root, capture_output=True,
    )


# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------

def git_diff(worktree: Path) -> str:
    """Get the current uncommitted diff."""
    result = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=worktree, capture_output=True, text=True,
    )
    return result.stdout


def git_commit(worktree: Path, message: str) -> str:
    """Commit all changes, return short hash."""
    subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", message, "--allow-empty"],
        cwd=worktree, capture_output=True, check=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=worktree, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def git_reset_hard(worktree: Path):
    """Reset to previous commit (discard last experiment)."""
    subprocess.run(
        ["git", "reset", "--hard", "HEAD~1"],
        cwd=worktree, capture_output=True, check=True,
    )


def git_has_changes(worktree: Path) -> bool:
    """Check if there are uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree, capture_output=True, text=True,
    )
    return bool(result.stdout.strip())


# ---------------------------------------------------------------------------
# Experiment log (Phase 0: Telemetry)
# ---------------------------------------------------------------------------

class ExperimentLog:
    """Append-only experiment ledger. JSONL + TSV views."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = log_dir / "experiments.jsonl"
        self.tsv_path = log_dir / "results.tsv"
        self.patches_dir = log_dir / "patches"
        self.patches_dir.mkdir(exist_ok=True)

        # Initialize TSV with header if new
        if not self.tsv_path.exists():
            self.tsv_path.write_text(
                "experiment\tcommit\tmetric\tmemory\tstatus\tdescription\n"
            )

    def log_experiment(self, entry: dict):
        """Log a single experiment result."""
        # JSONL (full detail)
        with open(self.jsonl_path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

        # TSV (human-readable summary)
        with open(self.tsv_path, "a") as f:
            f.write(
                f"{entry['experiment_id']}\t"
                f"{entry.get('commit', 'n/a')}\t"
                f"{(entry.get('metric_value') or 0.0):.6f}\t"
                f"{entry.get('cost_usd', 0.0):.4f}\t"
                f"{entry['status']}\t"
                f"{entry.get('description', '')}\n"
            )

    def save_patch(self, experiment_id: int, diff_text: str, rationale: str = ""):
        """Archive a patch before potential git reset."""
        patch_path = self.patches_dir / f"{experiment_id:04d}.patch"
        with open(patch_path, "w") as f:
            if rationale:
                f.write(f"# Rationale: {rationale}\n")
            f.write(diff_text)

    def load_recent(self, n: int = 30) -> list[dict]:
        """Load last N experiment entries."""
        if not self.jsonl_path.exists():
            return []
        entries = []
        with open(self.jsonl_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries[-n:]

    def load_kept_diffs(self, n: int = 3) -> list[str]:
        """Load the last N patches from kept experiments."""
        entries = self.load_recent(100)
        kept = [e for e in entries if e["status"] == "keep"][-n:]
        diffs = []
        for e in kept:
            patch_path = self.patches_dir / f"{e['experiment_id']:04d}.patch"
            if patch_path.exists():
                diffs.append(patch_path.read_text())
        return diffs

    def count(self) -> int:
        if not self.jsonl_path.exists():
            return 0
        with open(self.jsonl_path) as f:
            return sum(1 for line in f if line.strip())

    def best_metric(self, direction: str) -> float | None:
        entries = self.load_recent(9999)
        kept = [e for e in entries if e["status"] == "keep" and e.get("metric_value") is not None]
        if not kept:
            return None
        values = [e["metric_value"] for e in kept]
        return min(values) if direction == "lower" else max(values)

    def total_cost(self) -> float:
        entries = self.load_recent(9999)
        return sum(e.get("cost_usd", 0.0) for e in entries)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def run_eval(worktree: Path, eval_command: str, metric_name: str,
             timeout: int = 600) -> tuple[float | None, str]:
    """Run eval command, extract metric. Returns (metric_value, raw_output)."""
    try:
        result = subprocess.run(
            eval_command,
            shell=True,
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr

        if result.returncode != 0:
            return None, f"CRASH (exit {result.returncode}):\n{output[-2000:]}"

        # Parse metric: look for "metric_name: value" or "metric_name=value"
        pattern = rf"^{re.escape(metric_name)}[:\s=]+([0-9.eE+-]+)"
        for line in output.split("\n"):
            m = re.match(pattern, line.strip())
            if m:
                return float(m.group(1)), output

        return None, f"METRIC NOT FOUND in output:\n{output[-2000:]}"

    except subprocess.TimeoutExpired:
        return None, f"TIMEOUT after {timeout}s"


# ---------------------------------------------------------------------------
# Mutator (LLM agent)
# ---------------------------------------------------------------------------

def build_prompt(config: dict, worktree: Path, log: ExperimentLog) -> str:
    """Construct the prompt for the LLM mutator."""
    parts = []

    # Program instructions
    program_md = config.get("program_md")
    if program_md:
        program_path = worktree / program_md
        if program_path.exists():
            parts.append(f"# Instructions\n\n{program_path.read_text()}")

    # Current state
    parts.append("# Current State")
    parts.append(f"Metric: {config['metric_name']} (goal: {config['metric_direction']})")
    best = log.best_metric(config["metric_direction"])
    if best is not None:
        parts.append(f"Current best: {best:.6f}")
    parts.append(f"Experiments so far: {log.count()}")

    # Editable files — show current content
    parts.append("\n# Editable Files (you may ONLY modify these)")
    for f in config["editable_files"]:
        fpath = worktree / f
        if fpath.exists():
            parts.append(f"\n## {f}\n```\n{fpath.read_text()}\n```")

    # Read-only context files
    if config["readonly_context"]:
        parts.append("\n# Read-Only Context (do NOT modify)")
        for f in config["readonly_context"]:
            fpath = worktree / f
            if fpath.exists():
                content = fpath.read_text()
                if len(content) > 10000:
                    content = content[:10000] + "\n... (truncated)"
                parts.append(f"\n## {f}\n```\n{content}\n```")

    # LEARNINGS.md
    learnings_path = worktree / "LEARNINGS.md"
    if learnings_path.exists():
        parts.append(f"\n# What Has Been Tried (avoid repeating)\n\n{learnings_path.read_text()}")

    # Recent results
    recent = log.load_recent(MAX_RESULTS_IN_PROMPT)
    if recent:
        parts.append("\n# Recent Experiment Results")
        parts.append("| # | metric | status | description |")
        parts.append("|---|--------|--------|-------------|")
        for e in recent:
            mv = f"{e.get('metric_value', 0):.6f}" if e.get("metric_value") is not None else "crash"
            parts.append(f"| {e['experiment_id']} | {mv} | {e['status']} | {e.get('description', '')} |")

    # Last N kept diffs
    kept_diffs = log.load_kept_diffs(MAX_KEPT_DIFFS_IN_PROMPT)
    if kept_diffs:
        parts.append("\n# Recent Successful Changes (diffs that improved the metric)")
        for i, d in enumerate(kept_diffs, 1):
            parts.append(f"\n## Kept diff #{i}\n```diff\n{d}\n```")

    # Task — instruction varies by engine type
    engine = config.get("engine", "claude")
    if engine == "llmx":
        # Non-agentic: model must output the complete file
        edit_instruction = (
            "Output the COMPLETE new version of each editable file in a fenced code block.\n"
            "Use the format:\n"
            "```python filename.py\n"
            "... complete file content ...\n"
            "```\n"
            "Before the code block, write a ONE LINE summary of what you changed and why."
        )
    else:
        edit_instruction = "Edit the file(s) now."

    parts.append(textwrap.dedent(f"""
    # Your Task

    Propose ONE change to improve {config['metric_name']} ({config['metric_direction']} is better).

    Rules:
    - Only modify files listed under "Editable Files"
    - Make a single focused change — not multiple unrelated changes
    - Explain your reasoning briefly in a comment or commit message
    - If recent experiments show a pattern of failures, try something radically different
    - Simpler is better: removing code for equal results is a win
    - Do NOT modify any read-only files

    {edit_instruction}
    """))

    return "\n".join(parts)


def _run_mutator_claude(config: dict, worktree: Path, prompt: str) -> tuple[str, float]:
    """Run claude to edit files. Returns (description, cost_usd)."""
    cmd = [
        "claude", "-p", prompt,
        "--dangerously-skip-permissions",
        "--model", config.get("model", "sonnet"),
        "--max-turns", str(config.get("max_turns", 10)),
        "--output-format", "json",
    ]

    # Must unset CLAUDECODE to avoid nested session detection
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_SESSION_ID")}

    try:
        result = subprocess.run(
            cmd,
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=config.get("mutator_timeout", 300),
            env=env,
        )

        # Parse JSON output — claude -p --output-format json returns an array:
        # [{type: "system", ...}, {type: "assistant", ...}, {type: "result", ...}]
        description = ""
        cost = 0.0

        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)

                # Handle array format (claude CLI JSON output)
                if isinstance(output, list):
                    for entry in output:
                        if not isinstance(entry, dict):
                            continue
                        if entry.get("type") == "result":
                            cost = entry.get("total_cost_usd", 0.0)
                            text = entry.get("result", "")
                            is_error = entry.get("is_error", False)
                            if is_error:
                                return f"ERROR: {text[:100]}", cost
                            if text:
                                description = text.split("\n")[0][:120]
                        elif entry.get("type") == "assistant":
                            msg = entry.get("message", {})
                            err = entry.get("error")
                            if err:
                                content = msg.get("content", [])
                                err_text = ""
                                for block in content:
                                    if isinstance(block, dict) and block.get("text"):
                                        err_text = block["text"]
                                return f"ERROR: {err}: {err_text[:80]}", 0.0

                # Handle dict format (older or different output)
                elif isinstance(output, dict):
                    cost = output.get("cost_usd", output.get("total_cost_usd", 0.0))
                    text = output.get("result", "")
                    if text:
                        description = text.split("\n")[0][:120]

            except json.JSONDecodeError:
                description = result.stdout.split("\n")[0][:120]

        if not description:
            description = "LLM edit (no description captured)"

        return description, cost

    except subprocess.TimeoutExpired:
        return "TIMEOUT: mutator took >5min", 0.0


def _run_mutator_codex(config: dict, worktree: Path, prompt: str) -> tuple[str, float]:
    """Run codex exec to edit files. Returns (description, cost_usd=0.0).

    Codex CLI uses subscription pricing (free). Output is plain text on stdout.
    Edits are applied directly to the worktree by Codex's agentic loop.
    """
    cmd = [
        "codex", "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        prompt,
    ]
    model = config.get("model")
    if model and model not in ("codex", "codex-cli"):
        cmd.extend(["-m", model])

    # Clean env to avoid nested session detection
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_SESSION_ID")}

    try:
        result = subprocess.run(
            cmd,
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=config.get("mutator_timeout", 300),
            env=env,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()[:200] if result.stderr else ""
            return f"ERROR: codex exit {result.returncode}: {stderr}", 0.0

        # Codex plain text output — take first line as description
        description = ""
        if result.stdout.strip():
            description = result.stdout.strip().split("\n")[-1][:120]

        return description or "Codex edit (no description)", 0.0

    except subprocess.TimeoutExpired:
        return "TIMEOUT: codex took >5min", 0.0


def _run_mutator_llmx(config: dict, worktree: Path, prompt: str) -> tuple[str, float]:
    """Run llmx to generate edited file content. Returns (description, cost_usd).

    Non-agentic: sends prompt (which includes file contents), model returns
    the complete new file in a code block, we parse and write it back.
    """
    import re

    model = config.get("model", "gemini-3.1-pro-preview")
    provider = config.get("provider", "google")
    timeout = config.get("mutator_timeout", 300)

    cmd = ["llmx", "-p", provider, "-m", model, prompt]

    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_SESSION_ID")}

    try:
        result = subprocess.run(
            cmd, cwd=worktree, capture_output=True, text=True,
            timeout=timeout, env=env,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()[:200] if result.stderr else ""
            return f"ERROR: llmx exit {result.returncode}: {stderr}", 0.0

        output = result.stdout.strip()
        if not output:
            return "ERROR: llmx returned empty output", 0.0

        # Extract code blocks: ```python [filename]\n...\n```
        # Pattern matches ```python optionally followed by a filename
        blocks = re.findall(
            r'```python(?:\s+(\S+))?\s*\n(.*?)```',
            output, re.DOTALL,
        )

        if not blocks:
            return "ERROR: no code block in llmx output", 0.0

        editable = config["editable_files"]

        for block_filename, block_content in blocks:
            # Match block to editable file
            target = None
            if block_filename:
                # Try exact match or basename match
                for ef in editable:
                    if block_filename == ef or block_filename == Path(ef).name:
                        target = ef
                        break
            if target is None and len(editable) == 1:
                target = editable[0]
            if target is None:
                continue

            target_path = worktree / target
            target_path.write_text(block_content)

        # Description: first non-empty line before the code block
        description = ""
        for line in output.split("\n"):
            line = line.strip()
            if line and not line.startswith("```") and not line.startswith("#"):
                description = line[:120]
                break

        return description or "llmx edit (no description)", 0.0

    except subprocess.TimeoutExpired:
        return f"TIMEOUT: llmx took >{timeout}s", 0.0


def run_mutator(config: dict, worktree: Path, prompt: str) -> tuple[str, float]:
    """Dispatch to the configured mutator engine."""
    engine = config.get("engine", "claude")
    if engine in ("codex", "codex-cli"):
        return _run_mutator_codex(config, worktree, prompt)
    if engine == "llmx":
        return _run_mutator_llmx(config, worktree, prompt)
    return _run_mutator_claude(config, worktree, prompt)


# ---------------------------------------------------------------------------
# LEARNINGS.md management
# ---------------------------------------------------------------------------

def update_learnings(worktree: Path, log: ExperimentLog, config: dict):
    """Summarize recent failures into LEARNINGS.md."""
    recent = log.load_recent(50)
    discards = [e for e in recent if e["status"] in ("discard", "crash")]

    if not discards:
        return

    learnings_path = worktree / "LEARNINGS.md"

    lines = ["# What Has Been Tried\n"]
    lines.append(f"_Auto-generated from {len(discards)} discarded/crashed experiments._\n")

    # Group by rough category (first few words of description)
    categories: dict[str, list] = {}
    for e in discards:
        desc = e.get("description", "unknown")
        # Use first 3 words as category key
        key = " ".join(desc.split()[:3]).lower()
        categories.setdefault(key, []).append(e)

    for key, entries in sorted(categories.items(), key=lambda x: -len(x[1])):
        lines.append(f"\n## {key} ({len(entries)} attempts)")
        for e in entries[-3:]:  # show last 3 per category
            mv = f"{e.get('metric_value', 0):.6f}" if e.get("metric_value") is not None else "crash"
            lines.append(f"- Exp #{e['experiment_id']}: {mv} — {e.get('description', '')}")

    learnings_path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Progress visualization
# ---------------------------------------------------------------------------

def print_progress(log: ExperimentLog, direction: str):
    """Print ASCII progress chart."""
    entries = log.load_recent(9999)
    if not entries:
        print("No experiments yet.")
        return

    kept = [e for e in entries if e["status"] == "keep" and e.get("metric_value") is not None]
    if not kept:
        print(f"Total experiments: {len(entries)}, no improvements yet.")
        return

    values = [e["metric_value"] for e in kept]
    best_val = min(values) if direction == "lower" else max(values)
    baseline = values[0] if values else 0

    print(f"\n{'='*60}")
    print(f"  Autoresearch Progress")
    print(f"{'='*60}")
    print(f"  Total experiments: {len(entries)}")
    print(f"  Kept:    {len(kept)}")
    print(f"  Discard: {sum(1 for e in entries if e['status'] == 'discard')}")
    print(f"  Crash:   {sum(1 for e in entries if e['status'] == 'crash')}")
    print(f"  Baseline: {baseline:.6f}")
    print(f"  Best:     {best_val:.6f}")
    if baseline != 0:
        improvement = abs(best_val - baseline) / abs(baseline) * 100
        print(f"  Improvement: {improvement:.2f}%")
    print(f"  Total cost: ${log.total_cost():.2f}")
    print(f"{'='*60}")

    # Running best chart
    print(f"\n  Running best ({direction} is better):")
    running_best = []
    current_best = baseline
    for e in entries:
        if e["status"] == "keep" and e.get("metric_value") is not None:
            if direction == "lower":
                current_best = min(current_best, e["metric_value"])
            else:
                current_best = max(current_best, e["metric_value"])
        running_best.append(current_best)

    # Simple ASCII chart (last 50 experiments)
    display = running_best[-50:]
    if len(display) > 1:
        lo, hi = min(display), max(display)
        spread = hi - lo if hi != lo else 1
        width = 40
        for i, v in enumerate(display):
            bar_pos = int((v - lo) / spread * width)
            marker = "█" * bar_pos
            exp_num = len(entries) - len(display) + i
            print(f"  {exp_num:4d} |{marker:<{width}}| {v:.6f}")

    print()

    # Top improvements
    print("  Top improvements:")
    for e in kept[-5:]:
        print(f"    #{e['experiment_id']:4d}: {e['metric_value']:.6f} — {e.get('description', '')[:60]}")
    print()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_experiment_loop(config: dict, config_path: Path, tag: str,
                        max_experiments: int = DEFAULT_MAX_EXPERIMENTS):
    """Run the autoresearch loop."""
    # Resolve paths relative to config file
    config_dir = config_path.parent.resolve()
    repo_root = config_dir

    # Find actual git root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=config_dir, capture_output=True, text=True,
    )
    if result.returncode == 0:
        repo_root = Path(result.stdout.strip())

    log_dir = config_dir / "runs" / tag
    log = ExperimentLog(log_dir)

    print(f"[autoresearch] Config: {config_path}")
    print(f"[autoresearch] Tag: {tag}")
    print(f"[autoresearch] Log dir: {log_dir}")
    print(f"[autoresearch] Metric: {config['metric_name']} ({config['metric_direction']})")
    print(f"[autoresearch] Editable: {config['editable_files']}")
    print(f"[autoresearch] Max experiments: {max_experiments}")
    print()

    # Setup worktree
    print("[autoresearch] Setting up worktree...")
    worktree = setup_worktree(repo_root, tag)
    print(f"[autoresearch] Worktree: {worktree}")

    experiment_id = log.count()
    consecutive_discards = 0
    keeps_since_holdout = 0

    try:
        while experiment_id < max_experiments:
            experiment_id += 1
            t0 = time.time()
            print(f"\n{'='*60}")
            print(f"[autoresearch] Experiment #{experiment_id}")
            print(f"{'='*60}")

            # 1. Build prompt
            prompt = build_prompt(config, worktree, log)

            # 2. Run mutator (LLM edits code)
            print("[autoresearch] Running mutator...")
            description, cost = run_mutator(config, worktree, prompt)
            print(f"[autoresearch] Mutator done: {description[:80]}")

            # 2b. Check for mutator errors (billing, model errors, etc.)
            if description.startswith("ERROR:"):
                print(f"[autoresearch] MUTATOR ERROR: {description}")
                log.log_experiment({
                    "experiment_id": experiment_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "description": description,
                    "cost_usd": cost,
                })
                # Fatal errors — don't keep looping
                if "billing" in description.lower() or "credit" in description.lower():
                    print("[autoresearch] FATAL: billing error, stopping loop")
                    break
                consecutive_discards += 1
                continue

            # 3. Check if anything changed
            if not git_has_changes(worktree):
                print("[autoresearch] No changes made, skipping eval")
                log.log_experiment({
                    "experiment_id": experiment_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "no_change",
                    "description": description,
                    "cost_usd": cost,
                })
                consecutive_discards += 1
                continue

            # 4. Archive patch before commit
            diff = git_diff(worktree)
            log.save_patch(experiment_id, diff, rationale=description)

            # 5. Commit
            commit_msg = f"experiment #{experiment_id}: {description[:72]}"
            commit_hash = git_commit(worktree, commit_msg)
            print(f"[autoresearch] Committed: {commit_hash}")

            # 6. Run eval
            print(f"[autoresearch] Running eval: {config['eval_command']}")
            metric_value, eval_output = run_eval(
                worktree, config["eval_command"], config["metric_name"],
                timeout=config["time_budget_seconds"] + 60,  # budget + startup margin
            )

            elapsed = time.time() - t0

            # 7. Decide keep/discard
            if metric_value is None:
                status = "crash"
                print(f"[autoresearch] CRASH: {eval_output[:200]}")
                git_reset_hard(worktree)
                consecutive_discards += 1
            else:
                best = log.best_metric(config["metric_direction"])
                improved = False
                if best is None:
                    improved = True  # first successful experiment
                elif config["metric_direction"] == "lower":
                    improved = metric_value < best
                else:
                    improved = metric_value > best

                if improved:
                    status = "keep"
                    keeps_since_holdout += 1
                    consecutive_discards = 0
                    print(f"[autoresearch] ✓ KEEP: {config['metric_name']}={metric_value:.6f} "
                          f"(prev best: {best})")
                else:
                    status = "discard"
                    consecutive_discards += 1
                    print(f"[autoresearch] ✗ DISCARD: {config['metric_name']}={metric_value:.6f} "
                          f"(best: {best})")
                    git_reset_hard(worktree)

            # 8. Log
            entry = {
                "experiment_id": experiment_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "commit": commit_hash if status == "keep" else None,
                "metric_value": metric_value,
                "status": status,
                "description": description,
                "cost_usd": cost,
                "elapsed_seconds": round(elapsed, 1),
                "eval_output_tail": eval_output[-500:] if eval_output else None,
                "patch_hash": hashlib.sha256(diff.encode()).hexdigest()[:12],
            }
            log.log_experiment(entry)

            # 9. Update LEARNINGS.md periodically
            if experiment_id % LEARNINGS_UPDATE_INTERVAL == 0:
                print("[autoresearch] Updating LEARNINGS.md...")
                update_learnings(worktree, log, config)

            # 10. Stall detection
            if consecutive_discards >= DEFAULT_STALL_THRESHOLD:
                print(f"[autoresearch] STALL: {consecutive_discards} consecutive discards")
                # Will naturally inject "try something radically different" via the prompt
                # (recent results table shows the streak)

            # 11. Holdout eval
            if (status == "keep"
                and config.get("holdout_eval_command")
                and keeps_since_holdout >= config.get("holdout_every_k_keeps", 5)):
                print("[autoresearch] Running holdout evaluation...")
                holdout_val, holdout_out = run_eval(
                    worktree, config["holdout_eval_command"], config["metric_name"],
                    timeout=config["time_budget_seconds"] * 2,
                )
                keeps_since_holdout = 0
                if holdout_val is not None:
                    print(f"[autoresearch] Holdout {config['metric_name']}={holdout_val:.6f}")

            # Progress summary every 10 experiments
            if experiment_id % 10 == 0:
                print_progress(log, config["metric_direction"])

    except KeyboardInterrupt:
        print("\n[autoresearch] Interrupted by user")
    finally:
        print(f"\n[autoresearch] Final results after {experiment_id} experiments:")
        print_progress(log, config["metric_direction"])
        print(f"[autoresearch] Worktree preserved at: {worktree}")
        print(f"[autoresearch] Results: {log.tsv_path}")
        print(f"[autoresearch] To merge best to main:")
        print(f"  cd {repo_root} && git merge autoresearch/{tag}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_run(args):
    config = load_config(args.config)
    tag = args.tag or datetime.now().strftime("%b%d").lower()
    run_experiment_loop(
        config,
        Path(args.config),
        tag,
        max_experiments=args.max_experiments,
    )


def cmd_results(args):
    config = load_config(args.config)
    config_dir = Path(args.config).parent.resolve()

    # Find most recent run
    runs_dir = config_dir / "runs"
    if not runs_dir.exists():
        print("No runs found.")
        return

    tag = args.tag
    if not tag:
        # Use most recent
        tags = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if not tags:
            print("No runs found.")
            return
        tag = tags[0].name

    log = ExperimentLog(runs_dir / tag)
    entries = log.load_recent(args.last)

    if args.status:
        entries = [e for e in entries if e["status"] == args.status]

    print(f"Results for {tag} (last {args.last}, filter={args.status or 'all'}):\n")
    print(f"{'#':>4}  {'metric':>10}  {'cost':>7}  {'status':<8}  description")
    print("-" * 80)
    for e in entries:
        mv = f"{e.get('metric_value', 0):.6f}" if e.get("metric_value") is not None else "  crash"
        cost = f"${e.get('cost_usd', 0):.3f}"
        print(f"{e['experiment_id']:4d}  {mv}  {cost:>7}  {e['status']:<8}  {e.get('description', '')[:40]}")


def cmd_progress(args):
    config = load_config(args.config)
    config_dir = Path(args.config).parent.resolve()
    runs_dir = config_dir / "runs"
    if not runs_dir.exists():
        print("No runs found.")
        return

    tag = args.tag
    if not tag:
        tags = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if not tags:
            print("No runs found.")
            return
        tag = tags[0].name

    log = ExperimentLog(runs_dir / tag)
    print_progress(log, config["metric_direction"])


def main():
    parser = argparse.ArgumentParser(
        description="Autoresearch — evolutionary code search with LLM-as-mutator"
    )
    sub = parser.add_subparsers(dest="command")

    # run
    p_run = sub.add_parser("run", help="Run the experiment loop")
    p_run.add_argument("--config", required=True, help="Path to config JSON")
    p_run.add_argument("--tag", help="Run tag (default: date-based)")
    p_run.add_argument("--max-experiments", type=int, default=DEFAULT_MAX_EXPERIMENTS)
    p_run.set_defaults(func=cmd_run)

    # results
    p_res = sub.add_parser("results", help="Show experiment results")
    p_res.add_argument("--config", required=True)
    p_res.add_argument("--tag", help="Run tag")
    p_res.add_argument("--last", type=int, default=30)
    p_res.add_argument("--status", help="Filter by status (keep/discard/crash)")
    p_res.set_defaults(func=cmd_results)

    # progress
    p_prog = sub.add_parser("progress", help="Show progress chart")
    p_prog.add_argument("--config", required=True)
    p_prog.add_argument("--tag", help="Run tag")
    p_prog.set_defaults(func=cmd_progress)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
