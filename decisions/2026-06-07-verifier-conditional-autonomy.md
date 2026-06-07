---
id: 2026-06-07-verifier-conditional-autonomy
concept: autonomy-vs-judgment-coupling
repo: agent-infra
decision_date: 2026-06-07
recorded_date: 2026-06-07
provenance: contemporaneous
status: accepted
initial_leaning: "ratify + sharpen the pending 2026-06-04 AMPLIFY/AUTOMATE split by making the discriminator explicit (verifiability, not domain); REVISED after cross-model review to a three-regime model with domain-as-prior and a non-perverse metric; constitution/GOALS edits human-gated"
relations:
  - type: branches_from
    target: 2026-06-04-consumption-over-autonomy
  - type: depends_on
    target: 2026-06-07-guardian-angels-transfer
---

# 2026-06-07: Verifier-conditioned autonomy — amend the Generative Principle

> **APPLIED 2026-06-07 with Markus's explicit approval ("Alright let's go").**
> The redline is live in CLAUDE.md (Generative Principle → Verifier-conditioned
> scope) and GOALS.md (Generative Principle + Primary Success Metric). The
> `interview-prompt` answer *motivated* the amendment; the explicit go-ahead on
> this record's redline is the approval. Constitution/GOALS remain human-owned —
> further changes still require sign-off.

## What prompted this
Two threads converged:
1. The `interview-prompt` smoke-test (2026-06-07, route: feedback) asked the
   amplify-vs-automate telos fork **directly**. Markus: *"Depends on domain and if
   there's a clear verifier/eval — art/writing/taste/visuals is me; engineering,
   optimization, domain-knowledge of STEM, math is agents better than me."* He
   gave the **same** register-split for voice-emulation. Captured in feedback
   memory `feedback-amplify-automate-by-verifiability`. **Note he said domain
   AND verifier — not "ignore domain."**
2. The pending proposal `2026-06-04-consumption-over-autonomy` Finding 2 already
   argued the autonomy metric is the wrong yardstick for the judgment-coupled
   core and proposed an AUTOMATE/AMPLIFY split — framed as **domain**
   (intel = secular-tech investing), unratified, human-gated.

## The tension being resolved
The Generative Principle (CLAUDE.md + GOALS.md) reads, unconditionally:
*"Autonomy is the primary objective… measured by declining supervision."* Per
Markus, the right objective is **conditional on whether the work can be checked
against ground truth**. Where the verifier is him (irreducibly subjective taste),
declining-supervision is the wrong objective — the goal is to deepen and extend
*his* judgment, not remove him.

## Alternatives considered (how to encode it)
1. **Leave it in memory only** — *rejected*. The Generative Principle is the root
   every session reads; a known-conditional principle stated unconditionally keeps
   agents optimizing declining-supervision in taste work (autonomous essay
   authoring, over-automated conviction calls). Per P1, if it matters it goes in
   the architecture, and the constitution *is* the architecture.
2. **New standalone principle** — *rejected*. The conditioning belongs *on* the
   north star, not floating beside it.
3. **Two-way split (verifiable vs verifier-is-him)** — the original draft.
   *Rejected after cross-model review*: it's a false binary. Both reviewers
   (Gemini 3.5 Flash, GPT-5.5) independently flagged that the **common** case is
   *partial/noisy/delayed* verification (research synthesis, code review,
   investing theses, architecture) — stranded by a binary.
4. **Three-regime, verifier-quality-graded, domain-as-prior** (chosen) — see
   below.
