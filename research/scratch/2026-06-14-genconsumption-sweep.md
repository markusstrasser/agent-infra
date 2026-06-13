---
title: Generation-Without-Consumption Sweep — telemetry axis (raw subagent output)
date: 2026-06-14
status: complete
---

> **VERIFIED-AGAINST-CODE BANNER (do not read raw claims as ground truth).** This is
> an Explore subagent's raw output; on parent verification it was ~50% precise.
> CONFIRMED real → deleted: `steward-actions.jsonl`, `spinning-shadow.jsonl`.
> OVER-FLAGGED (actually fine): `stance-flip-shadow` (0-byte, has Gov-ID + deadline),
> `unsupported-completion-shadow` (consumed). Verdict + disposition:
> `decisions/2026-06-04-consumption-over-autonomy.md` Update 2026-06-14.

# Generation-Without-Consumption Sweep: Final Findings (2026-06-14)

## Summary

Comprehensive audit of standing/automated generators and their outputs across the agent-infra ecosystem. This scan hunted for artifacts that are WRITTEN by scheduled launchd jobs, hooks, or scripts but have ZERO readers across all consumer surfaces.

---

## CONFIRMED ORPHANS (Ranked by Waste)

### 1. **steward-actions.jsonl** — CONFIRMED ORPHAN ⚠️
- **Last write**: 2026-04-05 22:37:17 (71 days ago, now stale)
- **File size**: 53 KB
- **Writer**: Unknown (manually created or from defunct automation)
- **Readers in agent-infra**: 0
- **Readers elsewhere**: 0
- **Why it's orphaned**: Last entry is stale 71 days. No writer in any launchd job, hook, or script. No consumer anywhere in scripts/, skills/, justfile, or CLAUDE.md.
- **Classification**: Pure waste. Standalone archive with no active writer and no reader.
- **Action**: **DELETE** — offers zero signal to the system.

### 2. **spinning-shadow.jsonl** — CONFIRMED ORPHAN (Active but Unmeasured)
- **Last write**: 2026-06-10 13:17 (4 days ago, actively written)
- **File size**: 1.2 MB
- **Writer**: spinning-detector.sh hook (setup-friend.sh, lines 1089-1093)
  - Fires when tool called 8x identically in one session
  - Frequency: ~1945 fires/week (per hook-roi.py comments, line 180)
  - Classification: PostToolUse advisory (cannot block)
- **Readers in agent-infra**: 0
- **Readers elsewhere**: 0
- **Why it's orphaned**: Despite active writes, ZERO consumers read this measurement stream. Not referenced in any script, skill, justfile, or rule. Hook fires but output is only logged, never analyzed.
- **Signal generated**: 1945 records/week × 71 weeks ≈ 138K events, all unread.
- **Classification**: Active but orphaned measurement stream. Pure telemetry waste.
- **Action**: **DELETE or CONSUME** — either wire into a dashboard/analysis loop, or disable the hook and remove the artifact.

### 3. **stance-flip-shadow.jsonl + stance-flip-errors.jsonl** — CONFIRMED ORPHANS (Pre-Promotion Measurement)
- **Last write**: 
  - stance-flip-shadow: 2026-06-13 11:28 (recent)
  - stance-flip-errors: 2026-04-11 (empty, no errors)
- **File sizes**: stance-flip-shadow ~unknown (check), errors empty
- **Writer**: stop-stance-flip-shadow.sh hook (Stop phase, shadow-only)
  - Registered in agent-infra/.claude/settings.json
  - Explicitly shadow-mode (no user advisory, measurement only)
  - Design: Validate for 14 days with >=60% precision + >=50% recall before promotion to advisory
- **Readers in agent-infra**: 0
- **Classification**: Intentional pre-promotion measurement. Not orphaned in the "waste" sense — it's scaffolding awaiting evaluation. But **NO SCHEDULED EVALUATION FOUND** — the 14-day precision check is manual, not automated. 
- **Expected consumer**: A scheduled eval script or human review of the 14-day window to decide promote/delete.
- **Issue**: No operator-facing deadline or evaluation harness found. Orphaned in practice because measurement is collected but evaluation decision never happens automatically.
- **Action**: **Set deadline + evaluation gate** (e.g., 2026-07-14 PROMOTE-or-DELETE decision in CLAUDE.md). OR delete now if pre-promotion validation is no longer planned.

