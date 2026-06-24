# Agent-Infra Sweep — our RSI loop vs the harness-self-evolution frontier (2026-06-24)

**Date:** 2026-06-24 · **Window:** 06-20 → 06-24 · **Type:** INWARD sweep (our architecture vs the frontier), the complement to the outward `trending-scout-2026-06-24`.
**Frontier source:** `research/trending-scout-2026-06-24.md` (4 parallel scouts) flagged a tight cluster — **harness self-evolution** — as the live frontier. This memo does the inward half the trending-scout doesn't: *given these systems/papers, where does OUR loop stand, and what's the concrete gap?* Satisfies the `agent-infra-sweep` freshness cadence with differentiated content, not an outward re-scan (the 06-20 12-scout sweep already covered the outward landscape 4d ago).

**Frontier timeliness caveat (per global `<ai_text_policy>`):** the paper RATE claims below run on pre-frontier open models (the trending-scout flagged this). I lean on the **METHOD** (transfers regardless of model generation), never the specific rate, for every finding.

## Our loop vs each frontier system

| Frontier system | What it does | Our loop's standing | Gap |
|---|---|---|---|
| **Harness-Updating-Is-Not-Harness-Benefit** (2605.30621) | update-GENERATION ≠ update-BENEFIT; uptake is the bottleneck, measure mutator-quality and consumer-uptake **separately, held-out, per-consumer** | Our F3 predict-then-falsify gate (`predict-then-falsify-gate.md`) already does the negative-control half (a confounded control = reject) — and it BIT twice this session (over_caution, risky-diff both CONFOUNDED). | **REAL GAP (finding below): F3 measures "did the metric move vs control" but NOT "does the change transfer to a *weaker consumer* held-out."** A rule validated on Opus is not validated for a Haiku subagent. |
| **MiMo-Code** (judge-gated `/goal`, `/dream`, `/distill`) | independent-judge model gates stopping (anti "optimistic stop") | Our `/rsi` close + reflect gate already verify one principal claim independently; verifier-conditioned autonomy is the constitution's spine. | Covered in shape — no build (we're single-operator, no OpenCode fork; settled in trending-scout verdict). |
| **APEX** (2606.15363) — L2 success-trace distillation | distill behavioral principles from SUCCESS traces | We distill **failure** (the correction ledger / `[obs]` stream); the positive-trace half is thin. | Known gap (the "save from success AND failure" note). Low-urgency; our failure ledger is the higher-signal half. |
| **HarnessFix** (2606.06324) — held-out trace attribution | trace→IR, step-level provenance, attribute failure to a step×harness-layer, report held-out | `session-trace` / `debug-until-dry` do span replay; attribution is coarser (session-level, not step×layer). | Watch — the held-out-attribution discipline reinforces the finding below; not a standalone build. |

## The one actionable finding (routed to improvement-log)

**F3 gate is consumer-tier-blind.** `mechanism_record.py` `metric_query`/`control_query` aggregate over ALL sessions — they never segment by the consumer model that the changed rule/hook actually runs under. The Harness-Updating result (method, not rate): a harness change's BENEFIT is non-monotonic in consumer strength, so a governance change validated on the operator's Opus turns can be neutral-or-harmful for a Haiku/cheap subagent that also reads the rule. Our gate would score it FIRED on aggregate and we'd keep it — blind to the weaker-consumer regression. This is the held-out/per-consumer discipline the frontier formalizes, applied to our own gate.

- **Routing:** agent-infra-local, F3-gate enhancement → `improvement-log.md` `[ ]`. NOT a shared-hook change (the gate is agent-infra-only). Discrete + checkable (add a consumer-tier split to the metric/control queries where `runs.model` varies).
- **Honest bound:** binds only where a rule's consumers actually span tiers AND the trace store has the per-consumer signal. Many rules are operator-only (no weaker consumer) → exempt. Validate at 1/10: first measure how many governance changes even HAVE cross-tier consumers before building the split.

## Verdict

Frontier is **convergent validation** of our existing architecture (verifier-conditioned autonomy, the F3 control-gate, failure-distillation) — not a call to adopt any external system. One real gap surfaced (F3 consumer-tier-blindness), routed. No builds triggered beyond that finding's `[ ]`.
