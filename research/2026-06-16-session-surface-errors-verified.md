---
date: 2026-06-16
topic: Session-verified surface errors — corrected Codex skills, measured budgets, agentlogs forensics
tier: deep
method: agentlogs.db SQL + live mount checks + improvement-log cross-ref
supersedes_claims_in:
  - research/2026-06-15-agent-extensibility-surfaces.md  # Codex "no skills" — WRONG
  - research/2026-06-15-agent-surface-architecture.md     # "Codex invisible" — WRONG
---

# Session Surface Errors — Verified Research (2026-06-16)

**Question:** What surface errors actually recur in sessions, and what did we get wrong about Codex skills?

**Data:** `~/.claude/agentlogs.db` (3.8GB, indexed through 2026-06-15), live filesystem mounts, git, improvement-log.

---

## Correction: Codex has skills

**Prior error:** Memos claimed Codex lacks a skills primitive and needs AGENTS.md flattening.

**Verified:** Codex ships the **open agent skills standard** (same `SKILL.md` format as Claude/Cursor).

[SOURCE: https://developers.openai.com/codex/skills]

| Path | Role | Our state (2026-06-16) |
|------|------|------------------------|
| `~/.agents/skills/` | User-global discovery | **22 symlinks** → `~/Projects/skills/*` |
| `~/.codex/skills/` | Legacy user path | **12 symlinks** + `.system/` bundled |
| `<repo>/.agents/skills/` | Repo-scoped | Symlink → `.claude/skills` via `codex_parity_sync.py` |
| `~/Projects/skills/` | Source of truth | 52 skills; friend-sync origin |

**Codex loads skills with progressive disclosure:** name + description in index (~8k char budget); body loaded on invoke. [SOURCE: OpenAI Codex skills docs]

**Agentlogs blind spot:** Codex never emits `tool_name='Skill'` (0 rows ever). Usage appears as:

```
exec_command: sed -n '1,220p' .../skills/modal/SKILL.md
exec_command: sed .../genomics/.agents/skills/genomics-pipeline/SKILL.md
```

**Measured Codex skill file reads (60d):**

| project | SKILL.md reads via exec_command |
|---------|--------------------------------|
| genomics | 536 |
| intel | 194 |
| phenome | 126 |
| agent-infra | 92 |

**Conclusion:** Skills are live on Codex. Gaps are **mount coverage** (`~/.codex/skills` 12 vs `~/.claude/skills` 41) and **description budget**, not a missing primitive. **Do not build AGENTS.md skill flattening.**

---

## Description budget — measured today

Codex caps skills index at **~8,000 chars** (or 2% context). [SOURCE: developers.openai.com/codex/skills]

| Population | Chars (sum of `description:` lines) | vs 8k |
|------------|-------------------------------------|-------|
| `~/.claude/skills` (Claude index) | **10,553** | **OVER** |
| `~/.agents/skills` (Codex user-global) | **6,442** | OK |
| `~/.codex/skills` (legacy subset) | **2,423** | OK |
| `intel/.agents/skills` (per-repo) | **7,726** | OK (was 10,002; fixed intel@5b449075) |
| **intel session combined** (global + repo) | **14,168** | **1.8× over** |

**Binding error:** Measuring `~/Projects/skills` or `~/.claude/skills` alone misses the **combined** load Codex applies (user-global + repo `.agents/skills`). improvement-log 2026-06-13 caught this.

**Preempt:** `just skills-budget` recipe — sum descriptions for the **loaded set** per vendor/session, not source dir.

---

## Hypothesis results (session evidence)

| ID | Hypothesis | Verdict | Evidence |
|----|------------|---------|----------|
| H1 | Review stacking post-partition | **PARTIAL** | 0 sessions with both `code-review` + `critique` Skill since 2026-06-14. Also **0** `code-review` Skill invocations — partition **not exercised**, not proven. |
| H2 | Codex skills = mount gap not missing primitive | **VERIFIED** | See above; `codex_parity_sync --check` OK for 4 repos. |
| H3 | intel skills over 8k budget | **PARTIAL** | Per-repo fixed (7726). Combined global+repo still 14,168. |
| H4 | MCP bypassed for modal bash | **REFUTED (Jun 2026)** | genomics codex 60d: `mcp__genomics__modal_volume_inspect` **457**, `mcp__modal-triage__list_apps` **166**; `modal app list` bash **3**. Apr finding stale. |
| H5 | Premature plan-complete | **VERIFIED** | improvement-log: genomics 2026-04-10/12, agent-infra 2026-06-03; **no architectural gate shipped** ([ ] proposed). |
| H6 | Advisory hooks without behavior change | **PARTIAL** | subagent-gate promoted BLOCK 2026-05-11; `read-discipline` **6680**/60d still advisory (gov-report). |
| H7 | Four-surface dedup minting | **REFUTED post-fix** | intel 2026-06-04 incident; extract-generators fix shipped; 0 recurrence logged. |

---

## Tool surface inventory (agentlogs, 60d)

**Codex tool names differ from Claude** — queries must use `exec_command`, not `Bash`:

| Codex tool | Calls (all time in DB) | Notes |
|------------|------------------------|-------|
| exec_command | 47,867 | Primary shell; includes skill reads |
| apply_patch | 7,656 | |
| modal_volume_inspect | 409 | MCP-exposed native name |
| spawn_agent | 375 | Subagent dispatch |

**Claude Skill invocations (60d):** critique 162, research 63, code-review 19 — **Codex: 0** (telemetry gap, not absence).

---

## Revised error priority (evidence-ranked)

| Rank | Error | Confidence | Preempt |
|:----:|-------|------------|---------|
| **1** | **Skills index over budget** (Claude 10.5k; intel combined 14k) | HIGH [DATA] | Trim descriptions; scope intel skills; `skills-budget` check in drift-sentinel |
| **2** | **Premature plan-complete** (recurring, no gate) | HIGH [DATA] | Stop hook shadow → BLOCK on missing closeout artifacts |
| **3** | **Opaque MCP/script failures** (no `fix:`) | HIGH [INFERENCE + ADR] | Failure envelope on agent_infra_mcp |
| **4** | **Closeout partition unenforced** (docs yes, 0 post-ship exercise) | MED | `review_gate triage` lint before design pass |
| **5** | **Codex mount drift** (12 vs 41 symlinks on legacy path) | MED [DATA] | Extend `friend-sync` / parity to sync `~/.agents/skills` from full Claude set |
| **6** | **Advisory hook noise** | MED [DATA] | gov.py promote-or-kill loop |
| ~~7~~ | ~~MCP modal bash bypass~~ | REFUTED Jun 2026 | Monitor only |
| ~~8~~ | ~~Codex AGENTS.md skill bridge~~ | N/A | **Cancel** — wrong diagnosis |

---

## Claims table

| Claim | Status | Source |
|-------|--------|--------|
| Codex has SKILL.md skills | VERIFIED | developers.openai.com/codex/skills; live mounts |
| Codex skill usage invisible in Skill tool_calls | VERIFIED | agentlogs: 0 codex Skill rows; 536 genomics SKILL.md reads |
| Claude skills index exceeds 8k descriptions | VERIFIED | wc: 10,553 chars |
| intel combined skills index ~1.8× Codex budget | VERIFIED | 6442+7726=14168 |
| Review stacking eliminated post-2026-06-14 | UNVERIFIED | 0 stacked sessions but 0 closeout exercise |
| Modal MCP bypass still dominant | REFUTED | MCP modal tools >> bash app list (Jun 2026) |
| Four-surface dedup still minting dupes | REFUTED | Post 2026-06-04 fix |

---

## Plan revisions

**Cancel:** Wave 3 "Codex AGENTS.md skill bridge" from `preempt-surface-errors.md`.

**Add:**
1. `just skills-budget` — measure loaded description chars per vendor context
2. Sync `~/.agents/skills` to match `~/.claude/skills` in friend-sync (not legacy `~/.codex/skills` only)
3. Trim Claude global descriptions to ≤8k (or accept Codex shortening behavior per docs)

**Keep:** failure envelopes, closeout dispatch lint, plan-complete gate, advisory retirement.

---

## Appendix: background query results (2026-06-16)

### subagent-gate / advisory (task 769742)

`SUBAGENT WRITE-FIRST` events post BLOCK fix (2026-05-11):

| date | count |
|------|-------|
| 2026-06-11 | 42 (peak) |
| 2026-06-12 | 23 |
| 2026-06-13 | 8 |
| 2026-06-14 | 1 |

Pattern **persists but declining** — not eliminated by BLOCK promotion.

`read-discipline` top sessions (60d): genomics `07992a15` (7), agent-infra `019e9c97` (7), genomics `019ebcf1` (6).

### premature plan-complete (task 114531)

60d query: sessions with `complete_claim=1` AND (`had_plan_close=0` OR `user_challenge=1`) → **15 hits**.

Notable (non-noise):
- `e286ccea` genomics 2026-06-12 — complete claim + **user challenge** (matches improvement-log)
- `2b8ac808`, `bcaa3f63`, `e29014d6` agent-infra 2026-06-13 — complete claim, no plan-close

Many hits are `Users-alien-cache-llmx-cursor` Cursor sessions — likely false positives from generic "done" language; filter by project slug for gate design.