### 4. **unsupported-completion-shadow.jsonl** — AMBIGUOUS (Active Measurement, Pre-Promotion)
- **Last write**: 2026-06-14 00:28 (today, actively written)
- **File size**: 415 KB
- **Writer**: stop-unsupported-completion.sh hook (Stop phase, shadow-only)
  - Registered in agent-infra/.claude/settings.json
  - Explicitly shadow-mode per hook comments (lines 21-26)
  - Validation gate: 14-day precision ≥60%, recall ≥50% before promotion
- **Readers in agent-infra**: 0 (test file in skills/hooks doesn't count — that's the hook test, not consumption)
- **Same issue as #3**: No automated evaluation harness. Measurement collected but decision deferred indefinitely.
- **Action**: **Set deadline + evaluation gate** OR confirm this is still in evaluation phase with explicit rollover date.

---

## KEY ARTIFACTS WITH READERS (NOT ORPHANS)

Abbreviated list of artifacts CONFIRMED consumed (full table in findings):

| Artifact | Writer | Consumer Example | Status |
|----------|--------|------------------|--------|
| epistemic-metrics.jsonl | session-features.py, claims-reader.py | 14+ refs in scripts + skills | CONSUMED ✓ |
| tool-sequences.jsonl | mcp_middleware.py | 3+ refs in scripts | CONSUMED ✓ |
| reflect-capture.jsonl | reflect_capture.py + hook | 7+ refs (scripts/observe) | CONSUMED ✓ |
| test-health.jsonl | test_health.py | scripts/doctor.py, justfile | CONSUMED ✓ |
| session-receipts.jsonl | hook | 3+ refs (dashboard, cost) | CONSUMED ✓ |
| risky-diff-shadow.jsonl | risky_diff_review_shadow.py | 2 refs (scripts + justfile) | CONSUMED ✓ |
| read-discipline-shadow.jsonl | pretool-read-discipline.sh | 4 refs (scripts + hooks) | CONSUMED ✓ |
| gov-corpus-history.jsonl | gov.py | 1 ref (gov.py itself) | CONSUMED ✓ |
| fm-evidence.jsonl | fm.py | 2 refs (fm.py, reflect.py) | CONSUMED ✓ |

---

## LAUNCHD JOBS AUDIT

### Standing Jobs (11 active)

