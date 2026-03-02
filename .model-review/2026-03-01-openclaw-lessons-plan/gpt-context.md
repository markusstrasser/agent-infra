# CONTEXT: Cross-Model Review of OpenClaw Lessons Implementation Plan

# PROJECT CONSTITUTION
Quantify alignment gaps. For each principle, assess: coverage (0-100%), consistency, testable violations.

## Core Principles
1. Architecture over instructions — instructions alone = 0% reliable
2. Measure before enforcing — log triggers for false-positive data
3. Self-modification by reversibility + blast radius
4. Recurring patterns (10+ occurrences) → architecture
5. Cross-model review for non-trivial decisions
6. Fail open, carve out exceptions

## Generative Principle
Maximize autonomy rate (declining supervision) AND error correction per session.

# PROJECT GOALS
Quantify alignment. Which goals are measurably served? Which neglected?

**Primary metric:** Ratio autonomous-to-supervised work. Currently 94.1% autonomous (5.9% wasted supervision, down from 21%).
**Strategy:** Session forensics → hook engineering → observability → research → cross-project propagation → self-improvement.
**Orchestrator:** UNBLOCKED. ~100 lines Python, cron + SQLite + subprocess, fresh context per task.

---

# PLAN UNDER REVIEW (5 phases)

## Phase 1: Daily Memory Logs (30 min, low risk)
Add append-only memory/YYYY-MM-DD.md alongside curated MEMORY.md.
Rationale: Decompose "decide what to remember" into cheap-write + batched-curate. Reduces context collapse from frequent MEMORY.md rewrites.
Validation: After 5 sessions, check daily log usage and MEMORY.md churn reduction.

## Phase 2: Pre-Compaction Context Save (1 hour, medium risk)
**Constraint:** Claude Code PreCompact hook has NO decision control. Cannot inject agentic turns like OpenClaw does.
**Option A:** UserPromptSubmit prompt hook — fires on every user message, Haiku eval (~1s latency), injects save reminder when context is high.
**Option B:** CLAUDE.md instruction only (0% reliable per constitution).
**Option C:** PostToolUse prompt hook — rejected as too noisy.
**Key question:** Is 1s latency per message worth ~30% improvement in context preservation?

## Phase 3: Skills Gating (30 min, low risk)
Remove unnecessary skill symlinks per project. 16+ skills currently loaded everywhere.
Expected token savings: ~30% of skills budget.

## Phase 4: Orchestrator MVP (4 hours, medium risk)
Lane model from OpenClaw: main (max 1), research (max 2), maintenance (max 1).
Fresh claude -p per task. 15 turns max. Subprocess timeout 30min.
Task types: research sweep, entity refresh, self-improvement pass.
Result → daily summary file (announce pattern).

## Phase 5: Doctor Script (1 hour, low risk)
Unified diagnostic: hooks, settings, skills, MCP, memory, git, symlinks.
Read-only, no mutations.

## Priority: 1→3→2→5→4

---

# OPENCLAW REFERENCE ARCHITECTURE

**Pre-compaction flush:** Silent agentic turn (model writes memory, replies NO_REPLY). Trigger: tokens > contextWindow - 24K. One per compaction cycle.

**Heartbeat:** Periodic turns (30min). Empty HEARTBEAT.md = skip API call. HEARTBEAT_OK = prune transcript. 24h duplicate suppression.

**Lanes:** 4 lanes (main/cron/subagent/nested), per-session serial (1 concurrent), global concurrent (main=4, subagent=8).

**Memory:** 3 layers — Markdown files (MEMORY.md + daily logs) → vector search (hybrid BM25+embedding 0.7/0.3) → temporal decay (30d half-life).

---

# QUANTITATIVE DATA POINTS

- 16+ skills loaded per session, each ~97 chars + field lengths in prompt
- PreCompact fires ~2-3 times per long session (from compact-log.jsonl)
- UserPromptSubmit would fire ~20-50 times per session (~1s latency each = 20-50s total overhead)
- Orchestrator cost: ~$4-5 per session, 15 turns max
- Current wasted supervision: 5.9% (down from 21% in 48 hours)
- MEMORY.md: ~200 lines, <5KB
- Daily logs: ~0.5-1KB per day estimated
- Skill token budget: 2% of context window (~16K chars)
- 13 hooks deployed, 17 events available
- 4 projects served, 20+ recent sessions analyzed

---

# KEY QUESTIONS (quantitative focus)

1. **Cost-benefit of UserPromptSubmit hook:** 20-50s total latency per session vs estimated 30% context preservation improvement. Is this ROI positive?
2. **Heartbeat vs cron for orchestrator:** Heartbeat accumulates context (risk: context rot). Cron = fresh context (risk: no continuity). Quantify the tradeoff.
3. **Daily logs vs native auto-memory:** Native auto-memory already manages topic files. Is daily logs redundant or complementary?
4. **Lane model complexity:** Our orchestrator has 3 task types. Is a lane model over-engineering for N=3? When does it pay off?
5. **Skills gating ROI:** 16 skills × ~97 chars = ~1,552 chars. Removing 30% saves ~465 chars. Is this measurable against 16K char budget?
