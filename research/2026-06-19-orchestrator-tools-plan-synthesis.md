---
title: Orchestrator-model tooling — empirical test + brainstorm + critique synthesis
date: 2026-06-19
tags: [observe, tools, critique, brainstorm]
status: active
---

# Tooling plan (tested, critiqued, renamed)

Cross-model critique: `.model-review/2026-06-19-orchestrator-tools-plan-268558/` (36 findings, cross2).

## Empirical value (I ran these 2026-06-19)

| Tool | genomics | arc-agi | Value | Verdict |
|------|----------|---------|-------|---------|
| **audit-delta** | 20 commits, 7 files, useful log | 20 commits, 16 files, R3 cluster visible | **4/5** | Keep → rename **`since-green`**, fix bugs |
| **commit-prep** | planctl -361/+182 visible | overview drift visible | **4/5** | Fold into **`ship-plan --glance`** |
| **commit-plan** | 5 slices OK; bad artifacts slice | misses untracked without flag | **3/5** | Fold into **`ship-plan`** + exclusions |
| **scout-triage** | **0 findings** vs 619-line fix-backlog | no audit dir | **1/5** | Replace with **`findings-merge`** |
| **session-classify** | global 92.6% auto | same | **2/5** | Rename **`session-telemetry --project`** |
| **loop-funnel** | N/A | N/A | **3/5** | Keep (RSI inbox) |
| **integrate-rank** | generic infra top-3 | not project-specific | **2/5** | **Cut LLM path**; loop-funnel enough |

**Ground truth:** `genomics/docs/audit/2026-06-19-fix-backlog.md` (P0 INT-01…) beats all automated triage today.

---

## Final plan (P0 → P1)

### P0 — correctness before features

1. **baseline-since-last-green** (rename from audit-delta)
   - Per-repo state: `artifacts/baseline-since-last-green/{slug}.json`
   - `--suggest-only` → gate **UNKNOWN**, not GREEN
   - Auto-detect gate: `canary` (genomics), `health` (arc-agi), `smoke` fallback
   - Emit JSON contract: `{baseline_sha, head_sha, gate_status, files_changed, trigger_reasons[]}`

2. **audit-findings-consolidation** (replace scout-triage)
   - Inputs: debug FINDING blocks, `fix-backlog.md` tables, handoffs, code-review jsonl
   - Output: `{date}-findings-consolidation-handoff.md`
   - Test: genomics fix-backlog → must extract P0 rows

3. **commit-slice-planning** hygiene
   - Merge prep + plan; `--status-only` for glance
   - Exclude `artifacts/**`; refuse apply on placeholder subjects; stamp `head_sha`

### P1 — operator surface

4. **`just operator-status-briefing`** — operator one-pager
5. **`session-automation-telemetry --project genomics`**
6. **`verification-gate-runner`**

### Cut / defer

- **integrate-rank LLM** — maintenance drag, score 2; keep deterministic launchd memo or delete
- **fan-out-lib** — defer until premise-scout launcher exists
- **fix-prep, config-consistency-scan, review-queue** — P2 after findings-merge works
- **Monolithic orchestrate skill** — reject

---

## Naming map (canonical — multi-syllable)

| Old | Canonical name | Who runs it |
|-----|----------------|-------------|
| audit-delta | **baseline-since-last-green** | orchestrator model |
| scout-triage | **audit-findings-consolidation** | orchestrator model |
| commit-prep + commit-plan | **commit-slice-planning** | orchestrator model |
| session-classify | **session-automation-telemetry** | operator / infra |
| integrate-rank | **sensor-integration-ranking** | launchd |
| gate-for | **verification-gate-runner** | orchestrator model |
| (new) | **operator-status-briefing** | operator |
| debug | **adversarial-debug-scout** (`/debug` skill) | orchestrator dispatches |

Registry: `.claude/rules/orchestrator-tool-names.md`

Legacy just aliases for ~30d during rename.

---

## Critique highlights (accepted)

- Fake GREEN in suggest-only is **fail-open** → fix P0
- commit-plan staging its own artifacts → exclusion list P0
- P0 order was wrong (merge before parser) → findings-merge parser first
- `drift`/`brief` too vague → prefer **`since-green`**, **`preflight`** for gate+baseline bundle

## Critique highlights (partially reject)

- **Delete all tools → 3 commands only** — agree on public surface (`brief`, `since-green`, `ship-plan`, `findings-merge`, `debug`) but keep scripts modular internally (Constitution: architecture over monolith skill, not monolith binary)
- **Delete integrate-rank entirely** — keep deterministic daily memo OR fold into act-drain; don't require LLM
- **Schema-only fix-backlog** — don't force migration; parser for *existing* table format first

---

## Operator vs orchestrator model (unchanged)

- **Operator (you):** `just brief`, approve tier-1/2, ship/no-ship
- **Orchestrator model:** since-green → debug → findings-merge → ship-plan draft → gate-run
- **Scouts:** files only
