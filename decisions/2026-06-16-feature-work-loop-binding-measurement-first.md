---
id: 2026-06-16-feature-work-loop-binding-measurement-first
concept: feature-work-loop (decompose → fan-out → review)
repo: agent-infra
decision_date: 2026-06-16
recorded_date: 2026-06-16
provenance: contemporaneous
status: proposed
initial_leaning: "Bind blast-radius + gate-coverage to the decompose/review moments (build a decomposition-time check + a review-weighted-diff surface). REVERSED to measurement-first after grounding: the review side is already a live shadow experiment, the structural tooling already exists as deps, and a build-first repeats the repo's documented build-then-undo failure."
relations:
  - type: subsumes_probe
    target: risky-diff-review-shadow (improvement-log 2026-06-07)
  - type: applies_lesson_from
    target: 2026-06-13-rsi-outer-loop-skill   # FINDING 5: run the who-loads-this probe at decide-time
  - type: relates_to
    target: 2026-06-16-loop-core-rsi-ledger-factoring
affects: [agent-infra, skills, all-projects-feature-work]
---

# Feature-work loop: the decompose→review binding is a MEASUREMENT problem, not a BUILD problem

## Context
The operator's daily feature-work loop — "draw the owl" (loose first attempt, expect garbage) → if the
diff is too big, decompose into atomic reviewable tasks → fan out parallel agents → repeat until under a
review threshold; HITL at UI/API/contract boundaries — is an instance of the **SHORT reflex loop**
(`ARCHITECTURE.md`) operating at two moments: **decompose** (task-split) and **review/merge**. The posed
question: how to improve the infra supporting it. (Prior-art scan: `research/2026-06-16-agentic-decomposition-gating-prior-art.md`;
one-repo binding inventory: `research/scratch/2026-06-16-genomics-loop-binding-surface.md`.)

## The real axis (Phase 0)
First framing was "which primitives to build/bind at decompose + review" (genomics-flavored seed:
blast-radius + gate-coverage + isolation). Grounding — an Explore inventory, the engineering prior-art
scan, and the repo's own decision history — **reverses it**: the primitives, the prior art, and even the
specific experiment already exist. The real axis is:

> **Of the loop's moments, which already have a measured-demand signal, and which gap is real enough to
> instrument BEFORE building — versus duplicating a live experiment or repeating the repo's
> build-then-undo failure?**

### Hidden assumptions made explicit
1. "Improve the loop" = build a gate. **FALSE** — the binding constraint (review throughput, decomposition
   quality) is *measurable*, and the review side is already being measured.
2. genomics' blast-radius (closure-hash count over 123 stages) generalizes upward. **FALSE** — agent-infra's
   blast-radius is a **path-class** notion (governance / hook / schema / contract / settings), already encoded
   in `risky_diff_review_shadow.py`.
3. The writer/reviewer split is missing. **FALSE** — integrated 6× (`/code-review`, `/critique model`,
   `fresh-eyes-review`, `code-reviewer` subagent, `Workflow`, `posttool-review-check`); self-review did not
   degenerate on Opus 4.8 (improvement-log 2026-06-07).

## Decision — measurement-first
1. **Do NOT build** a decomposition-time gate, a review-weighted-diff surface, or a coverage-cell partition
   now. Each either duplicates `risky_diff_review_shadow.py` (review side) or has no measured demand
   (decompose side).
2. **Subsume, don't duplicate.** The review/merge moment rides the existing `risky-diff-shadow` and its
   **promote/cut decision (~2026-06-21)**; the feature-work loop registers as a named consumer of that
   decision rather than spawning a parallel one.
3. **Instrument the one unmeasured moment** — decompose / fan-out / merge — as a **report-only demand probe**
   on the existing substrate (`agentlogs`, `loop_funnel`, `supervision-kpi`). The target numbers
   (decomposition overlap → rework; merge-conflict rate; review-time per landed change) are ones the
   prior-art confirms **nobody has published** (§3b/§3c).
4. **If/when demand is proven, buy don't build.** Any eventual gate = `inspect`/`kai`/`vibediff` (MCP-native,
   evaluated as dependencies) + a thin domain-policy layer — never a from-scratch engine.
5. **Build as harness-state edges, not prose rules** (`state-externalization-lens`): a detector that emits a
   signal the slow loop can judge, not a CLAUDE.md instruction.

## Invariants to preserve
1. **Measure before enforcing** — shadow → promote/cut on *correlated* demand (the risky-diff-shadow pattern).
2. **Run the "who loads this / do consumers already do it natively?" probe at decide-time** — the FINDING-5
   lesson; this ADR is its application, not its next victim.
3. **No redundant writer/reviewer pipeline** (decided 2026-06-07).
4. **Buy the structural half** (affected-graph / semantic-diff) as a dependency; build only the
   domain-invariant half, thin.
5. **Terminal review gate = single-logical-change / reviewable-in-~60-min**, NOT raw line count. 1500 lines is
   the cheap *alarm*; ~200–400 lines is the empirical reviewability band.
6. **Harness-state, not prose rules.**

## Rejected alternatives
- **Build the decompose+review binding now** (the seed plan / genomics Phase-1 spine). Rejected: duplicates the
  live `risky-diff-shadow`; no measured decompose-side demand; repeats build-then-undo.
- **A new CLAUDE.md rule "decompose by blast radius."** Rejected: wrong layer (state-externalization); rules
  ratchet up, never down.
- **A from-scratch semantic-diff / blast-radius gate.** Rejected: `inspect`/`kai`/`vibediff` exist (prior-art
  §2C); evaluate as deps first.
- **A new feature-work RSI / outer-loop platform.** Rejected: the outer-loop skill was built-then-killed for
  zero consumers (2026-06-13 FINDING 5).
- **Status quo (pure operator discipline, no measurement).** Rejected: the telos is declining *measured*
  supervision; an unmeasured loop can't show the curve.

## Revisit if
- The 2026-06-21 risky-diff-shadow decision promotes to an auto-review trigger → the review need is served;
  only the decompose probe remains.
- The decompose demand probe shows bad decompositions correlate with rework above a threshold → spec + build
  the thin domain layer on `inspect`/`kai` (re-enter `/decide` Phase 2 for the build).
- A second project beyond the operator's loop becomes a concrete consumer → the proven-common ≥2 bar may
  justify a shared artifact.

## Plan
`.claude/plans/12b7853a-feature-work-loop-instrumentation.md`
