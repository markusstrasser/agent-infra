# RSI loop unification — synthesis + Opus 4.8 review

**Date:** 2026-06-20  
**Status:** proposal (revised after cross-model review)  
**Executes:** `decisions/2026-06-16-rsi-unified-control-surface.md` — not a re-decision  
**Provenance:** 4× composer-2.5 best-of-n runs (control-plane, feedback-loop, anti-Goodhart, motor-consolidation) → Opus 4.8 `max` critique via `llmx chat --subscription`

## Verdict

**Revise and ship incrementally.** Direction is right: finish the accepted pulse ADR, unify surfacing/handoffs, earn apply lane on tier-0 only. Opus flagged three load-bearing contradictions in the draft synthesis — fixed below.

## Diagnosis (unchanged)

Sensors healthy (reflect, fm.py, blindspot, AIR). Control layer scattered: ~12 launchd jobs, 4 SessionStart digests, 3 conductors, no inbox→act→verify→close path. Motor drafts exist; apply lane triple-gated off. Predictions register but rarely resolve.

## Target architecture

**One control plane (`pulse`), one interactive conductor (`/improve maintain`), sensors unchanged.**

```
Sensors (keep) → pulse tick (internal phased runner, NOT parallel script/plist)
              → pulse status / canary / gate / resolve
              → Ledger spine: improvement-log + maintenance-actions.jsonl
              → Independent verifiers: harness-eval, gov ablation, questions VIEW
```

**Do not** expose `scripts/rsi_tick.py` + separate launchd — phased tick is `pulse tick` subcommand inside `scripts/pulse.py`. Post-change conductor count must go **down**, not add a 4th.

## Revised ship order

| Phase | Work | Notes |
|-------|------|-------|
| **-1** | Fix `agentlogs-index`; bulk-triage legacy improvement-log rows; freeze tier taxonomy in `build-autonomy-tiers.json` (loop-immutable) | Prerequisites, not "blockers" |
| **0** | `pulse status` **additive** alongside 4 digests; prove parity | Do NOT delete digests until parity proven |
| **1** | `blindspot_convert.py` → maintain-candidates; structured `[ ]` frontmatter + harness-eval lint | Clean ledger first |
| **2** | Manually resolve existing predictions (VOI probe); then `pulse resolve` stub | Confirm auto-checkable before building |
| **3** | Delete legacy digests post-parity | Same dry-run discipline as motor |
| **4** | `pulse tick --dry-run`; shadow-write egress; work-done parity gate (not exit-0 alone) | External freshness canary; no self-report from tick state |
| **5** | Consumed-alert spine (4-state: fired→consumed→outcome-known→scored); supervision vector → joint-alarm; autonomy-exception → questions VIEW (no 5th queue) | Architecture, not prose guards |
| **6** | Negative half: revert→demote, marker-file kill-switch, per-tick token budget | Before apply lane |
| **7** | Earned tier-0 apply (5-condition AND + stricter PPV than surfacing threshold) | Same timing, complete mechanism |

## Opus revisions incorporated

1. **`pulse tick` not `rsi_tick.py`** — internal module OK; no parallel entry/plist.
2. **Additive→parity→cutover** for every build+delete; Phase -1 before lint/parity.
3. **Negative feedback arc** — SHADOW→promote→apply→**revert→demote** before flipping apply.
4. **Kill-switch** — external marker file halts all applies independent of tick process.
5. **Drop "single ledger" oversell** — one spine (improvement-log + maintenance-actions.jsonl); side-stores must fold or justify against no-5th-queue ADR.
6. **Deletion gate** — work-done parity (candidates drained, drafts produced), not ≥95% exit-0.
7. **Canary independence** — freshness clock external to `last-tick.json`.
8. **Parity window** — shadow-write only; no double-drain on live ledger.

## Anti-Goodhart (mechanisms, not memo prose)

| Guard | Enforcement surface |
|-------|---------------------|
| No composite RSI health score | Never build; pulse reports components only |
| Joint alarm | supervision↓ ∧ error-visibility↓ detector in act-drain |
| PPV thresholds | Surfacing ≥60%; apply lane stricter + rate math |
| Signal lifecycle | 4-state; consumed ≠ outcome-known |
| Per-tick cost | reason_tok/out_tok log + budget gate |
| Tier boundaries | Single-sourced config + drift test; loop cannot mutate |

## Keep / delete

**Keep:** gov.py report-only, harness-eval, reflect_capture, blindspot logic, `/improve maintain`, agentlogs-index, clash-detect (sole LLM shadow).

**Delete (post-parity):** integrate-rank launchd, separate SessionStart digests, loop_funnel CLI → `pulse funnel`, steer-mining orphan, prose-only new `[ ]` entries, legacy motor plists (after work-done parity).

## Cross-model review

Full Opus 4.8 `max` critique: session artifact at `.cursor/rsi-unification-opus-review.md` (not checked in — ephemeral). Key quote: *"Earned autonomy without the negative-feedback arc and a kill-switch is just Goodhart in slow motion."*

## Next action

Phase -1 + Phase 0 only: fix agentlogs-index, triage improvement-log tail, ship `pulse status` additive.
