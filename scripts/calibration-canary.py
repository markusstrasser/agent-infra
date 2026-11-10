#!/usr/bin/env python3
"""Run canary set for answer-confidence calibration.

35+ canaries across 10+ categories. Measures accuracy, Brier score,
and consistency across multiple runs.

Modes:
  --mode verbalized  (default) Ask for boolean + confidence, compute Brier score
  --mode sampling    Run N times, measure answer frequency (no confidence prompt)
  --mode compare     Run both modes, output comparison table
  --analysis         Compute per-category correlation matrix (discriminant validity)
  --difficulty easy|hard|all  Filter by difficulty level
  --model a,b,c      One or more models (comma-separated); default claude-haiku-5-5
  --backend llmx     (default) `llmx chat --subscription` — Claude/Codex plan, $0
  --backend anthropic --allow-metered   Metered Anthropic SDK; needs ANTHROPIC_API_KEY
  --effort LEVEL     Pass an explicit thinking effort (default: the model's own)
  --workers N        Parallel calls (default 4; Opus reviews share a plan window)

Transport failures are not calibration data: any failed call prints [DEGRADED]
and the run exits 2 without logging a metric. Token cost per model is read back
from ~/.claude/llmx-usage.jsonl via the LLMX_CALLER tag (eval-token-costs rule).

2026-11-10 repair: the llmx path passed --stream and --max-tokens, both refused
by the subscription CLI transport, so every call failed and was silently skipped;
the default anthropic path needed ANTHROPIC_API_KEY, which no shell exports. The
rotation never produced a run.
"""

import json
import os
import re
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import METRICS_FILE, log_metric

CANARIES_PATH = Path(__file__).resolve().parent.parent / "schemas" / "calibration_canaries.json"


def load_canaries(limit: int | None = None) -> list[dict]:
    with open(CANARIES_PATH) as f:
        canaries = json.load(f)
    if limit is not None:
        return canaries[:limit]
    return canaries


# ---------------------------------------------------------------------------
# llmx backend — shells out to llmx CLI for multi-vendor model support
# ---------------------------------------------------------------------------

USAGE_LOG = Path.home() / ".claude" / "llmx-usage.jsonl"
RUN_TAG = f"calibration-canary:{uuid.uuid4().hex[:8]}"
EFFORT: str | None = None


class TransportError(RuntimeError):
    """A call that never produced a model answer. Not a calibration result."""


def llmx_chat(model: str, prompt: str) -> str:
    """Call `llmx chat --subscription` and return stdout. Raises TransportError.

    No --max-tokens/--stream (the subscription CLI transport refuses both) and no
    temperature (claude-cli ignores it; current Claude models reject it on the API).
    """
    cmd = ["llmx", "chat", "--subscription", "-m", model, "--timeout", "180"]
    if EFFORT:
        cmd.extend(["-e", EFFORT])
    cmd.append(prompt)
    env = {**os.environ, "LLMX_CALLER": f"{RUN_TAG}:{model}"}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=240, env=env)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise TransportError(f"{model}: {type(exc).__name__}") from exc
    if result.returncode != 0 or not result.stdout.strip():
        tail = (result.stderr or "").strip().splitlines()[-1:] or [""]
        raise TransportError(f"{model}: rc={result.returncode} {tail[0][:200]}")
    return result.stdout.strip()


def usage_for(model: str) -> dict:
    """Sum llmx usage rows this run logged for one model (prompt/output/reasoning)."""
    tag = f"{RUN_TAG}:{model}"
    tot = {"calls": 0, "prompt_tokens": 0, "cached_tokens": 0,
           "completion_tokens": 0, "reasoning_tokens": 0, "reported_cost_usd": 0.0}
    if not USAGE_LOG.exists():
        return tot
    with USAGE_LOG.open() as f:
        for line in f:
            if tag not in line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("caller") != tag:
                continue
            tot["calls"] += 1
            for k in ("prompt_tokens", "cached_tokens", "completion_tokens", "reasoning_tokens"):
                tot[k] += row.get(k) or 0
            tot["reported_cost_usd"] += row.get("reported_cost_usd") or 0.0
    tot["reported_cost_usd"] = round(tot["reported_cost_usd"], 4)
    return tot


