# Subagent Optimization — Implementation Summary

**Date:** 2026-03-02
**Cross-model review:** Gemini 3.1 Pro + GPT-5.2. 22 items extracted, 11 included, 5 deferred, 6 rejected.

## Problem

1,886 subagent calls across all projects. 60% (1,128) are `general-purpose` — mostly doing work Explore or direct tools could handle. Current 3-line instruction wasn't working.

## Research Basis

- Google arXiv:2512.08296: multi-agent +81% parallel, -70% sequential, 45% single-agent threshold
- arXiv:2505.18286: multi-agent benefits diminish as LLM capability increases
- arXiv:2512.24601 (RLM): "never summarize, delegate instead" — subagents are context compression

**Core insight:** Subagents are context shields, not capability multipliers. With Opus 4.6, the 45% single-agent threshold is exceeded on most tasks. The value is isolation, not parallelization.

## What Was Deployed

### Phase 1: Measurement (new)

| File | What |
|------|------|
| `~/Projects/skills/hooks/subagent-start-log.sh` | SubagentStart logger → `~/.claude/subagent-log.jsonl` |
| `~/Projects/skills/hooks/subagent-epistemic-gate.sh` | Extended: SubagentStop completion logging (full-length output_len) |
| `~/.claude/settings.json` | SubagentStart hook wired inside `"hooks"` object |

### Phase 2: Instructions

| File | What |
|------|------|
| `~/.claude/CLAUDE.md` | `<subagent_usage>` rewritten: delegate-when + do-NOT-delegate decision framework |

### Phase 3: Advisory Hooks (all exit 0 + additionalContext)

| File | What |
|------|------|
| `~/Projects/skills/hooks/pretool-subagent-gate.sh` | PreToolUse:Agent — 4 checks: brainstorm, single-tool, gp-as-explore, cascade (3+/5+) |
| `~/Projects/skills/hooks/subagent-epistemic-gate.sh` | SubagentStop — result-size warning (>2KB, using full MSG_LEN) |
| `~/.claude/hooks/tool-tracker.sh` | Extended: non-Agent tool timestamp for cascade reset |
| `~/.claude/settings.json` | PreToolUse:Agent matcher wired |

### Phase 4: Agent Fixes

| File | What |
|------|------|
| `~/.claude/agents/researcher.md` | Stop hook: prompt→command (broken prompt hooks), maxTurns 30→20 |
| `~/Projects/skills/hooks/subagent-source-check-stop.sh` | Researcher Stop: would-block advisory + logging (promote to blocking after 14d if ≤10% trigger rate) |

### Phase 5: Analysis

| File | What |
|------|------|
| `~/Projects/meta/scripts/subagent-analysis.py` | Reads `~/.claude/subagent-log.jsonl`, produces distribution/trend/waste/pairing metrics |

## Model Review Key Findings (Integrated)

| ID | Finding | Action |
|----|---------|--------|
| G1/P2 | settings.json nesting | Fixed: SubagentStart inside `"hooks"` object |
| G2 | try/except in logger | Fixed: matches epistemic-gate pattern |
| G3 | Cascade detection in PostToolUse fires too late | Fixed: moved to PreToolUse:Agent gate |
| P1/P11 | Phase 4 blocking contradicts advisory-only policy | Fixed: researcher Stop is would-block |
| P3 | Parse session_id/cwd from event, not filesystem | Fixed: subagent-start-log.sh reads event JSON |
| P4/P12 | Output-size warning unreachable (truncated MSG) | Fixed: MSG_LEN computed before truncation |
| P8 | Global changes = shared infra governance | Acknowledged in plan |
| P9 | Escalation on count not FP rate | Fixed: requires FP <10% + cross-model review |
| P15 | Need operational waste definition | Added to plan |

## Bugs Found During Implementation

| Script | Bug | Severity | Status |
|--------|-----|----------|--------|
| `subagent-source-check-stop.sh` | Shell injection in Python logging | HIGH | Fixed: env vars instead of interpolation |
| `pretool-subagent-gate.sh` | `stat -f %m` macOS-only | MEDIUM | Deferred: macOS-only environment |
| `subagent-epistemic-gate.sh` | f-string braces in agent_type | LOW | Deferred: agent_type is controlled string |

## Operational Waste Definition

A subagent call is "waste" if ANY of:
- Produces <200 chars output AND parent subsequently does the same work directly
- Makes exactly 1 tool call
- Is `general-purpose` where Explore or direct Grep/Read would suffice
- Produces zero output (suggestion/brainstorm agents)

FP measurement: `precision = warned_and_waste / warned_total`. Target: ≥90% before escalation.

## Verification Schedule

1. **Immediate:** Test each hook in a new session
2. **7-day:** `uv run python3 scripts/subagent-analysis.py --days 7` — check ≥95% log coverage, ≥98% start/stop pairing
3. **14-day:** Advisory gate precision ≥90%, researcher would-block ≤10%
4. **30-day:** general-purpose share <40% (baseline 60%). Escalation requires FP <10% confirmed + cross-model review

## What Was NOT Done (By Design)

- No new agents — 7 existing cover the use cases
- No blocking hooks — all advisory until measured
- No changes to Explore/Plan — used appropriately (628 legitimate Explore calls)
- No orchestrator — separate tracked item
- No spinning-detector.sh changes — cascade detection moved to PreToolUse instead
