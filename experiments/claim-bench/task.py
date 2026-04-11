"""Phase 2 Task for claim-verification benchmark.

Phase 0 confirmed inspect_ai's Task / Sample / Solver / Scorer types
cleanly represent a 5-class verdict enum on a placeholder solver with
memorizable cases. Phase 1 replaced the placeholder with a real chain:
    system_message(verdict_prompt) → use_tools(exa_search) → generate()
and added a groundedness_scorer alongside verdict_enum_scorer.

Phase 2 adds:
- 4 cross-domain cases (mixed, insufficient_evidence, not_verifiable,
  non-currency contradicted) — corpus is now 8 cases total
- 4 process-level scorers in process_metrics.py:
    currency_scorer (deterministic Crossref + judge for residual)
    calibration_scorer (verbalized hedge classifier)
    trace_faithfulness_scorer (deterministic citation check)
    retrieval_attempted_scorer (top-level promotion of tool_calls_seen)
- epochs=3 to average gpt-4o-mini stochasticity per Phase 1's variance
  finding (verdict_enum_scorer ranged 0.25-0.75 across 4 identical-config
  runs)

The joint_success metric is NOT a scorer — it's derived from the EvalLog
in cards.py (Phase 4). inspect_ai's Scorer API doesn't expose peer scorer
outputs in-band, and faking it via duplicated logic is worse than
computing it post-eval. The headline metric for Phase 2 reports is the
joint mean from cards.py; per-scorer columns stay live for debugging.

Run:
    cd ~/Projects/agent-infra
    uv run inspect eval experiments/claim-bench/task.py --model openai/gpt-4o-mini

The groundedness_scorer and currency_scorer use a cross-family judge
(google/gemini-2.5-flash by default; override with CLAIM_BENCH_JUDGE_MODEL
or CLAIM_BENCH_CURRENCY_JUDGE_MODEL env vars). Never same-family with
the SUT per FINCH-ZK. scorer.py bridges GEMINI_API_KEY → GOOGLE_API_KEY
at module load so operators don't need to manually export.
"""

from __future__ import annotations

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import generate, system_message, use_tools

# Local imports — siblings of this file
from process_metrics import (
    calibration_scorer,
    currency_scorer,
    retrieval_attempted_scorer,
    trace_faithfulness_scorer,
)
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
    """Phase 2 claim-verification task: retrieval + 6 scorers + 3 epochs.

    Solver: system_message → use_tools(exa_search) → generate()
        generate() auto-loops on tool calls while tools are in state, so
        the model retrieves evidence, adjudicates, and returns a final
        verdict in one chain. No manual chain or 6-layer decomposition —
        the model decides ordering per claim.

    Scorers (6 columns per sample):
        verdict_enum_scorer       — exact verdict match against gold
        groundedness_scorer       — cross-family judge: verdict supported by trace?
        currency_scorer           — Crossref hybrid: any cited DOI retracted/superseded?
        calibration_scorer        — verbalized hedge language matches accuracy?
        trace_faithfulness_scorer — explanation citations actually in trace?
        retrieval_attempted_scorer — did the model call a tool at all?

    epochs=3 averages gpt-4o-mini stochasticity. Phase 1 plan-close found
    verdict_enum varied 0.25-0.75 across 4 identical-config runs on 4
    cases — 8 cases × 3 epochs = 24 sample-runs gives a tighter CI.
    """
    return Task(
        dataset=_load_cases(),
        solver=[
            system_message(VERDICT_PROMPT),
            use_tools(exa_search()),
            generate(),
        ],
        scorer=[
            verdict_enum_scorer(),
            groundedness_scorer(),
            currency_scorer(),
            calibration_scorer(),
            trace_faithfulness_scorer(),
            retrieval_attempted_scorer(),
        ],
        # Tight cap — 3-query verification fits in ~10 turns; 20 leaves
        # headroom for retries without letting ToolError loops dominate
        # the trace and mislead the groundedness judge.
        message_limit=20,
        # Average out gpt-4o-mini variance per Phase 1 plan-close finding.
        epochs=3,
    )
