#!/usr/bin/env python3
"""Evaluation harness for the proposal ranker. DO NOT MODIFY."""

import argparse
import json
import sys
from pathlib import Path


def evaluate(ranker_module, test_cases: list[dict]) -> float:
    """Evaluate ranker on pairwise test cases. Returns accuracy (0.0-1.0)."""
    correct = 0
    total = 0

    for case in test_cases:
        total += 1
        try:
            higher_score = ranker_module.rank(case["higher"])
            lower_score = ranker_module.rank(case["lower"])
            higher_score = float(higher_score)
            lower_score = float(lower_score)
        except Exception as e:
            print(f"ERROR scoring '{case['name']}': {e}", file=sys.stderr)
            continue

        if higher_score > lower_score:
            correct += 1
        elif higher_score == lower_score:
            correct += 0.5  # tie = half credit

    return correct / total if total > 0 else 0.0


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

    # Import ranker
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        import ranker
        import importlib
        importlib.reload(ranker)
    except Exception as e:
        print(f"ERROR importing ranker: {e}", file=sys.stderr)
        print(f"accuracy: 0.000000")
        sys.exit(1)

    # Evaluate
    accuracy = evaluate(ranker, test_cases)

    # Output in standard format
    print(f"accuracy: {accuracy:.6f}")
    print(f"split: {split}")
    print(f"num_cases: {len(test_cases)}")


if __name__ == "__main__":
    main()
