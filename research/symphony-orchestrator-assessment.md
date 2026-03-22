# Symphony (OpenAI) — Deep Assessment

**Date:** 2026-03-07
**Source:** github.com/openai/symphony (8.7K stars, Apache 2.0)
**Status:** "Low-key engineering preview for testing in trusted environments"

## What Symphony Is

A long-running daemon that polls an issue tracker (Linear), creates isolated per-issue workspaces, and runs Codex (OpenAI's coding agent) in app-server mode against each issue. The repo ships a **language-agnostic spec** (SPEC.md, ~1500 lines) and an **Elixir/OTP reference implementation**.

Key framing: "Move from managing coding agents to managing work." The human manages a Linear board; Symphony turns tickets into autonomous agent runs.

## 1. Implementation Runs — Task/Step Model

An "implementation run" is one agent session for one Linear issue. It is **not** a multi-step pipeline — it's a single Codex invocation with a rendered prompt that tells the agent what to do (the WORKFLOW.md body). The agent itself handles all the steps (planning, coding, testing, PR creation, state transitions) via tools.

**Run attempt lifecycle phases:**
`PreparingWorkspace → BuildingPrompt → LaunchingAgentProcess → InitializingSession → StreamingTurn → Finishing → Succeeded|Failed|TimedOut|Stalled|CanceledByReconciliation`

**Multi-turn within a run:** After each turn completes, the worker checks if the issue is still in an active state. If yes, it sends a continuation prompt on the same thread (up to `max_turns`, default 20). After all turns exhaust, the orchestrator schedules a 1-second continuation retry to check again.

**Comparison to our orchestrator:** Our model is a multi-step pipeline (`pipelines/*.json`) where each step is a separate `claude -p` invocation or subprocess. Symphony has no pipeline concept — each issue = one agent session. The multi-step logic lives entirely in the WORKFLOW.md prompt (the agent decides what steps to take). This is a fundamentally different decomposition.

## 2. Fault Tolerance

**BEAM/OTP supervision:**
- Orchestrator is a `GenServer` (single process, serialized state mutations)
- Agent workers are spawned as monitored `Task`s — the orchestrator receives `{:DOWN, ref, :process, pid, reason}` messages
- No explicit supervision tree beyond this — the orchestrator monitors workers directly

**Process isolation:**
- Each issue gets its own workspace directory (filesystem isolation)
- Each agent runs as a separate OS subprocess (`Port.open` spawning `bash -lc codex app-server`)
- Workspace paths are validated against the root (path traversal protection, symlink escape detection)

**Recovery:**
- **No persistent database.** State is purely in-memory. On restart, the orchestrator re-polls Linear and re-discovers active issues. Workspaces survive on disk.
- Terminal workspace cleanup runs at startup (removes workspaces for issues already Done/Closed)
- Stall detection: if no Codex event arrives within `stall_timeout_ms` (default 5 min), kill and retry

**Retry with exponential backoff:**
- Normal completion + still active → 1s continuation retry
- Failure → `min(10000 * 2^(attempt-1), max_retry_backoff_ms)` (default cap: 5 min)

**Comparison to our orchestrator:** Our orchestrator uses SQLite for persistence, which survives restarts but adds complexity. Symphony's "no DB" approach is simpler but means restart loses all in-flight state (retries, token counts, session metadata). Our `fcntl.flock` single-execution is simpler than their GenServer but achieves the same mutual exclusion. Their stall detection is something we lack — our orchestrator doesn't monitor agent liveness during execution.

## 3. Checkpointing and Resumability

Symphony does **not** checkpoint agent state. There is no save/restore of conversation context. Instead:

- Workspaces persist on disk (code changes survive restarts)
- The agent maintains a "Codex Workpad" comment on the Linear issue (external state)
- On retry/continuation, the prompt includes `attempt` number and continuation guidance telling the agent to resume from workspace state rather than start fresh
- The `Rework` flow is a full reset: close PR, delete workpad, fresh branch, start over

**Comparison:** Our orchestrator also doesn't checkpoint agent state — each step is a fresh `claude -p` invocation. But our pipeline model naturally handles resumability: completed steps stay `done`, failed steps get retried. Symphony's single-agent-per-issue model means a failure loses all in-session context. The workpad-on-Linear is a clever workaround — the agent creates its own external checkpoint.

## 4. Agent Supervision Model — Human Oversight

**Minimal human oversight by design.** The philosophy is explicit:
- Approval policy defaults to `never` (auto-approve everything)
- Sandbox defaults to `workspace-write` (agent can only write within its workspace)
- User-input-required = hard failure (agents must be fully autonomous)
- Human review is a Linear board state, not a runtime concept

**The Linear state machine IS the human oversight:**
- `Todo` → agent picks up, moves to `In Progress`
- `In Progress` → agent works autonomously
- `Human Review` → agent stops, waits for human on Linear board
- `Merging` → human approved, agent runs `land` skill to merge
- `Rework` → human rejected, agent starts over from scratch
- `Done` → terminal

**"Proof of work" concept:** Not a formal system — it's in the WORKFLOW.md instructions. The agent must provide: CI green, PR passing checks, validation evidence documented in the workpad, walkthrough media. The human reviews this on the PR before approving `Merging`.

**Comparison:** Our orchestrator has `requires_approval` gates between pipeline steps and a `pause_before` mechanism. Symphony pushes all approval to the Linear board (asynchronous, human-paced). Our model is more granular (step-level approval) but requires more infrastructure. Their model is simpler but coarser — you approve entire issue outcomes, not intermediate steps.

## 5. Multi-Agent Coordination

**Bounded concurrency, no coordination:**
- `max_concurrent_agents` (default 10) — global slot limit
- `max_concurrent_agents_by_state` — per-state limits (e.g., limit how many `Merging` agents run)
- Each agent works on one issue independently — no inter-agent communication
- The orchestrator prevents duplicate dispatch via `claimed` set

**No shared context between agents.** Each workspace is isolated. Agents can't see each other's work. Coordination happens through Linear (blocker relations: if issue A has a non-terminal blocker, it won't be dispatched).

**Comparison:** Similar to our approach — we also run agents independently. We don't have per-state concurrency limits (would be useful for controlling how many research vs. execution tasks run). Neither system has inter-agent coordination, which is consistent with the research finding that multi-agent coordination helps only above 45% individual success rates.

## 6. LLM Provider Support

**Codex only.** The entire system is built around Codex's app-server JSON-RPC protocol over stdio. The spec abstracts this as a "coding agent app-server" but the implementation is tightly coupled to Codex.

Key protocol elements:
- `initialize` → `initialized` → `thread/start` → `turn/start` (JSON-RPC 2.0 over stdin/stdout)
- Approval handling via protocol messages
- Dynamic tool injection (currently just `linear_graphql`)
- Token usage tracking via `thread/tokenUsage/updated` events

**Comparison:** Our orchestrator is agent-agnostic (shell out to `claude -p` or raw subprocess). Symphony's deeper integration with Codex app-server gives it richer telemetry (per-turn token counts, stall detection, live session metadata) at the cost of vendor lock-in.

## 7. Architecture — What's Novel

### Novel concepts worth studying:

1. **WORKFLOW.md as the single configuration surface.** YAML front matter for runtime config + Markdown body as the agent prompt template. Versioned in-repo, hot-reloaded without restart. This is cleaner than our split between `pipelines/*.json` for steps and ad-hoc prompts. The template variables (`{{ issue.identifier }}`, `{{ attempt }}`) with strict rendering (unknown vars = error) is well-designed.

2. **Workpad-as-checkpoint.** The agent creates a persistent Linear comment (`## Codex Workpad`) that serves as both progress tracker and checkpoint. On continuation/retry, the agent reads this comment to understand where it left off. This is a "free" persistence mechanism — no DB needed because the issue tracker stores it.

3. **Active-run reconciliation.** Every poll tick, the orchestrator checks whether running issues are still in active states. If a human moves an issue to `Done` on Linear, the worker is killed immediately. This bidirectional sync (human can intervene at any time by changing issue state) is elegant.

4. **Per-state concurrency limits.** `max_concurrent_agents_by_state: { merging: 1 }` ensures only one agent is trying to land PRs at a time, preventing merge conflicts. Simple mechanism, high value.

5. **Stall detection.** Monitor elapsed time since last agent event. If the agent goes silent for 5 minutes, kill and retry. We don't have this.

6. **Spec-first design.** The SPEC.md is genuinely language-agnostic and thorough enough that you could reimplement in any language. The README literally says "tell your favorite coding agent to build Symphony in a programming language of your choice."

### What's NOT novel (we already have it or better):

1. **Multi-step pipelines.** We have them; Symphony doesn't. Their agent handles everything in one session, which works for code changes but wouldn't work for our research→implement→verify workflows.

2. **Persistent state.** Our SQLite task queue survives restarts; their in-memory state doesn't.

3. **Dual-engine (LLM + script).** We support both `claude -p` and raw subprocess steps. Symphony is Codex-only.

4. **Cost controls.** Our `DAILY_COST_CAP` and per-step `max_budget_usd`. Symphony tracks tokens but doesn't enforce limits.

5. **Dependency chains.** Our `depends_on` between pipeline steps. Symphony has no step dependencies (single-step model).

6. **Scheduled pipelines.** Our `scheduled_runs` table and cron integration. Symphony polls continuously.

## 8. Assessment: What to Adopt

### Worth adopting (concrete value):

| Concept | Value | Maintenance | Composability | Notes |
|---------|-------|-------------|---------------|-------|
| **Stall detection** | High | None (adds to tick()) | High — any orchestrator task | Monitor time since last agent output during `tick()`. Kill and retry if stalled >5min. We've seen agents hang silently. |
| **Per-state concurrency limits** | Medium | None (config addition) | Medium — orchestrator only | Add `max_concurrent_by_pipeline` to prevent e.g. 5 research tasks consuming all budget while blocking morning-prep. |
| **Active-run reconciliation** | Medium | Low (periodic check logic) | Medium — orchestrator only | Our `tick()` should check if running tasks are still relevant (e.g., project state changed). Currently we fire-and-forget. |

### Not worth maintaining (wrong fit, not wrong effort):

| Concept | Why not |
|---------|---------|
| **WORKFLOW.md single file** | Our pipeline JSON + separate prompts is more compositional. Symphony's approach works for single-step but doesn't scale to multi-step. |
| **Workpad-as-checkpoint** | We don't have a Linear board. Our git log + MEMORY.md serves the same purpose. |
| **No-DB in-memory state** | We need persistence across restarts. Their approach is simpler but fragile. |
| **Elixir/BEAM** | The reference implementation uses BEAM features (GenServer, Port, Task monitoring) but nothing that requires BEAM. Our Python orchestrator is fine. |
| **Codex app-server protocol** | Vendor-specific. `claude -p` or Agent SDK is our equivalent. |
| **Linear integration** | We don't use Linear. If we needed a ticket-driven workflow, the spec is a good reference. |

### Interesting but deferred:

| Concept | Why defer |
|---------|-----------|
| **Dynamic workflow reload** | Hot-reloading pipeline config without restart. Nice but not a pain point yet. |
| **HTTP dashboard** | Their Phoenix LiveView dashboard is slick but we have `dashboard.py`. |
| **Spec-first, implement-anywhere** | Writing a spec then having agents implement it is a meta-pattern worth remembering for future infrastructure. |

## 9. Key Architectural Difference

Symphony is a **continuous daemon** that polls a work source and dispatches agents. Our orchestrator is a **cron-triggered tick** that runs one task per invocation. Symphony's model is better for high-throughput (10 concurrent agents on a Linear board). Ours is better for low-throughput, high-value tasks with human oversight gates.

The deepest difference is where complexity lives: Symphony puts complexity in the WORKFLOW.md prompt (the agent figures out what to do), while we put complexity in the pipeline template (we tell the agent exactly what each step does). Symphony's approach requires a more capable agent but gives it more autonomy. Ours is more predictable but more brittle when steps need to adapt.

Neither approach is strictly better. Symphony's is optimized for "turn tickets into PRs" — a well-defined, repeatable workflow. Ours is optimized for diverse task types (research, analysis, code review, entity refresh) where each pipeline has different structure.

<!-- knowledge-index
generated: 2026-03-22T00:13:53Z
hash: 9a4d717460c3


end-knowledge-index -->
