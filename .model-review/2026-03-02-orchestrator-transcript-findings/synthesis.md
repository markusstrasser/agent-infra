# Cross-Model Review: Orchestrator Plan + Transcript Findings

**Mode:** Review (convergent)
**Date:** 2026-03-02
**Models:** Gemini 3.1 Pro, GPT-5.2
**Constitutional anchoring:** Yes (CLAUDE.md Constitution section + GOALS.md)
**Extraction:** 41 items extracted, 27 included, 2 deferred, 0 rejected, 12 merged into 6 parents

## Context

This review targets the orchestrator implementation plan (`.claude/plans/3a65775d-orchestrator.md`) combined with 11 new findings from transcript analysis of 193 transcripts across 70 sessions (4 projects, Mar 1-2 2026). The first model review (2026-03-01) focused on the plan alone; this review incorporates observed usage patterns that the plan should address.

---

## Verified Findings (adopt)

### Critical Bugs (fix before implementation)

| IDs | Finding | Source | Verified How |
|-----|---------|--------|-------------|
| P3 | **Worktree contradiction.** "Decisions" (line 49): drop `--worktree`. "Risks #4" (line 759): "Execute steps use `--worktree`". Irreconcilable. | GPT | Verified: plan lines 49 vs 759 directly contradict. Line 7 header also says "add worktree isolation" (from round 1 review). |
| P4, P21 | **Approval gating not enforced in SQL.** `claim_task()` selects `WHERE status='pending'` with no filter on `requires_approval`. Tasks with `requires_approval=1` and `status='pending'` would be silently executed. Text says they should be `blocked`, but no code implements this. | GPT | Verified: `claim_task()` at lines 145-160. No `requires_approval` check. No `approved_at` column. No `approve` CLI code shown. |
| P5 | **Permission denials recorded as `done`.** Lines 279-292: if `permission_denials`, prefix summary text but still set `status='done'`. Violates success criterion #6 ("No silent failures"). | GPT | Verified: lines 282-292. Task completes with `status='done'` regardless of denial count. |
| P6, P22 | **Timezone bug in daily cost cap.** `finished_at=datetime('now')` stores UTC. `check_daily_cost()` compares `date(finished_at)` (UTC) against `date('now','localtime')`. Day-boundary mismatch around midnight. | GPT | Verified: lines 176-180. UTC left side, localtime right side. |
| P7 | **Template `agent` field not in schema.** `"agent": "entity-refresher"` in template (line 380) but `tasks` table has no `agent` column. **cwd tilde expansion bug:** `os.path.expanduser()` applied only to default path (line 198), not to `task["cwd"]`. Templates using `~/Projects/...` in cwd would fail. | GPT | Verified: schema lines 71-96 (no agent column); line 198 (expanduser on default only). |

### Architectural Changes (implement as designed)

| IDs | Finding | Source | Verified How |
|-----|---------|--------|-------------|
| G1, G9, P20 | **Split orchestrator into two engines: script + LLM.** Tasks like `skills_drift`, `earnings_refresh`, `pipeline_state` are deterministic scripts. Routing them through `claude -p` wastes tokens and adds failure modes. Add `engine` field to schema: `{'script','claude'}`. Script-engine tasks run directly with captured stdout+exit code. | Both models | Verified: F2 (skills drift) and F3 (earnings download) require zero LLM reasoning. `skills_drift` is literally `diff` + `rsync`. |
| G5, G10 | **Merge intel + meta orchestrators.** `intel/tools/orchestrator.py` has its own dispatch loop, creating an architectural collision with `meta/scripts/orchestrator.py`. Violates Principle 6 (Meta owns governance/tooling). Fix: delete intel's execution loop, preserve its `generate_*_tasks()` generators, have them INSERT into meta's SQLite DB. | Gemini | Claim verified by existence of `intel/tools/orchestrator.py` (noted in prior transcript analysis findings F6, F10). Schema compatibility (G15) is a valid risk — verify before merging. |
| G6, G8, G11, P11 | **Context Materialization as new task category.** The plan focuses on headless execution but misses the highest-ROI category: pre-computing STATE.md/TODAY.md files so interactive sessions start with zero orientation tax. Transcript analysis shows 49-78% of genomics sessions and 40-60 tool calls in intel Monday briefs go to rebuilding existing state. Implementation: `morning-prep` pipeline writes project-specific state files before human working hours. | Both models | Verified: transcript analysis findings F1, F8, F11 independently measured the orientation tax. ROI: 300k-900k tokens/week saved (GPT estimate). |
| G7, P10 | **DuckDB PreToolUse hook.** 11 column-not-found errors in 2 days despite CLAUDE.md instruction. Instructions alone = 0% reliable (Principle 1). Hook intercepts DuckDB queries, auto-runs DESCRIBE on target table, returns schema via `additionalContext` JSON. | Both models | Verified: 11 errors from transcript analysis (F7). Category: cascading waste. Hookable. |
| G4 | **Setup-volumes.sh readiness probe.** Running `setup-volumes.sh` as preamble to every `claude -p` call is fragile — may hang on auth/sudo in headless mode. Replace with deterministic readiness probe that blocks the queue on failure, not a preamble that can silently hang. | Gemini | Valid design concern. Volumes may already be mounted (no-op with overhead) or require interactive auth (hang forever). |

