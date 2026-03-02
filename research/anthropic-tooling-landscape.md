# Anthropic Tooling Landscape (March 2026)

Comprehensive inventory of Anthropic developer tools, SDKs, and features.
Conducted as a gap analysis after the orchestrator was built using `claude -p` subprocess calls
while the Agent SDK existed and was documented in the design spec but deferred to Phase 5.

## Epistemic Failure Analysis

The Agent SDK **was found** during orchestrator research — documented in Section 8.2 of
`research/orchestrator-design.md` with code examples, and planned as Phase 5. The real failure:

1. **Communication gap**: The orchestrator session never surfaced "FYI, there's an Agent SDK I'm
   deferring because..." The user learned about it externally, which *feels* like a discovery gap
   even though it wasn't.
2. **Reasonable phasing**: `claude -p` subprocess is ~20 lines vs learning a new SDK (v0.1.x).
   Ship Phase 1 fast, swap engine in Phase 5. Defensible technically, but the *tradeoff was invisible*.
3. **Narrow tooling sweep**: While the SDK was found, many other Anthropic tools were not explored.
   No systematic scan of `github.com/anthropics` repos, no changelog review, no API feature inventory.

**Lesson**: After any research phase, do a "what else did they ship?" sweep of the vendor's GitHub
org + changelog. Five minutes. Would have caught plugins, domain-specific repos, and new API tools.

---

## 1. Claude Agent SDK

### Python (`claude-agent-sdk`)
- **Repo**: github.com/anthropics/claude-agent-sdk-python
- **Stars**: 5,099 | **License**: MIT | **Created**: 2025-06-11
- **Latest**: v0.1.44 (2026-02-26) | **51 releases**
- **Requires**: Python 3.10+
- **Bundles Claude Code CLI** — no separate install needed

Two interfaces:

| Feature | `query()` | `ClaudeSDKClient` |
|---------|-----------|-------------------|
| Session | New each time | Reuses same session |
| Conversation | Single exchange | Multi-turn with context |
| Interrupts | No | Yes |
| Custom Tools | Yes | Yes |
| Hooks | Yes | Yes |
| Continue Chat | No | Yes |
| Use Case | One-off tasks | Interactive/continuous |

**Key for orchestrator**: `query()` is the direct replacement for `claude -p` subprocess calls.
`ClaudeSDKClient` enables session reuse (currently impossible with subprocess).

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Update HIMS entity file",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
        permission_mode="acceptEdits",
        max_turns=30,
        cwd="/Users/alien/Projects/intel",
        setting_sources=["project"],
        mcp_servers={...},
    ),
):
    ...
