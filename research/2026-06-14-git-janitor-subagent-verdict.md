---
title: Custom subagents current state + git-janitor-subagent verdict
date: 2026-06-14
tags: [subagents, claude-code, git, worktree, context-shield, design-verdict]
status: active
---

# Custom subagents current state + git-janitor-subagent verdict

**Consult before:** proposing a "spin-off subagent to handle git/commits/hooks while the main
thread keeps going"; asking "are custom subagents deprecated / bad practice now"; designing any
concurrent-write-to-same-checkout agent pattern.

**Question:** Are Claude Code custom subagents (scoped contexts/tools) still best practice or now
discouraged? And is a dedicated git/commit/hooks "janitor" subagent that the main high-reasoning
thread spins off (to keep going) a sound pattern?

## Verdict (two parts)

1. **Custom subagents: ALIVE, supported, recommended.** Not deprecated. Scoped tools + scoped
   system prompt + per-agent memory + worktree isolation are all current, growing features.
2. **Git-janitor subagent: the *concurrent fire-and-forget* version is unsound; a *synchronous
   context-shield commit* subagent (cheap model, staging-only, escalate-on-feisty) is defensible —
   but verify the friction is real first, because the cheaper fix is auto-fixing hooks, not a babysitter.**

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Custom subagents are a current, supported, documented feature (not deprecated) | This session runs with 8 custom defs on disk + official docs + June-2026 playbooks | HIGH | code.claude.com/docs/en/sub-agents; verify_claim 0.9 | VERIFIED |
| 2 | Subagents are *gaining* surface, not losing it | SubagentStart/Stop hooks (v2.1.141), agent_id lineage (v2.1.134), dynamic workflows orchestrating 100s of bg agents (v2.1.154) | HIGH | research/2026-06-07-claude-code-codex-feature-delta.md | VERIFIED |
| 3 | A normal Task subagent BLOCKS the parent until it returns — "spin off and keep going" is false by default | Agent tool: only `run_in_background:true` (or Workflow bg agents) is truly concurrent | HIGH | Agent tool contract | VERIFIED |
| 4 | Concurrent commits on ONE checkout race the git index lock + clobber shared `.claude/` state | This is the repo's #1 multi-agent recurrence (13+ sessions, all 5 repos) | HIGH | research/2026-06-13-multiagent-state-coordination-prior-art.md | VERIFIED |
| 5 | The whole funded field converged on: isolate per agent (worktree) + merge via git; worktree beats soft isolation 7.8pp | CAID arXiv:2603.21489; Symphony; Anthropic's own multi-agent system | HIGH | same memo | VERIFIED |
| 6 | The repo already has ~10 git/commit hooks (the architecture-first answer to git friction) | commit-check-parse.py, pre-commit-guards.sh, prepare-commit-msg-session-id.sh, precommit-plan-completion-guard.sh, … | HIGH | `ls ~/Projects/skills/hooks/` | VERIFIED |

## Why the concurrent git-janitor fails

- **The "keep going" premise is mostly false.** Task subagents block the parent. To actually run
  concurrently you need `run_in_background`. But for *git specifically* that's the dangerous case:
- **Git is shared mutable state.** A background janitor committing while the main thread keeps
  editing the same checkout races the `.git/index.lock` and clobbers `current-session-id`/checkpoint
  — exactly the failure the repo just spent a research cycle converging on (claim 4/5).
- **Worktree isolation "solves" the race by relocating it.** A janitor in its own worktree commits
  to a *different* branch — now someone has to merge. The merge is the feisty part the user already
  flagged as needing higher reasoning. You can't isolate your way out of "the conflict needs Opus."
- **The feisty half can't be delegated to a cheap model anyway.** Rebase / conflict / revert /
  force-push / "did this regress something" IS the reasoning work. Delegating routine commits to a
  cheap model is fine; delegating the part that's actually hard defeats the purpose.

## The defensible version (if friction is real)

A **synchronous, context-shielding commit subagent**, not a concurrent janitor:
- **Synchronous** (parent waits): committing is a barrier anyway — the parent isn't doing other
  work mid-commit, so no race. The win isn't concurrency, it's **context-shielding**: the
  failed-commit → hook-error → retry transcript churn never enters the main Opus context.
- **Cheap model** (`opus-low` / `fable-low`): routine commits = "fully-briefed gated execution",
  which is exactly those lanes' measured sweet spot (0.34–0.65× tokens at equal quality).