def parse_response(text: str) -> tuple[bool, float] | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group())
    except json.JSONDecodeError:
        return None

    answer = payload.get("answer")
    confidence = payload.get("confidence")
    if not isinstance(answer, bool):
        return None
    if not isinstance(confidence, (int, float)):
        return None
    confidence = max(0.0, min(100.0, float(confidence)))
    return answer, confidence


def _build_sampling_prompt(canary: dict) -> str:
    has_context = canary.get("requires_context", True) and "context" in canary
    if has_context:
        return f"""Answer the boolean question from the provided context.

Return ONLY JSON: {{"answer": true}} or {{"answer": false}}

Context:
{canary["context"]}

Question:
{canary["question"]}"""
    else:
        return f"""Answer this boolean question using your knowledge.

Return ONLY JSON: {{"answer": true}} or {{"answer": false}}

Question:
{canary["question"]}"""


def _build_verbalized_prompt(canary: dict) -> str:
    has_context = canary.get("requires_context", True) and "context" in canary
    if has_context:
        return f"""Answer the boolean question from the provided context.

Return ONLY JSON in this exact shape:
{{"answer": true, "confidence": 73}}

Rules:
- `answer` must be boolean
- `confidence` must be 0-100 and means the probability your answer is correct
- do not add explanation

Context:
{canary["context"]}

Question:
{canary["question"]}"""
    else:
        return f"""Answer this boolean question using your knowledge.

Return ONLY JSON in this exact shape:
{{"answer": true, "confidence": 73}}

Rules:
- `answer` must be boolean
- `confidence` must be 0-100 and means the probability your answer is correct
- do not add explanation

Question:
{canary["question"]}"""


