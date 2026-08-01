---
title: Pi harness internals deep dive — compaction, tools, newest tricks (v0.83)
date: 2026-08-01
tags: [harness, pi, compaction, context, steal]
status: active
---

# Pi harness internals deep dive — 2026-08-01

**Question:** What do Pi’s *internals* actually do that makes Databricks report ~3× less context/turn and >2× lower $/task? What’s new since our 2026-07-09 skim?
**Clone:** `/Volumes/2TBPNY/projects-offload/best/pi` @ `a116523` (2026-08-01) — packages at **0.83.0**
**Prior memo:** `research/2026-07-09-databricks-pi-harness.md` (blog relevance + high-level steal list)

## Architecture (current monorepo)

| Package | Role |
|---------|------|
| `@earendil-works/pi-ai` | Multi-provider LLM API (OpenAI, Anthropic, Google, Bedrock, OpenRouter, …) |
| `@earendil-works/pi-agent-core` | Agent runtime: tool loop, steer/followUp queues, harness compaction helpers |
| `@earendil-works/pi-coding-agent` | Interactive CLI + session tree + tools + extensions |
| `@earendil-works/pi-tui` | Terminal UI (diff rendering, fullscreen transcript, scrollbars) |
| `@earendil-works/pi-protocol` + `pi-client` + `pi-server` | **New stack:** CBOR length-prefixed remote sessions, composable server |
| `@earendil-works/pi-storage` / sqlite-node | Session storage backends; recent work = linear-time SQLite ops + branch cache |
| `@earendil-works/pi-evals` | Eval harness for the project |

**Permission model (unchanged philosophy):** no built-in FS/network ACL. Isolation is external (Gondolin micro-VM extension, Docker, OpenShell). Do **not** steal permissiveness into our stack.

---

## Core trick 1 — Context compaction (still the main efficiency story)

**Source:** `packages/coding-agent/src/core/compaction/{compaction,utils,branch-summarization}.ts`  
**Docs:** `packages/coding-agent/docs/compaction.md`

### Trigger

```
contextTokens > contextWindow - reserveTokens
// defaults: reserveTokens=16384, keepRecentTokens=20000
```

`contextTokens` prefers provider `usage.totalTokens` (input+output+cacheRead+cacheWrite); trailing messages after last assistant usage estimated via **chars/4** (intentionally overestimates).

### Cut algorithm (not “drop oldest N messages”)

1. Walk **backwards** from newest, accumulate estimated tokens until `keepRecentTokens`.
2. Cut only at **valid cut points**: user, assistant, bashExecution, custom, branch/compaction summary — **never** toolResult (keeps tool-call/result pairs atomic).
3. **Split-turn:** if one huge turn exceeds the keep budget, cut mid-turn at an assistant message; generate **history summary + turn-prefix summary** and merge.
4. On re-compact: span starts at previous compaction’s `firstKeptEntryId` (not the compaction entry itself) so already-kept messages re-enter the next summary pass — iterative summary quality.
5. `tokensBefore` recalculated from rebuilt session context before write (not a stale counter).

### What the model sees after compact

```
system | structured summary | messages from firstKeptEntryId → tip
```

Older raw turns are **not sent**. Session file still appends a `compaction` entry (tree-preserving); path-to-LLM is rebuilt from summary + kept tail.

### Structured summary format (stealable)

Goal · Constraints · Progress (Done/In Progress/Blocked) · Key Decisions · Next Steps · Critical Context · plus cumulative:

```xml
<read-files>…</read-files>
<modified-files>…</modified-files>
```

File ops extracted from tool calls (`read`/`write`/`edit`) **and** previous compaction `details` — cumulative across compacts and branch summaries.

### Serialization before the summarizer LLM

`serializeConversation()` turns the history into tagged lines (`[User]:`, `[Assistant tool calls]:`, …) so the model **does not continue the conversation**.

| Truncation | Where | Limit |
|------------|--------|-------|
| Tool results in **summary input** | `utils.ts` `TOOL_RESULT_MAX_CHARS` | **2000 chars** + marker |
| Live tool outputs to the **agent** | `tools/truncate.ts` | **2000 lines OR 50KB** (whichever first); complete lines only |

These are different knobs. Our earlier “don’t global-2k live tool results” still holds; the 2k limit is for **summarizer input**, not agent vision of tools.

### Summarizer call economics (newest refinement)

```typescript
// completeSummarization — packages/coding-agent/src/core/compaction/compaction.ts
cacheRetention: "none",
sessionId: uuidv7(),  // fresh routing session
```

