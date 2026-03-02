# Cross-Model Review Synthesis: Orchestrator Plan

**Mode:** Review (convergent)
**Date:** 2026-03-01
**Models:** Gemini 3.1 Pro, GPT-5.2
**Constitutional anchoring:** Yes (CLAUDE.md Constitution section, GOALS.md)
**Extraction:** 38 items extracted, 19 included, 3 deferred, 0 rejected, 16 merged into 8 parents

## Verified Findings (adopt into plan)

| ID | Finding | Source | Verified How |
|----|---------|--------|-------------|
| G2/G10/P19 | **Drop auto_commit entirely.** Python wrapper should not touch git. Agent commits inside worktree per CLAUDE.md rules. | Both models | Constitutional check: irreversible state principle. Race condition with agent's own commits. |
| G7/G13 | **Use `--worktree` for execute steps.** Automated execution on trunk risks polluting main. Worktree creates a branch; human or CI reviews. | Both models | Native feature exists (`--worktree` flag). Gemini's #1 priority. |
| P7/P8/G8 | **Check returncode before marking done.** Current code marks done regardless of exit code. Empty stdout = success (wrong). | Both models | Code review: `json.loads(result.stdout)` with fallback `{}` — no returncode check anywhere. |
| G4/P4 | **Cascading failure + blocked state.** Failed task → downstream tasks stuck forever. Schema has 'blocked' but code never sets it. | Both models | SQL review: `pick_task` requires `status='done'` on dependency. No cascade logic. |
| P9/P18 | **Atomic task claiming.** Launchd 15min < timeout 30min = certain overlap. Need `BEGIN IMMEDIATE` + file lock. | GPT | Arithmetic: 15 < 30. No lock in code. |
| P1 | **15-turn cap violated.** Templates use 20-25 turns. Constitution says 15. | GPT | Direct text comparison. Easy fix. |
| G1/G15 | **Hook JSON goes to stdout, not stderr.** stop-research-gate prints to stderr + exit 2. Agent never sees the reason — just "blocked." | Gemini | Verified: spinning-detector already uses stdout JSON correctly. stop-research-gate uses stderr. |
| G6/G14 | **Verify `--no-session-persistence` doesn't kill transcripts.** If it does, session-analyst can't analyze orchestrated runs — breaks self-improvement loop. | Gemini | Can't test from inside session. Must verify empirically before deploying. |
| P2/P16 | **Verify `/model-review` works in `-p` mode.** If slash commands don't fire in batch mode, the cross-model review step is broken. | GPT | Can't test from inside session. Must verify empirically. |
| P5/P6 | **Template system unimplemented.** Pipelines table, variable substitution ({pipeline}, {topic}), pause_before — all described but no code. | GPT | Code review: runner has no template expansion, no pipeline CRUD. |
| P11/P13/P14 | **Success criteria need baselines + measurement.** "Plan-paste drop >50%" has no baseline. Realistic estimate: 13-20% reduction. Need regex definitions, baseline windows. | GPT | Quantitative analysis. 44% × 60% schedulable × 50% approval-needed ≈ 13-20%. |
| P12 | **Daily cost cap not enforced.** No rollup query, no stop-scheduling threshold. | GPT | Code review: cost_usd stored per task but never aggregated. |
| P21 | **Baseline instrumentation before deploy.** "Measure before enforcing" principle requires pre/post data. Add daily metrics.json. | GPT | Constitutional principle #3 check. |
| P10 | **Log/output directory creation missing.** mkdir -p needed. | GPT | Code review: LOG_PATH opened without ensuring parent dir exists. |
| G5 | **Soften the 30-min guillotine.** Use --max-turns + --max-budget-usd as primary limits. Keep subprocess timeout at 45min as last-resort safety net only. | Gemini | Valid: graceful limits > abrupt kill. |
| P3 | **Resolve hook fix contradiction.** Plan proposes specific changes while admitting root cause unverified. Rewrite: verify first, then propose. | GPT | Internal inconsistency in plan text. |
| G11 | **Retro skill: build as specified.** Both models agree. Clean replacement for clipboard snippet. | Both | No objection. |
| G12 | **Verification step: keep as specified.** Both models agree. Embodies cross-model review principle. | Both | No objection. |

## Deferred (needs empirical testing)

