# Vercel AI SDK for Python (`vercel-labs/ai-python`) — code deep-dive

**Date:** 2026-07-19 · **Version read:** v0.3.0 (public beta, released 2026-07-16), ~18.4K lines src
**Verdict: NO-ADOPT as dependency (unchanged from same-day triage); HARVEST 3 design patterns as references.**
Read: `agents/agent.py`, `agents/hooks.py`, `agents/_middleware.py`, `agents/runtime.py`, `types/events.py`, `providers/base.py`, `util.py` (primary, full files).

## What the codebase actually is

Not a thin OpenAI-wrapper. A serverless-replay-oriented agent runtime where *everything* —
messages, events, providers, hook state — is pydantic-serializable so a run can be
suspended, shipped over a wire, and resumed in a fresh process. The TS AI SDK's UI
protocol (`ui/ai_sdk/`) is a bridge layer on top; the core is the replayable loop.
Code quality is high: comment discipline explains *why* (GC-traversal workarounds,
asyncio contextvar semantics), tests cover the resume paths, typing is modern
(PEP 695, ParamSpec overloads).

## The three abstractions worth harvesting (pattern-level, not dependency)

### 1. Hooks = suspension points with a two-mode registry (`agents/hooks.py`)

`await ai.hook(label, payload=PydanticModel)` suspends the run. Resolution has two modes:
- **live**: `resolve_hook(label, data)` completes an `asyncio.Future` → run continues in-process;
- **pre-registered (serverless re-entry)**: no live hook yet → resolution is stashed; on
  *replay* of the serialized transcript, `hook()` finds it and returns without suspending.

The supporting discipline is the deep part: a deferred tool call still emits a
**placeholder `ToolResultPart(is_hook_deferred=True)`** so the transcript stays
well-formed (every tool_call paired with a result), and `_process_interrupted_hooks`
(`agent.py:86`) recognizes the interrupted tail shapes and marks messages `replay=True`
so completed sibling calls short-circuit to `cached_result` while suspended ones re-run.

**Relevance to us:** this is the in-process formalization of our "escalation is a file,
never a block" rule — suspend, serialize the ask, resume on async answer. We do it at
process level (HUMAN.md + fresh session); they do it at transcript level. If we ever
build a long-lived in-process agent service (Modal-hosted worker, Telegram approval bot
in ideas.md), this is the reference design for approval gates: **placeholder-result +
replay-flag + pre-registered resolution**, not "poll a flag."

### 2. Blocked-state as a pure fold over the event stream (`types/events.py` RunStateTracker)

"Is the run blocked awaiting human input?" is never a flag someone sets — it's derived:
fold every event; blocked ⟺ ≥1 deferred hook ∧ no model stream active ∧ every in-flight
tool_call_id attributed to a deferred hook. Works identically over a live run or a
serialized replay. Deliberate asymmetry: `RunBlocked` has no mirror unblock event because
the next non-pending HookEvent *is* the unblock signal.

**Relevance:** direct instance of our state-externalization lens (Harness-1) and
epistemic principle #10 (transcript is truth, summaries are proxies) — status fields
derived from the event log by a replayable fold, never stored beside it. Cosigns
agentlogs' architecture; the fold-with-attribution trick (in_flight ⊆ attributed) is a
reusable idiom for any "is this pipeline stalled on X" derivation.

### 3. Two-plane tool results via Aggregators on return-type annotations (`agent.py`)

Async-generator tools declare an aggregator in the *type*:
`type SubAgentTool = Annotated[AsyncGenerator[AgentEvent], Aggregate(MessageAggregator)]`.
Intermediate yields stream to the consumer (`PartialToolCallResult`); the aggregator
separates **snapshot** (rich shape stored/shown to UI) from **to_model_input** (what the
LLM sees next turn). Sub-agent-as-tool = the parent model sees only final text, the
consumer sees every event, and the split survives wire round-trips (`to_model_input` is
a classmethod, re-derivable without a live instance).

**Relevance:** this is our subagent output convention ("write file + return path +
≤10-line verdict") made structural — the rich-artifact plane vs the model-context plane
as a typed contract instead of a briefing rule. Reference if we ever formalize
subagent-return contracts in code.

## Noted, not harvested

- **Middleware over 5 surfaces** (run/model/generate/tool/hook), contextvar-scoped,
  zero-cost when empty; nested runs *extend* the parent stack. Clean, conventional.
- **`util.merge(restart=True)`** — merges model-stream + tool-result-stream where yielding
  a value can *re-arm* an exhausted peer stream (tool results trigger the next model
  turn). Plus `MultiWaiter` (add-while-waiting, completion order preserved — deliberately
  batch-free for Temporal determinism) and `TaskGroupGenExit` (GeneratorExit ∧
  ExceptionGroup dual-inheritance so aclose() through a TaskGroup doesn't drop errors).
  Careful asyncio plumbing worth pointing an agent at when writing merge-style loops.
- **Provider/Protocol split** with pydantic polymorphic serialization via class-id
  registries; model catalog from models.dev. Serializable providers serve the durable-
  execution goal; wrapping our subscription CLIs (claude-cli/codex) as a Provider is
  possible but loses the granularity the design exists for. Not worth it.

## Why still NO-ADOPT

1. **Transport gap is structural:** the SDK's value is provider-abstracted *metered API*
   calls (AI Gateway default). It cannot route our $0 subscription-CLI lanes, which is
   the binding constraint of our routing policy. llmx keeps the dispatch layer.
2. **No in-process consumer today:** our agent execution is CLI-dispatch + file-bus;
   programmatic loops are Claude-only (Agent SDK, subscription). Pre-Build #3.
3. **Beta churn:** `_middleware.py` header admits middleware is "dead code under the new
   Executor-based api.py, kept so the agents rewrite can land separately" — the core is
   mid-rewrite at v0.3.0.

## Resurrection triggers

- We build a long-lived in-process Python agent (Modal service, approval-bot backend)
  → re-evaluate as dependency; at minimum copy the hook/replay design (§1).
- Fable/Opus off subscription permanently + metered API becomes our norm → the transport
  gap closes; re-run the dependency evaluation.
- Formalizing subagent return contracts in code → use §3 as the reference shape.
