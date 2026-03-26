---
name: findings-tracker
description: Recurrence counts and promotion status for recurring anti-patterns across all analyzed sessions
type: project
---

## Repeated-Read Anti-Pattern
**Status:** active, approaching hook-promotion threshold
**First seen:** 2026-03-04 (sessions.py 2x read in f27cc590)
**Recurrence count:** 8-10 instances across documented sessions
**Sessions:** f27cc590 (2x sessions.py), e9037546 (6x setup-friend.sh), 560df1b2 (2x generate_unified_embeddings.py), aa2981a8 (6x doctor.py), 955b17d9 (3x research-index.md), 7e3fdd99 (4x model-review/SKILL.md)
**Promotion threshold:** 10+ = hook
**Action needed:** Verify tool-tracker.sh dup-read detection is deployed and active. If not, deploy PostToolUse hook on Read.

## Schema-Probe-Before-Docs Pattern
**Status:** active, meets 2-recurrence rule-update threshold
**First seen:** 2026-03-20 (wrong-tool-drift: bash/grep instead of sessions.py)
**Recurrence count:** 2 (2026-03-20 + 2026-03-26 aa2981a8)
**Latest evidence:** 9 sequential SQLite/runlog.py probes before checking runlog.md or --help
**Action needed:** Extend probe-before-build rule to: "check --help and project docs before probing underlying storage schema"

## Parallel Gemini Rate-Limit in generate-overview.sh
**Status:** code bug, not behavior anti-pattern
**First seen:** 2026-03-26 (aa2981a8)
**Evidence:** 6 simultaneous requests → source overviews truncated/empty, tooling overviews succeeded
**Action needed:** Cap concurrency to 2 in generate-overview.sh --auto mode. File in maintenance-checklist.md.

## Silent Pipeline Break ("zero = quiet day")
**Status:** resolved in session, watch for recurrence
**First seen:** 2026-03-26 (aa2981a8)
**Evidence:** 7-day sessionend-log outage undetected by all consumers (propose-work, doctor.py, supervision-kpi)
**Fix deployed:** doctor.py freshness canary, ast-check for inline Python in .sh files, trap improvement
**Watch for:** Other monitoring pipelines that return 0 without distinguishing "zero events" from "pipeline broken"

## Partial Feedback Propagation (memory-only saves)
**Status:** resolved in session, watch for recurrence
**First seen:** 2026-03-26 (7e3fdd99)
**Evidence:** User gave cross-cutting behavioral feedback; agent saved to memory only, required 2 follow-ups to propagate to skills + CLAUDE.md
**Fix deployed:** feedback_propagate_feedback_fully.md saved to project memory
**Watch for:** "saved to memory" responses to behavioral feedback that don't include skill/rule propagation in same turn

## Async Poll Loop (file-read variant)
**Status:** active, promotion candidate
**First seen:** 2026-03-18 (TaskOutput polling — genomics 48f0dedc)
**Recurrence count:** 3 (2026-03-18, 2026-03-19 meta 05482950, 2026-03-26 genomics a62b3f8f+955df826)
**Latest evidence:** 11 consecutive Read calls on same background-written file (a62b3f8f); 3 sleep-poll loops (955df826)
**Meets promotion:** Yes (3 recurrences, checkable predicate)
**Proposed fix:** Extend CLAUDE.md patience rule to file-read polls: "Do NOT repeatedly Read files written by background processes. Wait for task-complete notification, then read once."

## Brainstorm/Subagent Work Duplication
**Status:** active, promotion candidate
**First seen:** 2026-03-19 (subagents rediscovering completed work — meta a5a95b9a)
**Recurrence count:** 2 (2026-03-19, 2026-03-26 genomics 3x parallel sessions)
**Latest evidence:** 3 independent sessions ran same brainstorm topic, each created separate .brainstorm/ dirs, independently discovered overlapping ideas
**Meets promotion:** Yes (2+ recurrences, checkable: check .brainstorm/ timestamp before starting)
**Proposed fix:** Add pre-check to brainstorm skill — check for existing runs in last 24h on overlapping topics.

## Parallel Agent Commit Sweep
**Status:** active, first occurrence
**First seen:** 2026-03-26 (genomics dfc98f6c)
**Recurrence count:** 1
**Evidence:** Parallel Codex agent swept uncommitted edits from another agent into wrong commit (3e5a343)
**Action:** Fix applied to dispatch-research skill. Needs invariants.md or CLAUDE.md rule.

## Stale Pipeline Output at Canonical Path
**Status:** active, first occurrence
**First seen:** 2026-03-26 (genomics fddae46b)
**Evidence:** Agent read prs_percentiles_with_ci.json (had LOW_PRECISION flag, CI=100%), reported retracted SCZ PRS=100th as headline. User: "WE CORRECTED THIS 10 times"
**Action:** Correction pipeline should archive stale outputs. Agent should check precision/status flags before reporting.

## Correlated Cross-Model Hallucination (code-behavior)
**Status:** active, first occurrence
**First seen:** 2026-03-26 (genomics a62b3f8f)
**Evidence:** Both GPT-5.4 and Gemini Pro hallucinated same G4Hunter bug — `abs(mean)` claimed as `mean(abs)`. Test proved code correct.
**Action:** Existing verify-before-fix protocol worked. Document as evidence for model-guide update.

## Codex Agent Turn Exhaustion (stub-template pattern)
**Status:** self-fixed in session, monitoring
**First seen:** 2026-03-26 (genomics fddae46b + dfc98f6c)
**Recurrence count:** 2 in same 15h window
**Evidence:** 3/4 Codex agents wrote stub template then exhausted turns. -o files empty or stub-only.
**Fix applied:** dispatch-research/SKILL.md prompt template rewritten — removed "write report to file" instruction.
**Action:** Verify fix holds in next dispatch-research session.

## Subagent Genomic Coordinate Hallucination
**Status:** active, first occurrence
**First seen:** 2026-03-26 (genomics fddae46b)
**Evidence:** Claude subagent bio-constants audit: 4/5 coordinate/biology claims hallucinated, only 1 real bug found. MCP verification showed all 4 "wrong" claims were actually correct.
**Action:** Protocol of verifying coordinate claims against dbSNP/Ensembl before acting. Worked correctly in this session.

## Last analysis run — genomics 2026-03-26
**Date:** 2026-03-26
**Sessions analyzed:** 1833d541, a62b3f8f, fddae46b, 5584f9f9, 955df826
**Output:** /Users/alien/Projects/meta/artifacts/session-retro/2026-03-26-genomics.md

## Last analysis run — meta 2026-03-26
**Date:** 2026-03-26
**Sessions analyzed:** aa2981a8, 955b17d9, 7e3fdd99, a315e598
**Output:** /Users/alien/Projects/meta/artifacts/session-retro/2026-03-26-meta.md
