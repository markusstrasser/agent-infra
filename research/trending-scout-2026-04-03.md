---
title: "Trending Scout — April 3, 2026"
date: 2026-04-03
tags: [trending-scout, vendor-updates, fastmcp, claude-code]
status: complete
---

# Trending Scout — 2026-04-03

**Window:** 2026-03-29 to 2026-04-03
**Focus:** FastMCP, Claude Code
**Sources:** PyPI, GitHub Releases, official changelog, Exa, Brave
**Findings:** 3 actionable, 4 version bumps, 1 deferred trigger met

---

## New Findings

### 1. FastMCP 3.2.0 "Show Don't Tool" — Apps Architecture (March 30)

| Field | Content |
|-------|---------|
| Source | [github.com/PrefectHQ/fastmcp/releases/tag/v3.2.0](https://github.com/PrefectHQ/fastmcp/releases/tag/v3.2.0) (24K stars) |
| What it does | New `FastMCPApp` provider class: tools can return interactive UIs (charts, forms, dashboards) directly in conversations. `@app.ui()` separates visible UI from `@app.tool()` backend ops. 5 built-in providers: FileUpload, Approval, Choice, FormInput, GenerativeUI. New `fastmcp dev apps` CLI for browser-based preview + MCP message inspector. Major security hardening (SSRF/path traversal, JWT algorithm restrictions, OAuth scope enforcement, CSRF). |
| Why relevant | Apps are the FastMCP implementation of the MCP Apps spec we flagged as "watch" in the March 29 scout. FastMCP shipped it before Claude Code supports it natively. The `Approval` and `Choice` providers are interesting for human-in-the-loop gates, but need client support. The security hardening pass is independently valuable — we should update. |
| Integration path | **Update to 3.2.0** for security fixes. Apps features require MCP Apps client support (Claude Code doesn't have this yet). Watch for CC client support — when it lands, Approval provider could replace some permission hooks. |
| Current overlap | None for Apps. Security fixes are independent value. |
| Maintenance cost | Low — version bump only for now |
| Verdict | **Adopt (version bump for security)** / **Watch (Apps features)** |

### 2. FastMCP 3.1.0 "Code to Joy" — Code Mode + BM25 Search (March 3)

| Field | Content |
|-------|---------|
| Source | [github.com/PrefectHQ/fastmcp/releases/tag/v3.1.0](https://github.com/PrefectHQ/fastmcp/releases/tag/v3.1.0) |
| What it does | **Code Mode** (experimental transform): instead of loading full tool catalog, LLM gets meta-tools — searches for tools via BM25, inspects schemas, writes Python that chains `call_tool()` calls in a sandbox. Addresses context bloat from large catalogs. **Search Transforms**: standalone BM25 search over tool names/descriptions. **MultiAuth**: compose multiple token verifiers. **Lazy imports**: faster startup. |
| Why relevant | Code Mode directly addresses the tool catalog scaling problem. Our biomedical-mcp has 41 tools — with Code Mode, agents wouldn't need all 41 in context. BM25 search is the same pattern as Claude Code's deferred tools (client-side tool filtering). MultiAuth is useful if we ever share MCP servers across auth boundaries. |
| Integration path | **Evaluate Code Mode** for biomedical-mcp (41 tools) — this is where context bloat matters most. BM25 search could also help research-mcp when tool count grows. Need to test: does Claude handle the meta-tool → search → execute flow well? |
| Current overlap | Claude Code's deferred tools partially solve this client-side. Code Mode solves it server-side. |
| Maintenance cost | Medium — requires testing the meta-tool UX with Claude |
| Verdict | **Evaluate** — probe Code Mode with biomedical-mcp |

### 3. Claude Code v2.1.89 — Massive Release (April 1)

| Field | Content |
|-------|---------|
| Source | [code.claude.com/docs/en/changelog](https://code.claude.com/docs/en/changelog) |
| What it does | The largest single CC release in the window. Key new features: (1) **`"defer"` permission decision** for PreToolUse hooks — headless sessions can pause at a tool call and resume via `--resume`. (2) **`PermissionDenied` hook** — fires after auto mode denials, `{retry: true}` enables retry. (3) **`CLAUDE_CODE_NO_FLICKER=1`** — alt-screen rendering. (4) **`MCP_CONNECTION_NONBLOCKING=true`** for `-p` mode — skip MCP connection wait. (5) **Autocompact thrash loop detection** — stops after 3 compaction cycles instead of burning API calls. (6) **Hook `if` conditions** now match compound commands (`ls && git push`) and env-var prefixed commands. (7) **Hook output >50K** saved to disk with file path instead of injected into context. (8) **Edit tool works after `Bash` with `sed -n` or `cat`** — no separate Read required. (9) **PreToolUse hooks can satisfy `AskUserQuestion`** via `updatedInput` + `allow`. (10) **Thinking summaries off by default** in interactive sessions. |
| Why relevant | Several items directly improve our infrastructure: defer permission for headless orchestrator tasks; PermissionDenied hook for auto-mode recovery; hook output >50K to disk (our hooks sometimes produce verbose output); compound command matching fixes our `if` conditionals on git hooks; autocompact thrash detection prevents the cost spiral we've seen. |
| Integration path | **Adopt**: `MCP_CONNECTION_NONBLOCKING=true` for orchestrator `-p` calls. Review `defer` permission for headless pipelines. Check if `PermissionDenied` hook can replace any orchestrator retry logic. |
| Current overlap | Hook `if` conditionals already adopted in v2.1.85; this extends the matching. |
| Maintenance cost | Low — config/env var changes |
| Verdict | **Adopt** — multiple operational improvements |

---

## Version Bumps

| Tool | Previous | Current | Notable Changes |
|------|----------|---------|-----------------|
| FastMCP | 3.0.2 (local) | **3.2.0** (PyPI) | 3.1.0: Code Mode, BM25 search, MultiAuth, lazy imports. 3.1.1: pydantic-monty pin. 3.2.0: Apps, security hardening |
| MCP Python SDK | 1.26.0 (local) | **1.27.0** (PyPI) | Not investigated in detail |
| Claude Agent SDK | 0.1.44 (local) | **0.1.55** (PyPI) | 0.1.51: `fork_session()`, `delete_session()`, `task_budget`, `AgentDefinition` fields. 0.1.52: `get_context_usage()`, `Annotated` param descriptions, `tool_use_id`/`agent_id`. 0.1.53: `--setting-sources` fix, string prompt deadlock fix. 0.1.55: MCP large tool result `maxResultSizeChars` forwarding |
| Claude Code | 2.1.85 (last scout) | **2.1.91** | 7 releases. Major: defer permission, PermissionDenied hook, autocompact thrash detection, Edit after Bash, hook output to disk. See finding #3. |

---

## Deferred Item Trigger Met

**Item 8: Agent SDK `get_context_usage()`** — Now exists in Python SDK v0.1.55 (confirmed via import). Was deferred because it didn't exist in v0.1.52 Python package. `task_budget` status unknown (not in `dir()` output but may be a `query()` parameter). Update the deferred items file.

---

## Already Known (filtered out)

- MCP Apps spec (ext-apps repo) — flagged in March 29 scout as "watch"
- Codex CLI Rust rewrite — flagged in March 29 scout
- Google Gemini Skills — flagged in March 29 scout
- Agent SDK session management (fork/delete) — flagged in March 29 scout

## Actionable Summary

1. **Update FastMCP 3.0.2 → 3.2.0** — security fixes alone justify the bump
2. **Update Agent SDK 0.1.44 → 0.1.55** — `get_context_usage()`, `maxResultSizeChars` forwarding, deadlock fix
3. **Update MCP SDK 1.26.0 → 1.27.0** — keep current
4. **Set `MCP_CONNECTION_NONBLOCKING=true`** in orchestrator environment
5. **Evaluate FastMCP Code Mode** for biomedical-mcp (41-tool catalog)
6. **Update deferred items file** — mark item 8 trigger as met
7. **Review `defer` permission decision** for headless orchestrator pipelines
8. **Review `PermissionDenied` hook** for auto-mode recovery patterns

## Search Log

| Source | Query | Useful? |
|--------|-------|---------|
| WebFetch | code.claude.com/docs/en/changelog | Yes — definitive CC changelog |
| GitHub API | anthropics/claude-agent-sdk-python/releases | Yes — full release notes |
| PyPI | fastmcp | Yes — confirmed latest version |
| GitHub | PrefectHQ/fastmcp/releases | Yes — full release notes for 3.1.0, 3.1.1, 3.2.0 |
| Exa | FastMCP Python release changelog | Noisy (184K chars) — context limit essential |
| Brave | fastmcp python release 2026 | Good — triangulated PyPI version + blog posts |
| Exa | Claude Code new features update | Moderate — mostly older content |

<!-- knowledge-index
generated: 2026-04-03T19:21:07Z
hash: e74896a5d440

title: Trending Scout — April 3, 2026
status: complete
tags: trending-scout, vendor-updates, fastmcp, claude-code

end-knowledge-index -->
