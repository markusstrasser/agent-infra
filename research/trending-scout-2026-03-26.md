---
title: "Trending Scout — March 26, 2026"
date: 2026-03-26
tags: [trending-scout, weekly-scan, vendor-updates]
status: complete
---

# Trending Scout — 2026-03-26

**Window:** 2026-03-19 to 2026-03-26
**Sources:** Exa, Brave, GitHub Releases API, official changelogs
**Findings:** 8 actionable, 12 version bumps, ~20 already-known (filtered)

---

## Actionable Findings (ranked by value - maintenance)

### 1. LiteLLM Supply Chain Incident (URGENT)

| Field | Content |
|-------|---------|
| Source | OpenAI Agents SDK v0.13.2 + Google ADK v1.27.4 (both pinned/excluded versions within 48h) |
| What | Both vendors independently pinned LiteLLM ≤1.82.6, citing compromised versions |
| Why relevant | **We depend on LiteLLM in `emb` and `paper-qa`** (`litellm>=1.0.0` and `litellm>=1.81.14`). Two competing vendors don't coordinate patches for hypothetical risks — this is real. |
| Action | **Pin `litellm<1.83` in both projects immediately** |
| Maintenance cost | One line each |
| Verdict | **Act now** |

### 2. Claude Code Hook Conditionals (v2.1.85)