5. **Pursue the in-weight GBT** to close the verifier-is-him gap by emulation —
   *rejected this session* (`2026-06-07-guardian-angels-transfer`, "accept the
   ceiling").

## Counterevidence sought
- *Does any verifier-is-him work benefit from declining supervision?* Yes —
  Markus's own Q3 ("depends on register"): throwaway/correspondence/structure are
  cheap-to-verify and fine to automate. This **confirms** the discriminator at
  register granularity rather than refuting it.
- *Is "verifiability" too vague?* Partly — addressed by grading verifier *quality*
  and keeping domain as a prior (§Discriminator), not by a clean slogan.
- Found no case where the unconditional reading is what he actually wants.

## Proposed amendment (PROPOSED — human-gated, not applied)

### Three regimes, by verifier quality (domain is a prior, not the test)

| Regime | Verifier | Objective | Behavior |
|--------|----------|-----------|----------|
| **Clear** | clear, trusted, cheap ground-truth (tests, proofs, benchmarks, deterministic checks) | **AUTOMATE** — maximize autonomy | run, fix, iterate; step the human back |
| **Partial** *(the common case)* | noisy/delayed/proxy (research synthesis, code review, investing theses, architecture, product strategy) | **BOUNDED autonomy** | gather evidence, generate options, run checks, expose assumptions, produce *reversible* drafts, recommend — preserve human checkpoints at uncertainty / risk / irreversible / taste boundaries |
| **Principal-final** | the principal (taste, voice, aesthetics, conviction) | **AMPLIFY** | autonomously produce options/critiques/reversible drafts; the principal is the **final judge** at every taste/conviction/irreversible point |

**CLAUDE.md, `<constitution>` → Generative Principle.** Append after the
"arms race" paragraph:

> **Verifier-conditioned scope.** The objective is conditioned on whether the
> work can be checked against ground truth — graded, not binary. **Verifier
> quality is the task-level test** (is there a *clear, trusted, independent,
> cheap-enough* verifier for this claim/output?); **domain is a fast prior, not
> the test.** Three regimes: (1) *clear verifier* → **automate**, push declining
> supervision hard. (2) *partial / noisy / delayed verifier* (the common case:
> research synthesis, code review, investing theses, architecture) → **bounded
> autonomy** — gather evidence, generate options, run checks, expose assumptions,
> produce reversible drafts, recommend; keep human checkpoints at uncertainty /
> risk / irreversible / taste boundaries. (3) *the verifier is the principal*
> (taste, voice, conviction) → **amplify** — reduce the principal's *production*
> burden (autonomously generate options and reversible drafts) while preserving
> the principal's *judgment* supervision (he is the final judge). A model-as-judge
> proxy does **not** make taste work "verifiable" — ground-truth verifiers only;
> a bad eval is worse than none (Goodhart). Decompose: a taste call on top of
> checkable subtasks → automate the subtasks. The discriminator runs at
> register/task granularity, not whole-project.

This dissolves the "30 ideas, yes/no" point: that endgame is **amplify done
right** — autonomous *production* (generate the 30), retained *judgment* (he says
yes/no). Amplify means declining *production* supervision, not declining judgment
supervision.

**GOALS.md → Primary Success Metric.** Replace the single ratio with per-regime
metrics (and drop "maximize consumption rate" — a raw maximand incentivizes
flooding the human; an attention-vampire failure mode flagged by both reviewers):

> - **Clear-verifier autonomy rate** — autonomous/supervised ratio (the existing
>   metric), scoped to checkable work.
> - **Partial-verifier bounded-autonomy rate** — how much evidence/option/draft
>   work the fleet does per human checkpoint, without skipping risk boundaries.
> - **Principal-attention efficiency** — decision *density* and option *contrast*
>   per human turn; explicitly **not** generation volume. (This is the
>   Consumption principle as a *floor* — no generation without a named consumer —
>   not a maximand.)

This subsumes and *generalizes* Finding 2 of `2026-06-04-consumption-over-autonomy`
(domain → verifier-quality) and binds to Finding 1 (consumption as a floor).

### Anti-gaming (the real risk: mislabel hard work as "taste" to dodge the metric)
- Each task/session declares one regime: **clear / partial / principal-final**.
- Declaring **principal-final** requires naming *what exactly is non-delegable*.
- Reclassifying clear/partial → principal-final **mid-session** (especially after
  failing a hard task) logs as an **autonomy-exception**, not a silent goalpost
  move. "Unknown/uncertain" defaults to *partial* (bounded autonomy), never to
  principal-final.

## Where I reconciled vs adopted the review wholesale
Both reviewers nudged investing/conviction calls into *partial-verifier*, away
from *principal-final*. I **partially held**: per
`2026-06-04-consumption-over-autonomy`, intel's secular-tech core is AMPLIFY
because the conviction-to-sit-still is the irreplaceable human input. Resolution
(compatible with both): a thesis is **partial-verifier on process** (falsifiable
sub-claims, base rates, delayed outcomes are checkable → bounded autonomy) AND
**principal-final on conviction** (the sit-still call → his). The decompose rule
handles it; I did not collapse conviction into "partial."

## Risks
- **"Verifier quality" is a soft predicate** — a steering principle, not a hook
  (P1 semantic-predicate exception). No deterministic enforcement claimed; the
  declare-the-regime + autonomy-exception logging is the lightest check.
- **Under-automation excuse** ("this is taste, I'll ask") — closed by: default-to-
  partial, principal-final must name the non-delegable, decompose checkable
  subtasks.
- **Bad proxy verifiers** (Goodhart) — explicitly excluded; ground-truth only.

## Cross-model review (2026-06-07, Gemini 3.5 Flash + GPT-5.5)
Both dispatched adversarially on the *original two-way draft*; verdicts converged:
- **Consent overreach** (GPT) — draft said the interview "ratifies / supplies
  sign-off." It doesn't. **Fixed**: interview *motivates*; redline still needs
  Markus's yes/no.
- **False binary → add partial-verifier regime** (both, top objection) — **fixed**
  (three regimes).
- **"verifiability not domain" over-simplifies "domain AND verifier"** (both) —
  **fixed**: verifier-quality is the test, domain is a prior.
- **"maximize consumption rate" is perverse / attention-vampire** (Gemini) —
  **fixed**: consumption is a *floor* (named consumer), metric is attention
  *efficiency* (density/contrast), not volume.
- **amplify ≠ "not declining supervision"** (both) — **fixed**: declining
  *production* supervision + retained *judgment* supervision; dissolves the "30
  ideas" contradiction.
- **Gaming mitigation was "vibes"** (both) — **fixed**: declare-regime +
  name-the-non-delegable + reclassification-as-exception + default-to-partial.
- **Held**: investing/conviction stays principal-final-on-conviction (see above).
Raw reviews: `/tmp/vca-gemini.md`, `/tmp/vca-gpt.md` (transient).

## Pre-registered test
If adopted: within 30 days, (a) zero sessions push autonomous authoring of
long-form essays / conviction calls under the declining-supervision banner; (b)
session-analyst's classification keys on verifier-quality + regime, not project
label; (c) the per-regime metrics are live in GOALS.md; (d) ≥1 logged
autonomy-exception (reclassification) appears, proving the anti-gaming check
fires. If none change observable behavior in 30 days, the amendment was
decorative — revert.

## What is NOT proposed
- No edit applied without Markus's sign-off (hard limit #1).
- No new scored-quality gate (vetoed 2026-06-01) — regimes are a routing/declare
  property, not a composite score.
- No GBT / in-weight personalization (rejected `2026-06-07-guardian-angels-transfer`).