```

### TypeScript (`@anthropic-ai/claude-agent-sdk`)
- **Repo**: github.com/anthropics/claude-agent-sdk-typescript
- **Stars**: 875 | **Created**: 2025-09-27
- **Latest**: v0.2.63 (2026-02-28)

Formerly "Claude Code SDK" — renamed to "Claude Agent SDK." Same engine as Claude Code,
exposed as a library. The agent loop, built-in tools, context management, MCP integration.

### Implications for Orchestrator
- Phase 5 migration is straightforward: `query()` is async, returns streaming messages
- Gains: in-process MCP servers, proper session management, no subprocess parsing
- Gains: `effort` parameter per task for cost optimization
- Risk: v0.1.x maturity. 296 open issues on Python SDK.

---

## 2. Anthropic GitHub Organization (72 repos)

### Core SDKs
| Repo | Lang | Stars | Updated |
|------|------|-------|---------|
| anthropic-sdk-python | Python | 2.9K | Mar 2, 2026 |
| anthropic-sdk-typescript | TypeScript | 1.7K | Mar 2, 2026 |
| anthropic-sdk-go | Go | 846 | Mar 2, 2026 |
| anthropic-sdk-ruby | Ruby | 298 | Mar 2, 2026 |
| anthropic-sdk-java | Kotlin | 238 | Mar 2, 2026 |
| anthropic-sdk-csharp | C# | 164 | Mar 2, 2026 |
| anthropic-sdk-php | PHP | 105 | Mar 2, 2026 |

### Agent Infrastructure
| Repo | Stars | Description |
|------|-------|-------------|
| skills | 81K | Public Agent Skills repository (open standard) |
| claude-code | 73K | Claude Code CLI |
| claude-plugins-official | 8.8K | Official plugin marketplace directory |
| knowledge-work-plugins | 8.4K | Cowork plugins for knowledge workers |
| claude-code-action | 6K | GitHub Action for CI/CD integration |
| financial-services-plugins | 5.2K | Finance domain plugins |
| claude-agent-sdk-python | 5.1K | Python Agent SDK |
| claude-code-security-review | 3.5K | Security review GitHub Action |
| claudes-c-compiler | 2.4K | C compiler in Rust (written by Claude) |
| claude-agent-sdk-demos | 1.6K | SDK demo projects |
| claude-agent-sdk-typescript | 875 | TypeScript Agent SDK |
| life-sciences | 233 | Life sciences marketplace |
| devcontainer-features | 220 | Dev Container features |
| anthropic-cli | 194 | CLI tool for Anthropic services |
| claude-code-monitoring-guide | 182 | Monitoring guidance |
| healthcare | 104 | Healthcare marketplace |
| claude-ai-mcp | 97 | MCP integration |
| claude-constitution | 43 | Claude's values document |

### Research/Legacy (selectively relevant)
- `courses` (19K) — educational content
- `claude-cookbooks` (34K) — example notebooks
- `claude-quickstarts` (15K) — starter projects
- `prompt-eng-interactive-tutorial` (32K) — prompt engineering
- Various research paper repos, forks of open-source tools

---

## 3. Claude API — New Features (as of Feb 2026)

### Now Generally Available (no beta header)
| Feature | What it does | Relevance |
|---------|-------------|-----------|
| **Code execution tool** | Sandboxed Bash execution in API calls | Could replace some MCP tools |
| **Web search tool** | Built-in web search with dynamic filtering | Competes with Exa MCP |
| **Web fetch tool** | URL content retrieval | Competes with WebFetch tool |
| **Tool search tool** | Dynamic tool discovery from large tool sets | Relevant for scaling MCP |
| **Memory tool** | Built-in conversation memory | Competes with our file-based memory |
| **Programmatic tool calling** | Claude calls tools via code execution | Reduces round-trips |
| **Tool use examples** | Example-based tool usage learning | Better than schema alone |

### New in Claude 4.6
| Feature | What it does | Relevance |
|---------|-------------|-----------|
| **Adaptive thinking** | `thinking: {type: "adaptive"}` — Claude decides when/how much to think | Replaces `budget_tokens` |
| **Effort parameter** | `low/medium/high/max` controls thinking depth | **Cost optimization for orchestrator** |
| **Fast mode** (preview) | Same model, faster output | Good for routine tasks |
| **Interleaved thinking** | Think between tool calls | Better agentic reasoning |
| **1M context window** | Beta, Opus 4.6 + Sonnet 4.6 | Papers MCP / large analysis |

### Other Recent API Additions
| Feature | What it does |
|---------|-------------|
| **MCP connector** | Connect to remote MCP servers directly from API (`mcp_servers` param) |
| **Automatic caching** | Single `cache_control` field, system manages cache points |
| **Structured outputs** | `strict: true` guarantees schema conformance for tool inputs |
| **Files API** | Upload files for code execution container |
| **Citations** | Built-in citation support |
| **Dynamic filtering** | Code execution filters web search/fetch results before context |
| **Search results** | Structured search result handling |

---

## 4. Agent Skills — Open Standard

Launched Oct 2025 as Claude Code feature. **Open-sourced Dec 18, 2025** as independent standard.

- **Spec + SDK**: agentskills.io
- **Adopted by**: Microsoft (VS Code, GitHub), Cursor, Goose, Amp, OpenCode, OpenAI (Codex CLI)
- **Partner skills**: Atlassian, Figma, Canva, Stripe, Notion, Zapier
- **Enterprise features**: Organization-wide management, workspace-scoped skills, partner directory

### Skills via API
```
Beta headers: skills-2025-10-02, code-execution-2025-08-25, files-api-2025-04-14
```

Two types:
- **Anthropic skills**: Pre-built (`pptx`, `xlsx`, `docx`, `pdf`). Generate real files.
- **Custom skills**: Upload via Skills API. Private to workspace.

Both require code execution tool. Skills run in sandboxed container.

**We're already heavy users of the Claude Code skill format**. The API-side skills are a
different thing — they're about document generation and enterprise deployment, not the
SKILL.md files we author. Our skills are local; these are cloud-hosted.

---

## 5. Claude Code Plugins

A **newer distribution mechanism** than raw skills. Plugin = MCP server + skills + hooks bundled.

- **Official directory**: `anthropics/claude-plugins-official` (28+ plugins)
- **174+ marketplaces** on claudecodemarketplace.com
- **Install**: `/plugin install {name}@claude-plugin-directory`
- **Browse**: `/plugin > Discover`

### Notable Official Plugins
| Plugin | What it does |
|--------|-------------|
| typescript-lsp | TypeScript language server (type checking, go-to-definition) |
| playwright | Browser automation and testing |
| security-guidance | Vulnerability scanning |

### Domain-Specific Plugin Repos
| Repo | Stars | Focus |
|------|-------|-------|
| financial-services-plugins | 5.2K | **Finance** — directly relevant to intel |
| knowledge-work-plugins | 8.4K | General knowledge work |
| life-sciences | 233 | Biotech/pharma |
| healthcare | 104 | Healthcare |

**We're not using the plugin system at all.** Our skills are in `~/Projects/skills/`, symlinked.
This works but misses: dependency management, versioning, marketplace discovery, bundled MCP servers.

---

## 6. Claude Code Recent Versions (v2.1.x, Jan-Mar 2026)

Key features from changelog scan:

| Version | Date | Feature |
|---------|------|---------|
| 2.1 | Jan 2026 | **LSP integration** (type-aware code understanding) |
| 2.1.33 | Feb 6 | TeammateIdle, TaskCompleted hooks; agent memory persistence; Sub-agent restrictions |
| 2.1.45 | Feb 17 | Sonnet 4.6 support; dynamic plugin loading |
| 2.1.49 | Feb 19 | `--worktree`/`-w` flag; `isolation: "worktree"` for subagents; `background: true`; ConfigChange hook |
| 2.1.50 | Feb 20 | Worktree hooks; 6 memory leak fixes; enterprise hooks |
| 2.1.51 | Feb 24 | `claude remote-control`; custom npm registry; tool result persistence (>50K → disk) |

Features we're already using: worktrees, background agents, agent memory, subagent restrictions, hooks.
Features we're NOT using: LSP, plugins, `remote-control`, TeammateIdle/TaskCompleted hooks.

---

## 7. Gap Analysis — What We Should Evaluate

### High Priority (direct value)

1. **Agent SDK migration (orchestrator Phase 5)** — already planned. `query()` replaces subprocess.
   Gains: proper async, in-process MCP, session management, no output parsing.

2. **Effort parameter for cost optimization** — orchestrator tasks don't all need `high` thinking.
   Entity refreshes → `low`. Research sweeps → `high`. Saves money.

3. **Financial-services-plugins** — 5.2K stars, finance-specific. Check what's in there for intel.

4. **Adaptive thinking config** — our API calls (if any) should use `thinking: {type: "adaptive"}`
   not the deprecated `budget_tokens`.

### Medium Priority (evaluate ROI)

5. **Plugin system** — should we package our skills as plugins? Better distribution, dependency
   management, versioned. But: our symlink system works fine for a single-user setup.

6. **MCP connector** — API-side remote MCP connection. Useful if orchestrator moves to API calls
   instead of CLI subprocess.

7. **Built-in web search/fetch** — competes with Exa MCP. Dynamic filtering via code execution
   is interesting (filter results before they hit context).

8. **Tool search** — dynamic tool discovery from large tool sets. We have ~20 tools; not urgent.

9. **claude-code-action** — GitHub integration. Not using CI/CD currently but worth knowing about.

### Low Priority (not relevant yet)

10. **Agent Skills API** (cloud-hosted skills) — enterprise feature for document generation.
    Our skills are local and that's fine.

11. **Memory tool** — built-in memory. We have file-based memory that's more flexible and
    version-controlled.

12. **LSP integration** — Claude Code already uses it internally. No action needed from us.

---

## 8. Architecture Implications

### What changes nothing
- Our skills system (SKILL.md) is compatible with the open standard — we're already conformant.
- Our hooks architecture leverages native Claude Code features well.
- File-based memory + git is more powerful than the built-in memory tool.

### What might change
- **Orchestrator engine**: `claude -p` subprocess → `query()` SDK call. Planned as Phase 5.
- **Cost control**: `effort` parameter per task type. Not available via `claude -p` flag.
- **Intel plugins**: The `financial-services-plugins` repo might have tools we'd want.

### What probably won't change but should be monitored
- Plugin ecosystem maturity (currently 174 marketplaces, growing fast)
- MCP connector for API-side tool execution
- Agent Skills cloud platform evolution

---

## Sources

- github.com/anthropics (72 repos, all 3 pages reviewed)
- platform.claude.com/docs/en/agent-sdk/python — Python SDK reference
- platform.claude.com/docs/en/release-notes/overview — API changelog
- docs.anthropic.com/en/docs/claude-code/sdk/sdk-python — SDK docs
- anthropic.com/news/claude-opus-4-6 — Opus 4.6 announcement (Feb 5, 2026)
- anthropic.com/news/claude-sonnet-4-6 — Sonnet 4.6 announcement (Feb 17, 2026)
- anthropic.com/engineering/advanced-tool-use — Advanced tool use (Nov 24, 2025)
- venturebeat.com — Agent Skills open standard announcement (Dec 18, 2025)
- claude-world.com — Claude Code v2.1.33, v2.1.45, v2.1.50, v2.1.51 release notes
- claudecodemarketplace.com — Plugin marketplace directory
- promptfoo.dev/docs/providers/claude-agent-sdk — Promptfoo integration docs
- nader.substack.com — Agent SDK guide (Jan 8, 2026)
