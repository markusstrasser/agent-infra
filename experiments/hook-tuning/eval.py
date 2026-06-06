#!/usr/bin/env python3
"""Evaluation harness for hook-policy tuning."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def evaluate(split: str) -> dict:
    sys.path.insert(0, str(HERE))
    import policy

    importlib.reload(policy)
    data = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    cases = data[split]
    results = []
    for case in cases:
        try:
            got = policy.recommend(case["features"])
        except Exception as exc:  # pragma: no cover - defensive for mutators
            got = f"ERROR:{exc}"
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "got": got,
                "passed": got == case["expected"],
            }
        )
    passed = [case for case in results if case["passed"]]
    return {
        "split": split,
        "cases": results,
        "passed": passed,
        "failed": [case for case in results if not case["passed"]],
        "accuracy": len(passed) / len(results) if results else 0.0,
    }


def print_result(result: dict) -> None:
    print(f"accuracy: {result['accuracy']:.6f}")
    print(f"split: {result['split']}")
    print(f"num_cases: {len(result['cases'])}")
    if result["failed"]:
        print("failed_cases:")
        for case in result["failed"]:
            print(f"- {case['id']}: expected={case['expected']} got={case['got']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", action="store_true")
    parser.add_argument("--locked", action="store_true")
    args = parser.parse_args()
    if args.locked:
        results = [evaluate("dev"), evaluate("holdout")]
        total = sum(len(result["cases"]) for result in results)
        passed = sum(len(result["passed"]) for result in results)
        print(f"accuracy: {(passed / total if total else 0.0):.6f}")
        print("split: locked")
        print(f"num_cases: {total}")
        for result in results:
            print(f"{result['split']}_accuracy: {result['accuracy']:.6f}")
            print(f"{result['split']}_cases: {len(result['cases'])}")
        return 0
    print_result(evaluate("holdout" if args.holdout else "dev"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
