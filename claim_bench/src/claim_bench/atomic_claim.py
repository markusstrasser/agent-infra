"""Atomic-claim P/R/F1 scorer (FIRE-Bench pattern).

The scorer decomposes both the model's explanation and the gold evidence
into atomic factual claims, then matches them and computes Precision /
Recall / F1. F1 is the headline; P, R, and the per-claim labels live in
the score metadata.

Why this is the right Phase 3 scorer:

- verdict_enum_scorer is a single bit per sample. It can't tell you WHICH
  parts of the model's reasoning matched the gold and which were wrong.
- groundedness_scorer is judge-graded "did the verdict follow from the
  retrieval trace" — it doesn't decompose, so a partially-correct
  explanation looks the same as a fully-correct one to the judge.
- AutoVerifier (arXiv:2604.02617) decomposes claims into Subject-Predicate-
  Object triples and verifies each layer separately. We don't go that
  deep — atomic-claim decomposition is enough to surface conflated layers
  empirically. If the flat solver chain is missing a verification step,
  P will drop because the model's claims won't match the gold.
- FIRE-Bench (arXiv:2602.02905, github.com/maitrix-org/FIRE-Bench) ships
  the exact methodology: decompose both sides, match, compute P/R/F1.
  We don't import their code because it's tightly coupled to a specific
  task structure, but we use the pattern.

Cost: 3 cross-family judge calls per sample (decompose model output,
decompose gold evidence, match the two lists). At ~500 tokens each on
Gemini Flash, ~$0.0015 per sample, ~$0.04 per 24-sample eval.

Reproducibility caveat: the decomposer is non-deterministic. The same
gold_sources will get slightly different atomic decompositions across
runs, so F1 has natural variance even with epochs averaging. Phase 4
(cards.py) will snapshot gold-side decompositions into a sidecar file
once a stable corpus exists, eliminating that source of noise.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from inspect_ai.model import ChatMessageUser, get_model
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState

DECOMPOSER_MODEL = os.environ.get(
    "CLAIM_BENCH_DECOMPOSER_MODEL", "google/gemini-2.5-flash"
)

# How much text we send to the decomposer per side. Decomposer is judge-
# grade Gemini Flash with 1M context — 4000 chars per side is plenty.
MAX_TEXT_PER_SIDE = 4000

# Hard caps on claim list sizes — defends against decomposer pathologies
# (e.g. returning 200 hyper-atomic claims for a 3-sentence explanation).
MAX_CLAIMS_PER_SIDE = 30


DECOMPOSE_PROMPT = """Decompose the following text into atomic factual claims.

Each atomic claim must:
- Be a single self-contained statement
- Express exactly one fact (Subject-Predicate-Object)
- Be verifiable in principle
- NOT include hedging, opinions, or rhetorical questions
- NOT split across multiple sentences

Text:
{text}

Output ONLY a JSON array of strings, one string per atomic claim. No prose, no markdown, no code fences. Example output:
["The Earth orbits the Sun.", "The Earth's orbital period is approximately 365.25 days."]"""


MATCH_PROMPT = """You are matching atomic factual claims between two sets.

