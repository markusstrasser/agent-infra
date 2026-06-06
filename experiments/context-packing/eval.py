#!/usr/bin/env python3
"""Evaluation harness for context-packing policy experiments."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def score_case(case: dict, packed: list[str]) -> dict:
    include = set(case.get("include", []))
    forbid = set(case.get("forbid", []))
    got = set(packed)
    missing = sorted(include - got)
    forbidden = sorted(forbid & got)
    over_budget = len(packed) > int(case.get("budget", 5))
    passed = not missing and not forbidden and not over_budget
    precision = 1.0 if not packed else len(include & got) / len(packed)
    recall = 1.0 if not include else len(include & got) / len(include)
    return {
        "id": case["id"],
        "packed": packed,
        "missing": missing,
        "forbidden": forbidden,
        "over_budget": over_budget,
        "precision": precision,
        "recall": recall,
        "passed": passed,
    }


def evaluate(split: str) -> dict:
    sys.path.insert(0, str(HERE))
    import packer

    importlib.reload(packer)
    data = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    cases = data[split]
    results = []
    for case in cases:
        try:
            packed = packer.pack(case, budget=int(case.get("budget", 5)))
        except Exception as exc:  # pragma: no cover - defensive for mutators
            packed = [f"ERROR:{exc}"]
        results.append(score_case(case, packed))
    passed = [case for case in results if case["passed"]]
    return {
        "split": split,
        "cases": results,
        "passed": passed,
        "failed": [case for case in results if not case["passed"]],
        "accuracy": len(passed) / len(results) if results else 0.0,
        "mean_recall": sum(case["recall"] for case in results) / len(results) if results else 0.0,
        "mean_precision": sum(case["precision"] for case in results) / len(results) if results else 0.0,
    }


def print_result(result: dict) -> None:
    print(f"accuracy: {result['accuracy']:.6f}")
    print(f"split: {result['split']}")
    print(f"num_cases: {len(result['cases'])}")
    print(f"mean_recall: {result['mean_recall']:.6f}")
    print(f"mean_precision: {result['mean_precision']:.6f}")
    if result["failed"]:
        print("failed_cases:")
        for case in result["failed"]:
            print(
                f"- {case['id']}: missing={case['missing']} "
                f"forbidden={case['forbidden']} packed={case['packed']}"
            )


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
            print(f"{result['split']}_mean_recall: {result['mean_recall']:.6f}")
            print(f"{result['split']}_mean_precision: {result['mean_precision']:.6f}")
        return 0
    print_result(evaluate("holdout" if args.holdout else "dev"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
