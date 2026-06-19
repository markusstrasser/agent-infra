---
title: Leverage Hunt — RSI + autoresearch (the win is actuation, not a new idea)
date: 2026-06-19
tags: [leverage, rsi, autoresearch, predict-then-falsify, accept-gate, consumption-over-autonomy]
status: active
---

# Leverage Hunt — RSI + autoresearch

**Mode:** `/leverage` default, but the surface is the most-swept in the repo
(constitution + wakeup-cadence + the whole 06-19 SoTA cluster). Per the skill's
divergence-budget calibration, a fresh five-axis brainstorm would only rediscover.
The load-bearing leverage move on a surface this mature is **VOI probe first: did the
already-ranked order-of-magnitude win actuate?** It did not — and *that gap is the win*.

**Consumer (step 1):** the agent loop itself (act-drain/maintain-tick admit harness
edits) + Markus (governance-shrink is his call). Mixed → the autonomous half (the
accept-gate logic) ships agent-side; the apply lane stays double-gated.

## Inventory-before-dispatch (anti-rediscovery)
Read before claiming anything: `2026-06-19-rsi-sota-synthesis-what-to-integrate.md`
(ranks 5 steals + sequence), `2026-06-14-leverage-hunt-rsi-system.md` (ran the full
default loop on this surface 5 days ago; WIN2 = the report-without-actuator disease).
This hunt deliberately does NOT re-derive RSI theory or re-rank the steals — it probes
their *actuation state* and finds the highest-leverage residue.

## The probe that decided the hunt (measured, this session)

| Ranked steal (06-19 synthesis) | Shipped? | Probe |
|---|---|---|
| #1 predict-then-falsify — *ledger* half | YES | `scripts/predictions.py` + `register_implementations.py` (daily via drift-sentinel) |
| #1 predict-then-falsify — *registration trigger* (WIN2 gap) | YES | `register_implementations.scan()` auto-registers an earn-its-keep prediction per newly-implemented finding in a 4-day window, idempotent |
| **#1 predict-then-falsify — the ACCEPT-GATE / auto-falsify half** | **NO** | see below — this is the leverage residue |
| #2 embedding novelty-rejection (hutter) | not here | needs hutter repo (separate go) |
| #3 Bayesian-Agent dep-eval | NO | no consumer wired |
| act-drain EFC quality-gate | NO | `grep quality.gate scripts/ src/` → 0 (only lesswrong corpus noise) |

```
$ wc -l predictions.jsonl                        → 23
$ grep -c '"kind":"prediction"' predictions.jsonl → 5
$ grep -c '"kind":"resolution"' predictions.jsonl → 0
```

**Five predictions registered, ZERO ever resolved.** No code calls
`predictions.resolve()` except the manual CLI verb. The only consumer of a DUE
prediction is `questions_view._collect_predictions` — it *surfaces it to the human as
a question*. There is no auto-resolver (the "falsify" half) and no gate that consumes a
`refuted` resolution to revert/flag the change.

## The finding (the leverage)

The 06-19 synthesis ranked #1 as **"pre-register the metric a change should move;
accept only if the trace shows the intended mechanism fired; else auto-revert/flag"**
and called it the *preventive cure for our measured #1 failure mode (accretion / policy
maze)*. What shipped is the **prediction-emission half** — the system now writes
falsifiable predictions automatically. What did NOT ship is the **falsification +
accept-gate half** — the half that actually closes the loop and prevents accretion.

This is the project's own named disease — **consumption-over-autonomy** — recurring at
the meta layer, *inside the very machinery built to measure self-improvement*. WIN2 of
the 06-14 hunt diagnosed exactly this ("report-without-actuator repeated 4×") and the
06-19 synthesis re-ranked it #1. Five days later the ledger fills with write-only
predictions that no actuator reads. The 13× add-vs-retire asymmetry in
improvement-log (`259 [x] / 19 [~]`) is the same asymmetry, unmoved.

**Why this is the order-of-magnitude win and a new idea is not:** the field (AHE,
Prosus, Henry-Pan, all triple-sourced) converged on *our architecture*; the synthesis'
own meta-finding is "integrate bolt-on mechanisms, not a rebuild." The single bolt-on
that the whole 2026 frontier says is load-bearing — the accept-gate — is the one piece
sitting half-built. Building a sixth idea has near-zero marginal leverage against
finishing the #1-ranked one.

## Axis (the one that matters here)
**Unnecessary** (the human step that shouldn't exist: a DUE prediction routed to a
human question is the consumption-over-autonomy tell) **+ better** (the loop closes;
declining-supervision becomes *measured*: resolution-rate + auto-retire-rate as KPIs).
NOT *faster* — this is a closure, not a speedup, so it can't be sized in a factor.

## The actuation residue — ranked, with named consumers

1. **Auto-resolver for predictions** [AUTONOMOUS, agent-infra-only]. On `check_date`,
   for predictions whose metric is machine-derivable (the `register_implementations`
   ones carry `metric="gov-shrink verdict if Gov-ID/verifier present"` — that IS
   machine-derivable: run the verifier with the scaffold removed = the ablation gate
   that `maintain_tick.py --ablate` *already implements*). Wire `maintain_tick --ablate`
   to call `predictions.resolve(pid, refuted|confirmed)`. **Consumer: the ledger's own
   resolution side + questions_view (DUE count drops as auto-resolution fires).** This
   is the falsify half, and the verifier for it already exists — the two halves are
   built and simply not connected.

2. **Accept-gate semantics on `refuted`** [PROPOSE — touches actuator]. A `refuted`
   resolution should mint a *retirement candidate* (not auto-revert — Markus's call on
   blast). This folds straight into the existing `--subtract` retirement-proposal lane
   in `maintain_tick.py`. **Consumer: gov-shrink / retirement proposals** — already a
   wired surface, currently fed only by frequency/date, not by evidence. This is steal
   #3 (evidence-posterior lifecycle) reduced to its zero-dep core: a refuted earn-its-
   keep prediction IS the negative evidence.

3. **EFC quality-gate on act-drain** [PROPOSE, queue]. Distinct lever (don't admit
   low-quality corrections as rules). Genuinely unbuilt, but lower-leverage than
   closing #1 and its base model is unverified-frontier — keep queued, not now.

## Honest factor
Cannot be a factor — it's a closure. The measurable win is that the
declining-supervision objective (the constitution's *primary* objective) becomes
**instrumented**: today `resolution_rate = 0/5`. Post-fix the KPI exists and can only
improve. The deeper win: the loop stops accreting silently, which is the #1
triple-sourced failure mode the frontier warns about — caught preventively, not by the
reactive `gov-shrink` mop.

## What I did NOT do (anti-rediscovery / scope honesty)
- Did not re-rank the 5 steals (06-19 synthesis owns that).
- Did not brainstorm new axes (mature surface; would rediscover — skill says probe).
- Did not touch hutter (#2 is a separate-repo go).
- Did not build the accept-gate — residue #1 is autonomous and should ship; #2/#3
  touch the actuator/blast and are Markus's call (propose-and-wait per WIN2's logic).

## Pre-registered check (eat-own-dogfood)
The fix for residue #1 should itself register a prediction: *"after wiring
maintain_tick --ablate → predictions.resolve, resolution_rate goes 0/5 → >0 within
one ablation-window."* If it doesn't fire, the wiring is write-only too — same disease,
one level down. (This is the recursion the accept-gate is supposed to prevent.)
