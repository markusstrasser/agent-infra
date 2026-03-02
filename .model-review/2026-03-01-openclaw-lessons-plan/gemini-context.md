# CONTEXT: Cross-Model Review of OpenClaw Lessons Implementation Plan

# PROJECT CONSTITUTION
Review against these principles, not your own priors.

## Constitution (from CLAUDE.md)

> **Human-protected.** Agent may propose changes but must not modify without explicit approval.

### Generative Principle

> Maximize the rate at which agents become more autonomous, measured by declining supervision.

Autonomy is the primary objective. In code, you can always run things — if they don't run successfully, they produce errors, and errors get corrected. With good verification, common sense, and cross-checking, autonomy leads to more than caution does. Grow > de-grow. Build the guardrails because they're cheap, not because they're the goal.

Error correction per session is the secondary constraint: autonomy only increases if errors are actually being caught. If supervision drops but errors go undetected, the system is drifting, not improving.

### Principles

1. Architecture over instructions. Instructions alone = 0% reliable (EoG). If it matters, enforce with hooks/tests/scaffolding. Text is a prototype; architecture is the product.
2. Enforce by category: cascading waste (hooks/block), irreversible state (hooks/block), epistemic discipline (advisory), style (instructions).
3. Measure before enforcing. Log every hook trigger to measure false positives.
4. Self-modification by reversibility + blast radius.
5. Research is first-class. Divergent → convergent → eat your own dogfood → analyze.
6. Skills governance. Meta owns skill quality.
7. Fail open, carve out exceptions.
8. Recurring patterns become architecture (10+ times → hook, skill, or scaffolding).
9. Cross-model review for non-trivial decisions.
10. The git log is the learning.

### Self-Improvement Governance
A finding becomes a rule or fix only if: (1) recurs 2+ sessions, (2) not covered by existing rule, (3) is a checkable predicate OR architectural change. Reject everything else.

# PROJECT GOALS

**Mission:** Maximize autonomous agent capability across all projects while maintaining epistemic integrity. The system should learn things once and handle them forever.

**Generative Principle:** Maximize the rate at which agents become more autonomous, measured by declining supervision — AND maximize error correction per session across all projects.

**Primary Success Metric:** Ratio of autonomous-to-supervised work across sub-projects. No reverted work, no 5-hour runs that should be 1-hour, no error spirals, no agent theater, no repeated corrections.

**Wasted supervision rate:** Currently 5.9% (down from 21%).

**Strategy:**
1. Session forensics
2. Hook engineering
3. Observability
4. Research
5. Cross-project propagation
6. Self-improvement

**Orchestrator:** UNBLOCKED. Build for tasks that are clearly automatable now.

---

# CURRENT SYSTEM STATE

## Cross-Project Infrastructure

**4 projects:** intel (investment research), selve (personal knowledge), genomics (WGS pipeline), meta (agent infrastructure)
**13 deployed hooks** across global + per-project settings
**16+ skills** shared via symlinks from ~/Projects/skills/
**MEMORY.md** for cross-session persistence (auto-memory at ~/.claude/projects/)
**Session-analyst pipeline** for self-improvement (session-analyst → improvement-log → architectural fixes)

## Deployed Hooks
- Global: bash-loop-guard, session-init, precompact-log, sessionend-log, commit-check, search-burst, spinning-detector, userprompt-context-warn, bare-python-guard
- Intel: data-guard, secrets-guard, source-check, stop-research-gate, failure-loop
- Genomics: (minimal)
- Selve: prompt Stop hook for research quality

## Claude Code Constraints (verified 2026-03-01)
- PreCompact hook: NO decision control, side-effect only
- 17 hook events, 4 hook types (command, http, prompt, agent)
- Native memory: auto-manages topic files, 200-line limit. Complementary.
- Agent Teams: experimental, session-scoped only
- No native heartbeat, no native cron, no native skills gating
- Subagent persistent memory available (memory: user|project|local)

## Existing Orchestrator Spec (from maintenance-checklist.md)
```
Every 15 minutes (cron):
  1. Query SQLite task queue
  2. Pick highest-priority task
  3. Run: claude -p "task prompt" --max-turns 15 --output-format json
  4. Kill if stuck (subprocess timeout 30min)
  5. Log result, pick next task
```
~100 lines Python. Fresh context per task (NOT --resume). Already validated by prior model review.

