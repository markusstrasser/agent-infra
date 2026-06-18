---
concept: unified cross-domain RSI/research-loop infrastructure (scaffold + skills + cookbook)
decision_date: 2026-06-18
status: proposed
relates_to:
  - research/2026-06-18-loop-core-probe-v2-algorithm-layer.md
  - research/2026-06-18-hutter-anim-rsi-comparative-report.md
  - decisions/2026-06-16-loop-core-rsi-ledger-factoring.md
  - decisions/2026-06-07-verifier-conditional-autonomy.md
affects: [agent-infra, research, phenome, hutter, anim-workbench, intel, skills]
---

# Unified loop infra — scaffold + skills + COOKBOOK (not a runtime library)

> Output of a `/decide` arc (2026-06-18). Status `proposed` until the Phase-4 cross-model
> critique survives **without an architecture reversal** (constitution P12 — 3+ project shared
> infra). Then `accepted` → execute.

## Context

Every advanced loop here (hutter, anim, intel) + the research generator collection hand-rolls the
same propose→verify→rank→accept→ledger skeleton. The operator wants to spin up **3–5 new domain
loops soon** (immigration, phenome, …) and have each "find new things, rank them, build better
theses" with declining supervision. Question: what shared infra makes starting one *easy*?

## The real axis (Phase 0)

Not "what infra to design" but **build ahead-of-need vs prove-then-extract** — because ahead-of-need
shared loop infra is this repo's single most-repeated build-then-undo failure (the `outer-loop`
skill shipped with zero callers; `loop-core` resolved to a cookbook). Two facts resolve it:

1. **Probe v2 (committed `4eab73d`)** killed the *runtime library* layer: adopt-by-deletion fails
   3/3 because the verdict vocabulary IS the algorithm. The algorithm *shapes* are generic; the code
   is not shared. → Layer 3 is a **copy-stamp cookbook**, never a package.
2. **Operator roadmap = 3–5 domains** retires the build-then-undo risk for the *scaffold*: callers
   #2–5 are real, so `/loop-new` is justified ahead-of-need — provided it is **derived from one real
   instance** (immigration = caller #1), not theorized.

## Decision

```
L1  SCAFFOLD  /loop-new <domain>  → stamps LOOP.md · OUTER-LOOP.md · HERETIC.md ·
              GENERATORS.md · a DOMAIN-LOCAL ledger (own schema/engine) · the verifier slot.
              DERIVED from the immigration loop (built by generalizing one real instance).
L2  SKILLS (operate on the stamped conventions; NO shared runtime):
    /loop-generators  diverge → candidates → verifier-RANK → ledger → park-dry   (the discovery engine)
    /loop-outer       tri-lab review (Opus RSI + GPT arch + Gemini heretic)       — THIN pointer to
    /loop-health      ledger views + status                                         existing hutter/anim ports
L3  COOKBOOK (docs, copy-stamp): role pattern Proposer→Runner→Verifier→Auditor→Accept→Ledger
              + 6 algorithm SHAPES (clade-yield · calibration · funnel · tag-yield · heretic · leaderboard).
```

The **one domain-specific fill is the verifier** — and it *sets the autonomy regime* the loop runs at:
clean→automate · partial→bounded · principal→amplify (`decisions/2026-06-07-verifier-conditional-autonomy.md`).
"Easy to start" = stamp L1+L3, the L2 skills already exist, answer one question: *what's your
ground-truth check?*

## Invariants (must survive)

1. **Verifier is ground-truth, never LLM-judged.** A bad eval is worse than none (Goodhart). The
   scaffold's first prompt is "what's your ground-truth check?"; an LLM-judge / coherence / persuasion
   answer is flagged **amplify-only, no auto-ratchet, heretic-heavy** (the IQ trap, generalized).
2. **Cookbook is copy-stamp, not shared code** (probe v2). Each loop owns its schema/engine + verdict
   vocabulary; it copies a skeleton, never imports a runtime.
3. **Born with a caller.** No scaffold/skill ships without ≥1 real consumer. Immigration is #1; the
   3–5 roadmap is #2–5. If a layer can't name its caller, it isn't built.
4. **Generator lifecycle:** retrodiction ≥2 priors · negative-space required · consumption-path
   required · park-after-2-dry-cycles (`skills/leverage/references/generators.md`).
5. **Ledger is append-only, domain-local.** Supersede, never mutate (the replayable moat).
6. **Auditor (heretic) is mandatory even when the accept-gate is greedy** (PACE: greedy alone =
   self-p-hacking).

## Rejected alternatives

- **`loop-core` / `ledger-core` runtime library** — probe v2: adopt-by-deletion fails 3/3 because a
  shared schema is **LOSSY** (can't hold anim's prose verdicts or hutter's 12-value verdict taxonomy
  without discarding semantics). Rejected for *correctness*, NOT effort — so it **survives "depth over
  effort"** (#g 2026-06-18): the cookbook + each loop's own schema IS the deepest *correct*
  representation. The 6 shapes are still implemented as clean **parameterized functions** inside
  `/loop-generators` (depth, born-with-caller = immigration); the shared-helper-lib question (hutter
  agent's "lift the column-agnostic skeleton into a called helper") re-opens at the **2nd same-contract
  caller**, not before. (`research/2026-06-18-loop-core-probe-v2-algorithm-layer.md`)
- **Defer everything / prove-first-only (option b)** — overturned by the 3–5 domain roadmap (the fact
  that flips the gate; deferring wastes the recurrence signal).
- **Pure-docs cookbook only (no skills)** — wastes the 4× recurrence; the discovery engine
  (`/loop-generators`) is real reusable leverage, not theory.
- **Central orchestrator over all loops** — eradicated 2026-06-07; per-repo launchd + mechanical tick
  is the proven pattern.
- **MCP server (`loop-ops`)** — knowledge-substrate MCP retired (4 reads/60 writes); files + skills win.
- **Rebuild `/loop-outer` + `/loop-health` from scratch** — hutter/anim already have the ports; the
  skills are thin pointers, not reimplementations.

## First execution target

Immigration generator sweep on the existing warehouse (verified: `lifetime_generators` 104,
`parameter_claims` 563, 25 fiscal data tables for the consumption-path verifier). This is the
proving instance the scaffold + `/loop-generators` are derived from.
