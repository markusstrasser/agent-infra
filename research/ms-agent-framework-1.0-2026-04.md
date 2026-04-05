---
title: "Microsoft Agent Framework 1.0 — Architecture Deep Dive"
date: 2026-04-05
tags: [agent-framework, microsoft, claude-code-sdk, multi-agent, middleware, skills, a2a, declarative-agents]
tier: Standard
---

## Microsoft Agent Framework 1.0 — Architecture Deep Dive

**Question:** What does MS Agent Framework 1.0 offer vs our personal agent infrastructure, and specifically how does their Claude Code SDK integration work?

**Tier:** Standard | **Date:** 2026-04-05

**Ground truth:** We run Claude Code as primary harness via Anthropic's Agent SDK (`claude_code_sdk`), with a custom Python orchestrator (`scripts/orchestrator.py`), file-based skills (`~/Projects/skills/SKILL.md`), CC hooks (PreToolUse/PostToolUse/Stop), and MCP servers for tools. No multi-provider orchestration. No declarative agent definitions.

**Primary sources:** Blog post (devblogs.microsoft.com/agent-framework), GitHub repo source code (microsoft/agent-framework, `_agent.py`, `_middleware.py`, `_skills.py`), pyproject.toml, YAML samples.

---

### 1. Architecture Overview

Microsoft Agent Framework 1.0 (released April 2, 2026) unifies Semantic Kernel's enterprise SDK with AutoGen's multi-agent orchestration into a single open-source framework. 8,892 GitHub stars. Python + .NET dual implementations. 24 Python packages spanning core agent primitives, provider integrations (OpenAI, Anthropic, Bedrock, Gemini, Ollama, GitHub Copilot), workflow orchestration, memory backends (Mem0, Redis, Neo4j), a declarative YAML layer, A2A protocol support, and a browser-based DevUI.

The key architectural insight: **agents are pluggable providers behind a common `BaseAgent` interface**, with orchestration patterns (sequential, concurrent, handoff, group chat, Magentic-One) composed on top. Middleware intercepts execution at every stage. Tools flow through MCP or custom FunctionTool definitions. This is an SDK for building agent systems, not an opinionated harness.

### 2. Claude Code SDK Integration (Main Section)

