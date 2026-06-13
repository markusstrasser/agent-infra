---
title: "RSI outer-loop Phase-0 GATE — hutter + arc-agi contracts, probe-the-write, verdict"
date: 2026-06-13
tags: [rsi, outer-loop, phase-0, gate]
status: active
---

# Phase-0 GATE: do all three regimes express via ONE routing fn + thin overrides + shared ledger?

Completes Phase 0 (items 1-4 of the migration plan). Pairs with the agent-infra probe
(`2026-06-13-rsi-phase0-probe-agent-infra-contract.md`, mixed regime → PASS). Decision gate:
all three express via one `route.autonomy_fn` + a thin `actions` override table + the shared ledger,
**with no per-regime structural control-flow fork in the skill** → #2′ holds; any structural fork → reconsider toward C.

## Item 3 — probe-the-write (ground the ledger in the REAL writer, not assumptions)

Read `~/Projects/hutter/scripts/ledger_schema.sql` (the source-of-truth; `ledger.db` is gitignored/
rederivable). The `experiments` table — what hutter actually STAMPS — matches the ADR's expanded
schema and corrects two things:

- **Fields confirmed present as written:** `parent_id` (lineage), `git_sha` (=parent_commit),
  `binary_sha256` (=artifact_hash), `s_bytes`/`baseline_s`/`d_s` (scores), `verdict`
  (BASELINE/ACCEPT/REJECT/ERROR/GATE_PASS/PROBE_*/ARC_STEP — the structured verdict), `error_class`
  (=quarantine state), `tags`, `dead_end`. → the shared schema is real, not invented.
- **ADD (under-weighted in the ADR): `predicted_ds`** — a PREREGISTERED predicted ΔS stamped at
  propose-time, the basis of `v_calibration` ("is the proposer honest?" predicted vs actual). This is
  the AHE *falsifiable-contract* pattern already running. The shared ledger MUST carry a
  `predicted_score` field + a calibration view. Folds into Phase 1.
- **Policy lives in VIEWS over the ledger** (confirms structure-transfers): `v_dead_ends` (proposer
  dedup edge), `v_clade_yield` (HGM restart-from-fertile-parent — own-score r=0.28–0.44 vs clade-pooled
  0.63–0.78), `v_tag_yield` (probe allocation), `v_probe_transfer` (PACE funnel).
- **PACE is regime-gated — direct quote, the deferral's evidence:** *"the deterministic ratchet
  (zero-variance byte count) is hutter's structural PACE-defense and it catches every false probe-win;
  PACE's e-process gate is NOT needed on the ratchet."* So clean→no PACE; partial→PACE. Confirms ADR.

arc-agi's ledger (HANDOFF.md, designed) explicitly *"reuse hutter's eval.py/schema shape"* + adds
`proxy_score, private_rhae (nullable), submissions_spent` — i.e. the hutter superset + 3 FIELDS. No
new machinery. (probe of the not-yet-written arc-agi writer is a Phase-1 re-check when it lands.)

## Item 1 — hutter contract (clean + cheap)

```yaml
loop: { repo: hutter, outer_loop_skill: {name: outer-loop, version: 2026-06-13, expected_schema: 1} }
schedule: { grinder: own-VM-process(NEVER-STOP), dreamer: "/loop /dream | launchd", noop_on: queue-healthy }
proposer: { skills: [leverage, research, brainstorm], dedup_against: [v_dead_ends, v_revisit] }
bus: { queue: queue/, human_queue: decisions-pending/, flags: [STALL, QUEUE_LOW], ledger: ledger.db#experiments }
verifier: { regime: clean-cheap }
accept_gate: { cmd: "just ledger / eval.py", independence: external, kind: bit-exact-deterministic,
               verdict: structured(BASELINE|ACCEPT|REJECT|ERROR|GATE_PASS|PROBE_*), pace: not-needed }
route:
  autonomy_fn: |
    if action in {modify_the_gate, model_class_change, GOALS}: human_required   # "never edit grinder code/ledger/harness"
    elif action == accept and bit_exact and verdict==ACCEPT and tier==search: unattended   # auto-ratchet
    elif action == discovery: human_required → decisions-pending/                # paradigm/model-class = human
    else: unattended                                                            # propose/probe/dead-end-mark
ledger_extra: { predicted_ds: preregistered, calibration_view: v_calibration }
```

