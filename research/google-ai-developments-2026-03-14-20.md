## Google AI / DeepMind Developments -- March 14-20, 2026

**Question:** What new Google AI/DeepMind developments occurred in the past 7 days?
**Tier:** Standard | **Date:** 2026-03-20
**Ground truth:** Gemini 3.1 Pro released Feb 19; Gemini 3.1 Flash-Lite released Mar 3; Gemini CLI at v0.32.1 known working (per meta CLAUDE.md)

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Gemini API now supports combining built-in tools (Search, Maps) with custom function calling in single API calls | Official changelog + blog post | HIGH | [SOURCE: ai.google.dev/gemini-api/docs/changelog] | VERIFIED |
| 2 | Google Maps grounding extended to Gemini 3 models | Official changelog (Mar 18) | HIGH | [SOURCE: ai.google.dev/gemini-api/docs/changelog] | VERIFIED |
| 3 | AI Studio added project-level spend caps and revamped usage/billing tiers | Official changelog (Mar 12-16) | HIGH | [SOURCE: ai.google.dev/gemini-api/docs/changelog, blog.google] | VERIFIED |
| 4 | Gemini CLI v0.34.0 released (Mar 17): MCP FQN migration, A2A 30-min timeout, plan mode default, loop detection | GitHub release notes | HIGH | [SOURCE: github.com/google-gemini/gemini-cli/releases/tag/v0.34.0] | VERIFIED |
| 5 | Gemini CLI v0.35.0-preview.1 released (Mar 17): Vim mode, customizable keybindings, native gRPC/A2A, SandboxManager, crypto integrity for extensions | GitHub release notes | HIGH | [SOURCE: github.com/google-gemini/gemini-cli/releases/tag/v0.35.0-preview.1] | VERIFIED |
| 6 | Google AI Pro ($19.99/mo) and Ultra ($249.99/mo) tiers announced with differentiated limits | 9to5Google report (Mar 17) | HIGH | [SOURCE: 9to5google.com/2026/03/17/google-ai-pro-ultra-features/] | VERIFIED |
| 7 | Vertex AI Agent Builder blog post on enhanced tool governance published Mar 20 | Blog metadata confirmed | MEDIUM | [SOURCE: cloud.google.com/blog] | VERIFIED (content not fully extractable) |
| 8 | ADK got TypeScript support, AgentTeam API, Cloud Run deployment | Third-party roundup (moltbook-ai.com) | MEDIUM | [SOURCE: moltbook-ai.com/posts/ai-agents-march-2026-roundup] | PARTIALLY VERIFIED |
| 9 | Wiz acquisition closed (mentioned in Mar 19 blog post) | Blog.google reference | MEDIUM | [SOURCE: blog.google/products/google-cloud/ai-business-trends-report-2026] | NOTED (blog rendered poorly) |
| 10 | Google I/O 2026 confirmed May 19-20 | Blog.google save-the-date | HIGH | [SOURCE: blog.google] | VERIFIED |

---

### Key Findings

#### 1. Gemini API: Tool Combination + Maps Grounding (Mar 17-18)

The most developer-relevant change this week. The Gemini API now allows combining built-in tools (Google Search, Google Maps) with custom function calling in a single API call. Previously, these were separate calls. This is significant for agentic workflows -- an agent can now ground its response in Search results AND call your custom functions in one turn.

Google Maps grounding was extended to Gemini 3 models specifically. [SOURCE: ai.google.dev/gemini-api/docs/changelog, blog.google/innovation-and-ai/technology/developers-tools/gemini-api-tooling-updates/]

**Relevance to us:** This affects how research-mcp or any tool using Gemini API might combine grounding with function calling. Worth noting for orchestrator tasks that use Gemini.

#### 2. Gemini CLI v0.34.0 + v0.35.0-preview.1 (Mar 17)

Two releases on the same day. Major changes relevant to our usage:

