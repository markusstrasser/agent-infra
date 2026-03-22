---
title: Anthropic Tooling Landscape (March 2026)
date: 2026-03-21
---

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

---

## Delta Update: 2026-03-02 Platform Sweep

Full findings in `research/anthropic-platform-sweep-2026-03-02.md`.

### New API Features (since original memo)
- **Compaction API** (beta `compact-2026-01-12`): Server-side context summarization. `context_management.edits`, `pause_after_compaction`, custom `instructions`. Billing via `usage.iterations[]` (top-level usage excludes compaction).
- **Automatic caching** (GA): Top-level `cache_control: {"type": "ephemeral"}`. 1-hour TTL option at 2x base.
- **Fast mode** (beta `fast-mode-2026-02-01`): `speed: "fast"`, 2.5x OTPS, $30/$150 MTok. Cache prefixes not shared between speeds.
- **Data residency** (GA): `inference_geo: "us"|"global"`. 1.1x pricing for US-only.
- **Effort** moved to `output_config.effort` (GA). Sonnet 4.6 recommended default: `medium`.

### Claude Code v2.1.30→v2.1.66 Highlights
- HTTP hooks (`type: "http"`), worktree isolation (`--worktree`, `isolation: worktree`), Agent Teams preview
- 15+ new env vars: `CLAUDE_CODE_EFFORT_LEVEL`, `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, etc.
- `last_assistant_message` in Stop/SubagentStop, `updatedInput` in PreToolUse, `updatedMCPToolOutput` in PostToolUse
- `CLAUDE_ENV_FILE` for SessionStart hooks to persist env vars
- Setup hook event (18th event). SessionStart matchers: startup/resume/clear/compact
- v2.1.66 (Mar 4) — latest as of this update

### Agent SDK v0.1.45 (latest as of Mar 3)
- `effort` param, `ThinkingConfig`, Python hooks via `hooks` param
- **Critical gotcha**: `setting_sources=None` (default) loads NO settings. Must pass `["user","project"]` for hooks/CLAUDE.md.
- Working spike: `meta/scripts/orchestrator_sdk_spike.py`
- v0.1.19 (Jan 8) through v0.1.45 (Mar 3) = 27 releases in ~2 months. High churn, v0.1.x maturity concerns remain.

### Financial Services Plugins (NEW)
- 5 core + 2 partner plugins, 41 skills, 11 MCP connectors
- **equity-research**: earnings analysis, initiating coverage, thesis tracker, idea generation (5 screening frameworks)
- **financial-analysis**: comps (628-line), DCF, competitive analysis, model auditor. MCP: S&P, FactSet, Daloopa, Morningstar, Moody's, etc.
- **partner/spglobal**: tear-sheet (4 audiences), earnings preview via S&P CIQ MCP
- All Apache 2.0, pure markdown, zero build steps

---

## Delta Update: 2026-03-03 Deep Research Sweep

### Complete API Release Timeline (Jan-Feb 2026)

Full changelog retrieved from `platform.claude.com/docs/en/release-notes/api`:

| Date | Feature | Status |
|------|---------|--------|
| Jan 5 | Opus 3 retired | Done |
| Jan 12 | Console redirect to platform.claude.com | Done |
| Jan 29 | Structured outputs GA | GA — `output_config.format` (moved from `output_format`) |
| Feb 5 | Opus 4.6 launch | GA — adaptive thinking, `budget_tokens` deprecated |
| Feb 5 | Effort parameter GA | GA — no beta header |
| Feb 5 | Compaction API | Beta `compact-2026-01-12` |
| Feb 5 | Data residency | GA — `inference_geo` param |
| Feb 5 | 1M context for Opus 4.6 | Beta |
| Feb 5 | Fine-grained tool streaming | GA |
| Feb 7 | Fast mode Opus 4.6 | Research preview |
| Feb 17 | Sonnet 4.6 launch | GA — $3/$15 MTok |
| Feb 17 | **Free code exec with web search/fetch** | GA — pricing change |
| Feb 17 | Web search + programmatic tool calling | **GA** (were beta) |
| Feb 17 | Code exec, web fetch, tool search, tool use examples, memory | **All GA** |
| Feb 19 | Automatic caching | GA — single `cache_control` field |
| Feb 19 | Sonnet 3.7 + Haiku 3.5 retired | Done |

**Key: entire tool-use stack is now GA.** No beta headers needed for any tool.

### Sonnet 4.6 Details

- 70% preferred over Sonnet 4.5 in Claude Code usage
- 59% preferred over Opus 4.5 for coding
- OfficeQA: matches Opus 4.6
- Major prompt injection resistance improvement vs Sonnet 4.5
- Same pricing as Sonnet 4.5 ($3/$15 MTok)

### New GitHub Repos (Jan-Mar 2026)

| Created | Repo | Stars | Notes |
|---------|------|-------|-------|
| Jan 19 | `original_performance_takehome` | 3,560 | Performance eng hiring test (open-sourced) |
| Jan 21 | `claude-constitution` | 43 | Claude's values document |
| Jan 23 | `anthropic-cli` | 198 | **Investigate** — separate CLI, unclear purpose vs Claude Code |
| Jan 23 | `homebrew-tap` | 3 | Homebrew formulae for Anthropic tools |
| Jan 23 | `knowledge-work-plugins` | 8,520 | Cowork plugins for knowledge workers |
| Jan 26 | `nix-eval-jobs` | 2 | Fork — internal Nix build infra |
| Feb 4 | `claudes-c-compiler` | 2,465 | Demo — C compiler written by Claude agents |
| Feb 6 | `argo-cd` | 2 | Fork — internal Kubernetes CD |
| Feb 15 | `maestro` | 5 | Fork — Netflix workflow orchestrator (internal infra) |
| Feb 20 | `moka` | 4 | Fork — Rust caching library (internal infra) |
| Feb 23 | `financial-services-plugins` | 5,318 | Finance domain plugins |

Internal infra forks reveal Anthropic uses: Nix builds, Argo CD, Netflix Maestro, Rust caching.

### Blog Posts & Research (Jan-Mar 2026)

**Agent Infrastructure Relevant:**

1. **Cowork** (Jan 12): Desktop agent for non-developers. Same engine as Claude Code, file-system access. Plugins connect to Google Workspace, DocuSign, FactSet. Enterprise plugin system.
2. **Agent Teams / C Compiler** (Feb): 16 parallel Claude instances, Docker containers, file-based task locking, git conflict resolution. 2K sessions, 2B tokens, $20K. Key lesson: test quality > orchestration complexity.
3. **Measuring Agent Autonomy** (Feb 18): Empirical data from millions of sessions. Autonomy duration doubled Oct->Jan. Expert users auto-approve 40%+, interrupt 9% (strategic). 0.8% irreversible actions.
4. **Claude Code Security** (Research Preview): AI-powered security review in Claude Code.
5. **Zero-Day Discovery**: Opus 4.6 found 500+ high-severity vulns via reasoning (not fuzzing). Git history analysis, parallel code path detection.
6. **Distillation Attacks**: DeepSeek (150K), Moonshot (3.4M), MiniMax (13M) API exchanges detected. Behavioral fingerprinting. Countermeasures could theoretically affect high-volume legitimate usage.

**Other:**
- Anthropic Labs: New product incubation team
- RSP v3.0 + Safety Roadmap update
- Claude in GitHub Copilot (public preview Feb 4)
- Ad-Free Claude commitment
- AI Fluency Index (education research)
- AI-Resistant Technical Evaluations (hiring engineering post)

### Sources (this delta)
- platform.claude.com/docs/en/release-notes/api — Full API changelog
- gh api graphql (anthropics org) — Repo inventory
- gh api releases — Claude Code, Agent SDK, API SDK release histories
- anthropic.com/news/claude-sonnet-4-6
- anthropic.com/engineering/building-c-compiler
- anthropic.com/research/measuring-agent-autonomy
- red.anthropic.com/2026/zero-days/
- anthropic.com/news/detecting-and-preventing-distillation-attacks
- claude.com/blog/cowork-research-preview (via Perplexity)
- techcrunch.com, axios.com (Cowork reporting)

---

## Delta Update: 2026-03-04 Cross-Model Review

Cross-model review (GPT-5.2 + Gemini 3.1 Flash) of this landscape analysis.
Both models reviewed independently, then synthesis merged surviving insights.

### Revised Priority List (from synthesis)

| Priority | Item | Status | Rationale |
|----------|------|--------|-----------|
| P0 | PostToolUseFailure hook → JSONL logger | **DONE** | Both models: prerequisite for all reliability improvements |
| P0 | Hook telemetry — comprehensive wiring | **DONE** | Prerequisite: can't measure hook ROI without data |
| P1 | Sonnet 4.6 as subagent default | **DONE** | 80% cost reduction, one-line change |
| P1 | Drop deprecated beta headers | **DONE** | Zero found in our code (all in reference repos) |
| P2 | PermissionRequest auto-allow (read-only) | **DONE** (disabled) | Built, awaiting telemetry data before enabling |
| P2 | Cost-aware effort tiers in orchestrator | **DONE** | DEFAULT_EFFORT table + budget degradation |
| P3 | Research MCP output rewrite (PostToolUse) | **DONE** | `updatedMCPToolOutput` for read_paper cleanup |
| MEDIUM | Telegram approval bot | Backlog | Demoted — latency ≠ supervision reduction |
| LOW | Research result caching | Backlog | Needs usage data first |

### New Items Identified

1. **Cost-aware scheduler** — orchestrator should degrade effort and skip non-critical tasks when approaching daily budget cap. **DONE** in orchestrator.py.
2. **Hook telemetry as prerequisite** — both models flagged that deploying new hooks without measurement violates constitution principle #3. All hooks now wired to `hook-trigger-log.sh`.
3. **Research cache** — Exa/S2/Brave results could be cached to avoid redundant API calls. Deferred: need usage frequency data.
4. **Search flooding hook** — already existed as `pretool-search-burst.sh` (warn at 4, block at 8). No new work needed.
5. **Hook retirement policy** — hooks with <1 trigger/week after 30 days should be candidates for removal. Tracked via `just hook-telemetry`.

### Testable Predictions (from GPT-5.2 review)

| ID | Prediction | Timeline | How to verify |
|----|-----------|----------|---------------|
| P1 | PostToolUseFailure JSONL accumulates >50 entries/week | 2 weeks | `wc -l ~/.claude/tool-failures.jsonl` |
| P2 | Hook telemetry reveals >1 hook with >20% false positive rate | 30 days | `just hook-telemetry` |
| P3 | Sonnet 4.6 subagent default reduces weekly cost by >30% | 2 weeks | Compare dashboard before/after |
| P4 | PermissionRequest auto-allow reduces avg permission prompts by >50% | After enabling | Compare session friction metrics |
| P5 | Budget degradation fires <5% of tasks | 30 days | `grep budget_degrade orchestrator-log.jsonl` |
| P6 | MCP protocol Tasks spec (SEP-1686) reaches draft status | 6 months | Check github.com/anthropics/model-context-protocol |

### Overclaimed/Underclaimed Corrections

- **Overclaimed in original**: "All beta features GA since Feb 17 2026" — Skills API is still beta (uses `skills-2025-10-02` header in SDK). Most other features are indeed GA.
- **Underclaimed**: Agent SDK's `updatedMCPToolOutput` in PostToolUse hooks — this is more powerful than documented. Can rewrite any MCP tool output before Claude sees it.
- **Corrected**: PermissionRequest hook can auto-allow or auto-deny but NOT modify tool input. It's a gate, not a transform.

<!-- knowledge-index
generated: 2026-03-22T00:15:42Z
hash: e1fe95218e80

title: Anthropic Tooling Landscape (March 2026)
cross_refs: research/anthropic-platform-sweep-2026-03-02.md, research/orchestrator-design.md

end-knowledge-index -->
