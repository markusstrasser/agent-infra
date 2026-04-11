---
name: Claude Code
category: coding-agent
vendor: Anthropic
last_refreshed: 2026-04-10
status: seed
---

# Claude Code

## Current State

- **Version:** (seed — first refresh will populate)
- **Latest release date:** (seed)
- **Pricing:** (seed — per-token via Claude API, plan-bundled via Claude subscriptions)
- **Context window:** (seed — varies by model, up to 1M for Opus 4.6)
- **Transport:** CLI (terminal), desktop app (Mac/Windows), web app (claude.ai/code), IDE extensions (VS Code, JetBrains)
- **Models supported:** (seed)
- **Hook events:** (seed — PreToolUse, PostToolUse, Stop, SessionStart, etc.)
- **SDK:** claude-agent-sdk-python, claude-agent-sdk-typescript

## Recent Changes

(seed — refresh pipeline populates a dated list from changelog diffs)

## Monitoring Triggers

Revisit our infrastructure if any of these change:

- New hook event type added (affects hooks design)
- New frontmatter field on skills (affects skill authoring)
- Tool output compression lands (tracked in `research/claude-code-native-features-deferred.md` as issue #32105)
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