### Constitutional Compliance

| IDs | Finding | Source | Verified How |
|-----|---------|--------|-------------|
| G12 | **Cross-project config propagation is Hard Limit.** F9 (skills/config drift) affects 3+ projects. Constitution explicitly lists "deploy shared hooks/skills affecting 3+ projects" as never-without-human. Must enforce `requires_approval=1`. | Gemini | Verified: CLAUDE.md Constitution "Hard limits" section. Also confirmed by GPT (P23). |
| P23 | **Principle 4 at 55% — cross-project boundaries not enforced at scheduler level.** Orchestrator schedules cross-project actions but has no mechanism to distinguish "meta-only" from "shared infrastructure" changes. Need scheduler-level project isolation: cross-project execute steps always `requires_approval=1`. | GPT | Valid. `claim_task()` has no project-boundary enforcement. |
| P24 | **Transcript vs blast-radius tension — unresolved.** Dropping `--worktree` preserves transcripts but increases irreversible-state risk. Using `--worktree` provides isolation but kills transcripts (session-analyst feedback loop). No clean solution exists today. | GPT | Verified: pre-flight tests (line 43). Architectural tension, not a fixable bug. Monitor for Claude Code changes. |

### Success Criteria Fixes

| IDs | Finding | Source | Verified How |
|-----|---------|--------|-------------|
| P1 | **Plan-paste rate 44% — denominator unstated.** 25 instances / 70 sessions = 35.7%, not 44%. If 44% is meta-only, need meta-specific denominator. Fix: state per-project rates with explicit denominators. | GPT | Partially verified. Different counting methods plausible (per-session vs per-instance), but the plan doesn't disambiguate. |
| P2 | **Supervision waste 5.9% is definition-sensitive.** 24 low-signal actions / 385 messages = 6.2% already, before counting all waste. Need auditable labeling rule for what counts as "waste." | GPT | Valid methodology concern. The 5.9% figure isn't anchored to a reproducible classifier. |
| P15 | **Silent failure invariant checker.** Success criterion #6 ("no silent failures") needs enforcement: exactly one start + one terminal event per task id. If `done`, require: returncode=0 AND json_parse_ok AND permission_denials=0 (or explicit `done_with_denials`). | GPT | Valid. Currently no invariant check exists. |
| P16 | **Autonomy metric needs defined classifier.** "Correction/boilerplate turns -20%" isn't falsifiable without specifying what counts as correction vs legitimate work. | GPT | Valid. Session-analyst labels need inter-rater agreement or model stability check. |
| P17-19 | **Three new falsifiable predictions** (better than existing criteria): (1) Orientation commands drop ≥60% after pipeline_state injection. (2) `ls -la .claude/skills/` drops ≥80% after skills_drift nightly. (3) Earnings searches drop ≥90% after earnings_refresh. | GPT | High-value. These are measurable from transcript grep patterns and directly tied to observed pain. |

### ROI & Prioritization

