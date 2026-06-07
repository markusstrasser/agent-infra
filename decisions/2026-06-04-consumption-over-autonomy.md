---
id: 2026-06-04-consumption-over-autonomy
concept: autonomy-vs-judgment-coupling
repo: agent-infra
decision_date: 2026-06-04
recorded_date: 2026-06-04
provenance: contemporaneous
status: proposed
initial_leaning: "two constitutional refinements + one unification; constitution/GOALS edits human-gated"
relations:
  - type: depends_on
    target: 2026-06-03-verifier-bound-autonomy
---

# 2026-06-04: Consumption over autonomy — two governance refinements + one unification

> **Constitution and GOALS.md are human-protected. Everything below that touches
> them is PROPOSED and awaits explicit approval. The decision-record itself and
> the shared-infra sketch are within meta's autonomy; the principle/metric edits
> are not.**

## What prompted this
A session that (a) inverted the "300 orphan tools" framing into a lint-blindness
fix, (b) ran the verifier-bound eval (cross-lab gate NOT justified at seeded-defect
difficulty — count-delta suffices), and (c) dogfooded the investing "knowability
loop" on a real memory divergence (intel research/2026-06-04_nand_coverage_gap).
Three unrelated workstreams surfaced the **same** failure and the **same**
mismatch.

## Finding 1 — The cross-cutting disease is generation-without-consumption
The system is good at GENERATING (research, detectors, signals, theses) and poor
at CONSUMING (converting them into decisions/positions/fixes). Evidence, now ≥4
instances across repos:
- corpus drift audit fired daily (exit 1) into a void for weeks (2026-06-03 incident).
- source_eval resolve-heartbeat FAILed daily, unconsumed (intel/genomics diagnosis).
- orphan lint was 65% false-positive — noise that trains agents to ignore it.
- **intel memory thesis: NAND ASP +292% was in the book's OWN 2026-05-24 notes;
  no NAND pure-play was ever added to coverage; SK Hynix stayed WATCHLIST 0%
  through ~+30%.**

This generalizes the verifier-bound thesis: **a verifier (or detector, or
research finding) with no consumer is equivalent to no verifier.** Generation is
cheap with agents; consumption is the bottleneck. The waste to hunt is not tool
sprawl or lint noise (symptoms) — it is unconsumed generation (the disease).

**PROPOSED constitutional principle (human-gated):** add a *Consumption* principle —
every detector/generator must name its consumer; unconsumed generation is the
primary measured waste; "fires into a void" is a defect class, not a nuance.
Operationalized by the consumed-alert spine in Finding 3.

## Finding 2 — The autonomy metric is the wrong yardstick for the judgment-coupled core
The Generative Principle ("maximize the rate of declining supervision") is correct
for *systematizable* work (the part machines can close a loop around). It is
**backwards** for the judgment-coupled core — secular-technology / compounding
investing (Thiel/Aschenbrenner archetype, which is what intel actually is: the
AI-buildout/power/compute book). There the point is *high* human-judgment coupling
on a few deep calls; the human (taste for durable trajectories, conviction to sit
still) is the irreplaceable input and the fleet's job is to *feed* judgment, not
replace it. Autonomy-maximization structurally pulls toward the systematizable
13%-with-fees grinder and away from the few deep bets that actually compound.

**PROPOSED GOALS/constitution refinement (human-gated):** split work into two
regimes with different metrics —
- **AUTOMATE-able** (mechanical, verifiable): metric = declining supervision (unchanged).
- **AMPLIFY-able** (judgment-coupled: theses, secular-tech calls, taste): metric =
  *depth of judgment per decision* + *consumption rate of generated signal*, NOT
  declining supervision. Keep the human in the loop by design; measure whether the
  fleet deepened the call, not whether it removed the human.

> **[2026-06-07 — GENERALIZED + APPLIED]** Ratified and generalized into
> `2026-06-07-verifier-conditional-autonomy` (applied to the constitution with
> Markus's approval). Changes from the form above: (1) discriminator is **verifier
> quality, not domain** — keys on whether a clear ground-truth verifier exists,
> generalizing past investing to writing/art/STEM. (2) **Third regime added**
> (partial/noisy/delayed → bounded autonomy) — the two-way split was a false binary
> (cross-model review). (3) The "consumption rate" *maximand* is **replaced** — as
> worded it incentivizes flooding the human; the live metric is principal-attention
> *efficiency*, with consumption kept only as a *floor* (no generation without a
> named consumer). Findings 1 and 3 remain PROPOSED.

## Finding 3 — Unify: one consume-or-escalate spine, not N detectors-into-void
The three loops (corpus drift, orphan GC, investing knowability) are one pattern:
detect divergence → post-mortem (noise / real / knowable) → upgrade the model.
Today each is bespoke and most fire into a void.

**Sketch (within meta autonomy to prototype; not yet built):** make `consumed-alert`
first-class shared infra — every detector routes its signal to a named consumer and
emits a *consumption receipt*; signals unconsumed past a threshold escalate (to a
human surface), they don't silently expire. This SIMPLIFIES by replacing N
detector-into-void patterns with one spine, and it is the operational form of
Finding 1. Pre-existing pending item ("make audit_corpus_sync abandoned_total
exit-affecting + routed to a consumer") is the first instance.

## What is NOT proposed
- No edit to constitution/GOALS without human sign-off (hard limit).
- No new scored-quality gate (vetoed 2026-06-01) — consumption is a routing/receipt
  property, not a composite score.
- No mass tooling rebuild — the spine wraps existing detectors.

## Pre-registered test
If the Consumption principle + spine are adopted: within 30 days, every standing
detector (corpus drift, source_eval, orphan lint, divergence) has a named consumer
and a non-void escalation path; zero "fired daily into a void for weeks" incidents
recur.
