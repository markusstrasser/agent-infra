#!/usr/bin/env python3
"""Evaluation harness for skill-routing autoresearch."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run_cases(cases_path: Path) -> dict:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "skill-routing.py"),
            "--cases",
            str(cases_path),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=25,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr[-2000:] or proc.stdout[-2000:])
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON from skill-routing.py: {exc}\n{proc.stdout[-2000:]}") from exc


def evaluate_split(name: str, cases_path: Path) -> dict:
    payload = run_cases(cases_path)
    cases = payload.get("cases", [])
    if not cases:
        return {"split": name, "cases": [], "passed": [], "failed": [], "accuracy": 0.0}
    passed = [case for case in cases if case.get("passed")]
    failed = [case for case in cases if not case.get("passed")]
    return {
        "split": name,
        "cases": cases,
        "passed": passed,
        "failed": failed,
        "accuracy": len(passed) / len(cases),
    }


def print_result(result: dict) -> None:
    print(f"accuracy: {result['accuracy']:.6f}")
    print(f"split: {result['split']}")
    print(f"num_cases: {len(result['cases'])}")
    if result["failed"]:
        print("failed_cases:")
        for case in result["failed"]:
            print(
                "- {id}: visible={visible} planned={planned}".format(
                    id=case.get("id"),
                    visible=case.get("visible_top"),
                    planned=case.get("planned_top"),
                )
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", action="store_true")
    parser.add_argument("--canonical", action="store_true")
    parser.add_argument("--locked", action="store_true", help="Run canonical, stress, and holdout as one aggregate score")
    args = parser.parse_args()

    if args.locked:
        split_paths = [
            ("canonical", ROOT / "schemas" / "skill-routing-cases.json"),
            ("stress", HERE / "stress_cases.json"),
            ("holdout", HERE / "holdout_cases.json"),
        ]
        results = [evaluate_split(name, path) for name, path in split_paths]
        total_cases = sum(len(result["cases"]) for result in results)
        total_passed = sum(len(result["passed"]) for result in results)
        accuracy = total_passed / total_cases if total_cases else 0.0
        print(f"accuracy: {accuracy:.6f}")
        print("split: locked")
        print(f"num_cases: {total_cases}")
        for result in results:
            print(f"{result['split']}_accuracy: {result['accuracy']:.6f}")
            print(f"{result['split']}_cases: {len(result['cases'])}")
            if result["failed"]:
                print(f"{result['split']}_failed_cases:")
                for case in result["failed"]:
                    print(
                        "- {id}: visible={visible} planned={planned}".format(
                            id=case.get("id"),
                            visible=case.get("visible_top"),
                            planned=case.get("planned_top"),
                        )
                    )
        return 0

    if args.canonical:
        result = evaluate_split("canonical", ROOT / "schemas" / "skill-routing-cases.json")
    elif args.holdout:
        result = evaluate_split("holdout", HERE / "holdout_cases.json")
    else:
        result = evaluate_split("stress", HERE / "stress_cases.json")
    print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
