"""Scorers for claim-verification benchmark.

Phase 0: verdict_enum_scorer — match predicted verdict against gold.
Phase 1: groundedness_scorer — cross-family judge checks whether the
    predicted verdict is actually supported by the retrieved evidence
    the model cited, rather than hallucinated.

Phase 2+ will split calibration / trace-faithfulness / atomic-claim
scorers into a separate `process_metrics.py`.
"""

from __future__ import annotations

import json
import os
import re

# The google-genai SDK prefers GOOGLE_API_KEY; most local envs set
# GEMINI_API_KEY. Bridge the two at module load so operators don't need
# to remember the mapping on every run. If both are set, GOOGLE_API_KEY
# wins (the SDK already warns on that case).
if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

from inspect_ai.model import ChatMessageTool, ChatMessageUser, get_model  # noqa: E402
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer  # noqa: E402
from inspect_ai.solver import TaskState  # noqa: E402

VERDICTS = (
    "supported",
    "contradicted",
    "mixed",
    "insufficient_evidence",
    "not_verifiable",
)

# Cross-family judge. SUT is expected to be openai/gpt-4o-mini in Phase 1
# dev runs, so Google Gemini is the cross-family first choice per the
# handoff routing table (FINCH-ZK requires cross-family for +31pp accuracy
# over same-family self-review). Gemini 2.5 Flash is $0.50/$4 per MTok,
# affordable for a per-sample scorer. The google-genai provider requires
# GOOGLE_API_KEY in the environment — the session has GEMINI_API_KEY, so
# the eval must be run with GOOGLE_API_KEY=$GEMINI_API_KEY.
GROUNDEDNESS_JUDGE_MODEL = os.environ.get(
    "CLAIM_BENCH_JUDGE_MODEL", "google/gemini-2.5-flash"
)


def _normalize(text: str) -> str:
    return text.strip().lower().replace("-", "_").replace(" ", "_")


def _extract_verdict(raw_output: str) -> str:
    """Extract the verdict token from a model's raw output.

    Handles three formats models have actually produced in practice:
    - 'supported\\nEvidence directly backs...'      (two lines)
    - 'contradicted: Evidence indicates...'          (colon-separated)
    - '**supported** Evidence...'                    (markdown emphasis)

    The previous implementation only split on '\\n' and normalized the
    first line, which failed on the colon-separated format (observed on
    case 002 during plan-close integration testing). This version picks
    the first verdict word appearing at the start of the output after
    stripping markdown decoration and whitespace.
    """
    if not raw_output:
        return ""
    first_line = raw_output.strip().split("\n", 1)[0]
    # Strip leading markdown emphasis / quotes / backticks that some
    # models prepend.
    first_line = first_line.lstrip("*_`\"' \t")
    # Break on any punctuation or whitespace that typically separates
    # verdict from explanation: ':', ',', ';', or a run of whitespace.
    first_token = re.split(r"[:,;\s]+", first_line, maxsplit=1)[0]
    # Strip any trailing markdown that survived the leading lstrip, e.g.
    # the closing ** of '**supported**'.
    first_token = first_token.rstrip("*_`\"'")
    return _normalize(first_token)


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
        predicted = _extract_verdict(raw_output)
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


GROUNDEDNESS_JUDGE_PROMPT = """You are an independent scientific reviewer auditing another AI's claim verification. Your job is to decide whether the AI's verdict is actually grounded in the evidence it retrieved — NOT whether the verdict is factually right in some absolute sense.

## The claim the AI was asked to verify
{claim}

## The AI's verdict and explanation
Predicted verdict: {predicted}
Explanation:
{explanation}

## Tool retrieval trace — what the AI actually searched and saw
{tool_trace}

## Your task

Grade the AI's verdict on groundedness — the degree to which its verdict follows from the evidence in the retrieval trace. Use this rubric:

- **grounded (1.0)**: The retrieval trace contains evidence that clearly supports the predicted verdict. The AI cited, quoted, or clearly relied on that evidence. A reasonable reviewer seeing the same evidence would reach the same verdict.
- **partial (0.5)**: The retrieval trace contains some relevant evidence, but (a) the AI's verdict goes beyond what the evidence supports, OR (b) the AI cited evidence in the explanation that is not actually in the trace, OR (c) the evidence is weak and the verdict is overconfident.
- **ungrounded (0.0)**: The retrieval trace is empty, irrelevant, or does not support the predicted verdict. The AI likely answered from training data, memorization, or confabulation — not from the evidence it retrieved.

Abstention verdicts (`insufficient_evidence`, `not_verifiable`) should be graded **grounded** if the retrieval trace also shows no useful evidence (honest abstention), **partial** if the trace has some evidence the AI ignored, and **ungrounded** if the trace has strong evidence that should have yielded a definite verdict.

## Output format

On the first line, output exactly one token: `grounded`, `partial`, or `ungrounded`.
On the second line, write a one-sentence justification citing the specific trace elements that support your grade.
Do not output anything else."""