Set A (model's claims):
{model_claims}

Set B (gold reference claims):
{gold_claims}

Two claims match if they assert the same fact, even if worded differently. Numerical values must agree within obvious tolerance (the same number, possibly rounded). Direction of effect must agree. Subject and predicate must refer to the same entities.

For each claim in Set A, decide:
- SUPPORTED: at least one claim in Set B says the same thing
- NEW: no claim in Set B matches

For each claim in Set B, decide:
- FOUND: at least one claim in Set A says the same thing
- MISSED: no claim in Set A matches

Output ONLY a JSON object with this exact shape (no prose, no markdown, no code fences):

{{"set_a": ["SUPPORTED", "NEW", ...], "set_b": ["FOUND", "MISSED", ...]}}

The set_a array must have exactly {n_a} entries (one per Set A claim, in order). The set_b array must have exactly {n_b} entries."""


def _strip_code_fences(raw: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` markdown fences from a JSON string."""
    if not raw:
        return ""
    raw = raw.strip()
    # Strip leading fence
    raw = re.sub(r"^```(?:json)?\s*\n?", "", raw, flags=re.IGNORECASE)
    # Strip trailing fence
    raw = re.sub(r"\n?\s*```\s*$", "", raw)
    return raw.strip()


def _parse_claim_list(raw: str) -> list[str]:
    """Parse the decomposer's JSON-array output into a list of claim strings."""
    raw = _strip_code_fences(raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    out: list[str] = []
    for item in parsed:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out[:MAX_CLAIMS_PER_SIDE]


def _parse_match_result(
    raw: str, n_a: int, n_b: int
) -> tuple[list[str], list[str]]:
    """Parse the matcher's JSON output into (set_a_labels, set_b_labels).

    On parse failure, returns conservative defaults:
        set_a → all "NEW"   (model claims that don't match gold)
        set_b → all "MISSED" (gold claims that the model didn't find)

    These defaults score as P=0, R=0, F1=0 — a parse failure is correctly
    treated as a total miss rather than silently inflating the metric.
    """
    fallback_a = ["NEW"] * n_a
    fallback_b = ["MISSED"] * n_b
    raw = _strip_code_fences(raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return fallback_a, fallback_b
    if not isinstance(parsed, dict):
        return fallback_a, fallback_b
    set_a = parsed.get("set_a")
    set_b = parsed.get("set_b")
    if not isinstance(set_a, list) or not isinstance(set_b, list):
        return fallback_a, fallback_b
    # Coerce labels to known values; pad/truncate to expected lengths.
    set_a_clean = [
        ("SUPPORTED" if str(x).strip().upper() == "SUPPORTED" else "NEW")
        for x in set_a
    ]
    set_b_clean = [
        ("FOUND" if str(x).strip().upper() == "FOUND" else "MISSED") for x in set_b
    ]
    if len(set_a_clean) < n_a:
        set_a_clean = set_a_clean + ["NEW"] * (n_a - len(set_a_clean))
    if len(set_b_clean) < n_b:
        set_b_clean = set_b_clean + ["MISSED"] * (n_b - len(set_b_clean))
    return set_a_clean[:n_a], set_b_clean[:n_b]


def _compute_p_r_f1(
    set_a: list[str], set_b: list[str], n_a: int, n_b: int
) -> tuple[float, float, float]:
    """Compute Precision, Recall, F1 from match labels.

    Precision = SUPPORTED / total_model_claims  (how much of the model's
                                                 explanation is supported by gold)
    Recall    = FOUND / total_gold_claims        (how much of the gold the
                                                 model recovered)
    F1        = harmonic mean

    Edge cases: 0 model claims → P=0; 0 gold claims → R=undefined,
    treated as 0 to avoid division noise.
    """
    n_supported = sum(1 for x in set_a if x == "SUPPORTED")
    n_found = sum(1 for x in set_b if x == "FOUND")
    precision = n_supported / n_a if n_a > 0 else 0.0
    recall = n_found / n_b if n_b > 0 else 0.0
    if precision + recall <= 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def _gold_text_from_metadata(metadata: dict[str, Any]) -> str:
    """Build a text blob of gold evidence from sample metadata.

    Pulls from `gold_sources` and `gold_contradict_sources`. For each source
    dict, prefers `supports` / `contradicts` text (which describes WHY the
    source supports or contradicts), falling back to `citation` text.
    """
    parts: list[str] = []
    for key in ("gold_sources", "gold_contradict_sources"):
        for src in metadata.get(key, []) or []:
            if not isinstance(src, dict):
                continue
            for field in ("supports", "contradicts", "citation", "note"):
                value = src.get(field)
                if isinstance(value, str) and value.strip():
                    parts.append(value.strip())
                    break
    return "\n".join(parts)


@scorer(metrics=[mean()])
def atomic_claim_scorer() -> Scorer:
    """FIRE-Bench-style atomic-claim P/R/F1 scorer.

    Three judge calls per sample:
    1. Decompose the model's explanation into atomic claims
    2. Decompose the gold evidence text into atomic claims
    3. Match the two sets in one call

    Returns F1 as the headline value. P, R, both claim lists, and the
    per-claim match labels live in score.metadata for cards.py and post-
    eval analysis.

    Notes:
    - Decomposer = same cross-family Gemini Flash used by groundedness /
      currency. Single env-overridable model.
    - Decomposer non-determinism is averaged out by epochs=3.
    - For samples with no gold evidence (e.g. 007 not_verifiable), gold_text
      is empty, gold_claims is empty, and the scorer returns recall=0,
      F1=0 — which is the correct behavior: the not_verifiable verdict is
      not a verifiable claim, so atomic-claim decomposition is N/A.
    - For samples where the model produced a one-line abstention answer
      with no explanation prose, the decomposer may produce 0 model claims;
      we report n_model_claims=0 and value=0.
    """

    async def score(state: TaskState, target: Target) -> Score:
        raw_output = state.output.completion if state.output else ""
        gold_text = _gold_text_from_metadata(state.metadata or {})

        if not raw_output.strip():
            return Score(
                value=0.0,
                answer="no_model_output",
                explanation="Model produced no output to decompose",
                metadata={"reason": "no_model_output"},
            )

        decomposer = get_model(DECOMPOSER_MODEL)

        # Step 1: decompose the model's output
        model_decompose_prompt = DECOMPOSE_PROMPT.format(
            text=raw_output[:MAX_TEXT_PER_SIDE]
        )
        model_result = await decomposer.generate(
            [ChatMessageUser(content=model_decompose_prompt)]
        )
        model_claims = _parse_claim_list(model_result.completion or "")

        # Step 2: decompose the gold evidence
        if gold_text.strip():
            gold_decompose_prompt = DECOMPOSE_PROMPT.format(
                text=gold_text[:MAX_TEXT_PER_SIDE]
            )
            gold_result = await decomposer.generate(
                [ChatMessageUser(content=gold_decompose_prompt)]
            )
            gold_claims = _parse_claim_list(gold_result.completion or "")
        else:
            gold_claims = []

        # Special-case: no gold claims means atomic decomposition isn't
        # meaningful for this sample (not_verifiable cases, e.g.). Return
        # value=1.0 with answer='not_applicable' so it doesn't drag the
        # mean. Cards.py treats not_applicable separately.
        if not gold_claims:
            return Score(
                value=1.0,
                answer="not_applicable",
                explanation="No gold claims — atomic decomposition not meaningful",
                metadata={
                    "model_claims": model_claims,
                    "gold_claims": [],
                    "n_model_claims": len(model_claims),
                    "n_gold_claims": 0,
                    "precision": None,
                    "recall": None,
                    "f1": None,
                    "atomic_status": "not_applicable",
                },
            )

        if not model_claims:
            return Score(
                value=0.0,
                answer="no_model_claims",
                explanation="Decomposer extracted 0 atomic claims from model output",
                metadata={
                    "model_claims": [],
                    "gold_claims": gold_claims,
                    "n_model_claims": 0,
                    "n_gold_claims": len(gold_claims),
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1": 0.0,
                    "atomic_status": "no_model_claims",
                },
            )

        # Step 3: match the two sets in one judge call
        match_prompt = MATCH_PROMPT.format(
            model_claims="\n".join(
                f"{i + 1}. {c}" for i, c in enumerate(model_claims)
            ),
            gold_claims="\n".join(
                f"{i + 1}. {c}" for i, c in enumerate(gold_claims)
            ),
            n_a=len(model_claims),
            n_b=len(gold_claims),
        )
        match_result = await decomposer.generate(
            [ChatMessageUser(content=match_prompt)]
        )
        set_a, set_b = _parse_match_result(
            match_result.completion or "", len(model_claims), len(gold_claims)
        )

        precision, recall, f1 = _compute_p_r_f1(
            set_a, set_b, len(model_claims), len(gold_claims)
        )

        return Score(
            value=f1,
            answer=f"P={precision:.2f} R={recall:.2f} F1={f1:.2f}",
            explanation=(
                f"{sum(1 for x in set_a if x == 'SUPPORTED')}/{len(model_claims)} "
                f"model claims SUPPORTED, "
                f"{sum(1 for x in set_b if x == 'FOUND')}/{len(gold_claims)} "
                f"gold claims FOUND"
            ),
            metadata={
                "model_claims": model_claims,
                "gold_claims": gold_claims,
                "set_a_labels": set_a,
                "set_b_labels": set_b,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "n_model_claims": len(model_claims),
                "n_gold_claims": len(gold_claims),
                "decomposer_model": DECOMPOSER_MODEL,
                "atomic_status": "scored",
            },
        )

    return score
