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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", action="store_true")
    args = parser.parse_args()

    cases_path = HERE / ("holdout_cases.json" if args.holdout else "stress_cases.json")
    payload = run_cases(cases_path)
    cases = payload.get("cases", [])
    if not cases:
        print("accuracy: 0.000000")
        print("ERROR: no cases returned", file=sys.stderr)
        return 1

    passed = [case for case in cases if case.get("passed")]
    failed = [case for case in cases if not case.get("passed")]
    accuracy = len(passed) / len(cases)

    print(f"accuracy: {accuracy:.6f}")
    print(f"split: {'holdout' if args.holdout else 'stress'}")
    print(f"num_cases: {len(cases)}")
    if failed:
        print("failed_cases:")
        for case in failed:
            print(
                "- {id}: visible={visible} planned={planned}".format(
                    id=case.get("id"),
                    visible=case.get("visible_top"),
                    planned=case.get("planned_top"),
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
