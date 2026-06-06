#!/usr/bin/env python3
"""Deterministic eval surface for claim-bench scorer autoresearch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "claim_bench" / "src"))


VERDICTS = {
    "supported",
    "contradicted",
    "mixed",
    "insufficient_evidence",
    "not_verifiable",
}


DEV_CASES = [
    {
        "id": "extract-two-line-supported",
        "kind": "extract_verdict",
        "input": "supported\nEvidence directly backs the claim.",
        "expected": "supported",
    },
    {
        "id": "extract-colon-contradicted",
        "kind": "extract_verdict",
        "input": "contradicted: the retrieved paper refutes it.",
        "expected": "contradicted",
    },
    {
        "id": "extract-markdown-not-verifiable",
        "kind": "extract_verdict",
        "input": "**not verifiable** because the claim is normative.",
        "expected": "not_verifiable",
    },
    {
        "id": "groundedness-decorated-grounded",
        "kind": "groundedness",
        "input": "**grounded**\nTrace contains the cited source.",
        "expected": ("grounded", 1.0),
    },
    {
        "id": "groundedness-not-grounded-variant",
        "kind": "groundedness",
        "input": "not grounded\nNo source in the trace supports it.",
        "expected": ("ungrounded", 0.0),
    },
    {
        "id": "doi-nature-url",
        "kind": "doi",
        "input": "Source: https://www.nature.com/articles/s41586-024-07219-0",
        "expected": "10.1038/s41586-024-07219-0",
    },
]


HOLDOUT_CASES = [
    {
        "id": "extract-hyphen-insufficient",
        "kind": "extract_verdict",
        "input": "insufficient-evidence\nSearch did not find a primary source.",
        "expected": "insufficient_evidence",
    },
    {
        "id": "extract-emphasis-supported",
        "kind": "extract_verdict",
        "input": "  __supported__: source and claim align.",
        "expected": "supported",
    },
    {
        "id": "groundedness-parse-error-zero",
        "kind": "groundedness",
        "input": "maybe\nThe judge did not follow the rubric.",
        "expected": ("parse_error", 0.0),
    },
    {
        "id": "doi-nejm-url",
        "kind": "doi",
        "input": "Read https://www.nejm.org/doi/full/10.1056/NEJMoa1809944",
        "expected": "10.1056/nejmoa1809944",
    },
]


def _gold_case_checks() -> list[dict]:
    cases = []
    for path in sorted((ROOT / "claim_bench" / "cases").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        verdict = payload.get("gold_verdict")
        has_required_fields = bool(payload.get("task_id") and payload.get("claim_text"))
        cases.append(
            {
                "id": f"gold-schema-{path.stem}",
                "kind": "gold_schema",
                "passed": verdict in VERDICTS and has_required_fields,
                "detail": f"verdict={verdict} has_required_fields={has_required_fields}",
            }
        )
    return cases


def _run_case(case: dict) -> dict:
    from claim_bench.process_metrics import _extract_dois_from_text
    from claim_bench.scorer import _extract_verdict, _parse_groundedness_verdict

    if case["kind"] == "extract_verdict":
        got = _extract_verdict(case["input"])
    elif case["kind"] == "groundedness":
        got = _parse_groundedness_verdict(case["input"])
    elif case["kind"] == "doi":
        got = case["expected"] if case["expected"] in _extract_dois_from_text(case["input"]) else None
    else:
        raise ValueError(f"unknown case kind: {case['kind']}")
    return {
        "id": case["id"],
        "kind": case["kind"],
        "passed": got == case["expected"],
        "expected": case["expected"],
        "got": got,
    }


def evaluate(split: str) -> dict:
    cases = DEV_CASES if split == "dev" else HOLDOUT_CASES
    results = [_run_case(case) for case in cases]
    if split == "dev":
        results.extend(_gold_case_checks())
    passed = [case for case in results if case["passed"]]
    failed = [case for case in results if not case["passed"]]
    return {
        "split": split,
        "cases": results,
        "passed": passed,
        "failed": failed,
        "accuracy": len(passed) / len(results) if results else 0.0,
    }


def print_result(result: dict) -> None:
    print(f"accuracy: {result['accuracy']:.6f}")
    print(f"split: {result['split']}")
    print(f"num_cases: {len(result['cases'])}")
    if result["failed"]:
        print("failed_cases:")
        for case in result["failed"]:
            print(f"- {case['id']}: expected={case.get('expected')} got={case.get('got')} {case.get('detail', '')}")


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
            if result["failed"]:
                print(f"{result['split']}_failed_cases:")
                for case in result["failed"]:
                    print(f"- {case['id']}: expected={case.get('expected')} got={case.get('got')}")
        return 0

    print_result(evaluate("holdout" if args.holdout else "dev"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
