---
title: Agent-infra frontier sweep — delta since 2026-06-12
date: 2026-06-15
tags: [rsi, harness, agent-infra, sweep]
status: complete
prior: research/2026-06-12-agents-rsi-gap-sweep.md
window: 2026-06-12 → 2026-06-15
---

# Agent-infra Frontier Sweep — 2026-06-15 (3-day delta)

**Question:** What changed in agent/RSI/harness land since the Jun 12 deep sweep — both **external** (papers/vendor) and **internal** (what we built/consumed)?

**Prior baseline:** `research/2026-06-12-agents-rsi-gap-sweep.md` (4-axis, 15 window items, PACE + Self-Harness + harness sub-field survey).

---

## Verdict

**Internal loop is consuming, not accumulating.** The Jun 12→15 window shipped Composer CLI integration, context-budget canary, agentlogs `v_run_kind`, and risky-diff-review FP fixes — all landing in semantic commits, not orphan docs. **External frontier is quiet** except one new paper (RHO) worth a read before reflect-eval Jun 17.

No new adopt-grade infra from the external scan. The highest-leverage external item is **Cursor `/review` CLI** (vendor-native pre-push review) — watch, don't build.

---

## Internal — built & integrated (Jun 12→15)

| Ship | Evidence | Loop-health |
|------|----------|-------------|
| **Cursor CLI + Composer 2.5** wired into skills | `research/2026-06-14-cursor-cli-composer-integration.md`, improvement-log 2026-06-14, `cursor-agent` skill symlink | Generate→consume: memo same session as wiring |
| **Context-budget canary** in drift-sentinel | `context-budget.py --check` daily; genomics OVER flag now caught autonomously | RSI convert: blindspot class → detector |
| **agentlogs `v_run_kind`** (migration 006) | Subagent vs main-thread split queryable; fixes silent load overcount | Architecture: externalized recoverable state |
| **Codebase map hierarchical** | 89–98% context reduction across 5 repos (session b211880d) | Consume-before-act on context |
| **risky-diff-review FP fix** | `94cc042` — path-based doc edits no longer fire; refuse iatrogenic enforce-gate | Probe-before-enforce discipline |
| **blindspot-miner count fix** | `1110563` — count flag lines only | Measurement hygiene |
| **test-health regression fix** | schema tests v5→v6 (this session) | Error-correction loop self-monitor |

**Forks reconverged:** commit-gateway `/decide` arc closed Jun 14 (per observe delta digest). No dangling architectural forks in agent-infra.

---

## External — new since Jun 12 sweep

| Item | Source | vs Jun 12 | Action |
|------|--------|-----------|--------|
| **RHO** (Retrospective Harness Optimization) | arXiv:2606.05922 | **NEW** — trajectory self-preference without labeled validation | Read before reflect-eval Jun 17; compare to PACE accept-gate |
| **Adaptive Auto-Harness** | arXiv:2606.01770 | **NEW** — open-ended task streams, harness tree + routing | Watch — addresses deployment stream we don't model yet |
| **Cursor Bugbot `/review`** | cursor.com/changelog Jun 10 | **NEW to us** (post sweep) | Watch for CLI; may affect risky-diff-review promote/cut |
| PACE, Self-Harness, Bayesian-Agent, HGM mismatch | various | Already in Jun 12 sweep | No re-read |

---

## Gaps still open (unchanged from Jun 12 deferred list)

1. **PACE e-process accept-gate** — still "read full text before design adoption"
2. **Amendment-time drift check hook** — still pre-registered, no incident yet
3. **AHE falsifiable-contract pattern** — defer to hutter design session
4. **Hook `if:` path hoisting** — `[ ]` proposed Jun 13, not yet probed

---

## Wild card

**Cursor SDK `local.autoReview`** (Jun 4) + **`/review` pre-push** (Jun 10) are converging on the same product shape as our risky-diff-review SHADOW — but vendor-native and diff-aware. If CLI `/review` ships before Jun 21 promote/cut, the shadow hook may be **cut not promoted**. Measure: wait for CLI changelog, don't extend SHADOW scope.

---

## Search log

- Prior sweep + git log since Jun 12
- trending-scout-2026-06-15 (same session)
- arxiv search: harness optimization June 2026
- No full 4-axis researcher dispatch (3-day delta; quiet window)
