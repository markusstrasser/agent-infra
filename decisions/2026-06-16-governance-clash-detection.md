---
date: 2026-06-16
status: proposed
concept: governance-clash-detection
supersedes: []
related:
  - decisions/2026-06-16-loop-core-rsi-ledger-factoring.md
  - .claude/rules/vetoed-decisions.md
  - skills/critique/SKILL.md  # curated-governance (the shared substrate)
provenance: user-directed (Markus, 2026-06-16) + probe-validated core assumption
---

# Governance clash-detection — make pushback architectural

## The axis

The constitution already **mandates** that I flag a user request clashing with a goal,
principle, or prior decision (`<technical_pushback>`: "No is a valid answer";
domain-weighted authority; provisional-by-construction). But that lives as
*instructions* → ~0% reliable (Principle 1). Markus's ask: **make it architecture.**

Unifying insight: **relevant-governance-retrieval is ONE substrate with TWO consumers.**
- **Critique** *injects* the relevant principles for a reviewer (the curated-governance
  fix, skills@1792128).
- **Clash-detection** *checks the user's message against* the relevant principles.
Same retrieval, opposite direction. Build the index once.

## Divergent options (mechanism for detect + surface)

1. **UserPromptSubmit prompt-hook + compact governance index** — fires on the user's
   message (the right event), cheap LLM judges clash against a thin index, injects an
   advisory flag. *(selected)*
2. Embedding-retrieval + LLM-judge over a governance vector store — abstract principles
   embed poorly; over-engineered; embedding-stack class already vetoed. *Rejected.*
3. Main agent self-checks via a `just check-intent` scaffold — relies on the agent
   remembering to run it (the instruction-reliability hole). *Rejected as primary.*
4. Corpus belief-ledger as substrate (content-addressed claims + contradiction) — the
   corpus is for research evidence, not design intent; cross-repo contradiction layer
   was vetoed (0 observed). *Rejected as substrate; borrow only its supersession model.*
5. Post-hoc session-analyst detection — too late to flag in the moment. *Kept as the
   CALIBRATION layer, not the live detector.*
6. Cross-model review on every consequential directive — too heavy per-message.
   *Rejected; reserve for explicitly consequential design packets.*

## Selection + probe evidence

**Selected: option 1**, scoped by a core-assumption probe (2026-06-16, gemini-3-flash,
8 grounded cases). **Precision 5/5 (zero false positives); recall 5/6.** Every *concrete*
clash (vetoed-decisions, breaking-by-default, proven-common) caught with the right
citation; the single miss was the *abstract* principle (blind-first-pass). Precision is
the metric that matters (false positives train the user to disable it) — and it was
perfect on the concrete tier.

## Scoping (from the probe)

- **Tier 1 — ship-able, ~perfect precision:** clash vs `vetoed-decisions.md` + the SHARP
  principles (breaking-by-default, proven-common-extraction, P8-silent-proxy). Concrete,
  already indexed, unambiguous. `vetoed-decisions.md` *literally exists* to be checked
  before proposing — this hook auto-checks it instead of relying on agent memory.
- **Tier 2 — harder, advisory-only, high threshold:** abstract principles (blind-first-
  pass, declining-supervision). Lower recall; surface only at high confidence.

## The real gap it exposes

Goals (`GOALS.md`), principles (constitution), and vetoes (`vetoed-decisions.md`) are
durably captured and queryable. **Markus's running PRODUCT/DESIGN INTENT across sessions
is NOT** — so "clash with previous *intent*" has no substrate to check against. The
missing piece: an **append-only design-intent ledger** (capture his design intents as
expressed; clash-check new directives against them). This is the load-bearing dependency
for the "previous intent" half of the request, and a plan-gated step (don't build the
ledger until the Tier-1 hook proves precise on the *existing* indexes).

## Closure — clash-detector IS the governance-staleness sensor

When a flagged clash is confirmed an **intentional override**, that is a belief-change:
mark the superseded item append-only (borrow the corpus supersession model). Repeated
overrides of principle X = X no longer serves → feed `gov-shrink` (governance shrinks as
IQ rises). So the detector is not a nag — it is the INPUT that keeps governance current:
surface tension → human resolves → supersede stale OR agent adjusts. RSI loop closure.

## Plan (shadow-first — no iatrogenic harm)

1. **Build the compact governance index** (shared with critique's curated-governance):
   vetoed-decisions lines + sharp-principle one-liners + GOALS core. Single source.
2. **Tier-1 clash-hook in SHADOW MODE** (UserPromptSubmit, directive-class messages
   only): log what it *would* flag to `~/.claude/clash-shadow.jsonl`, surface nothing.
3. **Measure live precision** over ~2 weeks of real messages (session-analyst scores the
   shadow log). Promote to advisory-surfacing ONLY if precision stays ≥ the probe's bar.
4. **Then** Tier-2 abstract principles + the design-intent ledger + the gov-shrink feed.

First slice: the index + the shadow hook. HALT-gate: if shadow precision on real
messages is materially below 5/5, narrow the index (Tier-1 concrete only) before any
surfacing.

## Risks

- **Noise = death.** Mitigated: directive-class gate, shadow-first, advisory-only, high
  threshold, concrete-tier-first.
- **Cheap-model recall on abstract principles is low** (probe: 1/1 miss). Accepted: Tier
  2 is explicitly lower-confidence; don't oversell it.
- **The hook model is Haiku in production** (not the probed gemini-flash) — re-probe
  Haiku via API before promoting out of shadow.
