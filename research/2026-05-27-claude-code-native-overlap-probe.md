---
title: Claude Code v2.1.139+ native primitives — overlap probe vs our infra
date: 2026-05-27
status: complete (probe only — no implementation)
trigger: research/2026-05-27-agentic-coding-swe-4w.md flagged 3 native primitives that overlap dashboard.py, /loop, and our epistemic-discipline hooks
cc_version_tested: 2.1.152 (build 2026-05-26)
---

# Claude Code Native Primitives — Overlap Probe

Method: string-search the CC binary (`/Users/alien/.local/share/claude/versions/2.1.152`, 214MB Mach-O) for the four primitives the 4-week sweep called out. Decision per primitive: keep ours, deprecate ours, compose, or watch.

## Confirmed in CC 2.1.152 binary

| Primitive | Evidence | Status |
|---|---|---|
| `/goal` slash command | `/goal <condition>`, `/goal clear`, `/goal active`, `/goal all tests pass` strings present; hooks-required; trusted-workspace only | Confirmed |
| `/agents` slash command | `/agents` in command list; per-session agent definitions | Confirmed |
| `continueOnBlock` PostToolUse option | String present in hook handling code path | Confirmed |
| Built-in session insights extractor | `goal_categories`, `outcomes`, `satisfaction`, `helpfulness`, `friction_counts`, `multi_clauding`, `tool_error_categories`, `user_response_times` facets present in `bsK`/`xsK`/`EsK`/`JAO` functions | Confirmed |

## Per-primitive decision

### 1. `/goal` vs `/loop` skill — **compose, no removal**

These are different primitives:
- **`/goal <condition>`** is a *completion condition* — "stop when X is true". One-shot termination check.
- **`/loop [interval] /cmd`** is a *recurring scheduler* — "fire /cmd every N minutes (or self-paced)".

They compose: `/loop /improve` + `/goal all_findings_resolved` is the natural pairing. Neither replaces the other.

**Action:** none. Maybe surface in the `/loop` skill description that `/goal` exists as a completion-condition counterpart.

### 2. `/agents` vs our subagent dispatch — **already aligned**

`/agents` manages per-session agent definitions (the same surface we use via `.claude/agents/*.md` for `researcher`, `Explore`, `claude-code-guide`, etc.). Not a fleet/dashboard replacement.

**Action:** none.

### 3. `continueOnBlock` PostToolUse — **highest-value lift; defer to a separate session**

The string is present in the binary's hook handling code path. Per the 4-week sweep, the semantic is: when a PostToolUse hook returns "block", instead of just halting, the hook's stderr/reasoning is fed back into the model's next turn as additional context.

Current state of our blocking hooks (from the startup-hook 24h telemetry):
- `source-check`: 91 fires/24h
- `commit-check`: 64 fires/24h
- `epistemic-gate`: 77 fires/24h
- `source-remind`: 33 fires/24h

These all fire often enough that **converting from "block + agent reads stderr next turn" to "continueOnBlock + reasoning lands in same turn"** would meaningfully shorten the correction loop. Currently the agent has to re-process its plan; with `continueOnBlock` it can adjust mid-stream.

**Action:** **not now** — this is a build proposal, not an update. Gate: need to (a) read the actual `continueOnBlock` semantics from the CC docs (binary strings are not a spec), (b) pick one hook to convert as a probe, (c) measure before/after. Park as a follow-up.

### 4. Built-in session insights vs `dashboard.py` — **watch — possible partial deprecation**

CC 2.1.152's binary contains a substantial session-facet extractor with these dimensions:

- `goal_categories` (per-session intent classification)
- `outcomes` (success/partial/abandoned)
- `user_satisfaction_counts` (extracted from conversational signals)
- `claude_helpfulness`
- `friction_counts` (what frustrated the user)
- `session_type`, `primary_success`
- `multi_clauding` (parallel-session overlap detection — sessions started within 30 min of each other)
- `tool_error_categories` with rollups
- `user_response_times` (median, avg, distribution)
- per-language LOC, git_commits, git_pushes
- `aggregated_data` block with all of the above per-user

This overlaps significantly with `scripts/dashboard.py` (which currently reads `~/.claude/session-receipts.jsonl` + Codex/OpenAI receipts for cost/duration). CC's extractor goes further — it does *qualitative* facet extraction via LLM that we don't do at all.

**Action:** **probe needed in a separate session.** Try `claude insights`, `claude analytics`, or similar subcommand to see if this is user-accessible. If exposed as JSON output, we may be able to replace the cost-rollup half of `dashboard.py` with a thin wrapper around it, OR add the facet-extraction dimensions to our dashboard. Per native-patterns.md ("Does a native tool handle this?"), this is the right kind of question to ask before extending `dashboard.py` further.

## Summary

| Primitive | Our equivalent | Decision |
|---|---|---|
| `/goal` | `/loop` autonomous mode | Compose, not replace |
| `/agents` | `.claude/agents/*.md` | Already aligned |
| `continueOnBlock` | source-check, epistemic-gate, etc. (blocking hooks) | Defer — separate build session; high-value lift but needs doc-spec read + measured probe |
| Built-in session insights | `dashboard.py` | Watch — probe `claude insights` subcommand availability before next dashboard extension |

## Pertinent negatives

- No evidence the CC binary ships a *cross-session* dashboard equivalent to ours — facet extraction is per-session/per-user only. Cost rollups across vendors (Codex, OpenAI receipts) are still ours alone.
- No evidence of a `claude agents view` (fleet-view) subcommand at the top-level. `/agents` is the in-session command.
- `continueOnBlock` semantics not documented in the binary strings alone — need official docs before converting any hook.

<!-- knowledge-index
generated: 2026-05-27T10:54:29Z
hash: 084833976441

index:title: Claude Code v2.1.139+ native primitives — overlap probe vs our infra
index:status: complete (probe only — no implementation)
cross_refs: research/2026-05-27-agentic-coding-swe-4w.md

end-knowledge-index -->