| Field | Content |
|-------|---------|
| Source | [Claude Code changelog](https://code.claude.com/docs/en/changelog) |
| What | `if` field for hooks using permission rule syntax — e.g., `if: "Bash(git *)"` |
| Why relevant | Replaces shell-level argument parsing in hooks. Could simplify several existing hooks. |
| Action | Audit hooks that parse tool arguments and migrate to `if` field |
| Maintenance cost | Reduces maintenance |
| Verdict | **Adopt** |

### 3. Claude Code `CwdChanged`/`FileChanged` Hook Events (v2.1.83)

| Field | Content |
|-------|---------|
| Source | [Claude Code changelog](https://code.claude.com/docs/en/changelog) |
| What | New hook events that fire on directory change or file modification |
| Why relevant | Could enable auto-reload of rules when `.claude/rules/` changes, or react to config file updates |
| Action | Evaluate for reactive environment management |
| Maintenance cost | Low |
| Verdict | **Evaluate** |

### 4. Claude Code `--bare` Mode (v2.1.81)

| Field | Content |
|-------|---------|
| Source | [Claude Code changelog](https://code.claude.com/docs/en/changelog) |
| What | Skips hooks/LSP/plugins for scripted `-p` calls — minimal overhead mode |
| Why relevant | Could speed up orchestrator.py pipeline steps and scripted invocations |
| Action | Test with orchestrator pipeline calls |
| Maintenance cost | Zero |
| Verdict | **Adopt** |

### 5. `initialPrompt` Agent Frontmatter (v2.1.83)

| Field | Content |
|-------|---------|
| Source | [Claude Code changelog](https://code.claude.com/docs/en/changelog) |
| What | Agents can declare their initial prompt in frontmatter — auto-submits first turn |
| Why relevant | Enables fully automated agent dispatch without passing initial prompt via CLI |
| Action | Check if applicable to our agent definitions |
| Maintenance cost | Low |
| Verdict | **Evaluate** |

### 6. `taskBudget` in Agent SDK (v0.2.84)

| Field | Content |
|-------|---------|
| Source | [Agent SDK TS releases](https://github.com/anthropics/claude-agent-sdk-typescript/releases) |
| What | Programmatic token budget per task, enforced API-side |
| Why relevant | Maps directly to our cost cap enforcement — could replace custom cost tracking |
| Action | Evaluate for orchestrator cost control |
| Maintenance cost | Low |
| Verdict | **Evaluate** |

### 7. `effort` Frontmatter for Skills (v2.1.80)

| Field | Content |
|-------|---------|
| Source | [Claude Code changelog](https://code.claude.com/docs/en/changelog) |
| What | Skills can declare effort level in frontmatter, overriding model effort |
| Why relevant | Route light tasks to low effort, heavy tasks to high effort |
| Action | Audit skills and add appropriate `effort` levels |
| Maintenance cost | One-time |
| Verdict | **Adopt** |

### 8. Claude Config Wipe Bug (#37871)

| Field | Content |
|-------|---------|
| Source | [github.com/anthropics/claude-code/issues/37871](https://github.com/anthropics/claude-code/issues/37871) |
| What | SDK update (2.1.76→2.1.78) wiped ~/.claude/ user config and memory |
| Why relevant | Critical data-loss risk for our memory, hooks, settings |
| Action | Monitor for fix; consider backup strategy for `~/.claude/` |
| Maintenance cost | Backup script only |
| Verdict | **Watch + backup** |

---

## Version Bumps

| Tool | Previous | Current | Notable Changes |
|------|----------|---------|-----------------|
| Claude Code | 2.1.80 | 2.1.85 | Hook conditionals, CwdChanged/FileChanged, --bare, initialPrompt |
| Agent SDK (TS) | 0.2.80 | 0.2.85 | taskBudget, reloadPlugins, seed_read_state |
| Agent SDK (Py) | 0.1.49 | 0.1.50 | Session tags, get_session_info() |
| Codex CLI | 0.116.0 | 0.117.0 | Plugins first-class, path-based sub-agents |
| OpenAI Agents SDK | 0.13.0 | 0.13.2 | LiteLLM pinning, any-LLM adapter |
| OpenAI Python SDK | 2.29.x | 2.30.0 | Multi-modal tool outputs |
| Gemini CLI | 0.34.0 | 0.35.2 | Parallel tool scheduler, vim mode, worktree support |
| Google ADK | 1.27.x | 1.28.0 | A2A integration, LiteLLM pinning, Slack, Spanner |
| ADK 2.0 alpha | — | 2.0.0a2 | Graph-based workflow orchestration |
| Modal | 1.3.x | 1.4.0 | CLI log overhaul, sandbox filesystem API, deployment strategies |
| Kimi CLI | 1.17.0 | 1.26.0 | (9 versions behind, updated locally) |
| MCP TS SDK | 1.26.x | 1.28.0 | Protocol updates |

---

## Cross-Cutting Signals

1. **Multi-agent orchestration converging** — Codex (path-based addressing), Gemini CLI (multi-registry + tool isolation), ADK 2.0 (graph workflows). Three vendors independently building the same subagent primitives.

2. **Skills as portable knowledge units** — 6 of top 15 trending repos are skills-related. VoltAgent's awesome-agent-skills lists cross-editor compatible skills. The `agentskills.io` standard is gaining traction.

3. **Hook systems expanding everywhere** — Claude Code (hook conditionals, FileChanged), Codex (userpromptsubmit), Gemini CLI (BeforeTool 'ask' decision). Validates our hook-heavy approach.

4. **Agent security becoming first-class** — AgentShield, Gemini HITL bypass, Claude config wipe. Security is moving from "nice to have" to "blocking adoption."

5. **Cursor's RL moat** — Real-time RL from production coding sessions. Composer 2 is first in-house model. Data flywheel no open-source project can replicate.

---

## Already Known (filtered)

- MCP ecosystem growth (covered in prior research memos)
- Claude Code plugin system (already tracking)
- Everything-claude-code repo (evaluated in prior scout)
- obra/superpowers (evaluated in prior scout)
- METR benchmark findings (aligns with known thesis)

---

## Search Log

| Source | Queries | Useful Results |
|--------|---------|----------------|
| Exa | 10 queries (vendor + ecosystem) | High — good for GitHub repos and changelogs |
| Brave | 8 queries | Medium — good for triangulation, some noise |
| GitHub Releases API | Direct for Anthropic, OpenAI, Google repos | Highest signal — primary source for version details |
| WebFetch | Official changelogs | High — confirmed details |

**Source memos:** `anthropic-claude-weekly-2026-03-26.md`, `openai-google-agent-dev-2026-03-19-26.md`, `agent-ecosystem-weekly-2026-03-26.md`

<!-- knowledge-index
generated: 2026-03-27T00:27:24Z
hash: b9b6287d3141

title: Trending Scout — March 26, 2026
status: complete
tags: trending-scout, weekly-scan, vendor-updates

end-knowledge-index -->
