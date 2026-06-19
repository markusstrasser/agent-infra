---
title: Multiagent session survey + orchestrator tool proposals
date: 2026-06-19
tags: [observe, multiagent, orchestrator, tools, agentlogs]
status: active
window: 2026-06-12 → 2026-06-19 (7d)
method: agentlogs SQL + audit addendum cross-check
---

# Multiagent session survey + orchestrator-model tool proposals

**Question:** Last 7 days of multiagent sessions — what patterns recur, and what tools should the **orchestrator model** (frontier parent) have?

**Roles:** **Operator** = human. **Orchestrator model** = frontier parent that dispatches scouts. See `.claude/rules/orchestrator-vocabulary.md`.

**Verdict:** Multiagent **works** (genomics hunt, anim worktrees, critique scouts, steer-mining). **~85–95% of session count is harness automation**, not operator work. The gap is **manifest/wait/merge/triage** for the orchestrator model — and **honest metrics** so the operator isn't misled by inflated session counts.

---

## Scale (7d, agentlogs)

| Day | Total sessions | Auto (subagent or <1m) | Operator (≥5m, parent) |
|-----|----------------|------------------------|-------------------------|
| Jun 12 | 195 | 102 | 73 |
| Jun 13 | 174 | 136 | 8 |
| Jun 14 | 330 | 300 | 18 |
| Jun 15 | 558 | 537 | 7 |
| Jun 16 | 352 | 327 | 8 |
| Jun 17 | 164 | 124 | 16 |
| Jun 18 | 219 | 183 | 21 |
| Jun 19 (partial) | 132 | 123 | 6 |
| **Sum** | **~2124** | **~1832 (86%)** | **~157 (7%)** |

**Vendor/project hotspots (7d):**

| Bucket | n | Role |
|--------|---|------|
| cursor `llmx-cache` workspace | 276 | llmx/cursor transport probes |
| cursor steer-mining-ws | 225 | parallel steer extract workers |
| codex `bare` bootstrap | 208 | AGENTS.md preamble / hook shim |
| cursor genomics | 179 | bug-hunt scouts |
| claude agent-infra | 304 (42 subagents in tree) | RSI/planning/decide |
| anim-workbench worktrees | 32+ named wt-* dirs | parallel implementation fan-out |

---

## Multiagent patterns (verified from first_message clusters)

### 1. Adversarial audit waves (dominant cursor pattern)

**Evidence:** genomics Jun 18–19 — 11 passes × 4–6 scouts; one parent cursor session logged **247 subagents**; 175 zero-duration sessions with generic "code reviewer" prompt; 43 "VOI premise scout" (critique/decide).

| Session prefix | Project | subagent_count | Pattern |
|----------------|---------|----------------|---------|
| cursor:f | empty-window | 247 | Extended bug-hunt orchestration |
| cursor:6 | genomics | 42 | `/debug` "Find bugs from today's work" |
| cursor:d | genomics | 15 | Full-repo lingering-bug audit |
| arc-agi | 14 | 6 parallel area audits (loop/, agent/, src/) |

**Now partially scripted:** `just debug` + `debug_triage.py`. **Still manual:** pass scheduling, pass count, fix vs doc-only policy, merging with code-review-scout JSONL.

### 2. Worktree parallel implementation (anim-workbench)

**Evidence:** claude:e anim-workbench **3728 min, 104 subagents** — explicit "You are the orchestrator" handoff. **50+ worktree slug sessions** (`anim-workbench-wt-*`, `anim-workbench-claude-worktrees-*`) with dispatch prompts: "IMPLEMENTATION… Dispatched by the orchestrator."

**Mechanism:** Claude parent decomposes → cursor/composer workers in isolated worktrees → orchestrator merges/reviews.

**Gap:** No `just worktree-dispatch` — entirely skill + manual Claude session. No **disjoint-file validator** before parallel dispatch (research memo: merge hell prevented at decomposition time, not merge time).

### 3. Research / RSI comparative fan-out

**Evidence:** Jun 18 agent-infra — 5 parallel cursor "Explore RSI in anim/hutter/intel/research" → `2026-06-18-hutter-anim-rsi-comparative-report.md`. Trending scout uses 4 parallel researchers.

**Gap:** No **bridge-promote** — hutter report did not auto-seed arc-agi scaffold; human re-triggered Jun 18–19.

### 4. Critique / decide repo-grounding panel

**Evidence:** 43 premise-scout cursor sessions; model-review context packets; debug pipeline critique used cross2 + repo-grounded cursor.

**Partially scripted:** `model-review.py`, `/critique`. **Missing:** unified **premise-scout-batch** launcher (same shape as debug_scout) + triage into `.model-review/*/findings.md`.

### 5. Steer-mining worker pool

**Evidence:** 225 cursor sessions, identical mine prompt in `Users-alien-claude-steer-mining-ws`. Manual `mine_steers.py --workers 3`.

**Gap:** Workers work; **cluster→improvement-log `[ ]`** does not. Vectors sit in JSONL until human reads steering-vectors memo.

### 6. Codex subagent trees (genomics)

**Evidence:** codex genomics session **74 subagents**, 222 min — long-running codex orchestration parallel to claude.

**Gap:** agentlogs indexes it; **no cross-vendor orchestrator view** (claude parent + codex parent + cursor scouts in one manifest).

### 7. Stop-hook verification fleet (invisible automation)

**Evidence:** 69 Haiku sub-sessions / 48h (audit addendum) — "review an AI coding agent…" Stop hook.

**Gap:** Counted as operator sessions in naive metrics. Needs **session-classify** in `loop_funnel.py` / dashboard.

