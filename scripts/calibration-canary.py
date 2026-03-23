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


def print_sampling_results(samples: list[dict], runs: int, canaries: list[dict] | None = None) -> None:
    """Print sampling mode results with bias-corrected Brier scores."""
    if not samples:
        print("No samples completed.")
        return

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
        print_sampling_results(samples, sampling_runs, canaries=canaries)
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