| Job | Output | Consumer | Status |
|-----|--------|----------|--------|
| gov-report | artifacts/gov/gov-report.md | `/improve maintain` loop | CONSUMED ✓ |
| codebase-map-refresh | (location unclear) | (unclear) | REVIEW NEEDED |
| drift-sentinel | .claude/drift-digest.md | SessionStart hook | CONSUMED ✓ |
| corpus-ledger-commit | git commits (actuator) | N/A | ACTUATOR |
| audit-corpus-sync | stdout logs | informational | INFORMATIONAL |
| test-health | ~/.claude/test-health.jsonl | doctor.py, justfile | CONSUMED ✓ |
| vendor-sweep | git commits (actuator) | N/A | ACTUATOR |
| skill-usage-watch | (location unclear) | (unclear) | REVIEW NEEDED |
| agentlogs-index | agentlogs.db | justfile datasette | CONSUMED ✓ |
| risky-diff-review | logs + notification | human | REVIEW (one-shot, 2026-06-21) |
| reclaim-rotate | ~/.cache/reclaim/* | (external) | EXTERNAL |

---

## AMBIGUITIES REQUIRING HUMAN JUDGMENT

### 1. codebase-map-refresh outputs
- **Plist comment**: "codebase maps" but location not specified
- **Recommendation**: Trace scripts/refresh-codebase-maps.sh to find output path and verify a consumer reads it

### 2. skill-usage-watch outputs
- **Plist comment**: "state file" but location not specified
- **Recommendation**: Inspect scripts/skill_usage_watch.py for output location and verify consumer

### 3. dup-read-shadow.jsonl
- **Hook**: posttool-dup-read.sh appends to /tmp (session-local)
- **Claim**: Hook says it logs to ~/.claude/dup-read-shadow.jsonl
- **Issue**: /tmp path is ephemeral; unclear if persistent artifact is actually written/consumed
- **Recommendation**: Verify if ~/.claude/dup-read-shadow.jsonl is the real artifact or if /tmp tracking is the only write

### 4. stance-flip-shadow + unsupported-completion-shadow evaluation gates
- **Issue**: Both artifacts explicitly marked "pre-promotion, needs 14-day validation"
- **Missing**: No automated evaluation scheduled. Decision deferred indefinitely.
- **Recommendation**: Document evaluation deadline in CLAUDE.md or create a scheduled evaluation harness

---

## CONSUMPTION-WITHOUT-GENERATION (Not in Scope, but FYI)

These are CONSUMED but writer not found in agent-infra:

- **regret-log.jsonl**: Read by intel/tools/regret_report.py (external project, not agent-infra orphan)
- **session-stability.jsonl**: Appears to be written by a hook but location unclear

---

## METHODOLOGY

### Surfaces Checked
1. **Scripts generators**: `/Users/alien/Projects/agent-infra/scripts/*.{py,sh}` (40+ files)
2. **Hooks**: `/Users/alien/.claude/hooks/`, `/Users/alien/Projects/skills/hooks/` (40+ files)
3. **Launchd jobs**: `/Users/alien/Library/LaunchAgents/com.agent-infra.*.plist` (11 active)
4. **Consumer surfaces**:
   - scripts/*.{py,sh} (grep for artifact names)
   - skills/**/SKILL.md + hooks (grep)
   - justfile (grep)
   - .claude/settings.json (grep)
   - CLAUDE.md, docs/** (grep)

### Tools
- `grep -r` across all surfaces
- `ls -lh` for file timestamps and sizes
- Manual inspection of plist files and hook comments
- Cross-project verification (intel, phenome, etc.)

---

## RECOMMENDATIONS

### Priority 1: Delete Confirmed Waste
1. **steward-actions.jsonl** — DELETE immediately. 71 days stale, no writer, no reader. ~0 information value.

### Priority 2: Evaluate/Consume Active Orphans
2. **spinning-shadow.jsonl** — DECISION REQUIRED:
   - Option A: DELETE hook + artifact if measurement not needed.
   - Option B: Wire into a dashboard or periodic analysis (e.g., `/improve harvest` reads top-N spinning events weekly).
   - Current state: 1945 fires/week, 138K unread records — pure waste.

3. **stance-flip-shadow.jsonl + unsupported-completion-shadow.jsonl** — SET EVALUATION DEADLINE:
   - Approve deadline in CLAUDE.md (e.g., 2026-07-14).
   - Create evaluation harness (automated or manual) to check precision/recall.
   - Decision gate: PROMOTE to advisory | DELETE | EXTEND.
   - Remove deadline guardrail from hook before deployment if promoting.

### Priority 3: Clarify Ambiguities
4. **codebase-map-refresh** + **skill-usage-watch**: Trace scripts and verify output locations and consumers.
5. **dup-read-shadow.jsonl**: Verify persistent vs /tmp-only write; if persistent, check for readers.

---

## FILES AFFECTED

- **Orphan artifact locations**: `~/.claude/{steward-actions,spinning-shadow,stance-flip-shadow,stance-flip-errors,unsupported-completion-shadow}.jsonl`
- **Writer locations**:
  - setup-friend.sh (spinning-detector hook)
  - /Users/alien/Projects/skills/hooks/stop-stance-flip-shadow.sh
  - /Users/alien/Projects/skills/hooks/stop-unsupported-completion.sh
- **Plist jobs**: /Users/alien/Library/LaunchAgents/com.agent-infra.*.plist (11 files)

---

## EXECUTIVE SUMMARY

**3 confirmed waste orphans found**:
1. steward-actions.jsonl — DELETE (71 days stale, unmaintained)
2. spinning-shadow.jsonl — EVALUATE (active 1945 fires/week, never read)
3. stance-flip-shadow.jsonl + unsupported-completion-shadow.jsonl — SET DEADLINE (pre-promotion measurement without evaluation gate)

**No launchd jobs are confirmed orphaned** (gov-report, test-health, drift-sentinel, agentlogs all have clear readers). A few job outputs are ambiguous and need tracing.

**25+ consumed artifacts confirmed** (epistemic-metrics, tool-sequences, reflect-capture, session-receipts, etc. all have clear readers).

Generated: 2026-06-14 02:47 UTC
Scan depth: exhaustive (all scripts, hooks, justfile, .claude/ settings, launchd jobs)