---

# OPENCLAW RESEARCH (from research/openclaw-deep-dive.md)

## Memory System — Three Layers
- Layer 1: MEMORY.md + memory/YYYY-MM-DD.md (daily append-only logs)
- Layer 2: Vector search (SQLite + embeddings, provider cascade)
- Layer 3: Hybrid BM25 + Vector (0.7/0.3 weighting), temporal decay (30d half-life), MMR re-ranking

## Pre-Compaction Memory Flush
- Silent agentic turn before context eviction
- Trigger: totalTokens >= contextWindow - 20K - 4K
- Model writes to memory/YYYY-MM-DD.md, replies NO_REPLY (suppressed)
- Wait-for-idle guard prevents collision with active tool calls
- One flush per compaction cycle

## Heartbeat System
- Periodic autonomous turns (30min default)
- Reads HEARTBEAT.md checklist — if empty, skips API call
- HEARTBEAT_OK response → transcript pruned (truncated back to pre-heartbeat size)
- Duplicate detection: same alert within 24h suppressed
- Queue check: skip if main queue busy

## Lane-Aware Command Queue
- 4 lanes: Main (max 4), Cron, Subagent (max 8), Nested
- Per-session serial (1 concurrent per session)
- Message coalescing: collect (default), steer, followup, steer-backlog

## Skills Gating
- Load-time filtering: check bins/env/config/OS before injecting into prompt
- Skills not meeting requirements never enter the prompt
- Token impact: 195 chars base + ~97 chars per skill

## Philosophy
- Agent-as-person (SOUL.md self-modifiable) vs our agent-as-tool (CLAUDE.md human-owned)
- Pi minimal core (4 tools) + everything else is extensions
- "Agent extends itself" philosophy

---

# THE IMPLEMENTATION PLAN UNDER REVIEW

## Phase 1: Daily Memory Logs (30 min)
Add memory/YYYY-MM-DD.md append-only pattern. Agent appends raw notes, curate to MEMORY.md weekly. Read today+yesterday on session start.

## Phase 2: Pre-Compaction Context Save (1 hour)
Option A (preferred): UserPromptSubmit prompt hook — inject save reminder when context high.
Option B: Strengthen CLAUDE.md instruction (acknowledged as 0% reliable per constitution).
Option C (rejected): PostToolUse prompt hook on Write/Edit — too noisy.
Claude Code constraint: PreCompact has no decision control. Cannot inject agentic turns.

## Phase 3: Skills Gating (30 min)
Audit and remove unnecessary skill symlinks per project. Deterministic (remove symlinks) over instructional (tell agent to self-filter).

## Phase 4: Orchestrator MVP with Lane Model (4 hours)
Build scripts/orchestrator.py. Lanes: main (1), research (2), maintenance (1). Fresh claude -p per task, 15 turns max, JSONL log, announce pattern (result → daily summary file).

## Phase 5: Doctor Script (1 hour)
Unified diagnostic: check hook syntax, settings.json validity, skill frontmatter, MCP connectivity, memory health, git state, symlink integrity.

## Priority Order
1. Daily logs (lowest effort, unblocks Phase 2)
2. Skills gating (quick win)
3. Pre-compaction save (experimental)
4. Doctor (useful, not urgent)
5. Orchestrator (most ambitious)

## Skipped
Vector search (scale <5KB), temporal decay, multi-channel, agent-as-person philosophy, queue coalescing, OpenClaw hook system (Claude Code strictly superior), ZeroClaw Rust rewrite, ClawHub registry.

---

# KEY QUESTIONS

1. Is UserPromptSubmit prompt hook for pre-compaction save worth the latency? Every user message gets a Haiku eval (~1s). Or accept instruction-only?
2. Heartbeat (persistent session, context accumulates) vs cron (fresh context per task, our current spec)? OpenClaw has both.
3. Daily logs worth added complexity vs relying on native auto-memory?
4. What patterns from agent infrastructure research are we missing?
5. Anything fighting Claude Code native feature evolution?
