---
title: Behavioral eval from session-corrections — feasibility + a design-foreclosing negative result
date: 2026-06-19
tags: [rsi, evals, over-caution, behavioral, testground]
status: active
---

# Behavioral eval from session-corrections — feasibility probe

**Question:** can the steer-mining corpus (human corrections of agent behavior) become a
standing behavioral eval / RSI-fitness signal for the over-caution / scope-authorization
class — the top blindspot cluster, which is *unhookable* (no deterministic check for "was
this ask legitimate?") and today is measured only post-hoc (`supervision-kpi.py --days 30` =
observability, not a controlled experiment)?

## Feasibility: YES (data is rich enough)

`scripts/extract_behavioral_eval_cases.py` (the ingestion bridge the evals repo lacked) turns
each steer signal into a labeled case: `before` (scenario) + `quote` (**human correction =
ground-truth label**) + `vector` (gold direction) + `_session` (full-transcript link).

- **1,319 merged signals → 29 clean over-caution-core cases** (tight classifier: agent
  asked/offered/deferred/waited AND human pushed to act), **29/29 transcripts recoverable on
  disk.** Reconstruction of the real pre-correction agent turn works (verified on 2 cases).
- The label is the operator's *revealed preference*, not a model-judge opinion — so this
  dodges the constitution's "a model-as-judge proxy doesn't make taste verifiable / bad eval
  worse than none" trap.

## Design-foreclosing negative result: over-ask is HARNESS-induced, not model-intrinsic

Smoke (`artifacts/rsi-experiments/overcaution_smoke.py`): 5 reconstructed scenarios × 2 arms
(baseline vs +"act on authorized scope" steer), `claude-opus-4-8 -e low`, $0 subscription:

```
baseline: ASK 1/5 (20%)  ACT 4
steer   : ASK 1/5 (20%)  ACT 4      # steer churned WHICH case asked; aggregate unmoved
wall 290s | $0 sub
```

**Bare Opus handed the scenario neutrally ACTS ~80%** — it does NOT reproduce the over-ask the
*live* agent exhibited (where the operator had to correct it). And both "ASK"s were grader
false-ish positives: case[3] led with a decisive recommendation then asked a *gold-correct*
scope-clarification; case[4] literally said *"the thing I'm not doing: sitting on a 'shall I
proceed?' stop"* — acting, with an embedded `?` the text-heuristic miscounted.

Two conclusions:
1. **The over-ask is induced by the full harness** (caution rules, the `AskUserQuestion`
   affordance, accumulated conversational hedging), not the model's base disposition. A
   **bare-model eval (fork A) is refuted as the faithful instrument** — it would measure ~nothing,
   because the model isn't the locus.
2. **A text act/ask grader is too crude** (embedded/rhetorical `?`, decisive-recommendation-
   plus-clarification). The faithful signal is **tool-call telemetry**: ended turn with a
   question AND zero tool calls = ask; made edits/tool calls = act.

## Implication for "RSI testgrounds vs evals"

The faithful home is **fork B: an agent-loop behavioral testground**, NOT the bare-model evals
repo. Replay the reconstructed scenario through the *real harness* (CLAUDE.md + hooks + tools)
and grade act-vs-ask from tool-call telemetry. This is a **new kind of testground**, distinct
from hutter/anim (program search w/ bit-exact verifier):

| | hutter / anim | behavioral testground (proposed) |
|--|--|--|
| candidate | a program | a **harness config** (rules/hooks/CLAUDE.md framing) |
| verifier | bit-exact + size/RAM | **human-correction label** (act/ask) via tool-call telemetry |
| fitness | compression ratio | over-ask rate ↓ without error-correction ↑ (supervision-kpi conjunction) |

This is exactly the controlled instrument the constitution's **Pre-Registered Test #2** wants
("≥50% reduction in failure streaks vs baseline") generalized to the unhookable behavioral
classes — and it can A/B a harness change, which `supervision-kpi` (uncontrolled live stream)
cannot.

## Caution floor (design constraint, operator-owned)

Label **only human-corrected cases** as "should've acted"; **never penalize an uncorrected
ask.** Measure *unnecessary* asks, not all asks — else the loop trains the agent out of the
legitimate irreversible/taste/boundary asks. Don't drive caution to zero.

## Artifacts
- `scripts/extract_behavioral_eval_cases.py` — signal→case bridge (reusable)
- `artifacts/rsi-experiments/behavioral-eval-cases.jsonl` — 29 cases (derived; regenerable)
- `artifacts/rsi-experiments/overcaution_smoke.py` — the discrimination smoke

## Next (gated on operator go + the 4 RSI-SoTA research dispatches landing)
Build the agent-loop replay harness OR fold the behavioral fitness into an existing testground
shape. Decide after the SoTA sweep — newest self-improving-agent work may supply the replay/
fitness pattern to steal rather than hand-roll.
