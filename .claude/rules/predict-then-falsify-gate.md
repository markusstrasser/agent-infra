---
paths:
  - "mechanism-records/**"
  - "improvement-log.md"
---

# Predict-then-falsify gate (F3)

<!-- Gov-ID: rule:predict-then-falsify-gate
goal: stop governance changes (rules/hooks/act-drain promotions) from being accepted on "aggregate score improved" instead of "the pre-registered mechanism fired"
verifier: scripts/mechanism_record.py (check subcommand; ground-truth query over agentlogs.db)
blast_radius: local
-->

A governance change — a new rule, a hook, an act-drain rule promotion — is accepted
only if its **pre-registered mechanism fired**, measured against the trace store, with
a **negative control** that stayed flat. Not because a score went up. This is the F3
foundation of `research/2026-06-20-paper-integration-plan.md` (EvoTrainer 2606.03108;
~30 of 38 deep-read papers converge on this exact gate). It directly attacks our
measured #1 risk — governance accretion / "policy maze" — and is the defense against
reward-hacking / self-preference (RHO 2606.05922, NRT-Bench 2606.20408): a control
that moves with the metric means the change is **CONFOUNDED**, not accepted.

## When required

Any change whose *justification is a behavioral claim* ("this reduces over-ask",
"this cuts bash-failure loops"). NOT required for: style/format rules, pure
refactors, or changes with no claimed failure-class effect.

## The mechanism record (single canonical schema — `scripts/mechanism_record.py`)

One git-tracked JSON per change in `mechanism-records/` (append-only governance
artifact, like `decisions/`). The enforceable definition is the `MechanismRecord`
dataclass; this is its prose mirror:

| field | meaning |
|---|---|
| `slug` | record id |
| `change_ref` | the commit / rule path / improvement-log id the gate guards |
| `predicted_failure_class` | the failure this change reduces (one line) |
| `expected_trace_observable` | what should change in the typed trace / agentlogs |
| `metric_query` | SQL over agentlogs.db; **one scalar**; binds `:since` `:until` |
| `direction` | `decrease` \| `increase` — predicted move of the metric |
| `control_query` | **REQUIRED** negative control, same shape; must stay ~flat |
| `change_date` | ISO date splitting before/after windows |
| `rollback_criterion` | when to revert |
| `baseline_window_days` | before-window length (default 30) |
| `min_effect_frac` | required relative move to count as fired (default 0.20) |
| `control_tolerance_frac` | control move beyond this ⇒ CONFOUNDED (default 0.20) |

The gate normalizes to **rate-per-day** (before and after windows differ in length)
and compares relative moves.

## Verdicts

- **FIRED** — metric moved the predicted way past `min_effect_frac` AND control stayed flat → accept.
- **NOT_FIRED** — metric didn't move (or moved the wrong way) → do not accept; revisit or revert.
- **CONFOUNDED** — metric moved but the control moved too → not attributable; reject the causal claim.
- **PENDING** — change_date not yet far enough in the past to measure.
- **INVALID** — record fails schema validation (missing control, unbound query, …).

## Use

```bash
uv run python3 scripts/mechanism_record.py record <slug> --change-ref … --failure-class … \
    --observable … --metric-query … --direction decrease --control-query … \
    --change-date YYYY-MM-DD --rollback …
uv run python3 scripts/mechanism_record.py check <slug>   # FIRED/NOT_FIRED/CONFOUNDED, persisted onto record
uv run python3 scripts/mechanism_record.py list
```

(`just mechanism-record|check|list` wrappers land once the in-flight justfile
`.sh`→`.py` migration settles — direct invocation is the current interface.)

## Honest bound (post-refute)

The papers support this gate as analogy from versioned experiments / replayable
objective evals — NOT as proof every local rule edit needs it. It bites only where
an **objective (or explicitly-labelled proxy) metric** exists in the trace store.
`trace_index` (the failure-class signature table) is currently empty; until L1/L2
populate richer signatures, gates bind to directly-populated signals (tool error
rate, message-length, permission-denied counts). Import the gate as a pattern; prove
each instance on our own traces. Never cite a paper's number as expected lift.