**Package:** `agent-framework-claude` v1.0.0b260402 (beta, not GA)
**Dependency:** `claude-agent-sdk>=0.1.36,<0.1.49` (Anthropic's official SDK)
**Source file:** `python/packages/claude/agent_framework_claude/_agent.py` (818 lines)

#### How It Works

`ClaudeAgent` wraps the Anthropic `ClaudeSDKClient` — the same library that Claude Code uses internally. It does **not** use subprocess to shell out to the CLI binary. The integration path is:

```
ClaudeAgent (AF wrapper)
  -> ClaudeSDKClient (from claude_agent_sdk)
    -> Claude Code CLI process (spawned by SDK as child process)
      -> Anthropic API
```

The `ClaudeSDKClient` manages a persistent connection to a Claude Code CLI instance. The AF wrapper handles:

1. **Lifecycle:** `connect()`/`disconnect()` via async context manager
2. **Query dispatch:** `await self._client.query(prompt)` sends user messages
3. **Streaming:** `async for message in self._client.receive_response()` yields `StreamEvent`, `AssistantMessage`, or `ResultMessage` objects
4. **Session management:** Session IDs track multi-turn conversations; `resume_session_id` reconnects to existing sessions
5. **Tool bridging:** AF `FunctionTool` instances are converted to `SdkMcpTool` objects and served through an in-process MCP server named `_agent_framework_tools`

#### Exposed Capabilities

From `ClaudeAgentOptions` (TypedDict with 25+ fields):

| Capability | How exposed | Notes |
|------------|-------------|-------|
| Built-in tools | String list: `"Read"`, `"Write"`, `"Bash"`, `"Edit"`, `"Glob"`, `"Grep"` | Passed directly to SDK |
| Custom tools | `FunctionTool` -> `SdkMcpTool` via in-process MCP | Pydantic models for schemas |
| MCP servers | `mcp_servers: dict[str, McpServerConfig]` | External MCP servers |
| Permission modes | `"default"`, `"acceptEdits"`, `"plan"`, `"bypassPermissions"` | Runtime-changeable |
| Model selection | `"sonnet"`, `"opus"`, `"haiku"` | Runtime-changeable |
| Fallback model | `fallback_model: str` | If primary fails |
| Budget limits | `max_budget_usd: float` | Per-agent |
| Turn limits | `max_turns: int` | Per-agent |
| Hooks | `hooks: dict[str, list[HookMatcher]]` | CC hook system passthrough |
| Sandbox | `SandboxSettings` | Bash isolation |
| Agents (sub-agents) | `agents: dict[str, AgentDefinition]` | CC agent definitions |
| Structured output | `output_format: dict[str, Any]` (JSON schema) | Via `ResultMessage.structured_output` |
| Extended thinking | `ThinkingConfig` | adaptive/enabled/disabled |
| Effort level | `"low"`, `"medium"`, `"high"`, `"max"` | Thinking depth |
| Plugins | `list[SdkPluginConfig]` | CC plugin configs |
| Settings sources | `list[SettingSource]` | `"user"`, `"project"`, `"local"` |
| File checkpointing | `enable_file_checkpointing: bool` | Rewind support |
| Betas | `list[SdkBeta]` | Beta feature flags |

#### Key Implementation Details

**Tool bridging pattern:** Claude Code only supports tools via MCP. When you pass Python `FunctionTool` instances, the wrapper creates an in-process MCP server (`_agent_framework_tools`) and registers them as `SdkMcpTool` objects. Tool names follow the `mcp__{server}__{tool}` convention. This is notable because it means **all external tools must flow through MCP** — there is no direct function-call path.

**Streaming architecture:** The `_get_stream` method processes three message types:
- `StreamEvent` with `content_block_delta` -> yields text or thinking content
- `AssistantMessage` -> checks for API errors (auth, billing, rate limit, server)
- `ResultMessage` -> captures `session_id` and `structured_output`

**Session resumption:** Each `run()` call checks if the requested session differs from the current one. If so, it disconnects and creates a new `ClaudeSDKClient` with `resume=session_id`. This enables multi-turn conversations across separate `run()` invocations.

**Telemetry:** `ClaudeAgent` (recommended class) extends `RawClaudeAgent` with `AgentTelemetryLayer` for OpenTelemetry instrumentation. No additional logic — just OTel spans wrapping the base methods.

#### Limitations

1. **Beta status** — version `1.0.0b260402`, not GA. The SDK version constraint (`<0.1.49`) means it's tracking a fast-moving target.
2. **Rich content omission** — tool results support text only. Images, audio, and URI content types log a warning and are silently dropped.
3. **No compaction passthrough** — `compaction_strategy` and `tokenizer` kwargs are accepted but not used by `ClaudeAgent` (Claude Code handles its own compaction).
4. **Single-model-per-agent** — no built-in routing to different models within a single agent (you'd compose multiple agents for that).
5. **No native cost tracking** — budget enforcement is delegated to the SDK/CLI level. The AF doesn't surface token counts or cost data back to the orchestrator.

#### Comparison to Our Infrastructure

| Aspect | Our setup | MS Agent Framework |
|--------|-----------|-------------------|
| SDK version | `claude_code_sdk` (latest, direct) | `claude-agent-sdk>=0.1.36,<0.1.49` (pinned range) |
| Tool definition | CC's native tools + MCP servers | AF `FunctionTool` -> MCP bridge + CC native tools |
| Hooks | CC hooks in `.claude/settings.json` | CC hooks passthrough via `hooks` option |
| Multi-provider | No (CC only) | Yes (7 providers) |
| Orchestration | Custom `orchestrator.py` (cron + queue) | Sequential/concurrent/handoff/group-chat/Magentic-One |
| Middleware | None (hooks are closest) | Full pipeline with `AgentContext` |
| Declarative config | No | YAML agent/workflow definitions |
| Telemetry | Custom scripts (dashboard.py, runlog.py) | OpenTelemetry native |
| Session management | File-based session IDs | SDK-managed session objects |

### 3. Declarative Agents + Skills

#### YAML Schema (from samples)

**Simple agent:**
```yaml
kind: Prompt
name: Assistant
description: Helpful assistant
instructions: You are a helpful assistant.
model:
    id: =Env.AZURE_FOUNDRY_PROJECT_MODEL_ID
    options:
        temperature: 0.9
        topP: 0.95
    connection:
        kind: remote
        endpoint: =Env.AZURE_FOUNDRY_PROJECT_ENDPOINT
outputSchema:
    properties:
        language:
            kind: string
            required: true
        answer:
            kind: string
            required: true
```

**Tool-equipped agent:**
```yaml
tools:
  - kind: function
    name: GetWeather
    description: Get the weather for a given location.
    bindings:
      get_weather: get_weather
    parameters:
      properties:
        location:
          kind: string
          description: The city and state
          required: true
```

**Workflow (Magentic-One pattern):**
The `DeepResearch.yaml` (280+ lines) defines a full multi-agent workflow with:
- `kind: Workflow` with `maxTurns: 500`
- `kind: OnConversationStart` trigger
- `SetVariable`/`SetTextVariable` for state management
- `InvokeAzureAgent` for agent delegation with named agents
- `ConditionGroup` for branching logic (if done, if stalling, stall count exceeded)
- `GotoAction` for loops
- Built-in stall detection (progress ledger, stall count, restart count)
- Fact-sheet and plan-revision loops on failure

The workflow YAML is essentially a visual programming language — it has variables, conditions, loops, and agent invocations. It is Azure-centric (references `InvokeAzureAgent`, `AzureOpenAI`). No Claude agent YAML sample exists yet.

#### Skills System

Their skills implementation (`_skills.py`, ~57KB) matches our SKILL.md pattern remarkably closely:

| Feature | MS Agent Framework | Our system |
|---------|-------------------|------------|
| Discovery | Scan directories for `SKILL.md` files | Same |
| Format | Markdown (SKILL.md) with frontmatter | Same |
| Progressive disclosure | 3-level: advertise (name+desc in prompt) -> load (full body via tool) -> read resources (on demand) | 2-level: loaded by CC when relevant (name+desc -> full body) |
| Resources | `SkillResource` — static content or async callable | `references/` subdirectory with markdown files |
| Scripts | `SkillScript` — inline function or file path | Shell scripts in `scripts/` subdirectory |
| Security | XML-escape metadata, path traversal guard, symlink escape guard | Trust-based (local-only) |
| Code-defined | `@skill.resource` decorator for dynamic resources | Not supported |
| Spec reference | `agentskills.io` | Our own convention |

Key differences:
1. **Code-defined skills** — they support creating skills entirely in Python with `@skill.resource` decorators. Our skills are file-only.
2. **Script execution** — `SkillScript` has a `SkillScriptRunner` for executing scripts with parameter schemas. Our scripts are invoked by the agent via Bash.
3. **Security hardening** — XML-escape on prompt injection, path traversal guards. We don't have these because our skills are all local/trusted.
4. **Still experimental** — `@experimental(feature_id=ExperimentalFeature.SKILLS)` decorator on all skill classes.
5. **agentskills.io** — they reference an external spec site. This suggests a push toward an interoperable skills standard.

### 4. Middleware Hooks

The AF middleware system (`_middleware.py`, ~58KB) is fundamentally different from CC hooks:

**CC hooks:** Event-driven (PreToolUse, PostToolUse, Stop), defined in JSON, execute as shell commands or prompt-based LLM calls. Fire on specific tool events. Cannot modify the request or response — they can only block or advise.

**AF middleware:** Pipeline-based (Django/Express style). Each middleware gets an `AgentContext` with full access to:
- `context.agent` — the agent instance
- `context.messages` — input messages (mutable)
- `context.session` — session state
- `context.tools` — tool overrides
- `context.options` — runtime options
- `context.metadata` — cross-middleware shared state
- `context.result` — output (observable after `call_next()`, settable to override)
- `context.stream_transform_hooks` — hooks to transform streaming updates
- `context.stream_result_hooks` — hooks on final result
- `context.stream_cleanup_hooks` — cleanup after streaming

**Three middleware types:**
1. `AgentMiddleware` — wraps agent execution (input -> output)
2. `FunctionMiddleware` — wraps tool invocation
3. `ChatMiddleware` — wraps LLM API calls

**Termination:** `MiddlewareTermination` exception allows early exit with an optional result, skipping downstream processing.

| Aspect | CC Hooks | AF Middleware |
|--------|----------|---------------|
| Execution model | Event-driven (fire on trigger) | Pipeline (wrap execution) |
| Can modify input | No | Yes (mutable `context.messages`) |
| Can modify output | No | Yes (set `context.result`) |
| Can block | Yes (exit code) | Yes (`MiddlewareTermination`) |
| Scope | Tool-level events | Agent/function/chat levels |
| Definition | JSON + shell/prompt | Python classes |
| Streaming support | No | Yes (transform/result/cleanup hooks) |
| Cross-middleware state | No | `context.metadata` dict |

**Assessment:** AF middleware is strictly more powerful than CC hooks. It can do everything hooks do plus modify inputs/outputs and share state. However, CC hooks have the advantage of being language-agnostic (shell commands) and declarative (JSON config). For our use case (personal infrastructure, single user), CC hooks are sufficient. AF middleware would matter if we needed input/output transformation or cross-middleware state sharing.

### 5. A2A Interop

The `agent-framework-a2a` package implements the Google A2A protocol (standardized agent-to-agent communication). From the README: "enables communication with remote A2A-compliant agents using the standardized A2A protocol."

**What's real:**
- Package exists with `_agent.py` implementation
- Connects to remote A2A-compliant agents
- Supports text, attachments, structured content
- Streaming responses
- Samples in `python/samples/04-hosting/a2a/`

**What's aspirational:**
- No discovery mechanism documented in visible code
- Message format details not exposed in README
- "A2A 1.0 support coming soon" in the blog post (despite the package existing)
- No Claude-to-Claude A2A sample

**Assessment:** A2A is real infrastructure but early. For us, MCP is the interop layer and will remain so. A2A matters for enterprise scenarios where agents from different vendors need to collaborate. Not relevant to our single-user, single-provider setup.

### 6. DevUI Patterns

The `devui` package provides a browser-based visualization tool for:
- Agent execution flows
- Message sequences
- Tool call chains
- Orchestration decisions

The blog post includes an embedded video (`devui6_720p.mp4`) showing the interface, but specific implementation details aren't in the source tree beyond the package skeleton.

**Also:** `ag-ui` package for frontend adapters (CopilotKit, ChatKit) with streaming, tool status, and human-in-the-loop approval flows.

**Comparison to our dashboard:** Our `scripts/dashboard.py` shows operational metrics (costs, run counts, errors). The AF DevUI shows execution traces — a fundamentally different view. The trace visualization (message flow, tool calls, orchestration decisions) would be valuable for debugging our multi-agent sessions. We don't have anything equivalent.

**Extractable pattern:** Execution trace visualization with message-level granularity. Our `sessions.py` has FTS5 search over session content but no visual trace view.

### 7. Patterns to Extract vs Patterns to Ignore

#### Extract (worth adopting)

1. **Tool bridging via in-process MCP** — Their pattern of converting `FunctionTool` -> `SdkMcpTool` via a local MCP server is clean. We already use MCP servers, but the "bridge arbitrary Python functions into MCP" pattern could be useful for custom tools without writing full MCP servers.

2. **Progressive skill disclosure (3-level)** — Their advertise -> load -> read-resources pattern is more granular than our 2-level approach. The "read resources on demand" level could reduce initial context consumption for skills with large reference material. [SOURCE: `_skills.py` docstring]

3. **Structured output passthrough** — `output_format` as JSON schema + `ResultMessage.structured_output` gives type-safe outputs from Claude Code. We don't use this. [SOURCE: `_agent.py` lines 157-158, 720-722]

4. **Workflow stall detection** — The DeepResearch YAML has a progress ledger with stall counting, restart limits, and fact-sheet revision on failure. This is a sophisticated failure recovery pattern. Our orchestrator has retry logic but no progress assessment or plan revision.

5. **Session resumption** — Their `resume_session_id` mechanism for reconnecting to existing CC sessions could replace our file-based session ID tracking.

#### Watch (interesting but not yet actionable)

6. **Declarative YAML agents** — Good for reproducibility and version control, but the schema is Azure-centric and no Claude sample exists. Watch for a provider-agnostic schema.

7. **agentskills.io** — If this becomes a cross-vendor skill standard, we should align. Currently vaporware.

8. **A2A protocol** — Not relevant until we need multi-provider agent collaboration.

#### Ignore (not relevant to our setup)

9. **Multi-provider orchestration** — We use Claude Code exclusively. Provider abstraction adds complexity without benefit.

10. **Azure/Foundry integration** — Enterprise cloud services. Not applicable.

11. **AG-UI / CopilotKit** — Frontend adapters for web apps. We use CLI.

12. **Magentic-One workflow YAML** — The visual-programming-language approach to workflows is overengineered for our needs. Our `orchestrator.py` with direct Python is simpler and more flexible.

### 8. Component Verdicts

| Component | Verdict | Rationale |
|-----------|---------|-----------|
| Claude Code SDK wrapper | **Watch** | Clean implementation but adds a layer over SDK we use directly. No capability gain. Beta status. |
| Tool -> MCP bridge | **Extract** | Pattern is useful: convert Python functions to MCP tools without writing server boilerplate. |
| Progressive skill disclosure | **Extract** | 3-level pattern reduces context waste. Add `read_skill_resource` tool to our system. |
| Structured output | **Extract** | JSON schema output format + typed results. We should use this via claude_code_sdk directly. |
| Middleware pipeline | **Watch** | Strictly more powerful than CC hooks, but our hooks are sufficient. Revisit if we need input/output transformation. |
| Workflow stall detection | **Extract** | Progress ledger + stall counting + plan revision. Implement in orchestrator.py. |
| Session resumption | **Extract** | `resume_session_id` via SDK. Replace file-based session tracking. |
| Declarative YAML agents | **Ignore** | Azure-centric, no Claude support, visual-programming complexity. |
| A2A protocol | **Ignore** | Single-provider setup. No benefit. |
| DevUI trace visualization | **Watch** | Execution trace view would be valuable but building our own is premature. |
| OTel integration | **Watch** | Good pattern but our custom telemetry (runlog, dashboard) is sufficient at current scale. |

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | AF Claude integration uses claude-agent-sdk, not subprocess | pyproject.toml dependency + source code imports | HIGH | [GitHub source] | VERIFIED |
| 2 | SDK version pinned to 0.1.36-0.1.49 | pyproject.toml | HIGH | [GitHub source] | VERIFIED |
| 3 | Custom tools bridged through in-process MCP server | `_prepare_tools()` creates `SdkMcpTool` via `create_sdk_mcp_server()` | HIGH | [GitHub source, lines 452-479] | VERIFIED |
| 4 | Skills system references agentskills.io spec | `_skills.py` docstring | HIGH | [GitHub source] | VERIFIED |
| 5 | 3-level progressive disclosure (advertise/load/read) | `_skills.py` docstring lines 8-12 | HIGH | [GitHub source] | VERIFIED |
| 6 | Rich content (images/audio) silently dropped in tool results | `_function_tool_to_sdk_mcp_tool()` handler, line 504-507 | HIGH | [GitHub source] | VERIFIED |
| 7 | Middleware can modify both input and output | `AgentContext` with mutable messages + settable result | HIGH | [GitHub source] | VERIFIED |
| 8 | A2A uses Google's standardized protocol | README states "standardized A2A protocol" | MEDIUM | [GitHub README] | PARTIAL — specific version/spec not confirmed |
| 9 | 8,892 GitHub stars | `gh api` query | HIGH | [GitHub API] | VERIFIED |
| 10 | Framework released April 2, 2026 | Blog post date April 3 + pyproject version suffix 260402 | HIGH | [Blog + source] | VERIFIED |

### What's Uncertain

1. **ClaudeSDKClient internals** — The AF uses `ClaudeSDKClient` from `claude_agent_sdk`, which itself spawns a Claude Code CLI process. The exact IPC mechanism (stdio JSON-RPC? WebSocket?) between SDK and CLI is not visible in AF source.

2. **agentskills.io** — Referenced in source but the site may not be public yet. Could be an internal MS initiative or a genuine cross-vendor effort.

3. **DevUI capabilities** — Only a video demo and package skeleton visible. Actual trace visualization features unknown.

4. **Declarative Claude support** — No Claude YAML sample exists. The declarative layer may not support Claude agents yet (all samples are Azure/OpenAI/Foundry).

5. **Performance overhead** — The MCP bridge for custom tools adds serialization. Unknown if this introduces meaningful latency for tool-heavy workloads.

### Search Log

| Tool | Query | Result |
|------|-------|--------|
| WebFetch | MS blog post (1.0 announcement) | Architecture overview, all components listed |
| gh api | Repo metadata | 8892 stars, Python, created 2025-04-28 |
| Exa | "Microsoft Agent Framework Claude Code SDK" | 10 results, found Claude integration blog post + community tutorials |
| Brave | "Microsoft Agent Framework 1.0 Claude Code SDK" | 10 results, confirmed blog posts + GitHub releases |
| WebFetch | Claude SDK integration blog post | High-level integration details, code samples |
| WebFetch | GitHub repo main page | Package listing (24 packages) |
| gh api | pyproject.toml (claude package) | Dependency: `claude-agent-sdk>=0.1.36,<0.1.49` |
| gh api | `_agent.py` source (818 lines) | Full ClaudeAgent implementation — the critical source |
| gh api | `_middleware.py` source (58KB) | Full middleware pipeline implementation |
| gh api | `_skills.py` source (57KB) | Full skills system with progressive disclosure |
| gh api | YAML samples (3 files) | Declarative agent + workflow schema |
| gh api | Sample: anthropic_claude_with_tools.py | Usage example for built-in tools |

<!-- knowledge-index
generated: 2026-04-05T23:11:06Z
hash: 22aa0c7f9e07

title: Microsoft Agent Framework 1.0 — Architecture Deep Dive
tags: agent-framework, microsoft, claude-code-sdk, multi-agent, middleware, skills, a2a, declarative-agents
table_claims: 10

end-knowledge-index -->
