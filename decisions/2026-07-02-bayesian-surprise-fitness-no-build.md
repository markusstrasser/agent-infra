---
id: 2026-07-02-bayesian-surprise-fitness-no-build
date: 2026-07-02
status: decided
relates_to:
  - 2026-06-20-dynamics-decay-salience-no-build
  - 2026-06-07-verifier-conditional-autonomy
tags: [rsi, brainstorm, creativity-fitness, anti-over-build, autodiscovery]
supersedes_disposition: ".brainstorm/2026-07-02-creativity-verticals-d793e21a/synthesis.md#1 (EXPLORE → PARK)"
---

# Bayesian-surprise fitness for idea selection — NO-BUILD (now), PARK with trigger

## Decision
Do **not** build a Bayesian-surprise fitness signal (score an idea by the posterior shift it
causes in a cheap predictor) for either consumer named in the 2026-07-02 creativity-verticals
brainstorm. Phase-0 grounding of the `/decide` arc dissolved the decision before divergence: the
two consumers split, and each is already resolved by an existing artifact or falls the pain-point
gate. The synthesis's #1 disposition drops **EXPLORE → PARK**.

## Why (the axis, and why it collapsed)
The real axis is **not** "LLM-rating vs ground-truthable surprise." It is **"is idea-selection a
scoring-signal gap, or is it already served by the emb layer + the disposition table?"** Grounding
answers it:

**Consumer B — RSI ranker (`top_priorities.py`): REJECT (category mismatch + already vetoed).**
The ranker scores *already-actionable items* (broken tools=100, pending-decisions=80, open-findings=60),
not ideas. "Epistemic surprise" has no meaning for a broken tool's priority. And the
[2026-06-20 decay-salience veto](2026-06-20-dynamics-decay-salience-no-build.md) already killed
*any* scoring engine over this ranker via a read-only ablation: its real gap is **one sort key
(`days_since_last_touch`)**, not a fitness engine. Nothing here reopens that.

**Consumer A — `/brainstorm` Step 4/5 selection: PARK (buildable-cheap form already decided; no incident).**
Three independent grounds:
1. **The "cheap predictor" is the emb layer, and the buildable-cheap surprise metric is embedding
   distance — NOT a Bayesian posterior.** `scripts/export_sessions_for_emb.py` + the `emb` CLI already
   exist. The 2026-06-19 evolutionary-frameworks memo already measured this exact question for the
   evolver: **embedding-based novelty rejection (cosine on the mutated block) is "the whole win"; the
   LLM-judge/posterior stage is only marginal — skip it.** So the *specific* proposal (posterior shift
   over a predictor) is the EFE-style overbuild the 2026-06-16 predictive-arch memo explicitly said
   **"DON'T import … just do the cheap version."** The frontier the proposal claims to open is already
   a tooled-agent capability (`emb search`/`emb pairs`), failing the edge/moat kill-switch.
2. **No incident.** Pain-point gate: `git log` + memory grep found **zero** cases where Step 4/5
   selection mis-picked or an LLM-novelty rating misled. Absence of a feature ≠ presence of a problem
   (brainstorm Known-Issue 2026-03-26: 6/7 layers defended hypotheticals).
3. **Goodhart risk is live, not hypothetical.** Constitution: "a bad eval is worse than none";
   epistemic principle #8 (in-sample proxy Goodharts an OOD principal). AutoDiscovery's surprise
   reward is validated where a *ground-truth predictor over data* exists (scientific hypotheses);
   free-form infra ideas have no such oracle, so a surprise proxy risks ranking *weird* over *good*.
   Divergent mode also **bans evaluation during generation** — a score could only ever be a Step-3.5
   labeled coverage-matrix *column*, never a silent selector.

## What WOULD be built, if the trigger fires
Not an engine. An optional, **labeled** `surprise` column in `matrix.json`, computed as
mean cosine distance of an idea's embedding from the prior-ideas set (via the existing `emb` layer) —
a screen the operator reads, never an autonomous selector. Scope stays inside `/brainstorm` Step 3.5;
zero new store, zero RSI-loop coupling.

## Resurrection trigger (pre-registered, per `preregister-triggers-beat-elegant-theses`)
Build the labeled emb-distance column ONLY if a brainstorm run is recorded where the disposition
table demonstrably picked a worse idea than a higher-novelty parked one, in ≥2 sessions. "It would
be principled" is **not** a trigger. Retuning to a posterior/KL metric is NOT a valid path — the
cheap embedding form is the measured win.

## #2 anomaly self-seeding (noted, not decided here)
Its "is this anomaly interesting" gate was the stated dependency on #1. That gate resolves to the
same emb-distance-from-known screen, so the dependency is cheaply satisfiable — but #2 is separately
RSI-loop infra and stays PARKED behind its own consumer/incident gate. Not opened by this decision.

## Provenance
Source: `.brainstorm/2026-07-02-creativity-verticals-d793e21a/synthesis.md` (#1, #2). Arc: `/decide`
Phase 0 (scope gate failed at grounding — no full fan-out, per skill's over-application guard).
Prior art read: decay-salience veto (2026-06-20), evolutionary-frameworks memo (2026-06-19),
predictive-arch/RSI memo (2026-06-16).
