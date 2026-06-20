# RSI Loop Unification — Combined Recommendation (best-of-n synthesis)

**Date:** 2026-06-20  
**Source:** 4× composer-2.5 runs (control-plane, feedback-loop-closure, autonomy-without-goodhart, motor-consolidation)  
**Builds on:** `decisions/2026-06-16-rsi-unified-control-surface.md`, constitution verifier-conditioned autonomy

## Diagnosis

Agent-infra has healthy **sensors** (reflect, fm.py, blindspot, AIR) but **scatter at the control layer**: ~12 launchd jobs, 4 SessionStart digests, 3 conductors (`/observe`, `/improve maintain`, maintain-tick), no single inbox→act→verify→close path. Motor drafts exist but apply lane is triple-gated off. Predictions register (5) but never resolve (0).

## Target Architecture: "Pulse Inbox + Phased Tick"

**Principle:** Sensors stay; unify bookkeeping, handoffs, surfacing only.

```
Sensors (keep) → rsi-tick (phased: sense→drain→synthesize→motor→surface)
              → pulse (status/canary/gate/resolve) as control plane API
              → Single ledger: improvement-log ingress → maintenance-actions.jsonl egress
              → Independent verifiers: harness-eval, gov ablation, questions VIEW, predictions resolve
```

### Phase 0 — Unify surface (1–2 sessions)
- `pulse status` + unified `control-plane-inbox.md` / `rsi-digest.md` (kill 4-digest SessionStart merge)
- Wire motor drafts into inbox
- Fold top_priorities into act-drain
- Supervision direction vector in drain (not scalar SLI)

### Phase 1 — Close leaks
- `blindspot_convert.py` → maintain-candidates.json (≥2 sessions, ≥3 flags; no auto-ship)
- Structured `[ ]` frontmatter + lint in harness-eval
- `pulse resolve` for auto-checkable predictions
- `consumed-alert` spine on detectors
- `session-regime.jsonl` + autonomy-exception log

### Phase 2 — Motor consolidation (after 7d dry-run parity)
- `scripts/rsi_tick.py` + `artifacts/rsi/last-tick.json`
- Delete 6 legacy plists after ≥95% tick success / 14d
- Keep agentlogs-index, clash-detect, harness-eval separate

### Phase 3 — Earned autonomy
- Flip `go_live.maintain_tick_apply` only for tier-0 local + named verifier + prediction + harness-eval + 14d revert
- Gov-shrink auto-apply same pattern after track record
- Never auto-ship tier 2–3 or composite "RSI health score"

## Anti-Goodhart guards

**Do NOT optimize:** funnel capture count, [x] closure rate, drafts/week, hook fire count alone, automation %, composite RSI score, blindspot flags without PPV graduation.

**Keep independent:** harness-eval, fm 2+ recurrence, gov ablation, human questions VIEW, cross-model critique on shared infra, predictions resolve.

**Operating rule:** SHADOW → PPV ≥60% on ≥30 firings → promote. Alarm on supervision↓ AND error-visibility↓ jointly.

## Ship order
1. pulse status + unified digest
2. blindspot_convert + improvement-log frontmatter lint
3. pulse resolve stub
4. rsi_tick.py --dry-run (7d parity)
5. regime/exception log + consumed-alert
6. earned tier-0 apply

## Delete (consensus)
- integrate-rank launchd
- Separate SessionStart digests
- loop_funnel CLI → pulse funnel subcommand
- Steer-mining orphan ledger
- Prose-only new [ ] entries

## Keep
- gov.py report-only, harness-eval, reflect_capture, blindspot miner logic, /improve maintain as interactive conductor

## Known blockers
- pulse Phase 2–3 not fully shipped
- Apply lane triple-gated off (by design)
- agentlogs-index exit 1
- improvement-log legacy rows need bulk-triage
