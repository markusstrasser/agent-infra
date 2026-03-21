# MCP Protocol Evolution (March 2026)

Tracking MCP specification development that could affect our orchestrator, tool design, and agent architecture. [SOURCE: github.com/modelcontextprotocol/specification]

## 1. Tasks (SEP-1686) — Most Important for Us

**What:** Long-running, stateful tool operations. Amazon-authored. Defines lifecycle for tools that take seconds to hours.

**6 use cases specified:**
1. Long-running computations (CI/CD, data processing)
2. Background monitoring (file watchers, log monitors)
3. Multi-step workflows with intermediate results
4. Human-in-the-loop approval flows
5. Parallel task execution
6. Progressive result delivery

**Protocol:** `tasks/start`, `tasks/status`, `tasks/cancel`. Server sends `notifications/tasks/progress` with structured progress info. Client can poll or subscribe.

**Implications for orchestrator:** MCP Tasks could replace our `subprocess.run(command)` engine entirely. Currently orchestrator spawns `claude -p` or raw subprocess per task. If MCP Tasks matures, each pipeline step could be an MCP tool call with native progress tracking, cancellation, and result streaming — no subprocess management needed. [INFERENCE]

**Status:** Working group active (agents-wg). Not yet merged into main spec. [SOURCE: github.com/modelcontextprotocol/specification, agents-wg branch]

## 2. Skills Over MCP (experimental-ext-skills)

**What:** Open standard for agent skills as MCP extensions. Skills become portable across any MCP-compatible agent, not just Claude Code.

**Current state:** Experimental extension. Anthropic published the Skills Open Standard spec. Our skills in `~/Projects/skills/` use Anthropic's SKILL.md format which predates this — the open standard may supercede it.

**Implications:** If skills become MCP tools, our skill-embedded hooks and progressive disclosure patterns need rethinking. Currently skills are flat markdown files loaded into context. As MCP tools, they'd be invoked programmatically. [INFERENCE]

**Risk:** Our significant investment in SKILL.md authoring patterns, frontmatter, and skill-embedded hooks may need migration. However, Anthropic's track record suggests backward compatibility. [INFERENCE]

## 3. Multi Round-Trip Requests (transports-wg)

**What:** Allows a single MCP tool call to involve multiple client-server exchanges. Currently each tool call is request-response.

**Use case:** Interactive tools that need clarification ("which file did you mean?"), progressive refinement, or streaming structured results.

**Implications:** Would enable our research MCP to ask for clarification during `search_papers` (e.g., "found 500 results, narrow by year?"). Currently we handle this client-side with multiple tool calls. [INFERENCE]

## 4. Task Continuity (SEP-2339)

**What:** Resume interrupted tasks across sessions. Persistent task state that survives server restarts.

**Implications:** Combined with Tasks (SEP-1686), this would let our orchestrator resume failed tasks from the exact point of failure, rather than restarting from scratch. Currently a failed orchestrator task is simply re-queued. [INFERENCE]

## 5. HTTP Standardization (SEP-2243)

**What:** Standardizing the HTTP transport for MCP (currently has SSE and stdio transports). Would enable remote MCP servers as first-class citizens.

**Implications:** Our research MCP (`research-mcp`) currently runs as stdio subprocess. HTTP transport would let it run as a persistent service, shared across concurrent agent sessions. The orchestrator could share a single MCP server instance across all its tasks. [INFERENCE]

## Testable Predictions

| ID | Prediction | Timeline | Evidence to check |
|----|-----------|----------|-------------------|
| M1 | SEP-1686 (Tasks) reaches draft in main spec | 6 months | Check spec repo main branch |
| M2 | At least one Anthropic tool (Agent SDK or Claude Code) adopts MCP Tasks | 12 months | Check SDK changelogs |
| M3 | Skills Open Standard converges with SKILL.md format | 12 months | Check experimental-ext-skills branch |
| M4 | HTTP transport becomes the default for production MCP deployments | 9 months | Check MCP SDK defaults |

## 6. Production Deployment Gaps (NEW — March 2026)

**Source:** Srinivasan, "Bridging Protocol and Production" (arXiv:2603.13417, March 2026). Field lessons from enterprise MCP deployment with AWS Bedrock. 10K+ active servers, 97M monthly SDK downloads.

Three missing protocol-level primitives identified:

1. **Identity propagation (CABP).** No mechanism to carry user context (identity, permissions, tenant scope) with tool invocations. Proposed: Context-Aware Broker Protocol extending JSON-RPC with identity-scoped request routing. Broker sits between agent and MCP server, injects JWT claims. **Relevance for us:** Low — we don't have multi-tenant issues. But the broker pattern is useful if we ever share MCP servers across agents. `[SOURCE: arXiv:2603.13417]`

2. **Adaptive timeout budgeting (ATBA).** Sequential tool chains consume turn budget additively. If any tool exceeds timeout, entire turn fails. ATBA frames tool invocation as a budget allocation problem over heterogeneous latency distributions. **Relevance for us:** Medium — our orchestrator uses flat 600s timeout via `anyio.fail_after`. ATBA could reduce stalls on chains where one slow tool starves the rest. `[SOURCE: arXiv:2603.13417]`

3. **Structured error semantics (SERF).** Current MCP error response is binary `isError` boolean. SERF proposes machine-readable failure categories enabling deterministic agent self-correction (e.g., `{"error_type": "FILE_NOT_FOUND", "recoverable": true, "suggested_action": "search"}`). **Relevance for us:** HIGH — our MCP servers (`meta_mcp.py`, `repo_tools_mcp.py`) return unstructured error strings. SERF would enable our orchestrator to distinguish recoverable from fatal errors without LLM interpretation. `[SOURCE: arXiv:2603.13417]`

Additional finding: **Tool descriptions are "the most consequential artifact an MCP server ships."** Agent planner selects tools from `tools/list` based solely on name + description. Recommendation: 2-4 sentences per tool covering what it does, when to call it, what it returns, and side effects. Version suffixes (e.g., `_v2`) are an anti-pattern — agent can't determine which to invoke.

## What We Should Do Now

1. **Nothing on spec proposals.** All WG specs are pre-draft. Building on them = building on sand. [INFERENCE]
2. **Implement SERF-style structured errors** in our MCP servers. This is independent of spec evolution — it's just better error handling. Production-readiness, not spec compliance.
3. **Audit MCP tool descriptions** against the 2-4 sentence standard. One-time cost, ongoing benefit.
4. **Monitor agents-wg** for Tasks spec progress — most impactful for orchestrator.
5. **When Tasks reaches draft:** prototype replacing orchestrator's subprocess engine with MCP Tasks calls.
6. **Keep our MCP tools compatible** — ensure servers don't use patterns that conflict with evolving spec.

## Sources
- github.com/modelcontextprotocol/specification (main repo, agents-wg branch, transports-wg)
- github.com/anthropics/model-context-protocol (Anthropic's fork — experimental-ext-skills)
- anthropic.com/news/skills-open-standard
- SEP numbering from spec repo issues/PRs
