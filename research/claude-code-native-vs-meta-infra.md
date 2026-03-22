---
title: Claude Code Native Features vs Meta Infrastructure
date: 2026-03-21
---

# Claude Code Native Features vs Meta Infrastructure

> Assessment date: 2026-03-20. Based on actual documentation (code.claude.com), verified against v2.1.80.

## Summary

Claude Code is building primitives (hooks, subagents, memory) but meta's governance layer (what to enforce, when to promote, how to self-improve) has no native equivalent. Real consolidation opportunity is ~10-15%, mostly in memory mechanics and testing bundled skills against backlog items.

## 1. Agent Teams — NOT an orchestrator replacement

**Status:** Experimental, behind `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

Multiple Claude Code instances in one terminal sharing a task list and mailbox. One fixed lead + teammates. Each teammate = separate context window + full API cost.

**Known limitations (from docs):**
- No `/resume` with in-process teammates
- Task status can lag
- One team per session, no nested teams, lead fixed
- Split panes unsupported in VS Code, Windows Terminal, Ghostty

**Why not an orchestrator replacement:** Our orchestrator is cross-session, cross-project, cron-driven, SQLite task queue, fresh context per task. Agent teams are session-scoped — terminal closes, team gone.

**Possible use:** Within-session fan-out. `/batch` bundled skill more interesting — decomposes into 5-30 units, each in worktree, each opens PR.

## 2. Subagents — Mature, highest leverage

**Production-ready.** New since last audit:
- **Persistent memory** via `memory: user|project|local`. Per-subagent MEMORY.md across sessions.
- **Hooks in frontmatter** scoped to lifecycle. `Stop` auto-converts to `SubagentStop`.
- **Skills preloading** — full content injected at startup.
- **Worktree isolation** — `isolation: "worktree"`.
- **Transcripts** survive main compaction.
- **Resume** retains full history.

**Key gap:** Skills cannot have persistent memory. Only subagents get `memory` field. Refactor to subagent for cross-session learning.

## 3. Skills Platform — Mature, minor gaps

**New fields:**
- `model` — pin skill to specific model
- `hooks` — embed lifecycle hooks in frontmatter
- `argument-hint` — autocomplete hints

**Token budget:** 2% of context window (~16K chars) for all skill descriptions. Check `/context` for truncation.

**Bundled skills:**
- `/batch <instruction>` — parallel agents in worktrees, each opens PR
- `/simplify` — 3 parallel review agents (reuse, quality, efficiency)
- `/debug [description]` — session troubleshooting

## 4. Hook System — Significant new capabilities

**4 hook types now:**

| Type | What | Use for |
|------|------|---------|
| `command` | Shell script, JSON stdin | Deterministic checks (existing) |
| `http` | POST to URL | Remote validation services |
| `prompt` | Single-turn Haiku eval | Semantic checks too complex for bash |
| `agent` | Multi-turn with Read/Grep/Glob, 50 turns | Complex verification (the stop-hook-verifier from cockpit.md backlog) |

**`additionalContext`** on PreToolUse/PostToolUse — injects warning directly into Claude's context (better than stderr).

**`once: true`** — fires once per session then removed. Skills-only.

**Shell-only events (9/17):** SessionStart, SessionEnd, PreCompact, ConfigChange, Notification, SubagentStart, TeammateIdle, WorktreeCreate, WorktreeRemove.

## 5. Native Memory

Same storage path we use. Claude manages topic files, 200-line limit, auto-splitting. Machine-local, no git.

**Verdict:** Native handles mechanics. Our governance (recurs 2+, checkable predicate, evidence requirements) stays in CLAUDE.md. Complementary, not competing.

## 6. Native Observability

| Component | Custom | Native | Replace? |
|-----------|--------|--------|----------|
| Statusline | `statusline.sh` | Native JSON API | Already native. Script is customization. |
| Receipts | SessionEnd → JSONL | OTel (needs collector) | Keep JSONL. OTel overkill for single-user. |
| Dashboard | `dashboard.py` | `/stats`, `/insights` | Keep. `/stats` basic, `/insights` interesting but different. |
| Spinning detector | PostToolUse hook | None | Keep. |
| Idle notification | Stop hook | None | Keep. |

**OTel metrics available** (if we ever set up a collector): session count, lines changed, PR/commit count, cost by model, token usage, edit accept/reject, active time. Comprehensive but needs infrastructure.

## 7. Plugins

Bundle skills + agents + hooks + MCP + LSP. Distribution mechanism, not capability. Adds namespace overhead. Skip unless distributing to others.

## Concrete Actions

### High value, low effort
1. Test `/batch` for orchestrator-style parallel work
2. Test `/simplify` after feature implementation
3. Add `model` field to pinned skills
4. Try `additionalContext` in spinning-detector

### High value, moderate effort
5. Refactor researcher to custom subagent for persistent memory
6. Add prompt hooks for semantic checks (commit message quality)
7. Add hooks to skill frontmatter for per-skill validation

### Monitor / evaluate later
8. Agent teams — wait for stable
9. OTel — only if wanting Grafana
10. Plugins — only if distributing
11. `/insights` — test overlap with session-analyst

## What Meta Keeps (no native replacement)

- Cross-session orchestrator (cron-driven)
- Session-analyst pipeline
- Hook governance (promotion criteria, ROI telemetry)
- Cockpit receipts + dashboard
- Spinning detector, idle notification, custom stop hooks
- Cross-project propagation
- improvement-log → architectural fix pipeline

## GOALS.md Exit Condition Status

"Meta becomes unnecessary when Claude Code ships native equivalents" — not close. Primitives are building but governance layer is where meta's value lives.

---

*Sources: code.claude.com/docs/en/{skills, hooks, hooks-guide, sub-agents, agent-teams, memory, statusline, telemetry}. All fetched 2026-03-01.*

## Revisions

### 2026-03-20: v2.1.78–2.1.80 adoption sweep

**v2.1.78:** StopFailure event with matchers (billing_error, context_limit, etc.), effort/maxTurns/disallowedTools frontmatter for skills, line-by-line streaming, worktree skills/hooks fix (worktree agents now get full skill/hook access).

**v2.1.79:** `-p` subprocess hang fix (affects orchestrator — stalls no longer require manual kill), SessionEnd fires on `/resume` (receipts now capture resumed sessions).

**v2.1.80:** rate_limits in statusline JSON (five_hour + seven_day windows), effort frontmatter for skills (controls token budget), channels (research preview — webhook-style pub/sub, allowlisted plugins only, requires claude.ai OAuth), source:settings plugins, `--resume` parallel tool fix, 80MB memory reduction.

**Adopted:** StopFailure billing_error matcher with osascript alert + orchestrator gate. Rate limits extraction fixed (jq path was wrong — nested `five_hour.used_percentage`, not flat). Effort frontmatter propagated to 13/13 target skills. SessionEnd timeout env var (v2.1.74). Cron disable (v2.1.71).

**Deferred:** Channels (research preview, no persistent queue, requires OAuth — monitoring for webhook-receiver use case). worktree.sparsePaths (no SDK support). HTTP hooks (shell works). MCP elicitation.

Key finding: consolidation opportunity remains ~10-15% as assessed in original. Governance layer gap unchanged. New native features are useful but complementary, not replacing meta's orchestration or self-improvement loop.

<!-- knowledge-index
generated: 2026-03-22T00:15:42Z
hash: a06400c67a7f

title: Claude Code Native Features vs Meta Infrastructure

end-knowledge-index -->