**v0.34.0 (stable):**
- MCP tool naming migrated to `mcp_` FQN format (affects all tool references)
- `tools/list_changed` notifications now work (MCP spec compliance)
- `extensionRegistryURI` setting for custom extension registries
- A2A agent timeout increased to 30 minutes
- Loop detection with model feedback and AbortError
- Subagent-specific TOML policies (per-subagent permission scoping)
- Plan mode enabled by default
- OOM crash fixes for long-running sessions
- Chat resume footer + unified /chat and /resume UX
- IP validation framework + safeFetch
- Token storage migration to unified KeychainService

**v0.35.0-preview.1:**
- Customizable keyboard shortcuts (with `-` prefix to remove bindings)
- Vim mode: X, ~, r, f/F/t/T, df/dt, yank/paste
- Native gRPC support + protocol routing for A2A
- SandboxManager for tool process isolation
- Linux sandboxing (bubblewrap + seccomp)
- Cryptographic integrity verification for extension updates
- DisableAlwaysAllow setting (prevent auto-approvals)
- MCP tool FQN validation + OAuth validation improvements
- API error retry (up to 3 silent retries before halt)
- JIT context loading enabled by default
- Code splitting / deferred UI loading for faster startup
- Todo tracker tools returning TodoList display

[SOURCE: github.com/google-gemini/gemini-cli/releases/]

**Relevance to us:** The MCP FQN migration (`mcp_` prefix) may affect our `llmx` integration if it shells out to gemini-cli. The DisableAlwaysAllow setting and subagent TOML policies are exactly the kind of governance features we've been building manually. JIT context loading should improve startup time. The gRPC/A2A native support suggests Google is serious about agent-to-agent interop at the CLI level.

#### 3. Google AI Pro ($19.99/mo) and Ultra ($249.99/mo) Tiers (Mar 17)

New consumer/prosumer subscription tiers replacing or supplementing the previous Plus tier:

**AI Pro ($19.99/mo):**
- 1M token context window
- 300 thinking prompts/day, 100 Pro prompts/day
- Nano Banana 2: 100 images/day
- Veo 3.1 Fast: 3 videos/day
- Deep Research: 20 reports/day
- NotebookLM Pro (500 notebooks, 300 sources each)
- Jules coding agent with 5x limits
- 2TB storage, 1000 AI Credits/mo

**AI Ultra ($249.99/mo):**
- 192K token context for Deep Think
- 1,500 thinking prompts/day, 500 Pro prompts/day
- Deep Think 3.1: 10 prompts/day
- 1,000 images/day, 5 videos/day
- Project Mariner (browser agent)
- Project Genie (interactive worlds)
- 30TB storage, 12,500 AI Credits/mo
- YouTube Premium included

[SOURCE: 9to5google.com/2026/03/17/google-ai-pro-ultra-features/]

**Relevance to us:** The Ultra tier's Deep Think 3.1 access (10/day) and Project Mariner (browser agent) could be interesting for research tasks. The 192K context for Deep Think is notably smaller than the 1M for regular Pro -- suggesting Deep Think is compute-heavy.

#### 4. AI Studio Cost Controls (Mar 12-16)

Project-level spend caps and revamped usage tiers landed in AI Studio. Developers can now set monthly spending limits per project. [SOURCE: ai.google.dev/gemini-api/docs/changelog, blog.google]

**Relevance to us:** Direct parallel to our $25/day orchestrator cost cap. Worth checking if AI Studio spend caps can be set programmatically for our Gemini API usage.

#### 5. Vertex AI Agent Builder: Tool Governance (Mar 20)

Published today. The blog post title is "New Enhanced Tool Governance in Vertex AI Agent Builder." Key details from Brave search snippet:
- ADK and A2A now support the Interactions API (consistent multimodal I/O across agents)
- Enhanced tool governance (specifics not fully extractable from rendered page)

The A2A protocol native integration on Vertex AI Agent Engine actually dates to Sep 2025 but continues to get upgrades. [SOURCE: cloud.google.com/blog, discuss.google.dev]

#### 6. ADK Updates (March 2026, exact date unclear)

From third-party reporting:
- TypeScript SDK added (was Python-only)
- `AgentTeam` API for multi-agent orchestration
- Streamlined Cloud Run deployment
- Built-in evaluation/testing tools