| ID | Finding | Test Required |
|----|---------|---------------|
| G16 | `--worktree` may hang in headless `-p` mode awaiting confirmation | Run `claude -p "..." --worktree test` from terminal outside session |
| P22 | `/model-review` slash commands may work in `-p` mode | Run `claude -p "Use /model-review on X" --max-turns 5` outside session |
| G6 | `--no-session-persistence` may still write transcripts | Run with flag, check `~/.claude/projects/` for new .jsonl |

**These three tests should be the FIRST thing done before implementing.** They determine whether key features of the plan are viable.

## Where I (Claude) Was Wrong in the Original Plan

| My Original Claim | Reality | Who Caught It |
|-------------------|---------|--------------|
| "echo JSON to stderr; exit 2" for hooks | Hooks communicate structured data via stdout. stderr goes to terminal, not agent. | Gemini (G1) |
| Auto-commit function safe for orchestrator | Constitutional violation — irreversible state. Race condition with agent commits. | Both (G2, P19) |
| 15-25 turns in templates | Constitution caps at 15. Direct violation. | GPT (P1) |
| Code handles failures correctly | Marks done regardless of returncode. Empty output = success. | Both (P7, G8) |
| Plan-paste sessions drop >50% | Realistic: 13-20% unless full template system + habit change. | GPT (P13) |
| Hook error paste-back fix is clear | Internal contradiction: proposed changes while admitting root cause unverified. | GPT (P3) |

## Gemini Errors (distrust)

| Claim | Assessment |
|-------|-----------|
| "Emit JSON to stdout then exit 0 (let Claude Code parse block instruction)" | Partially wrong. For blocking PreToolUse hooks, exit 2 IS the block signal. `additionalContext` on stdout is separate from the block mechanism. Exit 2 + stdout JSON with `additionalContext` is the correct pattern. |
| Worktree may break in headless mode | Possible but unverified. Not a reason to skip — just test it first. |

## GPT Errors (distrust)

| Claim | Assessment |
|-------|-----------|
| "15-turn cap violated by templates" — constitution says 15 | CORRECT. But "Session Architecture" section says 15, while the orchestrator section in GOALS.md is open-ended. The 15-turn limit was for orchestrated tasks specifically. Still, safer to respect the documented cap and increase only with evidence. |
| "Concurrency 10-30% for long tasks" | Plausible but specific percentage is fabricated. The real question: does launchd guarantee no overlap? (No — `StartInterval` doesn't prevent it.) |
| Constitutional coverage scores (40-80%) | These percentages are invented. Useful as relative ranking but don't trust absolute numbers. |

## Revised Plan Changes

Based on this review, the plan needs these amendments before implementation:

### Critical (must fix)
1. **Drop auto_commit function.** Execute steps use `--worktree`. Agent commits inside worktree per its CLAUDE.md rules. No Python git operations.
2. **Add returncode check.** `if result.returncode != 0: status = 'failed'`. Don't parse stdout if returncode is bad.
3. **Add cascading failure.** When task fails: `UPDATE tasks SET status='blocked' WHERE depends_on = ?`
4. **Add atomic claiming.** `BEGIN IMMEDIATE` transaction + filesystem lock (`/tmp/orchestrator.lock`).
5. **Fix templates to 15 turns max.** Respect constitutional cap.
6. **Wrap JSON parse in try/except.** Save raw stdout on parse failure. Mark failed, not done.
7. **mkdir -p for all output dirs.** Trivial but necessary.

### Important (fix before deploy)
8. **Run 3 empirical tests first.** Worktree in -p, slash commands in -p, transcript persistence with --no-session-persistence.
9. **Fix hook output pattern.** stop-research-gate: output JSON to stdout with `additionalContext`, keep exit 2 for blocking. Don't touch stderr approach until after verifying the problem.
10. **Implement pipeline template expansion.** Without it, the orchestrator is just "batch claude-p" — no chaining.
11. **Add daily cost rollup + threshold check.** `SELECT SUM(cost_usd) FROM tasks WHERE date(finished_at) = date('now')`.
12. **Temper success criteria.** "Measurable decline from baseline" not ">50%". Add regex definitions per GPT's suggestions.
13. **Add baseline instrumentation** (daily metrics.json) BEFORE deploying orchestrator.

### Nice-to-have (can defer)
14. Replace /model-review in pipeline prompts with explicit llmx calls (in case slash commands don't work in -p).
15. Add --fallback-model to runner for resilience.
16. Implement `blocked_reason`, `requires_approval` columns for richer approval UX.