| IDs | Finding | Source | Verified How |
|-----|---------|--------|-------------|
| G13 | **Priority ordering: (1) merge orchestrators, (2) context materialization, (3) DuckDB hook.** | Gemini | Sound framework. Merging first prevents dual-system divergence; context materialization is highest ROI; DuckDB hook is highest frequency. |
| P11 | **Top 3 ROI by token savings/effort: pipeline_state, morning_brief, earnings_refresh.** | GPT | Consistent with transcript evidence (F1 orientation tax, F11 Monday brief, F3 earnings searches). |
| P12 | **execute_plan is often token-neutral or negative.** Moving plan text from chat to file doesn't reduce tokens (file content still enters context via Read). Primary value is human scheduling, not token savings. | GPT | Valid challenge to assumptions. The plan-paste automation's ROI is in scheduling flexibility and reduced human paste-fatigue, not token reduction. |
| P13 | **Audit tasks (supervision_audit, epistemic_metrics, model_review) are investments, not savings.** Justify only if downstream reductions are proven. | GPT | Correct framing. These tasks spend tokens to find improvements. Track whether findings lead to implemented fixes that reduce future waste. |
| P14 | **monthly_pruning and research_gap_sweep weakly evidenced.** May not pay back in 90 days on token-only basis. | GPT | Valid. Low frequency + uncertain impact. Keep as lower-priority optional templates. |

### Blind Spots & Cautions

| IDs | Finding | Source | Verified How |
|-----|---------|--------|-------------|
| G14 | **Script reliability assumed.** Both models assume `genomics_status.py` and Intel generators are fast and deterministic. If they crash or need LLM parsing, the script-engine recommendation fails. | Gemini | Valid caution. Add health checks: exit code, output non-empty, execution time <30s. |
| G15 | **Intel schema compatibility uncertain.** Intel's `generate_staleness_tasks` may not map cleanly to meta's sequential SQLite schema. DAG or custom logic requirements would break the merge. | Gemini | Valid. Must verify before merging. Read intel's generators first. |
| P8, P25 | **Session-retro churn risk.** Nightly governance-writing (session-retro → improvement-log → CLAUDE.md patches) may create churn without recurrence proof. Gates needed: only promote findings with 2+ session recurrence, per existing constitutional self-improvement governance. | GPT | Valid. Constitution already requires recurrence (2+ sessions), but the orchestrator plan doesn't enforce this gate programmatically. |
| P9 | **F4 (subagent output race) not solved by scheduling.** Claude Code internals use tmp for subagents regardless of how the parent was invoked. `claude -p` doesn't change this. Fix requires enforcement (hook/skill) or Claude Code behavior change, not orchestrator scheduling. | GPT | Valid. The orchestrator can't fix this — it's internal to Claude Code's subagent implementation. |

---

## Deferred (with reason)

| IDs | Finding | Why Deferred |
|-----|---------|-------------|
| G3 | Subagent outputs to orchestrator-managed dir, not docs/ | Valid concern, but root cause is Claude Code's internal tmp cleanup. Fix depends on Claude Code version behavior. Monitor — revisit when subagent behavior is better understood or configurable. |
| G16 | Pushing back on docs/research/ loses human observability | Genuine tension between clean state management and audit trail. Same as G3 — defer until subagent output story stabilizes. |

---

## Rejected (with reason)

None. All 41 extracted items were either included, merged, or deferred.

---

## Where I Was Wrong

| Original Assumption | Reality | Who Caught It |
|---------------------|---------|--------------|
| 44% plan-paste rate is robust | Denominator is project-specific; aggregate is 35.7%. Claim may be correct for meta-only but wasn't stated that way. | GPT (P1) |
| `requires_approval` blocks execution | No code enforces it — `claim_task()` ignores the field entirely. Documentation-only. | GPT (P4) |
| Permission denials are handled | They're noted in summary text but status is still `done`. Silent failure. | GPT (P5) |
| Context materialization is implied by findings | It's a genuinely new *category* not in the plan. The plan focuses on headless execution; state pre-computation for interactive sessions is architecturally distinct. | Gemini (G6) |
| execute_plan saves tokens | Token savings are often zero or negative. Value is in scheduling and human time, not compute. | GPT (P12) |

---

## Gemini Errors (distrust)