[SOURCE: moltbook-ai.com -- C3 reliability, not independently confirmed against Google docs]

#### 7. Gemini 3 Pro Preview Deprecated (Mar 9)

Just outside the window but operationally important: `gemini-3-pro-preview` was shut down Mar 9 and now redirects to `gemini-3.1-pro-preview`. If any of our configs reference the old model ID, they'll silently redirect. [SOURCE: discuss.ai.google.dev, ai.google.dev/gemini-api/docs/changelog]

Also noted: `gemini-3-pro-preview` on Vertex AI will be deprecated and removed on **March 26, 2026** (one week from now). [SOURCE: docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro]

---

### Gemini 3.1 Pro Benchmark Context (released Feb 19, not new this week)

For reference, since this is the current flagship:
- ARC-AGI-2: 77.1% (vs 31.1% for 3.0 Pro) -- massive jump
- SWE-Bench Verified: 80.6%
- GPQA Diamond: 94.3%
- MRCR v2 128k: 84.9%
- MCP Atlas: 69.2% (vs 54.1%)
- Context: 1M input, 64K output

[SOURCE: deepmind.google/models/model-cards/gemini-3-1-pro/]

---

### What's NOT New (filtering noise)

- Gemini 3.1 Pro itself (Feb 19)
- Gemini 3.1 Flash-Lite (Mar 3)
- Gemini 3 Deep Think upgrade (Feb 12)
- A2A native integration on Vertex Agent Engine (Sep 2025)
- Wiz acquisition announcement (reported Mar 19 but the deal was known earlier)

### What's Uncertain

- ADK TypeScript SDK timing and exact feature set [PARTIALLY VERIFIED via third-party only]
- Full details of the "Enhanced Tool Governance" blog post (Mar 20) -- Google Cloud blog pages render poorly via WebFetch [UNVERIFIED details]
- Whether the Interactions API for A2A/ADK is new this week or just newly documented [UNVERIFIED]
- Gemini CLI PR #23213 (prompt injection hardening) -- open PR, not yet merged [UNVERIFIED if shipped]

---

### Search Log

| Query | Tool | Hits | Signal |
|-------|------|------|--------|
| Google Gemini model release update March 2026 | Exa | 10 | High -- found official changelog, model card, third-party coverage |
| Gemini CLI update new features 2026 | Exa | 10 | High -- found both release tags, PRs, blog posts |
| Google Gemini update March 2026 | Brave | 10 | High -- found blog.google, Vertex docs, DeepMind model card |
| Google AI agent MCP protocol March 2026 | Brave | blocked (rate limit) | -- |
| Google Vertex AI agent builder A2A protocol update March 2026 | Brave | 10 | High -- A2A integration, tool governance blog |
| Google MCP support Gemini agent-to-agent March 2026 | Brave | blocked (rate limit) | -- |
| site:blog.google AI announcement March 2026 | Brave | 10 | Medium -- found I/O date, Wiz, ADK roundup |
| Google/DeepMind March 14-20 2026 | llm-stats.com | 1 | Low -- no Google entries in window |
| Official sources (changelog, release notes, model cards) | WebFetch | 8 pages | High -- primary source verification |

---

### Action Items for Meta

1. **Check gemini-cli version** -- we reference v0.32.1 in CLAUDE.md. v0.34.0 is stable now. Update.
2. **MCP FQN migration** -- v0.34.0 migrated to `mcp_` prefix. Verify our llmx integration handles this.
3. **Vertex model deprecation** -- `gemini-3-pro-preview` removed from Vertex on Mar 26. Check if any orchestrator pipelines or API calls reference this model ID.
4. **AI Studio spend caps** -- evaluate if programmatic spend caps can replace or supplement our manual $25/day orchestrator cap.
5. **Tool combination API** -- the ability to combine Google Search grounding with custom function calling in one API call could improve research agent quality. Worth a probe.

<!-- knowledge-index
generated: 2026-03-22T00:13:51Z
hash: 1a74c4ef3437

table_claims: 10

end-knowledge-index -->
