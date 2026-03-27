---
title: Agent Ecosystem Weekly — March 19-26, 2026
date: 2026-03-26
tags: [agent-ecosystem, weekly-scan, trending-repos, mcp, benchmarks]
status: complete
---

## Agent Ecosystem Weekly — March 19-26, 2026

**Tier:** Standard | **Date:** 2026-03-26
**Prior scan:** `agent-ecosystem-weekly-2026-03-20.md` (March 14-20)

---

### Summary

Skills are the new unit of agent knowledge. 6 of the top 15 trending repos this week are skills-related. The agent harness war continues with everything-claude-code (105K stars) and obra/superpowers (110K stars) leading. Cursor shipped Composer 2 (first in-house model). MCP SDK hit v1.27. Gemini CLI v0.36.0 adds multi-registry architecture. Claude Code hit v2.1.83 with 40+ fixes and 8 new env vars.

---

### Trending Repos (March 19-26)

| # | Repo | Stars/wk | Total | What | Relevance |
|---|------|----------|-------|------|-----------|
| 1 | affaan-m/everything-claude-code | +21,490 | 104,819 | Agent harness: skills, instincts, memory, AgentShield security | Competitor to our CLAUDE.md + hooks architecture; AgentShield is novel (security scanning for agent actions) |
| 2 | obra/superpowers | +19,621 | 110,358 | Spec-first agentic skills framework | Spec-then-plan-then-TDD methodology — parallel to our plan-mode workflow |
| 3 | bytedance/deer-flow | +10,201 | 43,085 | ByteDance SuperAgent harness v2.0 | Docker sandbox, memory, skills, sub-agent dispatch — batteries-included competitor |
| 4 | jarrodwatts/claude-hud | +7,069 | 12,626 | Real-time HUD: context usage, active tools, running agents | Direct analog to our cockpit/statusline system |
| 5 | HKUDS/ClawTeam | 3,383 | — | Agent swarm intelligence, worktree coordination | Multi-agent via git worktrees — same pattern as our `isolation: "worktree"` |
| 6 | louislva/claude-peers-mcp | 1,109 | — | MCP server for inter-Claude-instance messaging | Multi-agent coordination via MCP — worth evaluating for our subagent dispatch |
| 7 | MiniMax-AI/skills | 3,867 | — | Official skills package (full-stack, iOS/macOS) | Skills ecosystem maturing; vendor-backed skills packages emerging |
| 8 | VoltAgent/awesome-agent-skills | — | — | Curated cross-editor skills list | Skills as interoperable knowledge units across Claude/Codex/Cursor/Gemini |
| 9 | VoltAgent/awesome-codex-subagents | 2,421 | — | 130+ curated Codex subagents | Subagent pattern catalog — reference for our agent dispatch |
| 10 | danveloper/flash-moe | 1,847 | — | 397B MoE on MacBook via Metal | Local inference breakthrough; HN #1 (393 pts) |
| 11 | coder/mux | — | — | Desktop app for isolated parallel agentic dev | AGPL-3.0; tmux-style agent isolation |
| 12 | badlogic/pi-mono | — | — | AI agent toolkit (TypeScript) | MIT; monorepo agent toolkit |
| 13 | CoderLuii/HolyClaude | — | — | Dockerized Claude Code | Container isolation for agent execution |
| 14 | jenkinsci/ai-agent-plugin | — | — | Jenkins plugin for Claude/Codex/Cursor/Gemini | CI/CD agent integration — relevant to code-review-scout |

[SOURCE: shareuhack.com/en/posts/github-trending-weekly-2026-03-25, Exa GitHub search, Brave search]

---

### Coding Tool Releases

