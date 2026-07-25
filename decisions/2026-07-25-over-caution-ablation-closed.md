---
title: over_caution enforce→shadow ablation — closed, both bands PASS
date: 2026-07-25
tags: [governance, ablation, smart-judge, supervision-kpi]
status: active
supersedes: decisions-pending/2026-07-10-ablate-over-caution-enforce.md
---

# over_caution ablation — CLOSED, keep the vector out of enforce

The 2026-07-10 ablation removed `over_caution` from `SMART_JUDGE_ENFORCE_VECTORS`
(leaving it classified in shadow) on the theory that enforcing it cost 27–38s of
Stop-hook latency plus a metered haiku fast-path without reducing timidity. The
pre-registered 14d window closed 2026-07-24; measured 2026-07-25.

## Result — both pre-registered bands pass

Source: `scripts/supervision-kpi.py --days 14`, 791 sessions, 2026-07-11→07-25 (15 days).
Baseline window 2026-07-03→10 (observe run 1514): over_caution=9, rediscovery=7 per 7d.

| Metric | Baseline | Measured | Band | Verdict |
|---|---|---|---|---|
| typed `over_caution`/day | 1.29 | **0.40** (6 total) | flat or ↓ | **PASS** (−69%) |
| control: `rediscovery`/day | 1.00 | **0.20** (3 total) | no spike >2× (≤2.00) | **PASS** |

Removing the enforcement did not increase over-caution — it fell. The control did
not spike; it also fell. The latency and metered-haiku cost bought nothing.

## Decision

`over_caution` stays **out** of `SMART_JUDGE_ENFORCE_VECTORS`. The classifier vector
stays (shadow scoring is retained, per the ablation's non-goals). No replacement
timidity hook.

## Honest limits

The control is **weakly powered**: 3 rediscovery events in 15 days. "Did not spike
>2×" is satisfied with room to spare, but the band would also have been satisfied by
noise at this N. The over_caution arm is better supported (6 events vs a 1.29/day
baseline that would have predicted ~19). Directionally unambiguous, statistically thin
— treat as "no evidence of harm" rather than "proven improvement."

Confound worth naming: the window overlaps the Opus 5 rollout (2026-07-24), but only
its final day, so the bulk of the window is pre-rollout and the verdict is not an
Opus 5 artifact.

## Downstream

Unblocks `decisions-pending/2026-07-16-turn-retrieval-hook-activation.md` step 1
("close the ablation and record whether rediscovery/day stayed within its
preregistered control band" — it did). The control-hygiene freeze on
rediscovery-touching changes is lifted.

Evidence: `decisions-pending/2026-07-10-ablate-over-caution-enforce.md` (the prereg),
`scripts/supervision-kpi.py --days 14`.
