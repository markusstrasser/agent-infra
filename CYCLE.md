# Research Cycle — meta

**Cumulative cost:** $0.00 (first tick)
**Last tick:** 2026-03-25

## Discoveries

- [NEW] Claude Code v2.1.83: `CwdChanged` and `FileChanged` hook events — reactive file/directory change detection without launchd WatchPaths. Could enable direnv-style environment reloading, auto-refresh after external edits.
- [NEW] Claude Code v2.1.83: `initialPrompt` agent frontmatter — auto-submits first turn for agents. Could simplify orchestrator agent dispatch and skill startup patterns.
- [NEW] Claude Code v2.1.81: `managed-settings.d/` drop-in directory — team policy fragments. Could replace manual settings.json propagation across projects.
- [NEW] OpenSage (arXiv:2602.16891, Berkeley/UCSB/DeepMind) — self-programming agent generation engine. Dynamic sub-agent topology, tool synthesis, hierarchical graph memory. 59% SWE-Bench Pro. Conceptual parallel to meta's self-improvement loop — agents that optimize their own scaffolding. Not directly usable (different architecture) but validates direction.
- [KNOWN] `--bare`, `effort` frontmatter, `rate_limits` statusline — already tracked in `research/claude-code-native-features-deferred.md`. effort done (22 skills), rate_limits already had, --bare deferred (orchestrator uses SDK not CLI).
- [NOTE] Perplexity API quota exhausted — needs billing check before next research cycle.

## Improvement Signals (from live state)

- STEER/medium: `stop-hook-feedback-relay` (7x across 4 sessions) — human manually relaying stop-hook feedback
- STEER/medium: `plan-injection-manual` (6x across 5 sessions) — human manually injecting plan context
- STEER/medium: `user-status-check-nudging` (5x across 3 sessions) — human nudging for status checks
- RELIA/high: Missing hook scripts (setup_duckdb.py, others) — cross-project hook references to nonexistent files

## Gaps

1. **G1: Stop-hook feedback ignored (STEER, 7x/4 sessions)** — Stop hooks emit advisory feedback via `decision: "allow"` + `additionalContext`, but agent ignores it since it's already stopping. Human manually re-states the feedback as a user message. Fix: audit stop hooks, promote critical advisory outputs to `decision: "block"` so agent must address them. Autonomous — reversible, existing pattern.

2. **G2: Plans not auto-loaded on session start (STEER, 6x/5 sessions)** — `.claude/plans/` files exist but aren't injected into context at session start. Human manually pastes plan content. Fix: add a session-init phase that checks for recent plans (<24h) and emits them via `additionalContext`. Autonomous — reversible, existing pattern.

3. **G3: v2.1.83 hook events unevaluated** — `CwdChanged` and `FileChanged` are new hook events. Need evaluation memo for our use cases (direnv, auto-refresh, file watchers). `initialPrompt` agent frontmatter also unevaluated. Lower priority — informational, no supervision cost.

## Active Plan

### G1: Stop-hook feedback relay fix

**Problem:** Stop hooks fire with advisory feedback but agent ignores `additionalContext` on "allow" decisions because it's already stopping. Human relays feedback 7x across 4 sessions.

**Root cause:** The stop hooks use `decision: "allow"` for advisory feedback. When the hook allows stopping, the agent receives the additionalContext but has no obligation to act on it. The feedback gets printed to the human (who then relays it) but the agent has already stopped.

**Fix approach:** Two-part:
1. **Audit stop hooks** — classify each stop hook's feedback as advisory (truly optional) vs critical (agent should address before stopping). Critical = "block", advisory = "allow".
2. **Add meta-rule** — In global CLAUDE.md or rules file: "When a stop hook provides additionalContext, read and address it before confirming stop."

**Files to change:**
- `~/Projects/skills/hooks/stop-plan-gate.sh` — if plan has uncompleted items, this should "block" not "allow"
- `~/.claude/hooks/stop-verify-claims.sh` — already blocks on unverified claims (correct)
- `~/Projects/skills/hooks/stop-uncommitted-warn.sh` — already attempts auto-commit (correct)
- `~/.claude/hooks/stop-debrief.sh` — advisory debrief, should stay "allow" (optional)

**Verification:** After fix, check 5 subsequent sessions for "stop-hook-feedback-relay" signal. Should drop to 0.

## Queue

- [G1] Stop-hook feedback relay fix — audit stop hooks, promote critical advisory to blocking
- [G2] Plan auto-load in session-init — add phase to session-init.sh

## Autonomous (done)

- [2026-03-25] **G1: Stop-hook feedback relay** — Changed `stop-debrief.sh` from `decision: "allow"` to `decision: "block"`. Agent must now write debrief before stopping. Reflection: straightforward — the root cause was clear once I read the hook code.
- [2026-03-25] **G2: Plan auto-load** — Enhanced `05-plan-scan.sh` to include plan body snippet (800 chars) with file path in additionalContext. Agent now gets plan content at session start, not just "INCOMPLETE PLANS: slug". Reflection: the hook already existed but only emitted a one-liner — the gap was in the content, not the infrastructure.
- [2026-03-25] **Skill fix: research-cycle model override** — Removed `model: claude-sonnet-4-6` from SKILL.md frontmatter. Skill now inherits session model.

## Verification Results

## Cycle Retro

## Errors
