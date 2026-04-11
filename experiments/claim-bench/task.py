"""Phase 1 Task for claim-verification benchmark.

Phase 0 confirmed inspect_ai's Task / Sample / Solver / Scorer types
cleanly represent a 5-class verdict enum on a placeholder solver with
memorizable cases. Phase 1 replaces the placeholder with a real chain:
    system_message(verdict_prompt) → use_tools(exa_search) → generate()
and adds a groundedness_scorer alongside verdict_enum_scorer.

Two new post-cutoff cases (003 pair-instability gap, 004 Kotz retraction)
test whether retrieval actually fires rather than measuring memorization.

Run:
    cd ~/Projects/agent-infra
    uv run inspect eval experiments/claim-bench/task.py --model openai/gpt-4o-mini

The groundedness_scorer uses a cross-family judge model (anthropic/
claude-sonnet-4-5 by default; override with CLAIM_BENCH_JUDGE_MODEL env
var). Never same-family with the SUT per FINCH-ZK.
"""

from __future__ import annotations

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import generate, system_message, use_tools

# Local imports — siblings of this file
from scorer import groundedness_scorer, verdict_enum_scorer
from tools import exa_search

CASES_DIR = Path(__file__).resolve().parent / "cases"

VERDICT_PROMPT = """You are a claim verification system. Your job is to classify a factual claim into exactly one of these five verdicts:

- supported: evidence directly backs the claim
- contradicted: evidence directly refutes the claim
- mixed: both supporting and contradicting evidence exists in the literature
- insufficient_evidence: the claim is verifiable in principle but you cannot find sufficient evidence
- not_verifiable: the claim is rhetorical, opinion-based, or underspecified

You have access to the `exa_search` tool for web retrieval. USE IT — do not rely on memory alone. For claims that cite specific papers, DOIs, dates, retractions, or recent findings, you MUST search for the primary source before answering. Claims may reference events from 2025-2026 that are past your training cutoff; in those cases, retrieval is the only way to get the answer right.

Search strategy: run 1-3 targeted queries, using the tool's `start_published_date` / `end_published_date` parameters to narrow to the relevant time window. Read the returned text excerpts. If a claim references a retraction, search explicitly for "retraction" alongside the paper title or DOI. If a claim gives a specific numerical value, verify that number appears in a primary source, not just a derivative article.

When you have enough evidence (or confidently cannot retrieve it), respond with a single word (one of the five verdicts above) on the first line, followed by a one-paragraph explanation on the second line that cites the retrieved sources by URL or DOI. Do not output anything else."""


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
    """Phase 1 claim-verification task with retrieval and groundedness.

    Solver: system_message → use_tools(exa_search) → generate()
    Scorers: verdict_enum_scorer + groundedness_scorer (cross-family judge)

    generate() auto-loops on tool calls while tools are in state, so the
    model retrieves evidence, adjudicates, and returns a final verdict in
    one chain. No manual loop needed.
    """
    return Task(
        dataset=_load_cases(),
        solver=[
            system_message(VERDICT_PROMPT),
            use_tools(exa_search()),
            generate(),
        ],
        scorer=[verdict_enum_scorer(), groundedness_scorer()],
        message_limit=40,  # caps tool-call loops — adjudication fits in <20 turns
    )
