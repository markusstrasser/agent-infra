"""Phase 0 probe Task for claim-verification benchmark.

Goal: confirm that inspect_ai's Task / Sample / Solver / Scorer types
cleanly represent a claim-verification benchmark with a 5-class verdict
enum. Run this BEFORE writing any retrieval / process / atomic-claim code.

Run:
    cd ~/Projects/agent-infra
    uv run inspect eval experiments/claim-bench/task.py --model openai/gpt-4o-mini

The Phase 0 solver is intentionally minimal (single generate() call with
a verdict-enum prompt). Phase 1 will replace it with a real retrieve →
ground → adjudicate chain using the @tool retrieval adapters.
"""

from __future__ import annotations

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import generate, system_message

# Local import — scorer.py lives next to this file
from scorer import verdict_enum_scorer

CASES_DIR = Path(__file__).resolve().parent / "cases"

VERDICT_PROMPT = """You are a claim verification system. Given a factual claim, classify it into exactly one of these five verdicts:

- supported: evidence directly backs the claim
- contradicted: evidence directly refutes the claim
- mixed: both supporting and contradicting evidence exists in the literature
- insufficient_evidence: the claim is verifiable in principle but you cannot find sufficient evidence
- not_verifiable: the claim is rhetorical, opinion-based, or underspecified

Respond with a single word (one of the five verdicts above) on the first line, optionally followed by a one-line explanation on the second line. Do not output anything else."""


def _load_cases() -> list[Sample]:
    """Load JSON gold cases from cases/ as inspect_ai Samples."""
    samples = []
    for path in sorted(CASES_DIR.glob("*.json")):
        case = json.loads(path.read_text())
        samples.append(
            Sample(
                id=case["task_id"],
                input=case["claim_text"],
                target=case["gold_verdict"],
                metadata={
                    "domain": case.get("domain"),
                    "claim_type": case.get("claim_type"),
                    "verifiability": case.get("verifiability"),
                    "difficulty": case.get("difficulty"),
                    "gold_sources": case.get("gold_sources", []),
                    "gold_contradict_sources": case.get("gold_contradict_sources", []),
                },
            )
        )
    return samples


@task
def claim_verification_probe() -> Task:
    """Phase 0 probe: minimal claim-verification task.

    No retrieval, no atomic decomposition, no process metrics. Just:
    Sample.input → generate() → verdict_enum_scorer().

    Success criterion: the eval runs end-to-end, the EvalLog contains
    metadata fields we can later attach independence + adequacy cards to,
    and the verdict_enum_scorer() returns a value for each sample.
    """
    return Task(
        dataset=_load_cases(),
        solver=[
            system_message(VERDICT_PROMPT),
            generate(),
        ],
        scorer=verdict_enum_scorer(),
    )
