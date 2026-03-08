#!/usr/bin/env python3
"""Evaluation harness for the text relevance scorer. DO NOT MODIFY."""

import argparse
import json
import sys
from pathlib import Path


def evaluate(scorer_module, test_cases: list[dict]) -> float:
    """Evaluate scorer on test cases. Returns accuracy (0.0-1.0)."""
    correct = 0
    total = 0

    for case in test_cases:
        query = case["query"]
        docs = case["documents"]

        # Score all documents
        scores = []
        for doc in docs:
            try:
                score = scorer_module.score(query, doc["text"])
                score = float(score)
                score = max(0.0, min(1.0, score))  # clamp
            except Exception as e:
                print(f"ERROR scoring '{query}' vs '{doc['text'][:50]}...': {e}",
                      file=sys.stderr)
                score = 0.0
            scores.append((score, doc["relevant"]))

        # For each pair of (relevant, non-relevant), check ranking
        relevant = [(s, r) for s, r in scores if r]
        non_relevant = [(s, r) for s, r in scores if not r]

        for rel_score, _ in relevant:
            for nonrel_score, _ in non_relevant:
                total += 1
                if rel_score > nonrel_score:
                    correct += 1
                elif rel_score == nonrel_score:
                    correct += 0.5  # tie = half credit

    accuracy = correct / total if total > 0 else 0.0
    return accuracy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", action="store_true",
                        help="Evaluate on holdout set instead of dev")
    args = parser.parse_args()

    # Load test cases
    test_path = Path(__file__).parent / "test_cases.json"
    with open(test_path) as f:
        data = json.load(f)

    split = "holdout" if args.holdout else "dev"
    test_cases = data[split]

    # Import scorer
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        import scorer
        # Reload in case it was cached
        import importlib
        importlib.reload(scorer)
    except Exception as e:
        print(f"ERROR importing scorer: {e}", file=sys.stderr)
        print(f"accuracy: 0.000000")
        sys.exit(1)

    # Evaluate
    accuracy = evaluate(scorer, test_cases)

    # Output in standard format
    print(f"accuracy: {accuracy:.6f}")
    print(f"split: {split}")
    print(f"num_cases: {len(test_cases)}")


if __name__ == "__main__":
    main()
