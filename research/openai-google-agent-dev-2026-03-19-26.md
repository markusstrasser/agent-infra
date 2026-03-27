## OpenAI & Google Agent Dev Updates — March 19-26, 2026

**Question:** What shipped in OpenAI and Google agent infrastructure in the past 7 days?
**Tier:** Standard | **Date:** 2026-03-26
**Sources:** GitHub Releases API, developers.openai.com/changelog, developers.openai.com/codex/changelog, google.github.io/adk-docs

---

### OpenAI

| # | Title | Date | URL | Summary | Why Relevant |
|---|-------|------|-----|---------|--------------|
| 1 | **Codex CLI v0.117.0** | 2026-03-26 | [GitHub](https://github.com/openai/codex/releases/tag/rust-v0.117.0) | Plugins as first-class workflow (sync, browse `/plugins`, install/remove). Sub-agents get path-based addresses (`/root/agent_a`) with structured inter-agent messaging. App-server TUI gets `!` shell commands, filesystem watch, remote websocket auth. Image workflow improvements. | Plugin system = reusable skill packaging. Path-based sub-agent addressing is the multi-agent orchestration primitive we'd want to understand for our own subagent dispatch. |
| 2 | **Codex CLI v0.116.0** | 2026-03-19 | [GitHub](https://github.com/openai/codex/releases/tag/rust-v0.116.0) | ChatGPT device-code sign-in (eliminates API key setup). `userpromptsubmit` hook. Realtime sessions with thread context. Sandbox startup fixes. | New hook type (`userpromptsubmit`) — our hook system is analogous. Device-code auth is the pattern for eliminating API key friction. |
| 3 | **Codex App 26.323** | 2026-03-24 | [Codex changelog](https://developers.openai.com/codex/changelog) | Thread search, batch archive for local threads, settings sync between app and VS Code extension. | Thread search = session forensics equivalent. Settings sync across surfaces is a pattern we lack. |
| 4 | **Agents SDK v0.13.0** | 2026-03-23 | [GitHub](https://github.com/openai/openai-agents-python/releases/tag/v0.13.0) | Default Realtime model → `gpt-realtime-1.5`. Exposed MCPServer resource management methods. Opt-in reasoning content replay for chat completion models. Fixed concurrent writes in SQLAlchemySession. Fixed compaction issues with orphaned assistant message IDs. | MCP resource management exposure is relevant — we use MCP servers heavily. Compaction fix for orphaned message IDs is a bug class we've seen. |
| 5 | **Agents SDK v0.13.1** | 2026-03-25 | [GitHub](https://github.com/openai/openai-agents-python/releases/tag/v0.13.1) | Any-LLM adapter support (model flexibility). Preserved static MCP metadata in converted function tools. Realtime response sequencing fixes. Removed duplicate CompactionItem from RunItem union. | Any-LLM adapter = multi-model support. MCP metadata preservation during tool conversion is a subtle interop issue. |
| 6 | **Agents SDK v0.13.2** | 2026-03-26 | [GitHub](https://github.com/openai/openai-agents-python/releases/tag/v0.13.2) | Pinned LiteLLM upper bound to mitigate supply chain concerns. External web access feature for WebSearchTool. Fixed dependency on griffelib for docstring parsing. | **LiteLLM supply chain pinning** — same issue hit Google ADK (see below). Cross-vendor signal of a LiteLLM compromise or vulnerability. |
| 7 | **openai-python SDK v2.30.0** | 2026-03-25 | [GitHub](https://github.com/openai/openai-python/releases/tag/v2.30.0) | Added `keys` field to Click/DoubleClick/Drag/Move/Scroll computer actions. `ResponseFunctionToolCallOutputItem.output` now returns `string | Array<ResponseInputText | ResponseInputImage | ResponseInputFile>` instead of string only. | Computer-use API refinement. Multi-modal tool call outputs (images/files in tool responses) is a meaningful API expansion. |
| 8 | **OpenAI API: gpt-5.3-chat-latest** | 2026-03-19 | [Changelog](https://developers.openai.com/changelog/) | Model slug updated to latest GPT-5.3 Instant snapshot. | Routine model refresh. |
| 9 | **OpenAI API: Developer messages excluded from memory** | ~2026-03-20 | [Dev changelog](https://developers.openai.com/changelog/) | Developer messages now excluded from phase-1 memory input, reducing noisy content entering memory. Model resolution now preserves original slug instead of being rewritten. | Memory architecture change — developer/system messages no longer pollute memory. Relevant to our prompt engineering. |

### Google

| # | Title | Date | URL | Summary | Why Relevant |
|---|-------|------|-----|---------|--------------|
| 10 | **Gemini CLI v0.35.0** | 2026-03-24 | [GitHub](https://github.com/google-gemini/gemini-cli/releases/tag/v0.35.0) | Customizable keyboard shortcuts. Vim mode motions (X, ~, r, f/F/t/T, df/dt). AgentLoopContext threading through core. Legacy CoreToolScheduler removed. Retry fetch notifications. | AgentLoopContext is an architectural change for subagent lifecycle management. Vim mode — nice for terminal-native users. |
| 11 | **Gemini CLI v0.36.0-preview.0** | 2026-03-24 | [GitHub](https://github.com/google-gemini/gemini-cli/releases/tag/v0.36.0-preview.0) | **Multi-registry architecture and tool filtering for subagents.** Dynamic model resolution via ModelConfigService. Subagent local execution and tool isolation. BeforeTool hooks now support 'ask' decision. | Multi-registry + tool filtering for subagents is a significant orchestration feature. Tool isolation per subagent = sandboxing model. BeforeTool 'ask' hook = our PreToolUse equivalent. |
| 12 | **Gemini CLI v0.35.2** | 2026-03-26 | [GitHub](https://github.com/google-gemini/gemini-cli/releases/tag/v0.35.2) | Patch release (details in changelog diff). | Stability patch. |
| 13 | **ADK Python v1.27.3** | 2026-03-23 | [GitHub](https://github.com/google/adk-python/releases/tag/v1.27.3) | Protection for arbitrary module imports (security fix). | Security: agent name validation to prevent code injection via module imports. |
| 14 | **ADK Python v1.27.4** | 2026-03-24 | [GitHub](https://github.com/google/adk-python/releases/tag/v1.27.4) | **Excluded compromised LiteLLM versions, pinned to 1.82.6.** Gated builder endpoints behind web flag. | **LiteLLM supply chain incident** — both OpenAI and Google pinned/excluded specific versions within 48 hours. Indicates a real compromise, not precautionary. |
| 15 | **ADK Python v1.28.0** | 2026-03-26 | [GitHub](https://github.com/google/adk-python/releases/tag/v1.28.0) | A2A lifespan parameter for `to_a2a()`. New ADK-A2A integration extension. Slack integration. Spanner Admin Toolset. MultiTurn Task trajectory metrics. SSE streaming for conformance tests. Database role for fine-grained access control. | A2A (Agent-to-Agent) protocol integration maturing. Eval metrics for multi-turn trajectories = our session-features.py equivalent. Slack integration = agent-to-human notification channel. |
| 16 | **ADK Python v2.0.0-alpha.2** | 2026-03-26 | [GitHub](https://github.com/google/adk-python/releases/tag/v2.0.0a2) | ADK 2.0 alpha: graph-based workflow orchestration. Same security fixes (module import validation, LiteLLM pinning). GKE deployment defaults to ClusterIP (not public). Builder API file extension enforcement. | **ADK 2.0 alpha with graph-based workflows** is a major architectural shift from sequential agent orchestration. Worth tracking for pattern comparison. |
| 17 | **Google Developers Blog: ADK Integrations Ecosystem** | 2026-03-27 | [Blog](https://developers.googleblog.com/supercharge-your-ai-agents-adk-integrations-ecosystem/) | New ADK integrations ecosystem announcement — code repos, workflows, databases. | Ecosystem play — Google positioning ADK as the integration hub. |

---

### Cross-Cutting Signals

**1. LiteLLM Supply Chain Incident (HIGH PRIORITY)**
Both OpenAI (Agents SDK v0.13.2, 2026-03-26) and Google (ADK v1.27.4, 2026-03-24) independently pinned or excluded LiteLLM versions within a 48-hour window, citing "compromised versions" and "supply chain concerns." This is a confirmed security event, not precautionary — two competing vendors don't coordinate patches for hypothetical risks.
- **Action:** Check if any of our tooling depends on LiteLLM. If so, pin to ≤1.82.6.

**2. Plugin/Skill Systems Converging**
Codex CLI v0.117.0 introduces plugins as first-class workflows with marketplace. This is structurally similar to our skills system but with distribution infrastructure. Google's ADK integrations ecosystem announcement serves the same purpose.
- **Action:** Monitor for patterns we can adopt (plugin packaging, discoverability).

**3. Multi-Agent Orchestration Maturing**
- Codex: path-based sub-agent addressing (`/root/agent_a`), structured inter-agent messaging
- Gemini CLI: multi-registry architecture, tool filtering per subagent, subagent local execution with tool isolation
- ADK 2.0 alpha: graph-based workflow orchestration
- All three vendors independently converging on subagent isolation + structured messaging. Our subagent dispatch via `Task` is simpler but aligned.

**4. Hook Systems Expanding**
- Codex CLI adds `userpromptsubmit` hook (v0.116.0)
- Gemini CLI adds 'ask' decision for BeforeTool hooks (v0.36.0-preview.0)
- Both expanding the hook surface for user-controlled agent behavior. Validates our hook-heavy approach.

**5. Memory/Compaction Fixes**
- OpenAI API: developer messages excluded from phase-1 memory
- Agents SDK v0.13.0: compaction fixes for orphaned assistant message IDs
- Agents SDK v0.13.1: removed duplicate CompactionItem
- These are bug classes we've encountered. The developer-message-excluded-from-memory change is worth tracking for prompt engineering implications.

**6. Multi-Modal Tool Outputs**
- openai-python v2.30.0: tool call outputs now support images and files, not just strings
- Computer-use actions get `keys` field refinement
- This expands what agents can return from tool calls — relevant if we build tools that produce visual output.

---

### Not Included (filtered out)

- GPT-5.1 model deprecation (model lifecycle, not agent infra)
- ChatGPT release notes (product, not dev)
- Sora API updates (video, not agent infra)
- Legacy deep research removal (ChatGPT product)
- Tech journalism roundups (moltbook-ai, hendricks.ai, augmentcode.com — used only to cross-reference dates)

---

### Source Quality

All findings verified against primary sources (GitHub Releases API, official changelogs). No findings from tech journalism alone. The Augment Code article on Codex CLI v0.116.0 provided useful context (67K stars, 640 releases, 400 contributors, Rust rewrite at 95.6% of codebase) but the release details were confirmed via GitHub.

<!-- knowledge-index
generated: 2026-03-27T00:13:15Z
hash: 3275d3dc4cad


end-knowledge-index -->