| Tool | Version/Date | Key Changes | Relevance |
|------|-------------|-------------|-----------|
| **Cursor** | Composer 2 (Mar 19) | First in-house coding model; frontier SWE-bench scores; real-time RL training from user interactions | Cursor no longer dependent on third-party models; RL from production usage is a moat |
| **Cursor** | Mar 25 changelog | Self-hosted cloud agents (code stays in your network) | Enterprise isolation pattern |
| **Cursor** | Blog (Mar 26) | "Improving Composer through real-time RL" research post | RL on live coding sessions — unprecedented feedback loop |
| **Claude Code** | v2.1.80 (Mar 19) | Rate limit display in statusline; plugin system expansion | Our statusline already has rate limits; plugin system worth monitoring |
| **Claude Code** | v2.1.81 (Mar 21) | `--bare` flag (skips hooks/LSP/plugins for scripted -p calls); Windows improvements | `--bare` is directly useful for our orchestrator/scripted invocations |
| **Claude Code** | v2.1.83 (Mar 25) | 8 new env vars; 40+ bug fixes (largest single release by fix count) | Check if any new env vars improve our hook/subagent workflows |
| **Claude Agent SDK (TS)** | v0.2.83 (Mar 25) | `seed_read_state` control subtype | Agent SDK continues rapid iteration |
| **Claude Agent SDK (Python)** | v0.1.50 | `tag` and `created_at` on session info; `get_session_info()` | Session metadata — useful for our runlog integration |
| **Claude Agent SDK (Go)** | v1.1.0 (Mar 20) | Community Go SDK | Go alternative for claude-agent-sdk |
| **Windsurf** | 1.9577.42-43 (Mar 19) | Bug fixes; Mac x64 build fix | Minor maintenance release |
| **Gemini CLI** | v0.36.0-preview.0 (Mar 24) | Multi-registry architecture; CI skill for automated failure replication; agents disabled by default | Multi-registry = plugin ecosystem; CI skill = automated test failure debugging |
| **Cloudflare Agents SDK** | v0.8.0 (Mar 23) | Readable agent state, idempotent schedules, typed AgentClient, Zod 4 | Server-side agent infra maturing |

[SOURCE: cursor.com/changelog, claudeupdates.dev, github.com/anthropics/claude-code/releases, github.com/google-gemini/gemini-cli, developers.cloudflare.com/changelog]

---

### Framework Releases

| Framework | Date | What | Relevance |
|-----------|------|------|-----------|
| **Microsoft Agent Framework RC** | Mar 21 | Merges Semantic Kernel + AutoGen; graph orchestration; .NET + Python | Enterprise multi-agent; unified SDK replacing two separate projects |
| **OpenAI Symphony** | Mar 19 | New orchestration framework for multi-agent systems | OpenAI entering the orchestration space |
| **JetBrains Central** | Mar 24 | Open system for agentic software development | IDE vendor entering agent orchestration |
| **NVIDIA Nemotron 3** | Mar 24 | Agents for reasoning, multimodal RAG, voice, safety | GTC 2026 launch; enterprise agent building blocks |
| **EigenCloud AgentKit** | Mar 26 | Financially-capable agents (beta) | Niche: financial agent toolkit |
| **Databricks AI Dev Kit** | Mar 25 | Agent development on Databricks | Enterprise data platform adding agent support |

[SOURCE: Exa search, Brave search]

---

### MCP Ecosystem

| Item | Date | What | Relevance |
|------|------|------|-----------|
| **MCP SDK v1.27** | Mar 20 | TypeScript v1.27.1, Python updated | Core protocol SDK update |
| **MCP 2026 Roadmap** | Mar 20 | Transport scalability, agent-to-agent communication, governance, enterprise readiness | A2A communication is the big new direction — agents talking to agents via MCP |
| **Google MCP Toolbox for Databases** | Mar 20 | Official SDKs (Python, JS) for MCP-based DB access | Google backing MCP with first-party tooling |
| **easydns-mcp** | Mar 25 | DNS management via MCP | Niche but shows MCP adoption in infrastructure |
| **Redis MCP Server** | Mar 23 | LLM-to-Redis via MCP | Data store integration pattern |
| **claude-peers-mcp** | — | Inter-Claude messaging | Novel: MCP as agent-to-agent communication channel |

[SOURCE: modelcontextprotocol.io/development/roadmap, contextstudios.ai, marktechpost.com]

---

### Benchmarks & Evaluation

