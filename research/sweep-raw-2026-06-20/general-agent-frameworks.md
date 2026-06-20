# Agent / Multi-Agent Framework Scout — 2026-06-20

**Scope:** LangGraph, CrewAI, AutoGen/AG2, Microsoft Agent Framework, OpenAI Agents SDK, Pydantic-AI, Google ADK, Mastra, Agno, smolagents, Atomic Agents, LlamaIndex Workflows.  
**Method:** Exa MCP primary search over official GitHub releases/changelogs/docs. No Brave. Prioritized May-June 2026.

## Ranked Findings

### 1. LangGraph 1.2.x: v3 streaming, DeltaChannel, node timeouts/error recovery
**Primary URL:** https://github.com/langchain-ai/langgraph/releases/tag/1.2.3 and https://docs.langchain.com/oss/python/releases/changelog  
**Date:** 2026-06-01 to 2026-06-18  
**Claim:** LangGraph added v3 typed streaming primitives, RemoteGraph support, subagent naming, checkpoint overhead reduction via `DeltaChannel`, and per-node timeout/error recovery in the 1.2 line.  
**Demonstrated vs asserted:** Demonstrated in release notes and merged PR list; benchmark impact still asserted/unmeasured publicly.  
**Maturity:** GitHub ~34.9k stars; last push 2026-06-16; latest surfaced release 1.2.6 on 2026-06-18.  
**Why it matters locally:** Best steal is the typed event/projection model: local Codex/Claude harnesses should stream structured lifecycle/tool/subagent channels instead of parsing prose logs.

### 2. Google ADK 2.0 GA + 2.2 breaking model/default changes
**Primary URL:** https://github.com/google/adk-python/releases/tag/v2.0.0 and https://github.com/google/adk-python/releases/tag/v2.2.0  
**Date:** 2026-05-19 GA; 2026-06-04 v2.2.0  
**Claim:** ADK 2.0 GA formalizes graph workflows, task delegation, routing, fan-out/fan-in, loops, retry, state, HITL, and nested workflows; v2.2 changes default LLM model and updates for GenAI SDK v2.  
**Demonstrated vs asserted:** GA/API shape demonstrated in official repo; “production-grade” is vendor assertion.  
**Maturity:** GitHub ~20.2k stars; last push 2026-06-19; latest release v2.3.0 on 2026-06-18.  
**Why it matters locally:** The useful pattern is explicit workflow/task separation, not GCP hosting: local harness should keep deterministic workflow state separate from model-agent execution.

### 3. OpenAI Agents SDK 0.16-0.17: local tool concurrency, MCP namespacing, sandbox boundary hardening
**Primary URL:** https://github.com/openai/openai-agents-python/releases/tag/v0.16.0 and https://github.com/openai/openai-agents-python/releases/tag/v0.17.0  
**Date:** 2026-05-07 to 2026-06-19  
**Claim:** SDK added SDK-side local function tool concurrency config, opt-in MCP server-prefixed tool names, disabled max-turn limits via `None`, and tightened sandbox local source materialization.  
**Demonstrated vs asserted:** Demonstrated in official releases; operational robustness still must be measured per harness.  
**Maturity:** GitHub ~27.3k stars; last push 2026-06-19; latest release v0.17.6 on 2026-06-19.  
**Why it matters locally:** Directly relevant: local harnesses need separate knobs for provider parallel tool calls vs local execution concurrency, plus MCP tool namespace collision prevention.

### 4. Mastra 1.38-1.42: native tool suspension, durable harness sessions, per-request sandboxes
**Primary URL:** https://github.com/mastra-ai/mastra/releases/tag/%40mastra%2Fcore%401.42.0 and https://github.com/mastra-ai/mastra/releases/tag/%40mastra%2Fcore%401.41.0  
**Date:** 2026-06-03 to 2026-06-12  
**Claim:** Mastra moved `ask_user`/`submit_plan` onto a native tool-suspension primitive, added durable harness sessions, background-task stream continuity, and per-request sandbox routing.  
**Demonstrated vs asserted:** Demonstrated by changelog/API changes; production value asserted.  
**Maturity:** GitHub ~25.2k stars; last push 2026-06-17; latest core release 1.42.0 on 2026-06-12.  
**Why it matters locally:** Strong steal: represent “ask user / plan approval / resume” as resumable tool suspension keyed by `toolCallId`, not as ad hoc chat state.

### 5. CrewAI 1.14.7 + 1.14.8 alpha: FlowDefinition / JSON-first crews
**Primary URL:** https://github.com/crewAIInc/crewAI/releases/tag/1.14.7 and https://github.com/crewAIInc/crewAI/releases/tag/1.14.8a  
**Date:** 2026-06-11; alpha 2026-06-18  
**Claim:** CrewAI is pushing FlowDefinition metadata, JSON-first crews, `crewai run --definition`, chat API for conversational flows, pluggable backends, and checkpoint/runtime isolation fixes.  
**Demonstrated vs asserted:** Demonstrated in release notes; alpha features not mature.  
**Maturity:** GitHub ~54k stars; last push 2026-06-19; latest prerelease 1.14.8a2 on 2026-06-18.  
**Why it matters locally:** Don’t adopt the framework wholesale, but steal the “definition-loaded flow” idea for inspectable local plans that can run without Python glue.

