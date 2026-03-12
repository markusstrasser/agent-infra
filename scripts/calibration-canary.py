#!/usr/bin/env python3
"""Run canary set for answer-confidence calibration.

20 canaries across 4 categories: local-context, temporal/staleness,
external-fact (no context), and adversarial/tricky. Measures accuracy,
Brier score, and consistency across multiple runs.
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


def main() -> None:
    runs = 3
    limit = None
    temperature = 0.8
    model = "claude-haiku-4-5-20251001"

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

    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package required. Install with: uv add anthropic")
        sys.exit(1)

    canaries = load_canaries(limit=limit)
    client = anthropic.Anthropic()
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

    log_metric(
        "calibration_canary",
        suite="v2_mixed",
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


if __name__ == "__main__":
    main()