| Item | Date | What | Relevance |
|------|------|------|-----------|
| **METR PR rejection study** | Mar 10 | ~50% of SWE-bench Verified PRs by AI agents would NOT be merged by maintainers | Confirms our thesis: passing tests != production-ready code. Session-analyst should track merge-readiness, not just test-pass |
| **FieldWorkArena** (IEEE) | Mar 2026 | Safety benchmark for field-deployed agents (logistics, manufacturing) | New safety evaluation dimension |
| **AgentX AgentBeats** (Berkeley) | — | 7-dimension eval: accuracy, drift adaptation, token efficiency, error recovery, hallucination rate | Weighted composite score — most comprehensive agent eval framework seen |
| **SWE-CI benchmark** | prev week | CI-focused coding evaluation | Already covered in prior scan |

[SOURCE: metr.org, spectrum.ieee.org, rdi.berkeley.edu/agentx-agentbeats]

---

### Notable Bugs & Security

| Item | Source | What | Relevance |
|------|--------|------|-----------|
| **Claude Code config wipe** | github #37871 | SDK update (2.1.76 to 2.1.78) wipes ~/.claude/ user config and memory | Critical data-loss bug; labeled "has repro" — watch for fix |
| **Gemini CLI HITL bypass** | PR #23333 | Newline injection in command confirmations bypasses human-in-the-loop | Security: UI truncation can hide dangerous commands from approval prompts |
| **Claude SDK hook desync** | issue #739 | `control_cancel_request` silently ignored, causing hook desync | Relevant to our hook architecture — cancel semantics matter |
| **Gemini CLI agents default-off** | PR #23546 | `enableAgents` disabled by default | Conservative default; agents opt-in not opt-out |

[SOURCE: github.com/anthropics/claude-code, github.com/google-gemini/gemini-cli]

---

### Key Patterns This Week

1. **Skills explosion.** Skills are becoming the portable unit of agent knowledge. VoltAgent's awesome-agent-skills lists cross-editor compatible skills. MiniMax shipped vendor-backed skills. obra/superpowers built an entire methodology around them. Our `.claude/skills/` architecture is aligned with this trend.

2. **Agent-to-agent communication.** MCP 2026 roadmap explicitly targets A2A. claude-peers-mcp implements it today. ClawTeam coordinates via worktrees. This is the next infrastructure layer after tool-use.

3. **Security as first-class.** AgentShield in everything-claude-code, Gemini CLI HITL bypass discovery, Claude config wipe bug. Agent security is moving from "nice to have" to "blocking adoption."

4. **Cursor's RL moat.** Real-time RL from production coding sessions is a data flywheel no open-source project can replicate. Composer 2 is the first in-house model trained this way.

5. **`--bare` mode.** Claude Code v2.1.81's `--bare` flag for scripted invocations (skips hooks, LSP, plugins) — directly useful for our orchestrator.py and scripted `-p` calls.

---

### Relevance to Our Infrastructure

| Finding | Action | Priority |
|---------|--------|----------|
| `--bare` flag in v2.1.83 | Test for orchestrator.py scripted calls — may reduce overhead | High |
| claude-peers-mcp | Evaluate for multi-agent coordination (alternative to TaskOutput) | Medium |
| Claude config wipe bug (#37871) | Monitor for fix; consider backup strategy for ~/.claude/ | High |
| hook desync (#739) | Watch — could affect our hook reliability | Medium |
| AgentX 7-dimension eval | Compare to our session-features.py dimensions | Low |
| METR 50% rejection rate | Validates our code-review-scout approach | Informational |
| Gemini CLI multi-registry | Watch for skills/plugin interop patterns | Low |

---

### What's Uncertain

- OpenAI Symphony details are thin — "quietly released" per Medium post, no official docs found. [UNVERIFIED]
- Star counts from shareuhack are weekly estimates, not exact. [ESTIMATED]
- claude-peers-mcp maturity unknown — 1,109 stars but unclear if production-tested. [UNVERIFIED]
- Whether `--bare` flag persists in v2.1.83 (introduced in v2.1.81). [UNVERIFIED — check `claude --help`]

<!-- knowledge-index
generated: 2026-03-27T00:13:25Z
hash: 0b30dd4aec65

title: Agent Ecosystem Weekly — March 19-26, 2026
status: complete
tags: agent-ecosystem, weekly-scan, trending-repos, mcp, benchmarks

end-knowledge-index -->