def _format_tool_trace(state: TaskState) -> str:
    """Extract the tool-call trace (searches + results) as plain text.

    Walks state.messages and renders each tool call and tool result as
    a compact block. Returns '(no tool calls — the model did not retrieve
    any evidence)' if the model never called a tool AND no tool result
    appeared. Both events count as retrieval activity — a call without
    a result (e.g., an error at the tool layer) is still a retrieval
    attempt the judge should see.
    """
    blocks: list[str] = []
    event_count = 0
    for msg in state.messages:
        if isinstance(msg, ChatMessageTool):
            # Tool result message.
            fn = msg.function or "<unknown>"
            err = f" [ERROR: {msg.error.message}]" if msg.error else ""
            content = msg.text if hasattr(msg, "text") else str(msg.content)
            # Truncate each tool result to keep judge prompt bounded.
            if len(content) > 2500:
                content = content[:2500] + "\n...[truncated]"
            blocks.append(f"### Tool result from {fn}{err}\n{content}")
            event_count += 1
        elif (
            getattr(msg, "role", None) == "assistant"
            and getattr(msg, "tool_calls", None)
        ):
            for tc in msg.tool_calls or []:
                args = getattr(tc, "arguments", None) or {}
                try:
                    args_str = json.dumps(args, ensure_ascii=False)
                except (TypeError, ValueError):
                    args_str = str(args)
                blocks.append(f"### Tool call: {tc.function}({args_str})")
                event_count += 1
    if event_count == 0:
        return "(no tool calls — the model did not retrieve any evidence)"
    return "\n\n".join(blocks)


def _parse_groundedness_verdict(raw: str) -> tuple[str, float]:
    """Parse the judge's output into a (label, value) pair.

    Unparseable judge output scores 0.0, not 0.5. A parse failure means
    the judge did not comply with the output contract; treating it as
    half-grounded silently inflates the metric mean by +0.5 per sample.
    The explicit 'parse_error' label lets post-run analysis count how
    often the judge went off-format without polluting the headline
    groundedness score.
    """
    first = raw.strip().split("\n", 1)[0].strip().lower()
    first = first.strip(".*_-`: ")
    if "grounded" == first:
        return "grounded", 1.0
    if "partial" in first:
        return "partial", 0.5
    if "ungrounded" in first or "not grounded" in first:
        return "ungrounded", 0.0
    return "parse_error", 0.0


@scorer(metrics=[mean()])
def groundedness_scorer() -> Scorer:
    """Cross-family LLM judge: is the predicted verdict supported by the retrieval trace?

    This measures *support-by-trace*, not truth. A model can score grounded
    on an outdated source (e.g. a pre-retraction PDF) as long as the verdict
    follows from the retrieved text — capturing "does the model reason from
    its own evidence" without claiming "the verdict is correct in absolute
    terms." Factual currency and gold-source hit@k are separate scorers
    deferred to Phase 2.

    Runs a judge model (different family from the SUT) on the retrieval
    trace plus the predicted verdict. Returns 1.0 (grounded), 0.5 (partial),
    or 0.0 (ungrounded / confabulated / parse_error).

    Critical for Phase 1 because verdict_enum_scorer can't distinguish a
    lucky guess from a retrieval-backed answer. Model-graded scoring per
    FINCH-ZK must be cross-family; see GROUNDEDNESS_JUDGE_MODEL.
    """

    async def score(state: TaskState, target: Target) -> Score:
        raw_output = state.output.completion if state.output else ""
        predicted = _extract_verdict(raw_output)
        claim_text = state.input_text or ""
        tool_trace = _format_tool_trace(state)
        tool_calls_seen = not tool_trace.startswith("(no tool")

        judge_prompt = GROUNDEDNESS_JUDGE_PROMPT.format(
            claim=claim_text,
            predicted=predicted,
            explanation=raw_output[:2000],
            tool_trace=tool_trace,
        )

        judge = get_model(GROUNDEDNESS_JUDGE_MODEL)
        judge_result = await judge.generate([ChatMessageUser(content=judge_prompt)])
        judge_output = judge_result.completion or ""

        label, value = _parse_groundedness_verdict(judge_output)

        return Score(
            value=value,
            answer=label,
            explanation=judge_output[:500],
            metadata={
                "predicted_verdict": predicted,
                "judge_model": GROUNDEDNESS_JUDGE_MODEL,
                "judge_label": label,
                "tool_calls_seen": tool_calls_seen,
            },
        )

    return score
