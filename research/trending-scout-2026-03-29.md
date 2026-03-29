---
title: "Trending Scout — March 29, 2026"
date: 2026-03-29
tags: [trending-scout, weekly-scan, vendor-updates]
status: complete
---

# Trending Scout — 2026-03-29

**Window:** 2026-03-26 to 2026-03-29
**Sources:** Exa, Brave, GitHub Releases API, official changelogs, alphaXiv
**Findings:** 6 actionable, 5 version bumps, ~15 already known (filtered)

---

## New Findings (ranked by value - maintenance)

### 1. Google Gemini API Agent Skill — Benchmarked Context Injection (28% → 97%)

| Field | Content |
|-------|---------|
| Source | [Google Developers Blog](https://developers.googleblog.com/en/closing-the-knowledge-gap-with-agent-skills/) / [github.com/google-gemini/gemini-skills](https://github.com/google-gemini/gemini-skills/) |
| What it does | Google built a "developer skill" that feeds Gemini agents live SDK docs and sample code. On 117 coding tasks, Gemini 3.1 Pro Preview jumped from 28.2% to 96.6% success rate. Older 2.5 models saw smaller gains (attributed to weaker reasoning). |
| Why relevant | **This is exactly what context7 MCP does for us** — injecting current docs into agent context. Google's published benchmark validates the approach with hard numbers. The 28→97% delta on their own SDK tasks is the strongest evidence yet that context injection >> training data for SDK/API work. Also confirms that stronger reasoning models benefit more from skills (implication: Opus + good skills > weaker model + same skills). |
| Integration path | No adoption needed — we already have context7 MCP. Extract the evaluation methodology: 117 structured tasks with pass/fail, before/after comparison. Could inform our own skill evaluation framework. |
| Current overlap | context7 MCP (docs injection), claude-api skill (SDK guidance) |
| Maintenance cost | Zero (pattern extraction only) |
| Verdict | **Extract pattern** — evaluation methodology is the valuable part |

### 2. Claude Agent SDK Python v0.1.51–52 — Session Management + Context Usage API

| Field | Content |
|-------|---------|
| Source | [github.com/anthropics/claude-agent-sdk-python/releases](https://github.com/anthropics/claude-agent-sdk-python/releases) |
| What it does | v0.1.51: `fork_session()`, `delete_session()`, `task_budget` (token budget per task), `AgentDefinition` fields (`disallowedTools`, `maxTurns`, `initialPrompt`). v0.1.52: `get_context_usage()` (context window breakdown by category), `typing.Annotated` for per-param tool descriptions, `tool_use_id`/`agent_id` in `ToolPermissionContext`. |
| Why relevant | `get_context_usage()` is directly useful — could replace our heuristic context tracking. `task_budget` maps to cost cap enforcement. `fork_session()` enables branching conversations for A/B exploration. `Annotated` param descriptions improve tool schema quality. |
| Integration path | Evaluate `get_context_usage()` for dashboard/cockpit integration. `task_budget` could replace custom cost tracking in orchestrator. |
| Current overlap | Manual cost tracking in orchestrator, context heuristics |
| Maintenance cost | Low — SDK methods, not custom code |
| Verdict | **Adopt** — `get_context_usage()` and `task_budget` reduce custom code |

### 3. MCP ext-apps — Official MCP Apps Protocol (1.9K stars)

| Field | Content |
|-------|---------|
| Source | [github.com/modelcontextprotocol/ext-apps](https://github.com/modelcontextprotocol/ext-apps/) (1,943 stars) |
| What it does | Official spec and SDK for MCP Apps — UIs embedded in AI chatbots, served by MCP servers. Extends MCP beyond tools/resources into interactive UI components. |
| Why relevant | If MCP Apps become standard, MCP servers could serve interactive forms, dashboards, and visualizations directly in the chat UI. Could change how we present dashboard data, calibration results, or research summaries. |
| Integration path | Watch — the spec is young (created Nov 2025, ~2K stars). Worth monitoring for when Claude Code supports it natively. |
| Current overlap | None — we have no UI-embedded components |
| Maintenance cost | N/A (watch only) |
| Verdict | **Watch** — promising but not yet supported in Claude Code |

### 4. Codex CLI Rust Rewrite (v0.118.0-alpha.3)

| Field | Content |
|-------|---------|
| Source | [github.com/openai/codex/releases](https://github.com/openai/codex/releases) |
| What it does | Codex CLI is being rewritten in Rust. Alpha releases (v0.118.0-alpha.1 through alpha.3) shipped March 26-27. The v0.117.0 stable also landed with first-class plugins, path-based sub-agent addressing (`/root/agent_a`), structured inter-agent messaging, and app-server TUI as default. |
| Why relevant | Rust rewrite signals OpenAI is investing in CLI performance and stability. The sub-agent path-based addressing (`/root/agent_a`) is the same pattern Claude Code uses for agent naming. Plugin first-class support closes the feature gap with Claude Code skills. |
| Integration path | No direct action — we use Codex via codex_dispatch.py for cross-model audits. The 37K token MCP overhead issue may improve with Rust rewrite. Monitor. |
| Current overlap | codex_dispatch.py, /dispatch-research |
| Maintenance cost | Zero |
| Verdict | **Watch** — Rust rewrite may fix MCP overhead issue |

### 5. Microsoft Agent Governance Toolkit (343 stars)

| Field | Content |
|-------|---------|
| Source | [github.com/microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit) (343 stars, created 2026-03-02) |
| What it does | Policy enforcement, zero-trust identity, execution sandboxing, reliability engineering for autonomous AI agents. Claims coverage of all 10 OWASP Agentic Top 10 items. |
| Why relevant | Governance is our core concern. This is the first open-source toolkit explicitly targeting the OWASP Agentic Top 10. Could inform our hook/permission design, especially around identity and policy enforcement patterns. |
| Integration path | Extract patterns — compare their policy enforcement approach against our hooks. Not a dependency candidate (.NET/Python, enterprise-oriented). |
| Current overlap | Our hook system, permission rules, sandbox settings |
| Maintenance cost | Zero (pattern extraction) |
| Verdict | **Extract pattern** — compare governance approaches |

### 6. HKUDS/OpenSpace — Self-Evolving Agents (2.3K stars in 5 days)

| Field | Content |
|-------|---------|
| Source | [github.com/HKUDS/OpenSpace](https://github.com/HKUDS/OpenSpace) (2,318 stars, created 2026-03-24) |
| What it does | "Make Your Agents: Smarter, Low-Cost, Self-Evolving" — framework for agents that improve through experience. Community at open-space.cloud. |
| Why relevant | Self-improvement is a core meta concern. 2.3K stars in 5 days indicates significant interest. Worth checking if their self-evolution mechanism differs from what we've documented (SAMULE/ACE/ExIt patterns in agent-scaffolding-landscape memo). |
| Integration path | Read the repo to compare mechanisms. Likely pattern extraction at most. |
| Current overlap | Our session-analyst + improvement-log loop, autoresearch |
| Maintenance cost | Zero |
| Verdict | **Evaluate** — compare self-improvement mechanisms |

---

## Notable Research (alphaXiv trending)

| Paper | ID | Views | Relevance |
|-------|----|-------|-----------|
| AVO: Agentic Variation Operators for Autonomous Evolutionary Search | 2603.24517 | 1,568 | Directly relevant to our autoresearch engine — LLM agents as evolutionary optimizers discovering GPU kernels |
| Self-Distillation Degrades Reasoning | 2603.24472 | 1,078 | Warns against naive self-distillation for reasoning tasks — suppresses uncertainty expressions |
| Claudini: Autoresearch Discovers SOTA Adversarial Attacks | 2603.24511 | 558 | Already tracked in `research/scratch/claudini-dive.md` — validates autoresearch approach |
| Natural-Language Agent Harnesses | 2603.25723 | 159 | 47.2% vs 30.4% success for NL vs code-based harnesses on OS benchmarks. Validates our CLAUDE.md/skills approach |
| RL for Distributional Reasoning | 2603.24844 | 299 | Confidence calibration via RL — relevant to calibration canary system |
| UI-Voyager: Self-Evolving GUI Agent | 2603.24533 | 220 | 81% success learning from failure, exceeding human performance |

---

## Version Bumps

| Tool | Previous (Mar 26) | Current (Mar 29) | Notable Changes |
|------|----------|---------|-----------------|
| Claude Code | 2.1.85 | 2.1.87 | Session-Id header for proxy aggregation, .jj/.sl VCS exclusions, perf improvements (cache hits, reduced token overhead) |
| Agent SDK (Py) | 0.1.50 | 0.1.52 | fork_session, get_context_usage, task_budget, Annotated params |
| Agent SDK (TS) | 0.2.85 | 0.2.87 | getContextUsage, optional session_id, type fixes |
| Gemini CLI | 0.35.2 | 0.35.3 | Patch release (cherry-pick). v0.36.0-preview.6 also available. |
| Codex CLI | 0.117.0 | 0.117.0 (+ 0.118.0-alpha.3) | Stable unchanged; Rust rewrite alphas active |

---

## Already Known (filtered out)

- Codex v0.117.0 plugins + multi-agent v2 (covered in last scout as version bump)
- Microsoft Agent Framework RC (covered in agent-ecosystem-weekly-2026-03-26)
- Mastra framework (known, 22K stars, TS agent framework from Gatsby team)
- Cursor Automations (event-driven agents — covered in Cursor's RL moat discussion, last scout)
- JetBrains agentic platform (orchestrating AI — enterprise tooling, not directly relevant)
- ChromeDevTools MCP (already tracked, project-scoped per feedback)
- Claudini paper (already in research/scratch/)

---

## Cross-Cutting Signals

1. **Skills validated by benchmarks.** Google's 28→97% delta is the first hard benchmark showing skills/context injection dramatically outperform training data for SDK work. This validates our entire context7 + skills architecture.

2. **Context usage APIs arriving.** Both Claude Agent SDK and Codex now expose context window usage programmatically. The "how full is my context?" question is becoming a first-class API concern, not a heuristic.

3. **Governance tooling emerging.** Microsoft's Agent Governance Toolkit (OWASP Agentic Top 10) joins the growing list of governance frameworks. Our hook-based approach is directionally correct but could learn from their zero-trust identity patterns.

4. **Self-evolution repos exploding.** OpenSpace (2.3K stars in 5 days), AVO paper, UI-Voyager, Claudini — multiple independent groups building self-improving agent systems. The pattern is clearly resonating.

---

## Search Log

| Source | Query | Useful? |
|--------|-------|---------|
| WebFetch | code.claude.com/docs/en/changelog | Yes — comprehensive v2.1.84-86 details |
| GitHub API | anthropics/claude-agent-sdk-python releases | Yes — v0.1.51-52 release notes |
| GitHub API | anthropics/claude-agent-sdk-typescript releases | Yes — v0.2.85-87 release notes |
| GitHub API | openai/codex releases | Yes — v0.117.0 + Rust alphas |
| GitHub API | google-gemini/gemini-cli releases | Minimal — v0.35.3 patch only |
| Exa | Anthropic Claude API SDK release | Too broad, noisy results |
| Exa | OpenAI Codex CLI GPT API update | Good — found Codex plugins coverage |
| Exa | Google Gemini CLI API SDK update | Good — found Agent Skill coverage |
| Exa | AI agent framework MCP server (github) | Good — found ext-apps, governance toolkit, OpenSpace |
| Exa | AI agent coding tool new release | Mixed — mostly journalism |
| Exa | MCP server model context protocol (github) | Good — found ext-apps, ha-mcp, gh-aw-mcpg |
| Exa | Google Gemini API Agent Skill | Excellent — detailed coverage with benchmark numbers |
| Brave | Claude Code changelog March 2026 | Moderate — mostly links to changelog |
| Brave | AI agent framework trending (rate limited) | Rate limited (429) |
| alphaXiv | /explore trending | Good — 7 relevant papers identified |

<!-- knowledge-index
generated: 2026-03-29T15:38:49Z
hash: 61332ae1e74d

title: Trending Scout — March 29, 2026
status: complete
tags: trending-scout, weekly-scan, vendor-updates
cross_refs: research/scratch/claudini-dive.md

end-knowledge-index -->