def _parse_bool_answer(text: str) -> bool | None:
    match = re.search(r"\{.*\}", text.strip(), re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    answer = payload.get("answer")
    if not isinstance(answer, bool):
        return None
    return answer


def _sdk_call(client, model: str, prompt: str):
    """Metered Anthropic SDK call. Budget covers adaptive thinking; no sampling params."""
    try:
        return client.messages.create(
            model=model, max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 — any SDK failure is a transport failure
        raise TransportError(f"{model}: {type(exc).__name__}: {str(exc)[:200]}") from exc


def ask_canary_sampling(client, *, model: str, canary: dict, temperature: float, backend: str = "anthropic") -> bool | None:
    """Ask a canary in sampling mode — boolean answer only, no confidence."""
    prompt = _build_sampling_prompt(canary)

    if backend == "llmx":
        return _parse_bool_answer(llmx_chat(model, prompt))

    response = _sdk_call(client, model, prompt)
    text = "".join(
        block.text for block in response.content
        if getattr(block, "type", None) == "text"
    )
    return _parse_bool_answer(text)


def ask_canary(client, *, model: str, canary: dict, temperature: float, backend: str = "anthropic") -> tuple[bool, float] | None:
    prompt = _build_verbalized_prompt(canary)

    if backend == "llmx":
        return parse_response(llmx_chat(model, prompt))

    response = _sdk_call(client, model, prompt)
    text = "".join(
        block.text for block in response.content
        if getattr(block, "type", None) == "text"
    )
    return parse_response(text.strip())


FAILURES: list[str] = []
UNPARSED: dict[str, int] = defaultdict(int)
WORKERS = 4


_FAILED = object()  # transport failure sentinel (distinct from an unparsable answer)


def _parallel(fn, jobs: list, label: str) -> list:
    """Run fn(job) over jobs with WORKERS threads. TransportError -> _FAILED + FAILURES."""

    def wrap(job):
        try:
            return fn(job)
        except TransportError as exc:
            FAILURES.append(str(exc))
            return _FAILED

    out = []
    step = max(1, len(jobs) // 10)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i, res in enumerate(pool.map(wrap, jobs), 1):
            if i % step == 0 or i == len(jobs):
                print(f"  [{i}/{len(jobs)}] {label}", flush=True)
            out.append(res)
    return out


def run_sampling_mode(client, canaries: list[dict], *, model: str, runs: int, temperature: float, backend: str = "llmx") -> list[dict]:
    """Run canaries in sampling mode — boolean answer only, measure frequency."""
    samples = []
    jobs = [(canary, run_idx) for canary in canaries for run_idx in range(runs)]
    answers = _parallel(
        lambda job: ask_canary_sampling(client, model=model, canary=job[0],
                                        temperature=temperature, backend=backend),
        jobs, f"sampling {model}",
    )
    for (canary, run_idx), answer in zip(jobs, answers):
        if answer is _FAILED:
            continue
        if answer is None:
            UNPARSED[model] += 1
            continue
        expected = bool(canary["answer"])
        samples.append({
            "id": canary["id"],
            "category": canary["category"],
            "difficulty": canary.get("difficulty", "unknown"),
            "run": run_idx + 1,
            "expected": expected,
            "answer": answer,
            "correct": answer == expected,
        })
    return samples


def bootstrap_ci(values: list[float], n_boot: int = 2000, alpha: float = 0.05) -> tuple[float, float]:
    """Bootstrap confidence interval for the mean."""
    import random
    n = len(values)
    if n == 0:
        return (0.0, 0.0)
    means = []
    for _ in range(n_boot):
        resample = [random.choice(values) for _ in range(n)]
        means.append(sum(resample) / n)
    means.sort()
    lo = means[int(n_boot * alpha / 2)]
    hi = means[int(n_boot * (1 - alpha / 2))]
    return (lo, hi)


def sampling_brier_for_canary(entries: list[dict], expected: bool) -> tuple[float, float]:
    """Compute bias-corrected Brier score for a canary from sampling results.

    Returns (raw_brier, corrected_brier).
    Correction: subtract p̂(1-p̂)/(N-1) to remove Monte Carlo penalty.
    Per GPT-5.4 review (2026-03-23): raw sampling adds up to 0.025/item
    penalty at N=10, biasing compare-mode against sampling.
    """
    n = len(entries)
    if n == 0:
        return (0.0, 0.0)
    p_true = sum(1 for e in entries if e["answer"]) / n
    # Implicit confidence: probability assigned to the correct answer
    implicit_conf = p_true if expected else (1.0 - p_true)
    outcome = 1.0  # We always compare against the ground truth being correct
    raw_brier = (implicit_conf - outcome) ** 2
    # Bias correction: Monte Carlo variance penalty
    correction = (p_true * (1.0 - p_true)) / max(n - 1, 1)
    corrected_brier = max(0.0, raw_brier - correction)
    return (raw_brier, corrected_brier)


def print_sampling_results(samples: list[dict], runs: int, canaries: list[dict] | None = None) -> dict | None:
    """Print sampling mode results with bias-corrected Brier scores; return the summary."""
    if not samples:
        print("No samples completed.")
        return None

    by_id: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by_id[s["id"]].append(s)

    # Build expected lookup from canaries or samples
    expected_lookup = {}
    if canaries:
        for c in canaries:
            expected_lookup[c["id"]] = bool(c["answer"])
    else:
        for s in samples:
            expected_lookup[s["id"]] = s["expected"]

    accuracy = sum(1 for s in samples if s["correct"]) / len(samples)

    # Compute per-canary Brier scores
    raw_briers = []
    corrected_briers = []
    for cid, entries in by_id.items():
        expected = expected_lookup.get(cid, True)
        raw, corrected = sampling_brier_for_canary(entries, expected)
        raw_briers.append(raw)
        corrected_briers.append(corrected)

    avg_raw_brier = sum(raw_briers) / len(raw_briers) if raw_briers else 0
    avg_corrected_brier = sum(corrected_briers) / len(corrected_briers) if corrected_briers else 0
    brier_ci = bootstrap_ci(corrected_briers)

    print(f"{'=' * 65}")
    print("  Calibration Canary — SAMPLING MODE")
    print(f"{'=' * 65}")
    print(f"  Canaries: {len(by_id)}  |  Samples: {len(samples)}  |  Runs/canary: {runs}")
    print(f"  Overall accuracy:     {accuracy:.1%}")
    print(f"  Raw sampling Brier:   {avg_raw_brier:.4f}")
    print(f"  Corrected Brier:      {avg_corrected_brier:.4f}  95% CI [{brier_ci[0]:.4f}, {brier_ci[1]:.4f}]")
    print(f"  (Correction removes Monte Carlo penalty of p̂(1-p̂)/(N-1) per item)")
    print()
    summary = {
        "canaries": len(by_id), "samples": len(samples), "runs": runs,
        "accuracy": round(accuracy, 4), "raw_brier": round(avg_raw_brier, 4),
        "corrected_brier": round(avg_corrected_brier, 4),
        "corrected_brier_ci": [round(brier_ci[0], 4), round(brier_ci[1], 4)],
    }

    # Per-canary breakdown
    canary_data = []
    for cid, entries in sorted(by_id.items()):
        acc = sum(1 for e in entries if e["correct"]) / len(entries)
        majority = max(sum(1 for e in entries if e["answer"]), sum(1 for e in entries if not e["answer"]))
        cons = majority / len(entries)
        diff = entries[0].get("difficulty", "?")
        expected = expected_lookup.get(cid, True)
        _, corr_brier = sampling_brier_for_canary(entries, expected)
        canary_data.append((cid, acc, cons, diff, corr_brier))

    print(f"  {'ID':<35} {'Acc':>5} {'Cons':>5} {'Brier':>6} {'Diff':>6}")
    print(f"  {'-'*35} {'-'*5} {'-'*5} {'-'*6} {'-'*6}")
    for cid, acc, cons, diff, brier in canary_data:
        flag = " ←" if diff == "hard" and acc > 0.9 else ""
        flag = flag or (" !!" if diff == "easy" and acc < 0.7 else "")
        print(f"  {cid:<35} {acc:>4.0%} {cons:>4.0%} {brier:>5.3f}  {diff:<5}{flag}")

    # By difficulty
    by_diff: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by_diff[s["difficulty"]].append(s)
    print()
    print("  By difficulty:")
    for diff, entries in sorted(by_diff.items()):
        acc = sum(1 for e in entries if e["correct"]) / len(entries)
        # Collect corrected briers for this difficulty
        diff_briers = []
        diff_by_id: dict[str, list[dict]] = defaultdict(list)
        for e in entries:
            diff_by_id[e["id"]].append(e)
        for cid, elist in diff_by_id.items():
            expected = expected_lookup.get(cid, True)
            _, corr = sampling_brier_for_canary(elist, expected)
            diff_briers.append(corr)
        avg_db = sum(diff_briers) / len(diff_briers) if diff_briers else 0
        print(f"    {diff:<10} acc={acc:.0%}  brier={avg_db:.3f}  (n={len(entries)})")

    # Context vs no-context
    has_context_ids = set()
    no_context_ids = set()
    if canaries:
        for c in canaries:
            if c.get("requires_context", True) and "context" in c:
                has_context_ids.add(c["id"])
            else:
                no_context_ids.add(c["id"])
    if has_context_ids and no_context_ids:
        print()
        print("  By context type:")
        for label, ids in [("with-context", has_context_ids), ("no-context", no_context_ids)]:
            ctx_samples = [s for s in samples if s["id"] in ids]
            if ctx_samples:
                ctx_acc = sum(1 for s in ctx_samples if s["correct"]) / len(ctx_samples)
                ctx_briers = []
                ctx_by_id: dict[str, list[dict]] = defaultdict(list)
                for s in ctx_samples:
                    ctx_by_id[s["id"]].append(s)
                for cid, elist in ctx_by_id.items():
                    expected = expected_lookup.get(cid, True)
                    _, corr = sampling_brier_for_canary(elist, expected)
                    ctx_briers.append(corr)
                avg_cb = sum(ctx_briers) / len(ctx_briers) if ctx_briers else 0
                print(f"    {label:<15} acc={ctx_acc:.0%}  brier={avg_cb:.3f}  (n={len(ctx_samples)})")
    return summary


def main() -> None:
    """Run each requested model; exit 2 with [DEGRADED] if any call failed in transport."""
    global EFFORT, WORKERS
    args = sys.argv[1:]

    def opt(name: str, default=None):
        if name in args:
            idx = args.index(name)
            if idx + 1 < len(args):
                return args[idx + 1]
        return default

    EFFORT = opt("--effort")
    WORKERS = int(opt("--workers", "4"))
    models = [m.strip() for m in opt("--model", "claude-haiku-5-5").split(",") if m.strip()]
    report = []
    for model in models:
        FAILURES.clear()
        run_model(args, model)
        usage = usage_for(model)
        report.append((model, list(FAILURES), usage))
        print(f"  tokens[{model}]: calls={usage['calls']} prompt={usage['prompt_tokens']} "
              f"cached={usage['cached_tokens']} out={usage['completion_tokens']} "
              f"reason={usage['reasoning_tokens']} reported_usd={usage['reported_cost_usd']}")
        print()
    degraded = [(m, f) for m, f, _ in report if f]
    if degraded:
        for model, fails in degraded:
            print(f"[DEGRADED] {model}: {len(fails)} transport failure(s); first: {fails[0]}")
        print("[DEGRADED] calibration metrics for degraded models were NOT logged.")
        sys.exit(2)


def run_model(args: list[str], model: str) -> None:
    runs = 3
    limit = None
    temperature = 0.8
    mode = "verbalized"
    difficulty_filter = "all"
    do_analysis = False
    backend = "llmx"
    if "--runs" in args:
        idx = args.index("--runs")
        if idx + 1 < len(args):
            runs = int(args[idx + 1])
    if "--limit" in args:
        idx = args.index("--limit")
        if idx + 1 < len(args):
            limit = int(args[idx + 1])
    if "--temperature" in args:
        idx = args.index("--temperature")
        if idx + 1 < len(args):
            temperature = float(args[idx + 1])
    if "--mode" in args:
        idx = args.index("--mode")
        if idx + 1 < len(args):
            mode = args[idx + 1]
    if "--difficulty" in args:
        idx = args.index("--difficulty")
        if idx + 1 < len(args):
            difficulty_filter = args[idx + 1]
    if "--analysis" in args:
        do_analysis = True
    if "--backend" in args:
        idx = args.index("--backend")
        if idx + 1 < len(args):
            backend = args[idx + 1]

    client = None
    if backend == "anthropic":
        # Metered Anthropic API: never the default (Claude runs on the subscription);
        # needs an explicit --allow-metered and a key, else fail loud.
        if "--allow-metered" not in args:
            print("ERROR: --backend anthropic bills the metered API; pass --allow-metered to confirm.")
            sys.exit(1)
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ERROR: ANTHROPIC_API_KEY is unset (shells export it only as "
                  "ANTHROPIC_API_KEY_METERED). Export it for this run or use --backend llmx.")
            sys.exit(1)
        try:
            import anthropic
        except ImportError:
            print("ERROR: anthropic package required. Install with: uv add anthropic")
            sys.exit(1)
    elif backend == "llmx":
        # llmx temperature is model-controlled (reasoning models lock to 1.0)
        # No SDK needed — shells out to llmx CLI
        import shutil
        if not shutil.which("llmx"):
            print("ERROR: llmx CLI not found. Install with: uv tool install llmx")
            sys.exit(1)
    else:
        print(f"ERROR: unknown backend '{backend}'. Use 'anthropic' or 'llmx'.")
        sys.exit(1)

    canaries = load_canaries(limit=None)

    # Filter by difficulty BEFORE limit
    if difficulty_filter != "all":
        canaries = [c for c in canaries if c.get("difficulty", "easy") == difficulty_filter]

    if limit is not None:
        canaries = canaries[:limit]

    print(f"[{model}] canaries={len(canaries)} difficulty={difficulty_filter} backend={backend} "
          f"effort={EFFORT or 'model-default'} run_tag={RUN_TAG}")

    if backend == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
    else:
        client = None  # llmx backend doesn't need a client object

    # Sampling mode
    if mode == "sampling":
        sampling_runs = max(runs, 10)  # Sampling needs more runs
        samples = run_sampling_mode(client, canaries, model=model, runs=sampling_runs, temperature=1.0, backend=backend)
        summary = print_sampling_results(samples, sampling_runs, canaries=canaries)
        if UNPARSED[model]:
            print(f"  ! {UNPARSED[model]} answer(s) were not parsable JSON booleans (excluded)")
        if summary and not FAILURES:
            log_metric("calibration_canary", suite="v3_platinum", mode="sampling",
                       difficulty=difficulty_filter, model=model, backend=backend,
                       effort=EFFORT, unparsed=UNPARSED[model], run_tag=RUN_TAG,
                       tokens=usage_for(model), **summary)
            print(f"  Logged to {METRICS_FILE}")
        return

    # Compare mode — run both
    if mode == "compare":
        print("Running VERBALIZED mode...")
        # Fall through to verbalized below, then do sampling after

    # Verbalized mode (default)
    samples = []
    jobs = [(canary, run_idx) for canary in canaries for run_idx in range(runs)]
    results = _parallel(
        lambda job: ask_canary(client, model=model, canary=job[0],
                               temperature=temperature, backend=backend),
        jobs, f"verbalized {model}",
    )
    for (canary, run_idx), parsed in zip(jobs, results):
        if parsed is _FAILED:
            continue
        if parsed is None:
            UNPARSED[model] += 1
            continue

        answer, confidence = parsed
        expected = bool(canary["answer"])
        predicted_true = confidence / 100.0 if answer else 1.0 - (confidence / 100.0)
        outcome = 1 if expected else 0
        brier = (predicted_true - outcome) ** 2

        samples.append(
            {
                "id": canary["id"],
                "category": canary["category"],
                "difficulty": canary.get("difficulty", "unknown"),
                "run": run_idx + 1,
                "expected": expected,
                "answer": answer,
                "confidence": confidence / 100.0,
                "correct": answer == expected,
                "predicted_true": predicted_true,
                "brier": brier,
            }
        )

    if not samples:
        print("No canary samples completed.")
        return

    accuracy = sum(1 for s in samples if s["correct"]) / len(samples)
    avg_conf = sum(s["confidence"] for s in samples) / len(samples)
    avg_predicted = sum(s["confidence"] for s in samples) / len(samples)
    brier_score = sum(s["brier"] for s in samples) / len(samples)

    by_id: dict[str, list[bool]] = defaultdict(list)
    by_category: dict[str, list[dict]] = defaultdict(list)
    for sample in samples:
        by_id[sample["id"]].append(sample["answer"])
        by_category[sample["category"]].append(sample)

    consistency_scores = []
    for answers in by_id.values():
        majority = max(answers.count(True), answers.count(False))
        consistency_scores.append(majority / len(answers))
    avg_consistency = sum(consistency_scores) / len(consistency_scores)

    # Per-canary Brier for bootstrap CI
    canary_briers: dict[str, list[float]] = defaultdict(list)
    for s in samples:
        canary_briers[s["id"]].append(s["brier"])
    per_canary_brier = [sum(v) / len(v) for v in canary_briers.values()]
    brier_ci = bootstrap_ci(per_canary_brier)

    by_category_summary = {}
    for category, entries in by_category.items():
        by_category_summary[category] = {
            "accuracy": round(sum(1 for e in entries if e["correct"]) / len(entries), 4),
            "brier": round(sum(e["brier"] for e in entries) / len(entries), 4),
        }

    print(f"{'=' * 65}")
    print("  Calibration Canary — VERBALIZED MODE")
    print(f"{'=' * 65}")
    print()
    print(f"  Canaries:              {len(by_id)}")
    print(f"  Samples:               {len(samples)} ({runs} run(s) each target)")
    print(f"  Accuracy:              {accuracy:.1%}")
    print(f"  Avg predicted correct: {avg_predicted:.1%}")
    print(f"  Brier score:           {brier_score:.4f}  95% CI [{brier_ci[0]:.4f}, {brier_ci[1]:.4f}]")
    print(f"  Avg consistency:       {avg_consistency:.1%}")
    print()
    print("  By category:")
    for category, stats in sorted(by_category_summary.items()):
        print(f"    {category:<18} acc={stats['accuracy']:.0%}  brier={stats['brier']:.3f}")
    print()

    # By difficulty
    by_diff: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by_diff[s.get("difficulty", "unknown")].append(s)
    print("  By difficulty:")
    for diff, entries in sorted(by_diff.items()):
        d_acc = sum(1 for e in entries if e["correct"]) / len(entries)
        d_brier = sum(e["brier"] for e in entries) / len(entries)
        print(f"    {diff:<10} acc={d_acc:.0%}  brier={d_brier:.3f}  (n={len(entries)})")
    print()

    if FAILURES:
        print("  ! transport failures: metric not logged")
    else:
        log_metric(
            "calibration_canary",
            suite="v3_platinum",
            mode=mode,
            backend=backend,
            effort=EFFORT,
            run_tag=RUN_TAG,
            unparsed=UNPARSED[model],
            canaries=len(by_id),
            samples=len(samples),
            runs=runs,
            model=model,
            temperature=temperature,
            accuracy=round(accuracy, 4),
            avg_predicted_correctness=round(avg_predicted, 4),
            avg_confidence=round(avg_conf, 4),
            brier_score=round(brier_score, 4),
            avg_consistency=round(avg_consistency, 4),
            by_category=by_category_summary,
        )
        print(f"  Logged to {METRICS_FILE}")

    # Compare mode: also run sampling
    if mode == "compare":
        print()
        print("Running SAMPLING mode...")
        sampling_runs = max(runs, 10)
        sampling_samples = run_sampling_mode(
            client, canaries, model=model, runs=sampling_runs, temperature=1.0, backend=backend,
        )
        print_sampling_results(sampling_samples, sampling_runs, canaries=canaries)

        # Build expected lookup
        expected_lookup = {c["id"]: bool(c["answer"]) for c in canaries}

        # Per-canary Brier comparison
        verb_by_id: dict[str, list[dict]] = defaultdict(list)
        for s in samples:
            verb_by_id[s["id"]].append(s)
        samp_by_id: dict[str, list[dict]] = defaultdict(list)
        for s in sampling_samples:
            samp_by_id[s["id"]].append(s)

        print()
        print(f"{'=' * 70}")
        print("  COMPARISON: Verbalized Brier vs Corrected Sampling Brier")
        print(f"{'=' * 70}")
        print(f"  {'ID':<35} {'V-Brier':>8} {'S-Brier':>8} {'Delta':>8}")
        print(f"  {'-'*35} {'-'*8} {'-'*8} {'-'*8}")

        verb_briers = []
        samp_briers = []
        for cid in sorted(set(verb_by_id.keys()) | set(samp_by_id.keys())):
            expected = expected_lookup.get(cid, True)
            # Verbalized Brier
            v_entries = verb_by_id.get(cid, [])
            v_brier = sum(e["brier"] for e in v_entries) / max(len(v_entries), 1) if v_entries else float("nan")
            # Corrected sampling Brier
            s_entries = samp_by_id.get(cid, [])
            _, s_brier = sampling_brier_for_canary(s_entries, expected) if s_entries else (0, float("nan"))

            if v_entries:
                verb_briers.append(v_brier)
            if s_entries:
                samp_briers.append(s_brier)
            delta = s_brier - v_brier
            flag = " *" if abs(delta) > 0.05 else ""
            print(f"  {cid:<35} {v_brier:>7.4f} {s_brier:>7.4f} {delta:>+7.4f}{flag}")

        # Aggregate comparison
        avg_v = sum(verb_briers) / len(verb_briers) if verb_briers else 0
        avg_s = sum(samp_briers) / len(samp_briers) if samp_briers else 0
        v_ci = bootstrap_ci(verb_briers)
        s_ci = bootstrap_ci(samp_briers)
        print()
        print(f"  Verbalized mean Brier:  {avg_v:.4f}  95% CI [{v_ci[0]:.4f}, {v_ci[1]:.4f}]")
        print(f"  Sampling mean Brier:    {avg_s:.4f}  95% CI [{s_ci[0]:.4f}, {s_ci[1]:.4f}]")
        delta = avg_s - avg_v
        # Pre-registered criterion: ≥0.03 improvement, CI excludes 0
        deltas = [s - v for s, v in zip(samp_briers, verb_briers)]
        delta_ci = bootstrap_ci(deltas) if deltas else (0, 0)
        print(f"  Delta (sampling - verb): {delta:+.4f}  95% CI [{delta_ci[0]:+.4f}, {delta_ci[1]:+.4f}]")
        if delta < -0.03 and delta_ci[1] < 0:
            print("  → PASS: Sampling Brier significantly better (≥0.03, CI excludes 0)")
        elif delta > 0.03 and delta_ci[0] > 0:
            print("  → FAIL: Verbalized Brier significantly better")
        else:
            print("  → INCONCLUSIVE: Delta does not meet pre-registered ≥0.03 threshold")

    # Discriminant validity analysis
    if do_analysis:
        print()
        print(f"{'=' * 60}")
        print("  DISCRIMINANT VALIDITY — Category Correlation")
        print(f"{'=' * 60}")
        # Compute per-canary accuracy as a vector, group by category
        canary_acc = {}
        for cid, entries in by_id.items():
            canary_acc[cid] = sum(1 for a in entries if a) / len(entries)

        cat_canaries: dict[str, list[str]] = defaultdict(list)
        for s in samples:
            if s["id"] not in cat_canaries[s["category"]]:
                cat_canaries[s["category"]].append(s["id"])

        categories = sorted(cat_canaries.keys())
        if len(categories) >= 2:
            # For each pair, compute accuracy correlation
            print(f"  Categories with ≥2 canaries: {len(categories)}")
            print(f"  (Correlation requires variance — categories with 100% accuracy have none)")
            print()
            collapsed = []
            for i, cat_a in enumerate(categories):
                for cat_b in categories[i + 1:]:
                    ids_a = cat_canaries[cat_a]
                    ids_b = cat_canaries[cat_b]
                    accs_a = [canary_acc.get(c, 0) for c in ids_a]
                    accs_b = [canary_acc.get(c, 0) for c in ids_b]
                    # Report mean accuracy per category
                    mean_a = sum(accs_a) / max(len(accs_a), 1)
                    mean_b = sum(accs_b) / max(len(accs_b), 1)
                    # Flag if both at ceiling (can't compute meaningful correlation)
                    if mean_a > 0.95 and mean_b > 0.95:
                        collapsed.append((cat_a, cat_b, "ceiling"))
            if collapsed:
                print(f"  WARNING: {len(collapsed)} category pair(s) at ceiling (>95% accuracy)")
                print("  Cannot assess discriminant validity when all canaries are too easy.")
                print("  This is why hard canaries were added.")
                for ca, cb, reason in collapsed[:5]:
                    print(f"    {ca} × {cb}: both at {reason}")
        else:
            print("  Need ≥2 categories for correlation analysis.")


if __name__ == "__main__":
    main()