## Item 2 — arc-agi contract (clean + EXPENSIVE — the hardest schema test)

```yaml
loop: { repo: arc-agi, outer_loop_skill: {name: outer-loop, version: 2026-06-13, expected_schema: 1} }
schedule: { mode: episodic→dreamer-once-running, noop_on: queue-healthy }
proposer: { skills: [leverage, research], dedup_against: [ledger.dead_end] }
bus: { queue: queue/, ledger: ledger.db#experiments(+proxy_score,+private_rhae,+submissions_spent), git: bus }
verifier: { regime: clean-expensive }
accept_gate:                                  # DUAL — lives in arc-agi's gate cmd, the skill only shells it
  cmd: "proxy(local synthetic envs) ; on-submit: kaggle RHAE"
  rule: "accept iff proxy↑ AND (when submitted) ground_truth↑"     # dual-gate
  independence: { proxy: same-lineage(Goodhart-risk→track proxy↔truth corr), truth: external }
  budget: { ground_truth: "~5 submissions/day", field: submissions_spent }
route:
  autonomy_fn: |
    if action in {modify_the_gate, model_class_change, GOALS}: human_required
    elif action == run_candidate and proxy_up: unattended                       # local proxy free/infinite
    elif action == submit_ground_truth and budget_remaining>0: budgeted         # NEW input: budget gate
    elif action == accept and proxy_up and truth_up: unattended                 # dual-gate satisfied
    else: human_required
```

## Item 4 — THE GATE verdict

**PASS — #2′ holds.** All three regimes (clean-cheap / mixed / clean-expensive) express via:
- **one `route.autonomy_fn`** of the same shape — `if action∈PROTECTED → human; elif reversible ∧
  within-budget ∧ blast≤local ∧ gate-pass → unattended; else → human/decisions-pending`. The regime
  changes only its INPUTS (which gate cmd, budget?, proxy?), never the control flow. arc-agi adds one
  input (`budget_remaining`); the function generalizes without a fork.
- **a thin `actions` override table** — only the PROTECTED set (`modify_the_gate`, `model_class_change`,
  `GOALS`) is a hard human_required override, identical across all three. (Protected-verifier-boundary
  = uniform.)
- **the shared ledger** — hutter's `experiments` is the superset; agent-infra uses a subset (jsonl),
  arc-agi = superset + 3 fields. Differences are FIELDS, not machinery.

**No per-regime structural control-flow fork lands in the skill.** The regime-specific logic
(bit-exact ratchet / dual-gate+proxy+budget / consumed-setpoint) lives entirely in each repo's
`accept_gate` command, which the skill *shells and consumes* — exactly the policy/data/structure split
#2′ predicted. Gemini's "three skills in a trench coat" fear is answered: the trench coat is the gate
command (per-repo, by design), not the skill.

### Carry into Phase 1 (the build)
1. Ledger schema MUST include `predicted_score` (preregistered) + a `v_calibration` view — the
   honesty/falsifiable-contract field probe-the-write surfaced.
2. `route.autonomy_fn` is a first-class contract field (a few typed rules); `actions[*].autonomy:
   "route()"` defers to it; PROTECTED set = hard override. (from the agent-infra probe.)
3. `budget_remaining` is an autonomy_fn input (arc-agi); contract carries an optional `budget` block.
4. Gate cmd emits a STRUCTURED verdict (not bare exit); skill stamps it + `gate_version` in the ledger.
5. PACE stays OUT (clean = structural ratchet defense per the v_probe_transfer quote; partial = later, on measured need).

**→ Phase 0 complete. #2′ confirmed on all four regime points. Proceed to Phase 1: build the
`outer-loop` skill, first vertical slice = hutter, validated by trace-equivalence.**