- **Scoped HARD**: stage *named* paths, write a conventional message, satisfy hooks, report back.
  No `git add -A`, no rebase, no conflict resolution, no force-push, no revert.
- **Escalate-on-feisty**: if it hits a conflict / non-fast-forward / anything ambiguous, it returns
  "escalate" and the high-reasoning parent takes over. This is the user's own caveat, encoded.

## But measure first — the architecture-first counter (constitution P1/P11)

If Opus "keeps getting caught up in stupid git issues + hooks," the **first-order fix is the hooks,
not a babysitter for them.** A subagent that fixes recurring hook *rejections* is treating the
symptom. Options, in order of leverage:
1. **Make rejecting hooks auto-fix instead.** A `commit-msg`/`prepare-commit-msg` hook that
   *reformats* a bad message beats one that rejects and forces a retry loop. Same for staging.
2. **Then** (if friction survives) the synchronous context-shield commit subagent above.
3. A concurrent janitor is the *last* thing to reach for, and only worktree-isolated for genuine
   parallel multi-task fan-out — not for serial interactive commits.

**The /observe angle the user raised is correct:** git/commit/hook-retry churn IS wasted
supervision and `supervision-audit` / `/observe supervision` *should* surface it. Worth one audit
pass to confirm it's a real recurrence (constitution: 2+ sessions) before building anything.

## Update 2026-06-14 — empirics gathered + Anthropic checked (friction CONFIRMED)

**Anthropic ships no commit-hygiene janitor** (claude-code-guide check + today's marketplace audit).
They bet on **worktree isolation**; the commit gap is acknowledged in their tracker:
- #4834 — no deterministic `PreCommit`/`PostCommit` hook types (open FR)
- #40117 — agents bypass hooks via `--no-verify`/stash/quiet
- **#46808 — hooks silently DON'T fire inside worktrees** → rules OUT a worktree-isolated janitor (it would lose our guardrails)
- #56865 — web auto-commit overrides CLAUDE.md

**Empirics (agentlogs, last 21d, all repos) — clears the 2+ session bar ~40×:**
| class | calls | errors | err-sessions |
|---|---|---|---|
| commit | 4279 | 251 | **84** |
| stash | 138 | 67 | 35 |
| add/stage | 312 | 24 | 18 |
| reset | 103 | 13 | 10 |
| `--no-verify` (BYPASS) | 30 | 3 | **14 sessions use it** |

Single-session commit-retry thrash: agent-infra **25 calls / 22 failed**, genomics 65/21, 63/14 — the
concrete "Opus stuck on stupid git issues" pathology.

**Hook-layer truth (changed the design — supersedes the "auto-fix message hook" lean above):**
native `pre-commit` = `pre-commit-guards.sh` → no-large-binaries + validate-changed-hooks +
protected-paths (exit 1 = block; these SHOULD block — auto-fixing = antipattern). NO `commit-msg`
format rejecter; `commit-check-parse` is advisory; `prepare-commit-msg` only appends Session-ID.
∴ friction is **staging-confusion + legit-block-then-`--no-verify`-bypass**, NOT message format.

**Updated design — two SEPARABLE pieces (don't bundle):**
- **A. Close the `--no-verify` hole** — `PreToolUse Bash(git commit*)` hook blocks `--no-verify`,
  tells agent to escalate not bypass. Fixes the confirmed 14-session governance violation. Shared
  infra → pilot agent-infra-local, propose-before-global.
- **B. Synchronous context-shield commit subagent** — model `opus-low` + parent verifies
  `git show --stat` post-commit (low effort skips self-checking; risky for a git *writer*). Tools:
  `Bash`(git)/`Read`/`Grep`, NO Edit/Write. Job: stage named paths → conventional msg → satisfy
  hooks → report SHA. HARD-REFUSE→escalate: conflict / non-ff / rebase / revert / stash-pop /
  any guard block / "did this regress". Win = retry churn never enters Opus context. NOT concurrent
  (index race + #46808), NOT worktree-isolated.

## Still pending (the build gate)
- **Routine-vs-feisty ratio of the 251 commit errors** — being classified by the supervision-audit
  agent (`research/2026-06-14-supervision-audit-git-friction.md`). If mostly staging-confusion →
  subagent B has clear value; if mostly legit protected-path blocks → those should block, B helps
  less and piece A matters more. Build decision waits on this.
- **Deploy scope** (pilot-local vs global) + whether to ship piece A — user's call.