### 6. Agno 2.6.13-2.6.15: identity-aware AgentOS MCP surface + HITL/workflow streaming
**Primary URL:** https://github.com/agno-agi/agno/releases/tag/v2.6.15 and https://github.com/agno-agi/agno/releases/tag/v2.6.14  
**Date:** 2026-06-10 to 2026-06-15  
**Claim:** Agno added scoped identity-aware MCP tools, AgentOS registry auto-population, sub-agent event streaming, workflow HITL over sockets, and learning CRUD.  
**Demonstrated vs asserted:** Demonstrated in GitHub release notes; “AgentOS” platform value is asserted.  
**Maturity:** GitHub ~41k stars; latest release v2.6.16 on 2026-06-15.  
**Why it matters locally:** The MCP lesson is useful: tool exposure should be data-configured with scope, caller identity injection, authorization, and DNS-rebinding guards.

### 7. Pydantic-AI 1.105-1.107 / 2.0 beta: deferred loading + file-reference security fix
**Primary URL:** https://github.com/pydantic/pydantic-ai/releases/tag/v1.105.0 and https://github.com/pydantic/pydantic-ai/releases/tag/v1.107.0  
**Date:** 2026-06-02 to 2026-06-10  
**Claim:** Added on-demand/deferred loading of instructions/tools/settings/hooks; patched a confused-deputy file-reference issue in UI adapters.  
**Demonstrated vs asserted:** Demonstrated in releases and advisory reference.  
**Maturity:** GitHub ~18k stars; v1.107.0 latest stable on 2026-06-10; v2.0.0b7 prerelease same day.  
**Why it matters locally:** Deferred loading maps directly to skill/context budgets: load tools/instructions lazily, but keep file references stripped or explicitly trusted at UI boundaries.

### 8. AG2 / AutoGen lineage: AG2 v0.13.x beta path + Microsoft Agent Framework GA direction
**Primary URL:** https://github.com/ag2ai/ag2/releases/tag/v0.13.3 and https://learn.microsoft.com/en-us/agent-framework/support/upgrade/python-2026-significant-changes  
**Date:** 2026-05-23 to 2026-06-05  
**Claim:** AG2 is moving its beta framework toward v1.0 with sandbox protocol/local sandbox and eval agent-as-judge changes; Microsoft Agent Framework is the official AutoGen/Semantic Kernel successor with 2026 breaking changes.  
**Demonstrated vs asserted:** AG2 changes demonstrated; Microsoft docs demonstrate breaking/API migration; “successor” direction comes from Microsoft official discussion/docs.  
**Maturity:** AG2 ~4.7k stars; last push 2026-06-17; latest release v0.13.4 on 2026-06-12.  
**Why it matters locally:** Treat classic AutoGen as legacy; if extracting anything, take sandbox/eval primitives, not conversational group-chat orchestration.

### 9. smolagents 1.25-1.26: security pullback on remote execution
**Primary URL:** https://github.com/huggingface/smolagents/releases/tag/v1.26.0 and https://github.com/huggingface/smolagents/releases/tag/v1.25.0  
**Date:** 2026-05-14 to 2026-05-29  
**Claim:** Removed remote WasmExecutor, added Exa search option, and v1.25 tightened executor security after high-impact remote-executor issues.  
**Demonstrated vs asserted:** Demonstrated by release diff and removed files.  
**Maturity:** GitHub ~27.9k stars; last push 2026-06-16; latest release v1.26.0 on 2026-05-29.  
**Why it matters locally:** Negative steal: local code-agent harnesses should avoid “remote executor by convenience” unless isolation and serialization are explicitly audited.

### 10. Local-first agent framework benchmark repo
**Primary URL:** https://github.com/LukaszGrochal/agent-framework-benchmark  
**Date:** surfaced May-June 2026; repo page primary  
**Claim:** Implements the same company-research workflow across CrewAI, LangGraph, AutoGen, Microsoft Agent Framework, and OpenAI Agents SDK with local Ollama-first benchmarking and LLM-judge scoring.  
**Demonstrated vs asserted:** Harness existence demonstrated; ranking results are asserted by README and LLM-judge, not independently validated.  
**Maturity:** GitHub repo; exact stars/last-push not surfaced by Exa result.  
**Why it matters locally:** Useful not for its winner, but for its structure: same task, separate dependency groups, shared schemas/prompts/tools, local-first runs.

## Filtered / Low-Relevance

- **Atomic Agents:** no genuinely new May-June framework release. Latest GitHub release surfaced v2.7.5 on 2026-03-31; last push 2026-04-05. Skip for this window.
- **LlamaIndex Workflows:** important standalone Workflows 1.0 announcement exists, but it is 2025-06-30, not new in the requested May-June 2026 window. May 2026 LlamaIndex releases were mostly core/dependency updates, not a new Workflows development.
- **Framework comparison blog posts/listicles:** many May-June 2026 posts exist, but most are secondary, methodology-thin, or vendor content. I did not include them as findings.

## Top Steals

1. **Typed event streams:** Adopt LangGraph/Mastra-style structured lifecycle/tool/subagent projections instead of prose transcript parsing.  
2. **Tool suspension as state:** Represent user questions, approvals, and plan resumes as resumable tool calls with stable IDs.  
3. **MCP hardening:** Namespace tool names, scope built-ins, inject caller identity explicitly, and put authorization/DNS-rebinding guards at the MCP surface.