---
id: 2026-06-19-autoresearch-grounding-imports
concept: grounding-over-judge-score
repo: agent-infra
decision_date: 2026-06-19
recorded_date: 2026-06-19
provenance: contemporaneous
status: accepted
initial_leaning: "User listed 3 mechanisms (1=review calibration ladder + weakness-routing, 2=citation-quality gate, 3=phase-gated 6.0->8.5 score) and said '1 2 3 /decide' — i.e. adopt all three. REVERSED to 'adopt the grounding core, reject the holistic LLM-judge score' after Phase-0 inventory found #3 + #1-ladder conflict with a settled constitutional principle, and Phase-3 grounding found the citation-verify capability already exists."
relations:
  - type: grounded_in
    target: 2026-06-15-smart-judge-stop-hook
  - type: depends_on
    target: 2026-06-03-verifier-bound-autonomy
  - type: relates_to
    target: 2026-05-28-verify-against-ground-truth-not-model-text
  - type: relates_to
    target: 2026-06-13-rsi-outer-loop-skill
---

# 2026-06-19: Import AutoResearch's grounding core, reject its LLM-judge score

## Context

User surfaced Deli Chen's (DeepSeek) AutoResearch *paper-writing skill group*
(`victorchen96.github.io/auto_research`) and asked which mechanisms to integrate into our
shared skills, via `/decide` on three candidates:

1. Iterative-review **calibration ladder** (first-round score cap, max +Δ/round, ≥1 unresolved
   must remain, regression "previously-fixed stays fixed") + **weakness→component routing table**.
2. **Citation-quality gate** for `/research` (verify title/author/year/venue vs DBLP/OpenReview;
   ≥80% verified / 0 hallucinated; arxiv-only ratio cap; venue-upgrade; LQS scoring).
3. **Phase-gated score progression** (6.0→7.0→8.0→8.5, explicit "what's added per tier") as a
   loop template for partial-verifier loops.

We had already mined the framework's *outer-loop protocol* (`~/.claude/rules/wakeup-cadence.md` +
five RSI ADRs from `2026-06-13-rsi-outer-loop-skill.md` on). This decision covers the **skill-layer**
imports, which were not previously evaluated.

## The axis (Phase 0 reframe — the first framing was wrong)

The first framing — "adopt 1/2/3" — is wrong. Deli's mechanisms are **ground-truth checks wrapped
around a holistic LLM-judge score**. The real axis:

> **Which parts are GROUNDING (checks against ground truth) vs SCORING (a scalar LLM-judge
> proxy)? Adopt the grounding; reject the judge-score — because "ground-truth verifiers only,
> a bad eval is worse than none" is already settled here.**

Settled by: `CLAUDE.md:59` (constitution — "a model-as-judge proxy does not make taste work
verifiable; ground-truth verifiers only; Goodhart"); `2026-05-28-verify-against-ground-truth-not-model-text`;
and `research/scale-agentic-rubrics-2026-04.md` claim 5 — *LLM-generated rubric augmentation
degrades judge alignment 15–20%*; the value there is **repository-GROUNDING**, not the scalar.

## Decision (per item)

| Item | Verdict | Reason |
|---|---|---|
| #2 citation **verification as a rate-GATE** (≥80% resolved, 0 hallucinated, arxiv-only cap, venue-upgrade) | **ADOPT** | Pure ground-truth check (resolves-or-doesn't). The LQS *holistic scoring* is optional deterministic sugar — adopt the verification, treat LQS weighting as opt-in. |
| #1 weakness→component **routing table** | **ADOPT (downgraded)** | Judge-free actionability. But largely covered by `review_gate.py rank`/disposition; fold into `/improve` output formatting, do not over-build. |
| #1 **calibration ladder** | **REJECT** | (a) No host loop — `/critique` is single-shot convergence+anchor-verify, `/code-review` is a scout loop, `/improve` aggregates per-finding; nothing emits a quality score that trajectory-improves toward a target. (b) Building one re-introduces the rejected judge gate. |
| #3 **phase-gated 6.0→8.5 score** | **REJECT** | The holistic LLM-judge proxy in pure form. Our **verifier-regime operating points** (`2026-06-03`) already ARE the grounded "what does better look like." Also: `over_caution` is a top-3 violated discipline (`2026-06-15-smart-judge-stop-hook`; 56 corrections in the session-start digest) — bolting on score-gate machinery pushes toward *more* caution, our #1 measured gap. |

## Phase-3 grounding finding (reshaped #2 — Pre-Build #1)

The citation-verify **capability already exists** — we are missing the GATE + the rate METRIC,
not the resolution machinery:

- **`corpus`** resolves reference-strings → DOI/PMID (`references_resolved.json`,
  `crossref_response.json`), tracks venue/retraction (`show --depth full`) and citation stance
  (`cited-by --stance contrasting`, `contradictions`).
- **`/research`** already mandates S2/DB verification before citing, `verify_claim`, scite stance,
  and lists "Wrong DOIs → verify DOI resolves to the claimed paper."

So #2 shrinks to a **thin rate-gate over existing machinery**. Do NOT rebuild a Crossref/DBLP
client (Pre-Build #1; the vetoed "speculative shared-utility extraction").

## Alternatives considered

1. **Adopt all three as proposed** — rejected: #3 + #1-ladder are the LLM-judge gate the
   constitution + 2 ADRs + scale-rubrics memo reject; no host loop exists for them.
2. **Build a scored iterative review loop to host the ladder** — rejected: no demand; adds
   caution machinery against the over_caution gap; the regime matrix already serves the role.
3. **Build a standalone citation verifier (Crossref/DBLP client)** — rejected: `corpus` already
   resolves references (Pre-Build #1).
4. **Pure prose "verify your citations" in the skill** — rejected: instructions are ~0% reliable
   for checkable predicates (constitution P1); the gate must be a script/recipe.
5. **Adopt the grounding core (the rate-gate + routing table), reject the judge-score** ★ chosen.
6. **Just #2, skip #1 entirely** — viable; #1's routing table is marginal. Kept as a downgraded
   optional (see deferred-and-open).

## Invariants preserved

- Ground-truth verifiers only — no LLM-judge as a gate.
- Reuse proven-common machinery (`corpus`), don't extract speculatively.
- Architecture over instructions for checkable predicates (the gate is a script, not prose).

## Sign-off boundary

The `/research` (+ optional `/improve`) edits are **shared 3+ repo** changes → human gate via
`decisions-pending/2026-06-19-research-citation-verify-gate.md`. This ADR records *what to import*
(agent-infra's autonomous call); the proposal carries the diff for the shared-skill edit.

## Critique calibration (Phase 4)

`--quick` arc. Full cross-model + 6-cursor-panel adversarial review was **deliberately not run** —
over-applying it to a thin rate-gate over existing machinery is FM14 (toxic proactivity). The
disagree-self-check held: the rejects flipped on *named facts* (no host loop; corpus already
resolves; constitutional principle), not on conviction. The decisions-pending gate IS the
remaining adversarial checkpoint.
