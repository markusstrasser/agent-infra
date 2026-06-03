# Subagent Zero-Output-on-Failure — Fix Research

**Status: COMPLETE**
**Date:** 2026-06-03
**Question:** Has Anthropic / Claude Code fixed the class of bug where a subagent (Task/Agent tool) bugs out mid-run (rate limit, crash, turn exhaustion) and returns status=completed with ZERO usable output to the parent?

Source grades: **A** = official changelog/docs, **B** = GitHub issue, **C** = community/blog.

> NOTE on tool naming: the subagent tool was renamed **`Task` → `Agent` in Claude Code v2.1.63**. Current SDK emits `"Agent"` in tool_use blocks but still uses `"Task"` in the system:init tools list. Both names refer to the same mechanism. (Source A: https://code.claude.com/docs/en/agent-sdk/subagents)

---

## 1. THE EXACT FAILURE MODE IS DOCUMENTED — and OPEN

### Issue #47936 — "(Async) Subagents stopping early" — **OPEN** [B]
URL: https://github.com/anthropics/claude-code/issues/47936
- **Opened:** April 14, 2026 (matches your ~2026-04 observation). Reporter: rudra-sett. Version: Claude Code 2.1.104, Opus, area:agent-sdk, has-repro.
- **Status: OPEN.** No assignee, no linked PR, no maintainer response, no fix version. (Has `stale` activity but NOT closed.)
- **This is your exact failure mode.** Subagents spawned `run_in_background: true` stop mid-execution and are reported `<status>completed</status>` to the parent **with NO `<result>` block** — the parent receives a task-notification that looks successful but carries zero output. Reporter's verbatim contrast:
  - Prematurely stopped: `<status>completed</status> ... <!-- NO result block -->`
  - Successful: `<status>completed</status> <result>All 61 citations passed...</result>`
- Final subagent messages show `stop_reason: None` (external termination, not agent-chosen `end_turn`) while still mid-tool-call.
- **Occurrence rate reported: 14–30% of runs.**
- Requested fixes (NOT yet implemented): SDK should not report "completed" on premature termination; task notification should carry `stop_reason`/`termination_reason`.

### Issue #56869 — "Tool result missing due to internal error — no error propagation" — **OPEN** [B]
URL: https://github.com/anthropics/claude-code/issues/56869
- **Opened:** May 7, 2026. CLI as of 2026-05-06, Opus 4.7 (1M). area:agents, bug, platform:windows, `stale`.
- **Status: OPEN.** No assignee, no PR, no maintainer response.
- Parallel `Agent` calls: one subagent returns `"Tool result missing due to internal error"`; the parent does NOT treat it as terminal, hangs indefinitely, no timeout/retry. Suggested fix (unimplemented): raise an `InternalError` tool response for the specific tool_use_id.

### Issue #27053 — "Task subagents permanently return 'Rate limit reached' with 0 tokens" — **CLOSED (not planned / stale)** [B]
URL: https://github.com/anthropics/claude-code/issues/27053
- **Opened:** Feb 20, 2026. Reporter: MalekAG. Closed **not planned**, labeled stale. No fix.
- Closest to "rate limit after N calls → empty." Task subagents return `API Error: Rate limit reached` with `total_tokens: 0, tool_uses: 0` across all models/days. Reporter argues it's a masking error, not a real rate limit (a real limit would still count input tokens). **Closed without a fix** — absence of resolution, not a fix.

### Issue #59962 — "Completed subagent work leaves task state stuck in_progress; follow-ups no-op" — **OPEN** [B]
URL: https://github.com/anthropics/claude-code/issues/59962
- **Opened:** May 17, 2026. Version 2.1.139. area:agents/tools/tui. Status: OPEN, no fix version.
- Lifecycle desync: subagent reaches terminal state (side effects present, no live worker) but Claude's visible task state stays `in_progress`; follow-up prompts no-op. Links 5 adjacent issues (#44783, #48312, #55893, #58637, #59900).

### Issue #19295 — "SubAgent output files deleted before main agent reads results" — **CLOSED (duplicate)** [B]
URL: https://github.com/anthropics/claude-code/issues/19295
- **Opened:** Jan 19, 2026. Windows, v2.1.2. Closed as duplicate; no fix version cited. Output durability bug: background output `.output` files cleaned up before the parent Reads them.

### Issue #18240 — "Subagent return context exhaustion / premature token limit" — **CLOSED (duplicate)** [B]
URL: https://github.com/anthropics/claude-code/issues/18240
- **Opened:** Jan 14, 2026. v2.1.7, macOS. Closed as duplicate, no fix version. Turn/context-exhaustion variant: subagent return balloons parent messages to 132% of limit → "Context limit reached."

### Issue #4527 — "subagents slow down the longer they run" — CLOSED (duplicate) [B]
URL: https://github.com/anthropics/claude-code/issues/4527 — Opened Jul 27 2025. Performance degradation, tangential. No fix version.

---

## 2. WHAT THE CHANGELOG ACTUALLY FIXED (and what it did NOT)

Source A (official): https://code.claude.com/docs/en/changelog

### Closest entry — **2.1.161 (June 2, 2026)** [A]
> "Fixed completed subagents getting stuck showing as running when an error occurs while finalizing their result"

**CRITICAL distinction:** This fixes the **UI/lifecycle state** (subagent stuck *showing as running* after an error) — it is the symptom in #59962, NOT the output-durability symptom in #47936. It does **not** claim to deliver the missing `<result>` to the parent, nor to convert a premature `completed` into an error. Treat as adjacent, not the fix for zero-output-to-parent.

### Other adjacent changelog entries [A]
- **2.1.161 (Jun 2):** "Parallel tool calls: a failed Bash command no longer cancels other calls in the same batch — each tool returns its own result independently." (Parallel-failure isolation — related class, but Bash not Agent.)
- **2.1.152 (May 27):** "Fixed background subagent output corrupting `claude -p` stdout when using `--output-format text` or `json`." (Output-stream integrity, not durability-on-failure.)
- **2.1.147 (May 21):** "Fixed `Agent` tool with `subagent_type: 'claude'` running in an undocumented temporary worktree, which could **silently discard outputs** written to gitignored paths." (A real silent-output-loss fix — but specific to the claude-subagent-in-worktree case, not rate-limit/turn-exhaustion.)
- **2.1.154 (May 28):** Fixed subagents in background sessions bypassing worktree-isolation guard.
- **2.1.160 (Jun 2):** Fixed restoring a completed `claude agents` session dropping chat history / re-running the original prompt.
- **2.1.126 (May 1):** Fixed API retry countdown sticking at "0s". **2.1.121 (Apr 28):** `/usage` "rate limited" after stale OAuth → auto-refresh. (Rate-limit UX, not subagent output.)

**No changelog entry in 2.1.139–2.1.161 states "subagent returns empty/zero output to parent on rate-limit/turn-exhaustion was fixed."** The matching issues (#47936, #56869) have no linked PR and remain open.

---

## 3. AGENT SDK: error-result typing DID improve (partial, indirect mitigation) [A]

Source A: claude-agent-sdk-typescript CHANGELOG — https://github.com/anthropics/claude-agent-sdk-typescript/blob/main/CHANGELOG.md

- **v0.2.89:** "Fixed error result messages (`error_during_execution`, `error_max_turns`, `error_max_budget_usd`) to correctly set `is_error: true` with descriptive messages." → Before this, an automated pipeline checking `is_error` could silently treat a **max-turns termination as success**. This is the most direct *mitigation* of "turn-exhaustion → looks-completed" — but it lives in the **SDK result-message layer**, and guidance is to check `message.subtype`, not `is_error`.
- **v0.2.91:** Added optional `terminal_reason` field to result messages (`completed`, `aborted_tools`, `max_turns`, `blocking_limit`, etc.).
- **v0.2.31:** Added `stop_reason` to `SDKResultSuccess`/`SDKResultError`.

These give the SDK *caller* fields to detect abnormal termination — but they describe the top-level `query()` result, NOT the inner Agent-tool result a parent agent receives mid-conversation. The #47936 ask (put `stop_reason`/`termination_reason` in the **task notification** the parent agent sees) is a different surface and remains unaddressed.

## 4. Sub-agents docs: what the parent receives [A]

Source A: https://code.claude.com/docs/en/agent-sdk/subagents and https://code.claude.com/docs/en/sub-agents
- Documented happy path only: *"The parent receives the subagent's final message verbatim as the Agent tool result."*
- **No documentation of the failure path:** the docs do not state what the parent receives when the subagent has NO final message (rate-limited, crashed, or terminated mid-turn). Output durability is documented for *transcripts* (persist independently, 30-day `cleanupPeriodDays` cleanup) but says nothing about delivering partial/error output to the parent on abnormal termination.

## 5. Community (C — lower grade, not used to confirm fixes)
Search surfaced community guides (arsturn.com, dev.to, claudelog.com, codersera, aiqnahub) on subagent pitfalls. None document a *version-pinned fix* for zero-output-on-failure; they describe workarounds (have subagents write to files, verify outputs). No May–June 2026 community post claims the failure mode was fixed.

---

## KEY QUESTIONS — ANSWERED

**Q: Specific documented fix for subagent zero-output-on-failure, with version + date?**
NO. No changelog entry or merged PR addresses "subagent returns status=completed with zero output after rate-limit/turn-exhaustion." The exact issue (#47936) is OPEN with no linked PR. The 2.1.161 "finalizing their result" entry fixes the *UI-stuck-running* symptom (#59962-class), not output delivery to the parent.

**Q: When a subagent errors / hits a rate limit now, what does the parent receive?**
- In the **interactive CLI / agent-tool surface:** per OPEN #47936 (Apr 14, 2026) and #56869 (May 7, 2026), the parent can receive `status=completed` with **no result block**, or a non-terminal "Tool result missing due to internal error" string it hangs on. Not reliably an error.
- In the **SDK top-level result:** since v0.2.89 / v0.2.91, abnormal termination now sets `is_error: true` and exposes `terminal_reason`/`stop_reason` (`max_turns`, etc.) — so an SDK *caller* checking `message.subtype` can detect it. This does NOT propagate into the inner Agent-tool result a parent *agent* sees.

**Q: Has subagent output durability changed recently in any documented way?**
Marginally and obliquely: 2.1.147 (May 21) fixed one silent-output-discard case (claude-subagent temp worktree + gitignored paths); 2.1.152 (May 27) fixed background-subagent output corrupting `claude -p` stdout; SDK v0.2.89/0.2.91 improved error-result typing. None of these is a general "preserve/deliver partial output on subagent failure" fix.

---

## VERDICT

**The zero-output-on-failure mode is UNDOCUMENTED-AS-FIXED and the canonical issue (#47936) is CONFIRMED-STILL-OPEN as of June 3, 2026** — the only relevant mitigation is SDK-layer error-result typing (is_error/terminal_reason, v0.2.89–0.2.91) for callers checking `message.subtype`, NOT delivery of usable output to a parent agent.

---

## Local empirical corroboration (agent-infra, 2026-06-03)

`~/.claude/subagent-log.jsonl` records `output_len` per `subagent_stop` event
(`len(msg)` of the final message the parent receives; logged by
`skills/hooks/subagent-epistemic-gate.sh:35`). `output_len==0` = parent got an
empty result — the exact #47936 signature.

**Real Agent-tool dispatches (workflow-subagent excluded — its 0-len is a
structured-output instrumentation artifact, not a failure):**

| Month | completions | zero-output | rate |
|-------|-------------|-------------|------|
| 2026-03 | 1767 | 3 | 0.17% |
| 2026-04 | 942 | 17 | 1.80% |
| 2026-05 | 1107 | 48 | 4.34% |
| 2026-06 (partial) | 265 | 11 | 4.15% |

Affected types: `general-purpose` (47 all-time), `researcher` (30). Zero-outputs
cluster at identical timestamps on parallel fan-outs — consistent with
rate-limit cascades hitting concurrent subagents (the #27053 / #47936 mechanism).

**Verdict:** NOT fixed. Locally the rate rose then plateaued ~4%, ongoing through
the latest data (2026-06-02). Reporter's 14–30% (#47936) is higher but same
direction. This is *below* our threshold for trusting the platform to deliver
usable output on abnormal termination.

**Decision:** the `pretool-subagent-gate.sh` write-stub-first + file-output
BLOCKING gates (Checks 7, 10) STAY. The turn-budget block was correctly demoted
to advisory (maxTurns now returns a final message; that half *was* fixed), but
the durability half guards a failure mode that is empirically live and
upstream-open. Do not propose removing it without a version-pinned fix to
#47936 AND a local zero-output rate returning to <0.5%.
