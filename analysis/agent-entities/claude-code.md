---
name: Claude Code
category: coding-agent
vendor: Anthropic
last_refreshed: 2026-06-11
status: active
---

# Claude Code

## Current State

- **Version:** 2.1.172 (npm latest; changelog documented to 2.1.170)
- **Latest release date:** ~2026-06-10
- **Pricing:** per-token via Claude API, plan-bundled via Claude subscriptions; fast mode = Opus at premium pricing
- **Context window:** model-dependent; up to 1M (Fable 5, Opus long-context)
- **Transport:** CLI (terminal), desktop app (Mac/Windows), web app (claude.ai/code), IDE extensions (VS Code, JetBrains)
- **Models supported:** Fable 5 (default flagship), Opus 4.8/4.7/4.6 (fast mode default 4.7), Sonnet 4.6, Haiku 4.5
- **Hook events:** 31 documented event types (PreToolUse, PostToolUse, Stop, SubagentStart/Stop, Session/Worktree/Compact lifecycle, MessageDisplay, InstructionsLoaded, PermissionRequest, …); 5 handler types incl. `mcp_tool`; Stop-family hooks return `hookSpecificOutput.additionalContext` (2.1.163)
- **SDK:** claude-agent-sdk-python 0.2.96; claude-agent-sdk-typescript 0.3.172 (separate versioning from raw `@anthropic-ai/sdk` 0.104.1)

## Recent Changes

- 2026-06-11 [trending-scout] 2.1.145→2.1.172 sweep: `--safe-mode`/`CLAUDE_CODE_SAFE_MODE` clean-room flag (.169); Stop/SubagentStop `additionalContext` (.163); `disallowed-tools` skill frontmatter + `/reload-skills` + SessionStart `reloadSkills:true` (.152); MessageDisplay hook (.152); stdio MCP servers get `CLAUDE_CODE_SESSION_ID`+`CLAUDECODE=1` (.154); MCP reconnect summarizes tools (.147). Dynamic Workflows GA (.154). TS agent-SDK 0.3.162 breaking: Grep/Glob opt-in on native builds. Issue #32105 closed, feature NOT shipped (likely declined). Agent Teams still research preview. https://code.claude.com/docs/en/changelog — full detail: research/trending-scout-2026-06-11.md
- 2026-05-19 [trending-scout] 2.1.117→2.1.144: mcp_tool hook type (.118), duration_ms (.121), effort.level in hooks (.133/.141), hooks.args exec form (.139), skillOverrides (.128); SDK break TodoWrite→TaskCreate/Update/Get/List + MCP non-blocking startup (py 0.2.82 / ts 0.3.142). research/trending-scout-2026-05-19.md

## Monitoring Triggers

Revisit our infrastructure if any of these change:

- New hook event type added (affects hooks design)
- New frontmatter field on skills (affects skill authoring)
- Tool output compression lands (tracked in `research/claude-code-native-features-deferred.md`; issue #32105 CLOSED 2026-06 without shipping — watch for a replacement issue/feature)
- Agent Teams feature stabilization (deferred item)
- SDK signature change on `query()` options, hook input fields, or tool schemas
- New CLI flag that replaces an existing custom script
- Pricing model change

## Sources

- Changelog: `https://code.claude.com/docs/en/changelog`
- Python SDK releases: `https://github.com/anthropics/claude-agent-sdk-python/releases`
- TypeScript SDK releases: `https://github.com/anthropics/claude-agent-sdk-typescript/releases`
- Issue tracker (features we watch): `https://github.com/anthropics/claude-code/issues`
- Cookbook: `https://platform.claude.com`