| Claim | Assessment |
|-------|-----------|
| Temperature `-t 0.3` provides deterministic output | Gemini 3.1 Pro overrides to 1.0 (logged warning). Output was not actually low-temperature. Doesn't invalidate findings but note the lack of determinism. |
| Context Materialization "verification: >80% reduction in ls/cat discovery tool calls in first 10 turns" | Specific number (80%) is aspirational, not derived from baseline measurement. The direction is correct; the threshold needs baseline data. |
| "0 column-not-found DuckDB errors in the next 70 analyzed sessions" | Overly aggressive target. Some errors may come from novel tables not in the cached schema. 70% reduction (GPT's number) is more realistic initial target. |

---

## GPT Errors (distrust)

| Claim | Assessment |
|-------|-----------|
| Token savings estimates (150k-900k/week for pipeline_state) | GPT explicitly flagged this as high-variance (Section 6.1). "60 genomics sessions/week" is likely an overestimate. Directional ranking is more reliable than absolute numbers. |
| "2 days" observation window scaling to weekly by ×3.5 | Mar 1-2 was a weekend. If atypical (e.g., heavy exploration, no work sessions), scaling misleads. Need longer baseline. |
| Constitutional scoring (Principle 4 at 55%, Principle 8 at 80%) | Scoring rubric is explicit but hand-applied. The ordering (which principles are weakest) is more trustworthy than the exact percentages. |
| "0 invariant violations in 30 days" for approval gating | Correct target for a hard enforcement mechanism, but assumes the approval workflow is actually implemented. Currently it's not. |

---

## Revised Priority List

Incorporating both models' recommendations, verified findings, and constitutional alignment:

### Phase 0: Fix Plan Bugs (before any implementation)
1. **Resolve worktree contradiction** (P3) — pick one isolation strategy and update all plan sections
2. **Add `requires_approval` enforcement to `claim_task()`** (P4) — `AND (requires_approval=0 OR approved_at IS NOT NULL)`. Add `approved_at` column. Add `approve` CLI command.
3. **Fix permission denial status** (P5) — `status='done_with_denials'` or `status='failed'` when denials occur
4. **Fix timezone in daily cost cap** (P6) — `datetime('now','localtime')` for `finished_at` or compare both as UTC
5. **Add `agent` column to schema** (P7) — or validate+ignore in template expansion
6. **Expand `~` in `task["cwd"]`** (P7) — `cwd = os.path.expanduser(task["cwd"]) if task["cwd"] else ...`

### Phase 1: Core Architecture
7. **Add `engine` field** (G1, P20) — `engine TEXT DEFAULT 'claude'` in schema; script-engine runner for deterministic tasks
8. **Implement context materialization pipeline** (G6, G8, G11) — `morning-prep` template: scripts → STATE.md/TODAY.md per project
9. **Merge intel orchestrator** (G5, G10) — port generators, delete execution loop (verify schema compatibility first per G15)

### Phase 2: Hooks & Enforcement
10. **DuckDB PreToolUse hook** (G7) — intercept queries, auto-DESCRIBE, return via additionalContext
11. **Setup-volumes readiness probe** (G4) — deterministic check before queue processing, not per-task preamble
12. **Cross-project approval gate** (G12, P23) — hard rule: cross-project execute steps always `requires_approval=1`

### Phase 3: Observability & Measurement
13. **Add three falsifiable predictions** (P17-19) to success criteria — orientation commands, skills audit, earnings searches
14. **Silent failure invariant checker** (P15) — script to verify one start + one terminal event per task id
15. **Recurrence gate for session-retro** (P8) — only promote findings with 2+ session recurrence
16. **Baseline metrics for 14 days** before enabling execute steps — per existing plan, now with sharper denominators (P1, P2)

### Deferred
- Subagent output persistence (G3, G16) — monitor Claude Code behavior
- Transcript-vs-worktree tension (P24) — no solution today; monitor
- monthly_pruning, research_gap_sweep (P14) — implement after top-3 templates prove ROI

---

## Model Agreement Map

| Topic | Gemini | GPT | Agreement |
|-------|--------|-----|-----------|
| Deterministic tasks bypass LLM | G1 (strong) | P20 (strong) | **Full** |
| Context materialization as category | G6, G8, G11 (strong) | P11 (via ROI analysis) | **Full** |
| DuckDB PreToolUse hook | G7 (strong) | P10 (strong) | **Full** |
| Merge orchestrators | G5, G10 (strong) | — (not explicitly) | Gemini only |
| Approval gating must be in SQL | — (not explicitly) | P4, P21 (critical) | GPT only |
| Worktree contradiction | — | P3 (critical) | GPT only |
| ROI ranking | G13 (qualitative) | P11 (quantitative) | **Compatible** |
| Constitutional alignment | G: qualitative narrative | P: quantified 55-80% | **Compatible** |
| Session-retro churn risk | — | P8, P25 | GPT only |
| Script reliability blind spot | G14 (self-identified) | — | Gemini only |
