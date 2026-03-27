## Anthropic/Claude Dev Updates — Weekly Scan (2026-03-19 to 2026-03-26)

**Tier:** Quick | **Date:** 2026-03-26
**Sources:** GitHub releases, official changelogs, platform release notes, SDK releases, Exa search

---

### Claude Code Releases (v2.1.80 through v2.1.85)

| Version | Date | Key Changes | Why Relevant |
|---------|------|-------------|--------------|
| **v2.1.85** | Mar 26 | Conditional `if` field for hooks (permission rule syntax); `CLAUDE_CODE_MCP_SERVER_NAME`/`URL` env vars for MCP headersHelper; timestamp markers in `/loop` transcripts; deep links up to 5K chars | **Hook conditionals are a significant capability** — can now gate hooks on specific tool patterns like `Bash(git *)` without writing shell matchers |
| **v2.1.84** | Mar 26 | PowerShell tool (Windows, opt-in); `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL_SUPPORTS` env vars; `CLAUDE_STREAM_IDLE_TIMEOUT_MS` (default 90s); `TaskCreated` hook event; `WorktreeCreate` HTTP hook support; transcript search (`/` in transcript mode); `allowedChannelPlugins` managed setting | `TaskCreated` hook enables reactive task monitoring; stream idle timeout is configurable now (was hardcoded) |
| **v2.1.83** | Mar 25 | `managed-settings.d/` drop-in directory; `CwdChanged` + `FileChanged` hook events; `sandbox.failIfUnavailable`; `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`; agents can declare `initialPrompt` in frontmatter | **`CwdChanged`/`FileChanged` hooks** enable reactive environment management — e.g., auto-reload config when files change. **`initialPrompt`** lets agents auto-submit their first turn without user interaction |
| **v2.1.81** | Mar 20 | `--bare` flag for scripted `-p` calls (skips hooks/LSP/plugins); `--channels` permission relay (research preview) | `--bare` is important for CI/scripted use — minimal overhead mode |
| **v2.1.80** | Mar 19 | `rate_limits` field for statusline; `source: 'settings'` plugins; `effort` frontmatter for skills/commands; `--channels` research preview | `effort` frontmatter lets skills override model effort level — useful for routing light tasks to low effort |