One-shot summary requests: **no prompt-cache writes**, fresh session id — avoid polluting cache with non-reusable prompts. Wrapped in `retryAssistantCall` for transient stream drops (resilient compaction, 0.81.x+).

### Extension surface

- `session_before_compact` — cancel or supply custom summary (own model, own details schema).
- `session_before_tree` — same for branch navigation summaries.
- `willRetry` flag when compacting after **overflow** (aborted turn will auto-retry once).

### Overflow recovery (important)

`AgentSession` tracks `_overflowRecoveryAttempted`:

1. Provider returns context overflow **or** usage exceeds window → compact with `reason: "overflow"`.
2. If the failed turn was mid-tool (`willRetry`), strip error, compact, **auto-retry once**.
3. Second overflow failure → stop with explicit error (don’t loop compact forever).

Threshold compact vs overflow compact share pipeline; queue/steer messages survive compaction (regression tests cover this).

---

## Core trick 2 — Minimal coding tool surface

**Default coding set** (`createCodingToolDefinitions`): **read · bash · edit · write** only.

Full set available: + grep · find · ls (and extensions). Databricks “bash for everything / minimum tools” maps to the **4-tool coding preset**, not zero tools.

**Live output discipline:**

- `truncateHead` / `truncateTail` — 2000 lines / 50KB, never partial lines (bash tail edge-case documented).
- Grep lines capped at **500 chars** per match line.
- **File mutation queue** (`file-mutation-queue.ts`): serialize mutations on the *same* realpath; different files stay parallel — prevents races without global lock.

---

## Core trick 3 — Session as a tree (not a linear log)

**Format:** JSONL under `~/.pi/agent/sessions/--path--/…`, **v3** tree with `id`/`parentId`.

Entry types include messages, compaction, branch_summary, bashExecution, custom (extensions). Branching is **in-file** via `/tree` — no new session file per side-quest.

**Branch summarization:** navigate away from a leaf → optional LLM summary of abandoned path → inject as `BranchSummaryEntry` so target branch inherits “what we learned over there” without replaying full side-quest tokens.

**Cumulative file tracking** works across nested branch summaries the same way as compaction.

---

## Core trick 4 — Agent loop: steer vs follow-up (not one queue)

**Source:** `packages/agent/src/agent.ts`, `agent-loop.ts`

| API | When delivered | Use |
|-----|----------------|-----|
| `steer()` | Mid-run, checked between tool batches | Redirect while tools execute |
| `followUp()` | After agent would stop (no more tools) | Next user turn without blocking tools |
| Modes | `one-at-a-time` (default) or drain-all | Ordering under concurrency |

`prompt()` / `continue()` throw if already streaming — no silent concurrent prompt races.  
`shouldStopAfterTurn` — exit before polling queues (scripted/eval runs).

When steer arrives mid tool list, remaining tools in that assistant message can be **skipped with error tool results** (queued-message steering) — saves useless tool work after user redirect.

---

## Newest tricks (HEAD ~0.83, late July → 2026-08-01)

From `CHANGELOG` + recent commits on the clone:

### A. Session storage overhaul (hottest recent work)

Commits around `#7398–#7431`:

- **Per-session store queues** — serialize mutations per session id.
- **Storage-owned session readers** — construction restricted to repositories.
- **Linear-time SQLite session ops** — fix scaling on large session trees.
- **SQLite branch cache (scalable)** — branch path materialization without O(n²) walks.
- Avoid counting all entries on session open — open stays cheap.

**Steal framing:** long-running agent state is a **database problem**, not “append JSONL forever and hope.” Our agentlogs thrash class is the same family.

### B. Remote session stack (new product surface)

- `pi-protocol`: CBOR schemas + length-prefixed framing.
- `pi-client`: transport-neutral client (`ByteTransport`), frame limits, ordered send under backpressure.
- `pi-server`: composable protocol server.
- Coding-agent **remote client controller** + ownership/lifecycle tests.

This is multi-client / headless coordination — closer to Omnigent “one session, many surfaces” than to our local Claude Code setup.

### C. Compaction hardening (0.81–0.82)

- Fresh routing session + **cacheRetention: none** on summary calls.
- Retry policy + lifecycle events for summarization stream drops.
- Messages queued during compaction preserve steer/follow-up semantics.

### D. Constrained tool sampling (0.82)

Tools can prefer/require **strict JSON Schema** or OpenAI Lark/regex grammars; model capability flags gate unsupported requests. Reduces tool-arg corruption (they already fail whole tool batch if assistant `stopReason === "length"` — truncated args never execute).