### 8. Cross-repo config consistency (one expensive session)

**Evidence:** claude:b agent-infra 128m — "Look thru all convos in phenome and genomics and hutter… hook/settings decisions."

**Gap:** No standing **config-consistency-scan** across projects.

### 9. Large-diff decomposition trigger (genomics heuristic)

**Evidence:** claude:1 genomics — "any diff over ~1500 lines is too big" + research memo `2026-06-16-agentic-decomposition-gating-prior-art.md`.

**Gap:** No **decompose-gate** script: diff stat → recommend serial vs N worktrees vs reject.

---

## Tool proposals (ranked by 7d evidence × loop closure)

Legend: **P0** = closes verified gap this week; **P1** = high leverage, needs decide; **P2** = useful, measure first.

| Rank | Tool | Job | Evidence | Tier |
|------|------|-----|----------|------|
| **T1** | `session-classify` | Tag sessions: operator / cursor-scout / stop-hook / steer-worker / codex-bootstrap in dashboard + loop_funnel | 86% inflation | P0 |
| **T2** | `fan-out-lib` + `scout-triage` | Shared launcher (debug + code-review-scout + premise-scout); JSONL manifest; one triage → handoff | 175+ review scouts; duplicate code in 2 scripts | P0 |
| **T3** | `audit-delta` | `since-green` + auto-suggest `just debug --scope recent` when N commits on path X or contract lint red | Genomics 11-pass hunt 100% manual | P0 |
| **T4** | `review-queue` | Rank scout findings by severity × confidence; cap at human review throughput (~200–400 LOC/hr) | Willison bottleneck; genomics doc-only hunt | P1 |
| **T5** | `gate-for` | Run verifier recipe, capture pass/fail artifact | Every multi-commit session | P1 |
| **T6** | `fix-prep` | Per handoff item: grep + test target + files → fix brief | Debug handoff → implement gap | P1 |
| **T7** | `config-consistency-scan` | Cross-project diff of hooks/settings/skills symlinks | 128m cross-repo session | P1 |
| **T8** | `bridge-promote` | When comparative memo lands, emit scaffold checklist for target repo (arc-agi from hutter RSI) | Manual re-seed twice | P1 |
| **T9** | `steer-cluster-promote` | Cluster steer JSONL → top 3 `[ ]` improvement-log stubs | 495 signals / manual read | P1 |
| **T10** | `decompose-gate` | `git diff --stat` → SERIAL / PARALLEL-N / ABORT + disjoint file sets | 1500-line heuristic + anim 104-sub | P1 |
| **T11** | `worktree-dispatch` | Given disjoint slices, spawn named worktrees + cursor agent with charter template | 50 anim wt sessions | P2 |
| **T12** | `fan-out-wait` | Poll manifest until all scouts done; aggregate exit codes | Parent waits ad hoc today | P2 |
| **T13** | `orchestrator-manifest` | Single JSONL: parent_session, scouts[], artifacts[], status | Cross-vendor blind spot | P2 |
| **T14** | `critique-handoff` | Merge model-review + code-review + debug into one ranked packet | decide/critique sessions | P2 |

**Already shipped this session:** `commit-plan`, `integrate-rank`.

**Do NOT build yet (measure first):**
- Semantic diff gate (inspect/kai/vibediff eval per `2026-06-16-agentic-decomposition-gating-prior-art.md`)
- Monolithic `orchestrate` skill (decide plan rejects)
- Subagent commit batching (rejected)

---

## Architecture insight (from week, not generic)

Three **successful** multiagent modes ran in parallel without sharing a motor:

1. **Verification scouts** (debug, code-review, premise-scout) — partial verifier domains
2. **Implementation fan-out** (anim worktrees) — clear file boundaries
3. **Preference capture** (steer-mining) — extract only, no synthesis

Unifying them doesn't mean one mega-agent. It means:

```
integrate-rank → pick mode → fan-out-lib → scout-triage → review-queue
     → fix-prep → gate-for → commit-plan --apply
```

maintain-tick handles tier-0 when human isn't in loop.

---

## Revised priority stack (supersedes audit addendum A0–A4 ordering)

| # | Action | Why |
|---|--------|-----|
| 1 | Load maintain-tick + integrate-rank launchd | motor + daily rank |
| 2 | session-classify | metrics lie without it |
| 3 | fan-out-lib + scout-triage | dedupe debug/code-review/premise |
| 4 | audit-delta | generalize genomics hunt |
| 5 | fix-prep + gate-for | close verify→fix loop |
| 6 | config-consistency-scan | one-shot → scheduled monthly |
| 7 | bridge-promote + steer-cluster-promote | synthesis gaps |

---

## /decide candidates (hard choices)

1. **fan-out-lib scope** — merge debug_scout + code-review-scout only, or include premise-scout + worktree-dispatch?
2. **audit-delta triggers** — commit count vs time vs gate-fail (genomics: canary green + contract lint red)?
3. **decompose-gate threshold** — 1500 LOC alarm vs 400 LOC review cap (research says both)?
4. **review-queue automation** — human-only ordering vs LLM rank (integrate-rank sub-module)?

See `.claude/plans/2026-06-19-orchestrator-tooling-decide.md` — extend with T1–T14.

---

## Verification

```bash
sqlite3 ~/.claude/agentlogs.db "SELECT COUNT(*) FROM sessions WHERE start_ts >= '2026-06-12'"
sqlite3 ~/.claude/agentlogs.db "SELECT project_slug, COUNT(*) FROM sessions WHERE start_ts >= '2026-06-12' AND vendor='cursor' AND duration_min < 1 GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
rg "fan-out-lib|audit-delta" scripts/  # should be empty until built
```
