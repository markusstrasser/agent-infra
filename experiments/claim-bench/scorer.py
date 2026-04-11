"""Verdict-enum scorer for claim-verification benchmark.

Custom inspect_ai Scorer that returns one of five verdicts:
    supported / contradicted / mixed / insufficient_evidence / not_verifiable

This is the Phase 0 probe — it does NOT yet implement atomic-claim P/R/F1
(Phase 3) or process metrics (Phase 2). It only confirms the inspect_ai
Scorer abstraction can cleanly represent the verdict enum.
"""

from __future__ import annotations

from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState

VERDICTS = (
    "supported",
    "contradicted",
    "mixed",
    "insufficient_evidence",
    "not_verifiable",
)


def _normalize(text: str) -> str:
    return text.strip().lower().replace("-", "_").replace(" ", "_")


@scorer(metrics=[mean()])
def verdict_enum_scorer() -> Scorer:
    """Score whether the model's predicted verdict matches the gold verdict.

    Returns a Score with:
        value=1.0 if exact verdict match, 0.0 otherwise
        answer=normalized predicted verdict
        explanation=raw model output
        metadata={'gold': gold, 'predicted': predicted, 'in_enum': bool}
    """

    async def score(state: TaskState, target: Target) -> Score:
        raw_output = state.output.completion if state.output else ""
        predicted = _normalize(raw_output.split("\n")[0]) if raw_output else ""
        gold = _normalize(target.text)

        in_enum = predicted in VERDICTS
        match = predicted == gold

        return Score(
            value=1.0 if match else 0.0,
            answer=predicted,
            explanation=raw_output[:500],
            metadata={
                "gold": gold,
                "predicted": predicted,
                "in_enum": in_enum,
                "match": match,
            },
        )

    return score