[SOURCE: https://github.com/anthropics/claude-code/releases]
[SOURCE: https://code.claude.com/docs/en/changelog]

---

### Claude Agent SDK (TypeScript) — v0.2.80 through v0.2.85

| Version | Date | Key Changes | Why Relevant |
|---------|------|-------------|--------------|
| **v0.2.85** | Mar 26 | `reloadPlugins()` SDK method; fixed PreToolUse hooks with `permissionDecision: "ask"` in SDK mode | Plugin hot-reload without session restart |
| **v0.2.84** | Mar 26 | `taskBudget` option (API-side token budget); `enableChannel()` method; `capabilities` field on `McpServerStatus`; exported `EffortLevel` type | **`taskBudget`** enables programmatic cost control per task |
| **v0.2.83** | Mar 25 | `seed_read_state` control subtype; `session_state_changed` events now opt-in (`CLAUDE_CODE_EMIT_SESSION_STATE_EVENTS=1`) | State events opt-in reduces noise for most integrations |
| **v0.2.81** | Mar 20 | Fixed `canUseTool` suggesting `addRules` bypass for safety checks | Security fix — safety check bypass was being surfaced as suggestion |
| **v0.2.80** | Mar 19 | Fixed `getSessionMessages()` dropping parallel tool results | Bug fix for multi-tool workflows |

[SOURCE: https://github.com/anthropics/claude-agent-sdk-typescript/releases]

---

### Claude Platform / API

| Date | Change | Why Relevant |
|------|--------|--------------|
| **Mar 18** | Models API now returns `max_input_tokens`, `max_tokens`, and `capabilities` object | Programmatic model capability discovery — no more hardcoding limits |
| **Mar 16** | `thinking.display: "omitted"` for extended thinking — streaming without thinking content, signature preserved | Faster streaming for production use; reduces bandwidth while keeping multi-turn continuity |
| **Mar 13** | 1M context GA for Opus 4.6 and Sonnet 4.6 at standard pricing (no beta header); dedicated 1M rate limits removed; media limit raised to 600 images/pages | We're already on this — confirms 1M is production-ready |

[SOURCE: https://platform.claude.com/docs/en/release-notes/overview]

---

### Python SDK

| Version | Date | Key Changes |
|---------|------|-------------|
| **v0.86.0** | Mar 18 | Filesystem memory tools support; 529/413 error handling fixes; pydantic `by_alias` fix | Memory tools API support in SDK |

[SOURCE: https://github.com/anthropics/anthropic-sdk-python/releases]

No releases after Mar 18 as of this scan.

---

### MCP Ecosystem

| Date | Item | Source | Why Relevant |
|------|------|--------|--------------|
| **Mar 20** | MCP v1.27 release analysis (ecosystem post) | [Context Studios blog](https://www.contextstudios.ai/blog/mcp-ecosystem-in-2026-what-the-v127-release-actually-tells-us) | Protocol-level changes worth checking |
| **Mar 19** | Google Colab MCP server (open-source) | [MarkTechPost](https://www.marktechpost.com/2026/03/19/google-colab-now-has-an-open-source-mcp-model-context-protocol-server/) | Colab integration for remote compute |
| **Mar 25** | easyDNS MCP server for DNS management | [easyDNS blog](https://easydns.com/blog/2026/03/25/easydns-mcp-model-context-protocol-server-for-the-rest-api-now-available/) | Niche but shows MCP adoption breadth |
| **Mar 23** | Redis MCP server | [mcp-ai.org](https://mcp-ai.org/server/redis-modelcontextprotocol) | Redis as MCP data layer |

[SOURCE: Exa search, date-filtered 2026-03-19+]

---

### Deprecation Notices

| Model | Status | Deadline |
|-------|--------|----------|
| Claude Haiku 3 (`claude-3-haiku-20240307`) | Deprecated | **April 19, 2026** |
| Claude Opus 4 and 4.1 | Removed from model selector | Already removed |

[SOURCE: https://support.claude.com/en/articles/12138966-release-notes]

---

### Items Directly Relevant to Our Agent Infrastructure

1. **Hook conditionals (v2.1.85)** — `if` field using permission rule syntax means we can write hooks like `if: "Bash(git *)"` instead of shell-level argument parsing. Check if this simplifies any existing hooks.

2. **`CwdChanged`/`FileChanged` events (v2.1.83)** — could replace file-watcher patterns. Potential use: auto-reload rules when `.claude/rules/` files change.

3. **`initialPrompt` frontmatter (v2.1.83)** — agents can auto-submit their first turn. Useful for fully automated agent dispatch without needing to pass the initial prompt via CLI.

4. **`--bare` mode (v2.1.81)** — minimal overhead for scripted `-p` calls. Could speed up orchestrator pipeline steps.

5. **`taskBudget` in Agent SDK (v0.2.84)** — programmatic token budget per task. Maps to our cost cap enforcement.

6. **`thinking.display: "omitted"` (Platform, Mar 16)** — streaming without thinking content. Could reduce bandwidth for production API integrations.

7. **`effort` frontmatter for skills (v2.1.80)** — skills can declare their effort level. We should audit skills to add appropriate effort levels.

8. **MCP v1.27** — need to check what protocol-level changes landed (unverified blog post, needs primary source check).

---

### Not Covered (filtered out)

- Tech journalism / hype pieces about Claude capabilities
- Blog posts explaining "what is MCP" (tutorial content, not releases)
- Product launches without code (Claude apps features, Cowork updates)
- Bun/Anthropic acquisition coverage (not agent infrastructure)

<!-- knowledge-index
generated: 2026-03-27T00:12:24Z
hash: 2f65d16b2263


end-knowledge-index -->
