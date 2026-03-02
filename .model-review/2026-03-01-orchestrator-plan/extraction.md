# Extraction & Disposition: Orchestrator Plan Review

**Date:** 2026-03-01
**Models:** Gemini 3.1 Pro, GPT-5.2
**Mode:** Review (convergent)

## Extraction: gemini-output.md

G1. [Hook JSON output goes to stdout, not stderr — current plan echoes to stderr which won't be parsed]
G2. [Auto-commit with `git add -A` violates irreversible state principle — blindly commits everything]
G3. [Auto-commit creates race condition with execute step's own commit instruction]
G4. [Zombie tasks — if step 1 fails, step 2+ stay pending forever, no cascading failure]
G5. [30-min subprocess.timeout is a guillotine — risks corrupting git state, lockfiles, SQLite]
G6. [`--no-session-persistence` may suppress transcript generation — breaks session-analyst feedback loop]
G7. [Missing worktree isolation for execute steps — automated execution on trunk is risky]
G8. [JSON parse errors on stdout will crash runner without updating DB — task stuck in 'running']
G9. [Upgrade core loop: wrap JSON parsing in try/except, regex fallback for cost, cascade failures]
G10. [Drop auto_commit function — rely on agent's own CLAUDE.md commit rules inside worktree]
G11. [Retro skill: agreed, clean replacement for clipboard snippet]
G12. [Verification step: agreed, embodies principle 9 (cross-model review)]
G13. [Prioritize worktree execution over auto-commit as #1 change]
G14. [Transcript persistence guarantee needed — ensure orchestrated tasks are visible to session-analyst]
G15. [stdout JSON for Stop hooks (not stderr) — correct implementation of additionalContext]
G16. [Self-doubt: --no-session-persistence may still write transcripts; worktree --worktree may hang in headless mode awaiting confirmation]

## Extraction: gpt-output.md

P1. [15-turn constitutional cap violated by templates — explore:20, review:25, retro:20, sweep:25]
P2. [/model-review slash command likely non-functional in claude -p batch mode]
P3. [Error paste-back fix has internal contradiction — proposes changes while admitting root cause unverified]
P4. [Schema supports 'blocked' status but code never sets it — pause_before/approval gate broken]
P5. [Pipelines table designed but no CRUD/scheduling/template-expansion code exists]
P6. [Template variables ({pipeline}, pause_before, agent, topic) not implemented in runner]
P7. [Marks task done regardless of returncode — false positives cause downstream execution on failed output]
P8. [Empty stdout treated as success with {} — should be failure]
P9. [Concurrency risk — launchd 15min interval + 30min timeout = overlap; no atomic claim or lock]
P10. [Log path directory creation missing — open("a") fails if dir doesn't exist]
P11. [Plan-paste reduction has no measurement definition or baseline]
P12. [Daily cost cap cannot be enforced — no rollup, no stop-scheduling logic, no timezone]
P13. [44% plan-paste → realistic 13-20% net session reduction, not >50%, unless pipeline templating + habit change]
P14. [Make all 6 success criteria falsifiable with regex definitions and baseline windows]
P15. [Constitutional coverage scored: architecture 80%, enforce-by-category 55%, measure-before-enforcing 40%, reversibility 60%, research 70%, skills 65%, fail-open 50%, recurring→arch 75%, cross-model 30%, git-log 45%]
P16. [Cross-model review in batch mode scored 30% — mechanism likely non-functional]
P17. [Top rec 1: semantic completion — require JSON schema + returncode check for 'done']
P18. [Top rec 2: atomic claim + filesystem lock to eliminate duplicate execution]
P19. [Top rec 3: constrain auto-commit — scoped diffs, governance guards, task_id in message]
P20. [Top rec 4: implement blocked/paused as first-class states with human approval CLI]
P21. [Top rec 5: daily metrics.json baseline + post-deploy instrumentation]
P22. [Self-doubt: /model-review may work in -p mode; --output-format json may be reliable; auto-commit may be safe in narrow scopes]

## Disposition Table

| ID | Claim (short) | Disposition | Reason |
|----|--------------|-------------|--------|
| G1 | Hook JSON → stdout not stderr | INCLUDE | Verified: Claude Code hook docs specify stdout for structured output. Critical bug in plan. |
| G2 | Auto-commit git add -A dangerous | INCLUDE | Both models flagged. Constitutional violation (irreversible state). |
| G3 | Auto-commit race with agent commit | MERGE WITH G2 | Same root issue — drop auto_commit. |
| G4 | Zombie tasks, no cascading failure | INCLUDE | Verified: SQL logic has no path from failed → block downstream. Both models flagged (G4+P7). |
| G5 | 30-min timeout is a guillotine | INCLUDE | Valid concern. Use --max-turns + --max-budget-usd as primary limits. Keep timeout as last resort but increase to 45min. |
| G6 | --no-session-persistence breaks transcripts | INCLUDE | Must verify empirically. If true, drop the flag. Critical for self-improvement loop. |
| G7 | Missing worktree for execute steps | INCLUDE | Both models flagged. Use --worktree for execute steps. Gemini's #1 priority. |
| G8 | JSON parse crash leaves task stuck | INCLUDE | Both flagged (G8+P8). Wrap in try/except. |
| G9 | Upgrade core loop error handling | MERGE WITH G8 | Implementation detail of G8+G4. |
| G10 | Drop auto_commit, use agent commit | INCLUDE | Both models agree. Agent commits in worktree, not Python wrapper. |
| G11 | Retro skill agreed | INCLUDE | No disagreement. Build it. |
| G12 | Verification step agreed | INCLUDE | No disagreement. Keep in pipeline. |
| G13 | Prioritize worktree > auto-commit | MERGE WITH G7 | Priority ordering, not separate item. |
| G14 | Transcript persistence guarantee | MERGE WITH G6 | Same concern. |
| G15 | Hook stdout not stderr | MERGE WITH G1 | Same issue. |
| G16 | Self-doubt: worktree may hang | DEFER | Needs empirical test. Low-cost to verify. |
| P1 | 15-turn cap violated by templates | INCLUDE | Direct constitutional violation. Fix templates to 15. |
| P2 | /model-review may not work in -p mode | INCLUDE | High risk. Need to verify. If broken, replace with explicit llmx calls in prompt. |
| P3 | Error paste-back contradiction | INCLUDE | Plan should resolve the "verify first" before proposing changes. Rewrite section. |
| P4 | 'blocked' status never set in code | INCLUDE | Both models. Must implement blocked state + approval gate. |
| P5 | Pipelines table unused | INCLUDE | Code needs CRUD for pipelines. Phase 2 scope. |
| P6 | Template variables not implemented | INCLUDE | Pipeline prompts use {pipeline}, {topic} — need string substitution in runner. |
| P7 | Done regardless of returncode | INCLUDE | Critical bug. Both models. Check returncode before marking done. |
| P8 | Empty stdout = success | MERGE WITH P7 | Same root issue — completion validation. |
| P9 | Concurrency / double-run risk | INCLUDE | Launchd 15min < timeout 30min. Need atomic claim or filesystem lock. |
| P10 | Log dir creation missing | INCLUDE | Trivial to fix. Add mkdir -p. |
| P11 | No measurement baseline for plan-paste | INCLUDE | Add baseline instrumentation before deploy. |
| P12 | Daily cost cap not enforced | INCLUDE | Add rollup query + stop-scheduling threshold. |
| P13 | 44% → realistic 13-20% reduction | INCLUDE | Temper success criterion from ">50%" to "measurable decline from baseline". |
| P14 | Make success criteria falsifiable | INCLUDE | Adopt GPT's regex definitions + baseline windows. |
| P15 | Constitutional coverage scores | DEFER | Informational, no direct action. Good diagnostic. |
| P16 | Cross-model review batch = 30% | MERGE WITH P2 | Same concern about /model-review in -p mode. |
| P17 | Semantic completion (schema+returncode) | MERGE WITH P7 | Implementation detail. |
| P18 | Atomic claim + lock | MERGE WITH P9 | Implementation detail. |
| P19 | Constrain auto-commit | MERGE WITH G2/G10 | Both models agree: drop or heavily constrain. |
| P20 | Blocked/paused as first-class states | MERGE WITH P4 | Same item. |
| P21 | Daily metrics.json baseline | INCLUDE | Aligns with "measure before enforcing" principle. |
| P22 | Self-doubt: slash commands may work in -p | DEFER | Needs empirical test. |

## Coverage Summary

- **Total extracted:** 38 items (16 Gemini + 22 GPT)
- **After dedup/merge:** 22 unique items
- **INCLUDE:** 19
- **DEFER:** 3 (empirical tests needed: G16 worktree headless, P15 scores, P22 slash in -p)
- **REJECT:** 0
- **MERGE:** 16 items merged into 8 parent items

## Key Themes (both models converge)

1. **Drop auto_commit or heavily constrain it** (G2, G3, G10, P19) — both models, constitutional violation
2. **Runner has critical bugs** (P7, P8, G8) — marks done on failure, crashes on bad JSON
3. **Use worktree for execution** (G7, G13) — Gemini's #1 priority
4. **Concurrency protection** (P9, P18) — launchd overlap is near-certain
5. **15-turn cap violated** (P1) — direct constitutional breach, easy fix
6. **Slash commands in -p mode unverified** (P2, P16) — /model-review may be broken
7. **Template system unimplemented** (P5, P6) — the plan describes features the code doesn't have
8. **Cascade failures** (G4) — zombie tasks will clog the DB
9. **Transcript persistence** (G6) — self-improvement loop at risk
