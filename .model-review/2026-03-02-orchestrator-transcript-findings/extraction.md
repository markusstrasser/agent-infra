# Extraction: Orchestrator Transcript Findings Review

**Date:** 2026-03-02
**Models:** Gemini 3.1 Pro, GPT-5.2
**Mode:** Review (convergent)

## Extraction: gemini-output.md

G1. [F2/F3 are deterministic scripts, should not go through claude -p / LLM task queue — use OS cron directly]
G2. [F1 pipeline_state injection must be project-scoped, not global — pollutes context for other projects]
G3. [F4 subagent outputs should NOT go to docs/research/ — use orchestrator-managed persistent dir instead]
G4. [F1 setup-volumes.sh as preamble is fragile — may hang on auth/sudo in headless mode. Use PreToolUse hook or separate readiness probe]
G5. [ARCHITECTURAL COLLISION: intel/tools/orchestrator.py vs meta/scripts/orchestrator.py — two parallel dispatch systems violate Principle 6]
G6. [Missing category: Context Materialization Tasks — pre-compute STATE.md files for interactive sessions, not just headless pipelines]
G7. [DuckDB hook should catch queries, auto-run DESCRIBE, return via additionalContext JSON pattern]
G8. [F1 better fix: write pipeline_state to MEMORY.md or STATE.md — solves tax for both orchestrated AND interactive sessions]
G9. [F2/F9: skills-drift should run via OS cron, trigger requires_approval=1 pipeline task if drift detected]
G10. [F6/F10: delete intel orchestrator execution loop, preserve generators, have them INSERT into meta's SQLite DB]
G11. [F8/F11: create morning-prep pipeline — step 1 runs scripts, step 2 uses sonnet to synthesize into TODAY.md]
G12. [F9 cross-project config propagation is constitutionally Hard Limit territory — must require approval]
G13. [Priority 1: merge orchestrators. Priority 2: context materialization. Priority 3: DuckDB PreToolUse hook]
G14. [Blind spot: assuming deterministic scripts are reliable — they may crash or need LLM parsing]
G15. [Blind spot: intel task generators may not map cleanly to meta's sequential SQLite schema]
G16. [Blind spot: pushing back on docs/research/ may lose valuable human observability of subagent reasoning]

## Extraction: gpt-output.md

P1. [Plan-paste rate: 25/70=35.7% but claim says 44% — denominators unstated, not verifiable from aggregate]
P2. [Supervision waste 5.9% is definition-sensitive — 24 low-signal actions / 385 messages = 6.2% already]
P3. [CRITICAL: worktree contradiction — "Drop --worktree" in decisions but "Execute steps use --worktree" in Risks #4]
P4. [CRITICAL: requires_approval not enforced in claim_task() SQL — documentation-only, violates Principle 1]
P5. [Permission denials recorded as status='done' — breaks "No silent failures" criterion #6]
P6. [Timezone bug: finished_at is UTC, daily cost check uses localtime — day-boundary leakage around midnight]
P7. [Template "agent" field not in schema; cwd tilde expansion bug in run_task()]
P8. [Session-retro writing to improvement-log may create churn without recurrence proof — "measure before enforcing" tension]
P9. [F4 not solved by claude -p — Claude Code internals still use tmp for subagents. Need enforcement, not scheduling]
P10. [F7 DuckDB fix requires PreToolUse hook, not just prompt injection — hookable cascading waste]
P11. [ROI analysis: pipeline_state, morning_brief, earnings_refresh are top 3 by token savings/effort ratio]
P12. [ROI analysis: execute_plan often token-neutral or negative — primary benefit is human scheduling, not token savings]
P13. [ROI analysis: supervision_audit, epistemic_metrics, model_review are investments, not savings — justify only if downstream reductions proven]
P14. [ROI analysis: monthly_pruning and research_gap_sweep weakly evidenced, may not pay back in 90 days]
P15. [Success criteria #6 "no silent failures" needs invariant checker: exactly one start + one terminal event per task id]
P16. [Success criteria #8 "autonomy metric" not falsifiable without defined classifier + error rate]
P17. [New prediction: orientation commands drop ≥60% after pipeline_state injection]
P18. [New prediction: ls -la .claude/skills/ drops ≥80% after skills_drift nightly]
P19. [New prediction: earnings searches drop ≥90% after earnings_refresh]
P20. [Recommendation: split orchestrator into script-engine + LLM-engine — scripts for deterministic tasks, claude for LLM tasks]
P21. [Recommendation: approval gating must be enforced in SQL (not prose) — add approved_at column]
P22. [Recommendation: fix timezone bug — store both UTC + local date]
P23. [Constitutional scoring: Principle 4 (self-mod by reversibility) at 55% — cross-project boundaries not enforced at scheduler level]
P24. [Constitutional tension: transcript preservation vs blast-radius containment — worktree kills transcripts, trunk increases risk]
P25. [Constitutional tension: nightly governance-writing (session-retro) may create churn without recurrence-gating]

## Disposition Table

| ID | Claim (short) | Disposition | Reason |
|----|--------------|-------------|--------|
| G1 | Deterministic tasks bypass LLM queue | INCLUDE | Both models agree (G1=P20). Pure scripts wasted through claude -p |
| G2 | Project-scoped context injection | INCLUDE | Obvious correctness issue — inject genomics state only for genomics tasks |
| G3 | Subagent outputs to orchestrator-managed dir, not docs/ | DEFER | Gemini raised valid point, but subagent race condition is Claude Code internal — fix depends on version behavior. Monitor. |
| G4 | setup-volumes.sh may hang headless | INCLUDE | Real risk — volumes may not be mounted. Use readiness probe, not blind preamble |
| G5 | Merge intel + meta orchestrators | INCLUDE | Critical architectural issue. Two dispatch systems = duplication + divergence |
| G6 | Context Materialization as task category | INCLUDE | Both models converge (G6=G8=G11=P11). Highest-ROI new finding. |
| G7 | DuckDB PreToolUse hook with DESCRIBE | INCLUDE | Both models agree (G7=P10). 11 errors, instructions don't prevent, hookable |
| G8 | Write state to persistent file (STATE.md/MEMORY.md) | MERGE WITH G6 | Same idea — context materialization |
| G9 | Skills drift via OS cron, not LLM | MERGE WITH G1 | Same principle — deterministic tasks don't need LLM |
| G10 | Port intel generators to meta's DB | MERGE WITH G5 | Part of orchestrator merge |
| G11 | Morning-prep pipeline | MERGE WITH G6 | Context materialization for intel |
| G12 | F9 config propagation is Hard Limit | INCLUDE | Constitutional compliance — already noted in findings, confirmed by both |
| G13 | Priority ordering: merge > context > DuckDB hook | INCLUDE | Good priority framework |
| G14 | Blind spot: script reliability assumed | INCLUDE | Valid caution — add health checks |
| G15 | Blind spot: intel schema compatibility | INCLUDE | Valid — verify before merging |
| G16 | Blind spot: subagent observability | DEFER | Tension between clean tmp and human audit trail. Revisit when subagent behavior is better understood. |
| P1 | Plan-paste rate denominators unstated | INCLUDE | Sloppy math — fix in success criteria |
| P2 | Supervision waste 5.9% is definition-sensitive | INCLUDE | Need auditable labeling rule |
| P3 | Worktree contradiction in plan | INCLUDE | Critical consistency bug — must resolve |
| P4 | Approval gating not enforced in SQL | INCLUDE | Critical — architecture over instructions |
| P5 | Permission denials as done = silent failure | INCLUDE | Need done_with_denials status or fail |
| P6 | Timezone bug in daily cost cap | INCLUDE | Correctness bug — trivial fix |
| P7 | Template agent field + cwd tilde expansion bugs | INCLUDE | Code bugs — fix in implementation |
| P8 | Session-retro churn risk | INCLUDE | Gate retro-generated changes on recurrence count |
| P9 | F4 not solved by claude -p alone | INCLUDE | Correct — subagent tmp cleanup is Claude Code internal |
| P10 | DuckDB needs PreToolUse hook | MERGE WITH G7 | Same finding |
| P11 | ROI: pipeline_state + morning_brief + earnings top 3 | INCLUDE | Quantitative prioritization |
| P12 | execute_plan often token-neutral | INCLUDE | Challenges our assumptions — primary value is scheduling, not tokens |
| P13 | Audit tasks are investments not savings | INCLUDE | Correct framing — measure downstream impact |
| P14 | monthly_pruning/research_gap weakly evidenced | INCLUDE | Be honest about ROI uncertainty |
| P15 | Silent failure invariant checker needed | INCLUDE | Concrete fix for success criterion #6 |
| P16 | Autonomy metric needs defined classifier | INCLUDE | Concrete fix for success criterion #8 |
| P17-19 | Three new falsifiable predictions | INCLUDE | Better than existing success criteria — add all three |
| P20 | Split into script-engine + LLM-engine | MERGE WITH G1 | Same recommendation |
| P21 | Approved_at column in SQL | MERGE WITH P4 | Part of approval enforcement |
| P22 | Timezone fix | MERGE WITH P6 | Same bug |
| P23 | Principle 4 at 55% — boundaries not enforced | INCLUDE | Add scheduler-level project isolation |
| P24 | Transcript vs blast-radius tension | INCLUDE | Unresolved — key architectural tension |
| P25 | Nightly governance churn risk | MERGE WITH P8 | Same concern |

## Coverage

- **Total extracted:** 41 items (16 Gemini + 25 GPT)
- **Included:** 27
- **Deferred:** 2 (G3, G16 — subagent output location)
- **Rejected:** 0
- **Merged:** 12 items into 6 parents
