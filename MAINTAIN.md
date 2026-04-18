# SWE Quality — agent-infra
## Last tick: 2026-04-17

## Findings
<!-- Format: - **M001** [new] [CATEGORY] description (source, YYYY-MM-DD) -->
- **M001** [new] [SUBAGENT] Worktree CWD escape — subagent bash calls don't chain `cd $WORKTREE_PATH` and execute against main repo (source: observe genomics 54b4a4fe, 2026-04-17)
- **M002** [new] [CONTRACT] Stages pass QC while producing 0-byte declared outputs — qc_checks not auto-bound to outputs declaration (source: observe genomics 54b4a4fe+b9e6a5b1, 2026-04-17)
- **M003** [new] [SUBAGENT] Cherry-pick subagent silently dropped test files from merge commit (source: observe phenome 9ab45210, 2026-04-17)

## Queue
<!-- Items awaiting Opus subagent dispatch or manual fix. WIP cap: 3 -->
- (empty)

## Fixed
<!-- Format: - **M001** [fixed] description (commit, YYYY-MM-DD) -->
- (none yet)

## Deferred
<!-- Items with revisit dates -->
- (none)

## Open Steward Proposals (10)
Status of `~/.claude/steward-proposals/` after 2026-04-17 archive sweep (4 implemented moved to `implemented/`):

| Proposal | Scope | Blocking on |
|---|---|---|
| brainstorm-dedup-precheck | meta skill | review |
| codex-agents-md-no-verify-mirror | genomics AGENTS.md | human approval (cross-repo) |
| destructive-git-ref-hook | shared hook (3+ projects) | human approval (shared infra) |
| genomics-precommit-repair | genomics | human approval (cross-repo) |
| hook-state-stateless-revalidation | shared hooks | human approval (shared infra) |
| llmx-f-polling-loop | meta script | review |
| observe-technical-findings-mode | observe skill | review |
| ownership-guard-circuit-breaker | shared hook | human approval (shared infra) |
| plan-completion-guard-precommit | shared hook + cross-repo plan format | human approval |
| truth-seam-lint-genomics | genomics lint | human approval (cross-repo) |

5/10 require shared-infra/cross-repo approval. 3/10 are meta-scope and could be implemented under autonomy rules but warrant review pass first (touch skills/hooks/MCP behavior).

## Strategic Notes
### 2026-04-17
- Findings/proposals pipeline is healthy on the *intake* side (28 [ ] proposed entries in improvement-log this month) but anemic on the *implementation* side. Most proposals correctly route to "needs human approval" per autonomy rules — that's working as designed, not broken.
- Two HIGH-severity NEW findings landed today (worktree CWD escape, contract bug QC blindness). Both have natural architectural fixes (env-pinned subagent CWD, qc_checks ⊇ outputs lint). Worth bundling into a single shared-infra approval ask.
- Subagent reliability theme: 2 of 3 new findings are subagent-related (CWD escape, silent file drop). Subagent contract enforcement may deserve its own focus area.

## Drift Alerts
- (none flagged this tick)
