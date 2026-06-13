---
title: "RSI outer-loop Phase-0 probe — agent-infra contract (schema-expressiveness test)"
date: 2026-06-13
tags: [rsi, outer-loop, phase-0, probe]
status: active
---

# Phase-0 probe: can the action×autonomy matrix express agent-infra's MIXED loop?

**Why this probe first:** agent-infra's `/improve maintain` is "mixed per-finding (tests=clean,
governance=partial, taste=principal)" — the exact case that broke draft-1's single `verifier.regime`
enum (ADR §Phase 4). If the matrix expresses it without per-regime special-casing, the central
reframe holds. This is a hand-authored DRAFT contract to test schema expressiveness — **not yet
authoritative** (agent-infra's loop migrates in plan Phase 3).

**Ground truth** (`~/Projects/skills/improve/SKILL.md` §maintain, read 2026-06-13): thin conductor,
`/loop 30m` attended; tick = SWEEP(`just hooks-smoke`) → noop-on-state-hash → pick ONE by
readiness×priority → **route by verifier boundary** → tick-report. Proposers: observe/leverage/
harvest/research/critique. Bus: improvement-log.md, decisions-pending/, MAINTAIN.md,
maintenance-actions.jsonl.

## The typed contract (proposed `LOOP.md` schema, instantiated)

```yaml
loop:
  repo: agent-infra
  outer_loop_skill: { name: outer-loop, version: 2026-06-13, expected_schema: 1 }
  schedule: { driver: "/loop 30m", unattended_fallback: null, noop_on: state-hash-unchanged }

proposer:
  skills: [observe, leverage, harvest, research, critique]   # swappable divergence engines
  dedup_against: improvement-log.md     # ledger edge: proposer reads it to not re-propose

bus:
  findings:    improvement-log.md        # [ ] open · [x] done · [obs] ledger · [>] superseded
  human_queue: decisions-pending/        # sign-off-ready items (the Generate lane output)
  state_board: MAINTAIN.md
  ledger:      maintenance-actions.jsonl
ledger_schema: { ref: outer-loop/references/ledger-schema, conformance_linted: true }

# CENTRAL REPRESENTATION — autonomy is a ROUTING FUNCTION of the picked item's properties,
# NOT a static per-repo regime. This is the reframe, validated.
route:                       # evaluated per picked finding (= maintain step 4)
  autonomy_fn: |
    if action in PROTECTED: human_required          # gate-edit, GOALS/constitution
    elif reversible and blast_radius == local: unattended       # "do it, auto-commit"
    else: human_required → decisions-pending/        # taste/money/irreversible/shared-3+/discovery

actions:
  sweep:            { autonomy: unattended,  gate: "just hooks-smoke", gate_independence: external, blast_radius: none, reversible: true }
  fix_finding:      { autonomy: "route()",   gate: "<finding's own check: tests|lint|grep>", gate_independence: differential, blast_radius: "<local|shared>", reversible: "<bool>", regime: "<clean|partial|principal>" }
  propose_finding:  { autonomy: human_required, gate: human-signoff, blast_radius: "shared|irreversible", reversible: false, regime: "partial|principal" }
  modify_the_gate:  { autonomy: human_required, reason: "loop must not self-edit its accept-gate (protected verifier boundary)" }
  amend_governance: { autonomy: human_required, cadence_cap: 1/week, targets: [constitution, GOALS.md] }
```

## Result: PASS — with one schema sharpening

**PASS.** The matrix expresses the mixed loop natively, because **regime is per-action/per-item,
not per-repo** — `fix_finding`'s autonomy resolves at runtime from the picked finding's
`{reversible, blast_radius, regime}`. The thing that broke the enum is gone: there is no top-level
regime to be "mixed". `modify_the_gate` (protected boundary) and `amend_governance` (cadence-capped)
fall out as first-class human-required actions.

**Sharpening (genuine Phase-0 finding):** draft-1 imagined a *static* per-action autonomy enum.
The real structure is an **`autonomy_fn` routing function** — `autonomy = f(action, reversible,
blast_radius, regime)` — evaluated per picked item. `/improve maintain` step 4 IS this function.
So the contract declares a routing *function* (a few typed rules), not a static lookup table. This
matches GPT's autonomy-matrix point AND keeps the contract small (one `route.autonomy_fn` + a thin
`actions` table of overrides like the protected boundary), avoiding the per-regime branch explosion
Gemini feared. **Schema impact:** `references/loop-contract.md` must define `route.autonomy_fn` as a
first-class field, with `actions[*].autonomy: "route()"` deferring to it and explicit overrides
(`human_required`) for protected/governance actions.

## Remaining Phase-0 (next focused pass)
- [ ] hutter contract (clean-cheap) — confirm `autonomy_fn` collapses to "unattended auto-ratchet for
  in-tier; human_required for discovery/model-class change" without special-casing.
- [ ] arc-agi contract (clean-expensive) — the hardest: proxy + dual-gate (`accept iff proxy↑ AND
  truth↑`) + submission `budget`. Confirm budget/proxy are expressible as gate fields, not new top-level machinery.
- [ ] probe-the-write: `git grep` hutter `eval.py` + arc-agi proposed ledger writers — confirm the
  shared ledger fields match what's STAMPED (not assumed).
- [ ] Gate (Phase-0 version): all three express via one `route.autonomy_fn` + thin overrides, no
  per-regime control-flow forks → #2′ holds. Any one needs a structural fork → reconsider toward C.
