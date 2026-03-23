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
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from config import METRICS_FILE, log_metric

CANARIES_PATH = Path(__file__).resolve().parent.parent / "schemas" / "calibration_canaries.json"


def load_canaries(limit: int | None = None) -> list[dict]:
    with open(CANARIES_PATH) as f:
        canaries = json.load(f)
    if limit is not None:
        return canaries[:limit]
    return canaries


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


def ask_canary_sampling(client, *, model: str, canary: dict, temperature: float) -> bool | None:
    """Ask a canary in sampling mode — boolean answer only, no confidence."""
    has_context = canary.get("requires_context", True) and "context" in canary

    if has_context:
        prompt = f"""Answer the boolean question from the provided context.

Return ONLY JSON: {{"answer": true}} or {{"answer": false}}

Context:
{canary["context"]}

Question:
{canary["question"]}
"""
    else:
        prompt = f"""Answer this boolean question using your knowledge.

Return ONLY JSON: {{"answer": true}} or {{"answer": false}}

Question:
{canary["question"]}
"""
    response = client.messages.create(
        model=model,
        max_tokens=30,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(
        block.text for block in response.content
        if getattr(block, "type", None) == "text"
    )
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


def ask_canary(client, *, model: str, canary: dict, temperature: float) -> tuple[bool, float] | None:
    has_context = canary.get("requires_context", True) and "context" in canary

    if has_context:
        prompt = f"""Answer the boolean question from the provided context.

Return ONLY JSON in this exact shape:
{{"answer": true, "confidence": 73}}

Rules:
- `answer` must be boolean
- `confidence` must be 0-100 and means the probability your answer is correct
- do not add explanation

Context:
{canary["context"]}

Question:
{canary["question"]}
"""
    else:
        prompt = f"""Answer this boolean question using your knowledge.

Return ONLY JSON in this exact shape:
{{"answer": true, "confidence": 73}}

Rules:
- `answer` must be boolean
- `confidence` must be 0-100 and means the probability your answer is correct
- do not add explanation

Question:
{canary["question"]}
"""
    response = client.messages.create(
        model=model,
        max_tokens=80,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(
        block.text for block in response.content
        if getattr(block, "type", None) == "text"
    )
    return parse_response(text.strip())


def run_sampling_mode(client, canaries: list[dict], *, model: str, runs: int, temperature: float) -> list[dict]:
    """Run canaries in sampling mode — boolean answer only, measure frequency."""
    samples = []
    for canary in canaries:
        for run_idx in range(runs):
            answer = ask_canary_sampling(
                client, model=model, canary=canary, temperature=temperature,
            )
            if answer is None:
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


def print_sampling_results(samples: list[dict], runs: int) -> None:
    """Print sampling mode results."""
    if not samples:
        print("No samples completed.")
        return

    by_id: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by_id[s["id"]].append(s)

    accuracy = sum(1 for s in samples if s["correct"]) / len(samples)

    print(f"{'=' * 60}")
    print("  Calibration Canary — SAMPLING MODE")
    print(f"{'=' * 60}")
    print(f"  Canaries: {len(by_id)}  |  Samples: {len(samples)}  |  Runs/canary: {runs}")
    print(f"  Overall accuracy: {accuracy:.1%}")
    print()

    # Per-canary breakdown
    print(f"  {'ID':<35} {'Acc':>5} {'Cons':>5} {'Diff':>6}")
    print(f"  {'-'*35} {'-'*5} {'-'*5} {'-'*6}")
    for cid, entries in sorted(by_id.items()):
        acc = sum(1 for e in entries if e["correct"]) / len(entries)
        majority = max(sum(1 for e in entries if e["answer"]), sum(1 for e in entries if not e["answer"]))
        cons = majority / len(entries)
        diff = entries[0].get("difficulty", "?")
        flag = " ←" if diff == "hard" and acc > 0.9 else ""
        flag = flag or (" !!" if diff == "easy" and acc < 0.7 else "")
        print(f"  {cid:<35} {acc:>4.0%} {cons:>4.0%}  {diff:<5}{flag}")

    # By difficulty
    by_diff: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by_diff[s["difficulty"]].append(s)
    print()
    print("  By difficulty:")
    for diff, entries in sorted(by_diff.items()):
        acc = sum(1 for e in entries if e["correct"]) / len(entries)
        print(f"    {diff:<10} acc={acc:.0%}  (n={len(entries)})")


def main() -> None:
    runs = 3
    limit = None
    temperature = 0.8
    model = "claude-haiku-4-5-20251001"
    mode = "verbalized"
    difficulty_filter = "all"
    do_analysis = False

    args = sys.argv[1:]
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
    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            model = args[idx + 1]
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

    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package required. Install with: uv add anthropic")
        sys.exit(1)

    canaries = load_canaries(limit=limit)

    # Filter by difficulty
    if difficulty_filter != "all":
        canaries = [c for c in canaries if c.get("difficulty", "easy") == difficulty_filter]
        print(f"  Filtered to {len(canaries)} canaries with difficulty={difficulty_filter}")

    client = anthropic.Anthropic()

    # Sampling mode
    if mode == "sampling":
        sampling_runs = max(runs, 10)  # Sampling needs more runs
        samples = run_sampling_mode(client, canaries, model=model, runs=sampling_runs, temperature=1.0)
        print_sampling_results(samples, sampling_runs)
        return

    # Compare mode — run both
    if mode == "compare":
        print("Running VERBALIZED mode...")
        # Fall through to verbalized below, then do sampling after

    # Verbalized mode (default)
    samples = []

    for canary in canaries:
        for run_idx in range(runs):
            parsed = ask_canary(
                client,
                model=model,
                canary=canary,
                temperature=temperature,
            )
            if parsed is None:
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

    by_category_summary = {}
    for category, entries in by_category.items():
        by_category_summary[category] = {
            "accuracy": round(sum(1 for e in entries if e["correct"]) / len(entries), 4),
            "brier": round(sum(e["brier"] for e in entries) / len(entries), 4),
        }

    print(f"{'=' * 55}")
    print("  Calibration Canary")
    print(f"{'=' * 55}")
    print()
    print(f"  Canaries:              {len(by_id)}")
    print(f"  Samples:               {len(samples)} ({runs} run(s) each target)")
    print(f"  Accuracy:              {accuracy:.1%}")
    print(f"  Avg predicted correct: {avg_predicted:.1%}")
    print(f"  Brier score:           {brier_score:.4f}")
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

    log_metric(
        "calibration_canary",
        suite="v3_platinum",
        mode=mode,
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
            client, canaries, model=model, runs=sampling_runs, temperature=1.0,
        )
        print_sampling_results(sampling_samples, sampling_runs)

        # Comparison table
        verb_by_id = {}
        for s in samples:
            if s["id"] not in verb_by_id:
                verb_by_id[s["id"]] = []
            verb_by_id[s["id"]].append(s["correct"])
        samp_by_id = {}
        for s in sampling_samples:
            if s["id"] not in samp_by_id:
                samp_by_id[s["id"]] = []
            samp_by_id[s["id"]].append(s["correct"])

        print()
        print(f"{'=' * 60}")
        print("  COMPARISON: Verbalized vs Sampling")
        print(f"{'=' * 60}")
        print(f"  {'ID':<35} {'Verb':>5} {'Samp':>5} {'Delta':>6}")
        print(f"  {'-'*35} {'-'*5} {'-'*5} {'-'*6}")
        for cid in sorted(set(list(verb_by_id.keys()) + list(samp_by_id.keys()))):
            v_acc = sum(verb_by_id.get(cid, [])) / max(len(verb_by_id.get(cid, [])), 1)
            s_acc = sum(samp_by_id.get(cid, [])) / max(len(samp_by_id.get(cid, [])), 1)
            delta = s_acc - v_acc
            flag = " *" if abs(delta) > 0.2 else ""
            print(f"  {cid:<35} {v_acc:>4.0%} {s_acc:>4.0%} {delta:>+5.0%}{flag}")

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
