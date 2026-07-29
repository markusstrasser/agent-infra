---
title: Agent-infra frontier sweep — 20d delta + RSI package consumption
date: 2026-07-29
tags: [rsi, harness, agent-infra, sweep]
status: complete
prior: research/2026-07-09-agent-infra-sweep.md
window: 2026-07-09 → 2026-07-29
---

# Agent-infra Frontier Sweep — 2026-07-29 (20-day delta)

**Question:** What changed externally and internally since `2026-07-09-agent-infra-sweep.md`, and what did we **consume** from the 2026-07-29 observe→improve→codex package?

**Priors:** `research/2026-07-09-agent-infra-sweep.md`, `research/trending-scout-2026-07-09.md`, observe run `artifacts/observe/2026-07-29-2149/`.

---

## Verdict

**External:** model-suite GAs (Opus 5, GPT-5.6 Sol/Terra/Luna) already in routing; vendor CLIs patch-bumped (CC 2.1.220, Codex ~0.146). No new harness architecture forcing a re-platform.

**Internal (this package):** full observe-all + harvest + Codex cosign (**ACCEPT with fixes**). Sole P0 was **agentlogs sticky `event_id`** on `(run_id, seq)` re-import — **fixed + tested this tick**. arc_agi residual probe: guard works; miner double-counts log tails. Surveillance freshness DUE cleared by this memo + trending-scout-2026-07-29.

---

## External — worth knowing

| Item | Read | Action |
|------|------|--------|
| GPT-5.6 Sol/Terra/Luna GA | Already Default Routing | Noop |
| Opus 5 primary Claude | Adopted mid-window | Noop |
| CC 2.1.220 / Agent SDK bump | Patch train | Watch hooks-smoke |
| Codex 0.146 npm / 0.144.6 local | Fine for subscription cosign | Optional bump |

## Internal — consumed this session

| Ship | Evidence | Loop-health |
|------|----------|-------------|
| Observe-all 7d Tier-0 + digests | `artifacts/observe/2026-07-29-2149/` | Vector grow_coverage=30 dominant |
| Codex cosign of RSI package | `codex-review.md` (Opus 529×2) | ACCEPT w/ fixes |
| **Sticky event_id on re-import** | `src/agentlogs/index.py` + `tests/agentlogs/test_sticky_event_id.py` | Closes launchd PK thrash class |
| arc_agi residual probe | agentlogs + guard selftest 33/33 | Guard OK; miner FP on log-tail |
| Operator no-genomics gate | improvement-log | BIOCONDA/worktree inventory deferred |

## What not to build
- Worktree-inventory detector without recurrence probe (Codex: false promotion as written)
- BIOCONDA republish from symbol-skew alone (needs image digest proof; genomics gated)
- Re-open over_caution enforce (ablation closed)

## Next triggers
- Confirm next launchd agentlogs-index cycle has **zero** `UNIQUE constraint failed: events.event_id` in stderr
- Optional: failure-miner exclude "error text only appears in tailed log file content"
- Optional: `uv run pytest` rewrite coverage residual in arc-agi cwd-guard (shared — separate gate)

## Freshness
Clears `agent-infra-sweep` row for `just freshness` (memo name matches `research/*sweep*.md`).
