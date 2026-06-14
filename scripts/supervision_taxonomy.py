#!/usr/bin/env python3
# Gov-ID: lib:supervision-taxonomy
# goal: single-source the supervision-event taxonomy so every RSI instrument
#       classifies corrections the SAME way and into a DIRECTION, not a scalar.
# verifier: scripts/tests/test_supervision_taxonomy.py
# blast_radius: local
"""Supervision taxonomy — the single source of truth for "what kind of correction is this?".

WHY THIS EXISTS (the sign-error it fixes)
-----------------------------------------
The constitutional objective is "maximize autonomy, measured by declining supervision."
The pre-existing instruments measured supervision as a WEIGHTED SCALAR
(`sli = corrections + 2*denials + 3*repeated + 5*blindspot`) and minimized it. But
supervision events are not fungible — different kinds imply OPPOSITE responses:

  • the agent was WRONG            → add a correctness guardrail   (REDUCE_ERROR)
  • the agent was TIMID            → loosen, let it act            (RAISE_AUTONOMY)
  • the agent MISSED known context → add a detector / grow recall  (GROW_COVERAGE)
  • the agent missed the human's TASTE → produce options, keep human judge (AMPLIFY_TASTE)

Summing these into one number hides the direction: a loop minimizing the scalar can't tell
"be more careful" from "stop hesitating." Worse, the old regexes were BLIND to RAISE_AUTONOMY
entirely — "why ask", "just do it", "why not build it now" matched neither the blunt-correction
nor the rediscovery pattern, so they scored zero. The failure mode most opposed to autonomy was
invisible to the autonomy metric.

THE FIX
-------
One closed taxonomy. Each correction type carries its DIRECTION (the RSI response it implies),
a deterministic tier-0 regex (high precision), and contrastive seeds (emb, paraphrase-robust).
Every consumer LOADS this — none re-states it (epistemic principle #9: a machine-checkable
invariant has ONE definition). The objective becomes a per-direction VECTOR; the autonomy
reading is a CONJUNCTION the scalar could never express:

    genuine autonomy gain  ==  RAISE_AUTONOMY ↓   AND   (REDUCE_ERROR + GROW_COVERAGE) not rising

i.e. the agent acts more freely (fewer timidity-corrections) WITHOUT erroring/missing more.

COMPOSABILITY / ENV
-------------------
Torch-free by construction (regex + dataclasses only). The emb tier is dependency-INJECTED
(`classify_emb_batch(leads, engine)`), so `supervision-kpi.py` uses it regex-only in the
agent-infra env while `blindspot_miner.py` injects `emb.EmbeddingEngine` in emb's env. numpy
is imported lazily inside the emb function — importing this module never drags in heavy deps.

INSPECTABILITY
--------------
Every classification returns a `Match` carrying its `method` (regex|emb), `score`, and
`evidence` (the regex name or nearest seed). "Why was this tagged over_caution?" is answerable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Direction(str, Enum):
    """The RSI response a correction implies. The objective is a vector over these."""

    REDUCE_ERROR = "reduce_error"        # agent was wrong → correctness guardrail; ↓ = fewer mistakes
    RAISE_AUTONOMY = "raise_autonomy"    # agent was timid → loosen; ↓ = acting freely (the pure autonomy signal)
    GROW_COVERAGE = "grow_coverage"      # agent missed existing context → detector; ↓ = better recall
    AMPLIFY_TASTE = "amplify_taste"      # taste/judgment steer → reduce production burden, keep human as judge


# Whether declining this direction's rate is, on its own, GOOD (autonomy/quality up) or merely
# AMBIGUOUS (could be the agent acting less, not better). Used to read the vector honestly.
DIRECTION_IS_AUTONOMY_GAIN: dict[Direction, bool] = {
    Direction.RAISE_AUTONOMY: True,   # fewer timidity-corrections = pure autonomy gain
    Direction.REDUCE_ERROR: True,     # fewer error-corrections = quality gain (guards the secondary constraint)
    Direction.GROW_COVERAGE: True,    # fewer rediscovery-corrections = recall gain
    Direction.AMPLIFY_TASTE: False,   # taste steers are not "errors"; their rate is a production-burden signal, not a defect
}


@dataclass(frozen=True)
class SupervisionType:
    """One correction class. `regex` may be None (emb-only). `structural` types are counted by the
    consumer (denials from tool results, repetition from similarity) rather than text-classified."""

    id: str
    direction: Direction
    weight: int            # relative supervision cost (gross-load aggregation only; NOT the objective)
    doc: str
    regex: re.Pattern | None = None
    seeds: tuple[str, ...] = ()
    structural: bool = False


@dataclass(frozen=True)
class Match:
    """An inspectable classification result."""

    type_id: str
    direction: Direction
    method: str            # "regex" | "emb"
    score: float           # 1.0 for regex hits; contrastive margin for emb
    evidence: str          # regex branch name, or nearest seed text


# ---------------------------------------------------------------------------
# THE TAXONOMY — single source. Order matters: classify_regex checks SPECIFIC,
# high-signal types before the blunt catch-all (error_correction last).
# ---------------------------------------------------------------------------

_OVER_CAUTION_RGX = re.compile(
    r"why (?:are you |did you |do you |would you )?(?:even )?ask"
    r"|why (?:not|didn'?t you|won'?t you|wouldn'?t you) (?:just )?(?:do|build|ship|act|proceed|run|go|make|fix)"
    r"|just (?:do|build|ship|run|make) it(?: now| yourself)?\b"
    r"|(?:stop|quit) asking"
    r"|you (?:don'?t|didn'?t|do not) (?:need|have) to ask"
    r"|(?:you can|you should) (?:just )?(?:decide|do|build|act|proceed)(?: that)?(?: yourself)?"
    r"|why (?:are you |did you |do you )?(?:defer|deferring|hesitat|wait|stop|stopping|pause)"
    r"|see it through"
    r"|don'?t ask (?:me |for )?(?:permission|first|before)"
    r"|no need to (?:ask|confirm|check with me)",
    re.IGNORECASE,
)

# Rediscovery == the prior "blindspot" class. Moved here VERBATIM as the single source;
# blindspot_miner.RGX and supervision-kpi.BLINDSPOT_PATTERNS were duplicate copies of this.
_REDISCOVERY_RGX = re.compile(
    r"why (?:did|didn'?t|don'?t|aren'?t|haven'?t|wouldn'?t|didnt|dont) (?:you|the loop|it|we) "
    r"(?:not |never |fail(?:ed)? to )?(?:find|catch|check|look|notice|see|spot|read|consult)"
    r"|(?:you|it) (?:should|could) have (?:found|caught|checked|looked|noticed|seen|read)"
    r"|did (?:you|the loop) (?:check|look at|read|see|notice|find|consider)"
    r"|we (?:already|just) (?:discussed|decided|did|tried|talked|covered|said)"
    r"|already (?:discussed|decided|exists|covered) "
    r"|(?:check|look at|read|consult) the (?:git|commit|log|history|ideas|docs|decision|prior|reasoning)"
    r"|you (?:didn'?t|never|forgot to) (?:check|look|read|consult|find|catch|grep)",
    re.IGNORECASE,
)

# Blunt error correction == the prior CORRECTION_PATTERNS. Start-anchored (checked on the lead);
# the consumer applies it to the message start to avoid mid-message false positives.
_ERROR_RGX = re.compile(
    r"^(?:#f\s+)?(?:no[,.\s]|not that|instead[,.\s]|that'?s wrong|wrong[,.\s]|don'?t\s|stop[,.\s]|undo\b|revert\b|that'?s (?:not right|incorrect))",
    re.IGNORECASE,
)

TAXONOMY: tuple[SupervisionType, ...] = (
    SupervisionType(
        id="over_caution",
        direction=Direction.RAISE_AUTONOMY,
        weight=3,
        doc="agent asked/deferred on a reversible action it should have just taken",
        regex=_OVER_CAUTION_RGX,
        seeds=(
            "why are you asking", "why ask", "just do it", "why didn't you just do it",
            "why not build it now", "you don't need to ask me", "stop asking and just do it",
            "why are you deferring this", "see it through when you're confident",
            "you can decide that yourself", "don't ask permission for a cheap probe",
            "why did you stop instead of continuing", "no need to confirm, go ahead",
        ),
    ),
    SupervisionType(
        id="rediscovery",
        direction=Direction.GROW_COVERAGE,
        weight=5,
        doc="agent missed existing context it should have found (git log, prior decision, existing tool/doc)",
        regex=_REDISCOVERY_RGX,
        seeds=(
            "why didn't you find this bug", "did you check the git log first",
            "you should have looked at the prior decisions", "we already discussed this",
            "you didn't check what already exists", "you keep rediscovering what we built",
            "isn't there a better tool for this", "that's already in the docs / ideas",
            "go check what exists before building", "how come you missed that",
            "why are you hand-rolling this instead of using the existing tool",
        ),
    ),
    SupervisionType(
        id="taste_steer",
        direction=Direction.AMPLIFY_TASTE,
        weight=1,
        doc="agent's output missed the human's taste/voice/judgment (not a correctness error)",
        regex=None,  # taste resists high-precision regex; emb seeds only (low recall by design)
        seeds=(
            "that's not the vibe I wanted", "this doesn't feel right",
            "that's not my taste", "the tone is off", "make it feel more like me",
            "that's not what I meant aesthetically", "this reads as generic",
        ),
    ),
    SupervisionType(
        id="error_correction",
        direction=Direction.REDUCE_ERROR,
        weight=2,
        doc="blunt correction of a wrong action (no / wrong / stop / undo / revert)",
        regex=_ERROR_RGX,
        seeds=(
            "no that's wrong", "that's not right", "stop, that's incorrect",
            "undo that", "revert that change", "no, do it differently",
        ),
    ),
    # Structural types — counted by the consumer (not text-classified), mapped to a direction here
    # so the vector is complete and single-sourced.
    SupervisionType(
        id="denial",
        direction=Direction.REDUCE_ERROR,
        weight=2,
        doc="permission denial on a tool call (agent attempted something the human refused)",
        structural=True,
    ),
    SupervisionType(
        id="repeated_instruction",
        direction=Direction.GROW_COVERAGE,
        weight=3,
        doc="human had to repeat a similar instruction (agent didn't internalize it the first time)",
        structural=True,
    ),
)

BY_ID: dict[str, SupervisionType] = {t.id: t for t in TAXONOMY}
TEXT_TYPES: tuple[SupervisionType, ...] = tuple(t for t in TAXONOMY if not t.structural)

# Baseline class for the contrastive emb tier — ordinary task instructions that are NOT
# corrections. Subtracting the nearest-normal similarity kills topical false positives
# (validated 2026-06-14: plain sim-to-seeds drowned in agent-instruction similarity).
NORMAL_SEEDS: tuple[str, ...] = (
    "add a test for the parser", "fix the bug in the resolver", "run the tests",
    "commit this and move on", "implement the feature", "what model are you using",
    "summarize the file", "check the tests pass before committing", "look at the PR",
    "deploy this", "go on", "do all three", "let's do it", "sounds good",
)

# Loose recall-preserving pre-filter: a correction almost always carries a 2nd-person /
# interrogative / recollection / imperative cue. Cuts pure task statements before embedding.
PREFILTER = re.compile(
    r"\b(you|your|why|did|didn|already|check|look|miss|should|we|isn'?t|exist|forgot|ask|just|now|stop|defer|wrong|instead)\b|\?",
    re.IGNORECASE,
)

EMB_THRESH = 0.10  # contrastive margin; tuned for precision (bench 2026-06-14: clear flags +0.19..+0.35)


def classify_regex(text: str, *, lead_chars: int = 250, tail_chars: int = 250) -> Match | None:
    """Deterministic tier-0. Returns the highest-priority matching type, or None.

    error_correction is start-anchored (checked on the stripped lead); the others are searched
    across lead+tail because the ask often lands mid-phrase ("SOOO why didn't you...") or at the
    end of a long pasted transcript.
    """
    if not text:
        return None
    t = text.strip()
    lead = t[:lead_chars]
    window = (t[:lead_chars] + "\n¦\n" + t[-tail_chars:]) if len(t) > lead_chars else t
    for st in TEXT_TYPES:
        if st.regex is None:
            continue
        hay = lead if st.id == "error_correction" else window
        m = st.regex.search(hay)
        if m:
            return Match(type_id=st.id, direction=st.direction, method="regex",
                         score=1.0, evidence=f"{st.id}:/{m.group(0)[:48]}/")
    return None


def classify_emb_batch(leads: list[str], engine) -> list[Match | None]:
    """emb tier — multi-class contrastive. `engine` must expose `embed_texts(list[str]) -> array`.

    For each lead, score against every TEXT type's seed-centroid set minus the NORMAL set
    (per-type max-sim − max-normal-sim); assign the argmax type if its margin > EMB_THRESH.
    Dependency-injected so this module stays torch-free.
    """
    import numpy as np

    def norm(xs: list[str]):
        e = np.asarray(engine.embed_texts(xs), dtype=np.float32)
        return e / (np.linalg.norm(e, axis=1, keepdims=True) + 1e-9)

    if not leads:
        return []
    types = [t for t in TEXT_TYPES if t.seeds]
    seed_mats = [norm(list(t.seeds)) for t in types]
    N = norm(list(NORMAL_SEEDS))
    E = norm(leads)
    normal_sim = (E @ N.T).max(1)  # nearest ordinary-instruction similarity per lead
    # per-type margin matrix: rows = leads, cols = types
    margins = np.stack([(E @ S.T).max(1) - normal_sim for S in seed_mats], axis=1)
    best_idx = margins.argmax(1)
    out: list[Match | None] = []
    for i, lead in enumerate(leads):
        j = int(best_idx[i])
        margin = float(margins[i, j])
        if margin > EMB_THRESH:
            st = types[j]
            # nearest seed within the winning type, for inspectability
            sims = norm([lead]) @ seed_mats[j].T
            near = st.seeds[int(sims.argmax())]
            out.append(Match(type_id=st.id, direction=st.direction, method="emb",
                             score=round(margin, 3), evidence=f"~{near!r}"))
        else:
            out.append(None)
    return out


def empty_vector() -> dict[str, int]:
    """A zeroed direction vector — the objective's shape."""
    return {d.value: 0 for d in Direction}


def add_to_vector(vec: dict[str, int], type_id: str, n: int = 1) -> None:
    """Accumulate a typed event count into the direction vector."""
    st = BY_ID.get(type_id)
    if st is not None:
        vec[st.direction.value] = vec.get(st.direction.value, 0) + n


def gross_load(vec_or_counts: dict[str, int], *, by_type: bool = False) -> int:
    """Weighted gross supervision load (a coarse total, NOT the objective). When by_type, the
    keys are type ids; otherwise direction values (weight = max type weight in that direction)."""
    if by_type:
        return sum(BY_ID[k].weight * v for k, v in vec_or_counts.items() if k in BY_ID)
    dir_weight = {d.value: max((t.weight for t in TAXONOMY if t.direction == d), default=1) for d in Direction}
    return sum(dir_weight.get(k, 1) * v for k, v in vec_or_counts.items())
