---
concept: rsi-loop-closure
decision_date: 2026-06-16
status: accepted
supersedes: []
relates_to:
  - decisions/2026-06-07-state-externalization-lens.md
  - research/2026-06-16-predictive-arch-rsi-loops.md
  - .claude/plans/4d40085a-recursive-session-learning-loop.md
---

# ADR: Close the RSI loop with a unified control surface over reused sensors

## Decision

Build **one control surface** (`pulse` CLI — `scripts/pulse.py`, invoked by `/improve maintain` on loop) that OWNS the
closure *brain* — instrument registry + null-canary, promotion gate + anti-windup, per-detector
precision weights, and the closure metric — and READS the existing sensors (`reflect_capture`,
`fm.py recurrence`, `supervision-kpi`/AIR, the miners) as data feeds. **Do not rewrite the
sensors.** The only rewrite is consolidating closure/control logic OUT of the ~7 scattered organs
INTO the one surface.

## The principle (the why — pinned before the plan)

The derivation loop senses well and does not close. The reflect-eval (2026-06-16) grades the
SENSING layer 3/4 PASS (capture 1069 incidents, throughput draining). The failure was never the
sensors — it was that **no single component owns "closure"**: a dead AIR field (one wrong
`hook_progress` vs `hook_success`) silently broke the loop for 1591 sessions and nothing noticed,
because instrument-liveness, graduation, and closure-measurement live in ~7 separately-grown organs
with no owner. **Owner-less scatter is the disease.** The fix is a single owner, not more organs.

This is greenfield **at the control layer** (where the architecture is bad) and reuse **at the
sensor layer** (where the eval proves it works). It is the state-externalization lens applied
(`2026-06-07`): externalize the recoverable bookkeeping — the instrument registry, the precision
weights, the closure ledger — into one harness surface; leave each sensor only its semantic job.

## Invariants this decision must preserve

1. **Sensors are reused, never reimplemented.** The controller calls `reflect`, `fm.py`,
   `supervision-kpi`, miners — it does not duplicate their logic. (Eval-proven; rewriting = churn.)
2. **Measure-before-enforce holds.** No detector graduates without clearing its precision gate
   (PPV≥60% on ≥30 firings, the loop's existing bar); nothing auto-applies an enforcer without the
   human. The controller owns the *gate*, not a license to skip it.
3. **The null-instrument problem becomes structurally impossible.** Every closure metric registers
   `{name, last_value, last_fresh_ts, expected_variance}`; a constant/null/stale instrument alarms.
   This is the one capability whose absence caused the 1591-session miss.
4. **Single API.** One queryable surface (`pulse` CLI). `/improve maintain` (already a loop) is its
   scheduler; the existing `/rsi` skill stays the human close-digest — no third surface.
5. **Sessions are the only sensor, the harness the only actuator** (unchanged from ARCHITECTURE.md).

## Rejected alternatives

- **Full greenfield rewrite (tear out reflect/fm/supervision-kpi).** Rejected: the eval proves
  those work (3/4 PASS, backlog draining); rewriting eval-passing code is pure churn + risk. The
  bad layer is *control*, not *sensing*.
- **Pure iterative / thin seam (bolt one null-canary onto AIR; wire each gate ad-hoc).** Rejected
  after operator pushback (2026-06-16): it preserves the owner-less scatter whose *seams* caused
  the failure — patch this dead instrument, the next one in another organ still dies silent; the
  patch-surface grows (Jevons). The unifying owner is the point.
- **Status quo ("what we have is good").** Rejected on the merits: the control layer is the
  diagnosed disease, not good.
- **History-based veto of any unified subsystem** (orchestrator/scored-gate/knowledge-substrate
  graveyard). Rejected as the deciding argument (operator 2026-06-16): those died for contingent
  reasons; going forward `/improve maintain` loops and runs skills, so "won't get run" no longer
  binds. The graveyard informs *form* (no new scheduler/daemon — ride the existing loop), not
  *whether* to unify.
- **EFE/FEP planner, JEPA, Gödel self-rewrite** — out of regime (research memo C6/C9: scaffolding-
  RSI, the converging kind; the formalisms are intractable and don't transfer).

## Verification posture

Hard-to-reverse arch decision → mandatory cross-model + repo-grounded critique panel (Phase 4 of
the decide arc) BEFORE building, with a dedicated fact-checker resolving every `file:line`/metric
claim in the plan. Build nothing until the panel stops producing reversals.

## Critique panel outcome & converged decision (2026-06-16)

3 repo-grounded cursor agents (opus-thinking-high spine, gpt-5.5-high cross-lab, composer-2.5
fact-check). Fact-checker: zero line-drift on cited anchors. The two arch critics CONVERGED on a
**partial spine reversal** — verified true against code:
- `drift-sentinel` (the autonomous daily monitor) does NOT invoke `doctor` → a doctor-only canary
  inherits the exact blind spot that let AIR rot on no-loop days. **Canary home = drift-sentinel.**
- `check_telemetry_freshness` tests `count==0` only → a wrong-field *constant non-null* (the AIR
  bug) is missed. **Constant/variance detection is the genuinely-new capability.**
- `reflect.PPV_CLEARED` is empty (0 graduated detectors, 1 family) → **weights is over-build ahead
  of load; deferred.**
- `views.sql` is dead orchestrator-DB plumbing → registry is a JSON manifest + live-read VIEW
  (questions_view.py pattern), standalone `scripts/pulse.py`, NOT an agentlogs subcommand.

**Converged scope (shipped `1e11f86`; renamed rsi→pulse):** the single `pulse` CLI exists now.
- `canary` — BUILT, full; wired into `drift-sentinel.sh`. Flags null/constant/stale per-instrument,
  fail-loud (no single aggregate verdict — avoids the choke-point failure mode the panel raised).
- `gate` — BUILT thin, FM-ID granularity (the free one fm.py emits); advisory until a promotion
  flow exists. Axis-granularity rollup deferred (open fork — needs an FM-ID→axis join fm.py lacks).
- `weights` — DEFERRED. Activates when ≥2 detectors clear PPV.

**Operator note:** the panel disagreed with the larger greenfield scope; the call to ship
canary+gate-thin and defer weights was made on verifiable evidence (empty PPV_CLEARED, fm.py
already emits the gate input), not punted — correcting an earlier mis-application of P12-as-ceremony
to what was a technical question.