### E. Supply-chain / model catalog discipline

Exact-pinned deps, shrinkwrap, `--ignore-scripts` installs, ETag revalidation of provider catalogs, lifecycle-script allowlist. Industrial packaging, not agent IQ — still a mature harness signal.

### F. Extension / streaming input model

`InputEvent.streamingBehavior` distinguishes idle prompts vs mid-stream steers vs queued follow-ups — extensions can react without guessing.

---

## Why Databricks saw ~3× less context (mechanism-level)

Not magic model weights. Convergent causes visible in code:

1. **Aggressive keep-tail + structured summary** instead of full history re-feed.
2. **Small default tool schema** (4 tools) vs CC’s large always-on tool/skill surface.
3. **Hard caps on tool payload** in the context path (50KB/2k lines live; 2k chars in summarizer).
4. **No permission-dialog / huge system scaffold** (tradeoff: weaker sandbox).
5. **Faster task completion** (fewer turns) compounds — less cumulative re-feed.

We still have **not** metered this on our repos (`harness_cost_meter` remains the instrument).

---

## What to steal into *our* stack (updated ranking)

| Priority | Steal | How here | Don’t |
|----------|-------|----------|-------|
| **P0** | Structured compact body (Goal/Progress/Decisions/Files) | PreCompact / checkpoint consumers; not free-form prose | Replace CC compact entirely |
| **P0** | Meter tokens/turn + $/task | `harness_cost_meter` on fixed tasks | Trust blog 3× unmeasured |
| **P1** | Summarizer-input tool truncation (2k) | Only if we own a summarizer path | Global PostToolUse 2k |
| **P1** | Overflow = compact + **one** auto-retry | Agent-loop policy when providers return context_length | Infinite compact loops |
| **P1** | Cumulative read/modified file lists in compact artifacts | Attach to checkpoint / session receipt | |
| **P2** | steer vs followUp semantics | Separate mid-run redirect from post-turn queue | One undifferentiated queue |
| **P2** | Fail tools if assistant hit length mid tool-calls | Guard truncated tool args | Execute borked JSON |
| **P2** | File mutation queue by realpath | Any parallel edit runners | |
| **P3** | Session tree + branch summary | Worktree-heavy multi-agent (arc-agi) | Full Pi migration |
| **P3** | SQLite/linear session storage lessons | agentlogs scaling | |
| **Skip** | Pi as RSI home | | Lose hooks/skills/fail-closed |
| **Skip** | No-permission default | | Against our invariants |

---

## What not to overclaim

- Pi is **not** “4 tools only” in absolute terms — grep/find/ls exist; **coding preset** is four.
- Branch/session storage work is about **scale/correctness**, not the Databricks cost claim.
- Remote CBOR stack is for multi-client Pi, not a required learning for local CC.
- Compaction quality still depends on the summarizer model — structured format is the contract, not a free lunch.

---

## Clone map (for future agents)

```
/Volumes/2TBPNY/projects-offload/best/pi   # a116523, 2026-08-01
  packages/coding-agent/src/core/compaction/   # the money
  packages/coding-agent/src/core/tools/        # truncate + mutation queue
  packages/coding-agent/src/core/agent-session.ts  # overflow recovery
  packages/agent/src/agent-loop.ts             # steer/followUp
  packages/coding-agent/docs/compaction.md
  packages/coding-agent/docs/session-format.md
  packages/coding-agent/CHANGELOG.md           # newest features by release
```

Refresh: `git -C /Volumes/2TBPNY/projects-offload/best/pi pull`

---

## Verdict

Pi’s efficiency edge is **implemented**, not rhetorical: tree sessions + keep-recent cut rules + structured iterative summaries + dual-layer tool truncation + tiny default tool surface + overflow compact-once-retry. Newest work (0.81–0.83) hardens that core (cache-free summary calls, retries) and scales **session storage** (SQLite linear ops, branch cache) while growing a **remote protocol** layer.

For agent-infra: steal **contracts and cut rules**, not the product. Highest ROI remains structured compact artifacts + task-level cost metering + never re-feed summarizer-scale tool dumps into long context.

### Sources

- Local clone HEAD `a116523` (earendil-works/pi)
- `packages/coding-agent/docs/compaction.md`, `session-format.md`, `CHANGELOG.md` (0.81–0.83)
- Source files cited inline above
- Databricks blog (workload claim, unreplicated here): https://www.databricks.com/blog/benchmarking-coding-agents-databricks-multi-million-line-codebase
- Prior: `research/2026-07-09-databricks-pi-harness.md`
