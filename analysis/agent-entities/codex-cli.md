---
name: Codex CLI
category: coding-agent
vendor: OpenAI
last_refreshed: 2026-04-10
status: seed
---

# Codex CLI

## Current State

- **Version:** (seed — first refresh will populate)
- **Latest release date:** (seed)
- **Pricing:** per-token via OpenAI API; bundled with ChatGPT plans for some models
- **Context window:** (seed — depends on model, GPT-5.4 and GPT-5.3-codex supported via ChatGPT auth)
- **Transport:** CLI
- **Models supported:** (seed — confirmed working with ChatGPT auth: `gpt-5.4`, `gpt-5.3-codex`; rejects `o3`, `gpt-4.1`)
- **MCP overhead:** ~37K tokens per call from 9 bundled MCP servers (no disable flag as of 2026-04)

## Recent Changes

(seed — refresh pipeline populates a dated list from GitHub releases and OpenAI changelog)

## Monitoring Triggers

Revisit our llmx routing if any of these change:

- New model supported under ChatGPT auth (specifically watch for `o3` or `gpt-4.1` support)
- MCP disable flag added (would change token overhead math in `.claude/rules/llmx-routing.md`)
- Pricing change on GPT-5.x
- CLI flag changes affecting llmx `--search`, `--max-tokens`, `--stream` behavior
- Exit code semantics change (we rely on exit 6 = billing exhausted, exit 3 = rate limit)

## Sources

- GitHub releases: `https://github.com/openai/codex` (or wherever codex-cli is published — verify on first refresh)
- OpenAI API changelog: `https://platform.openai.com/docs/changelog`
- Current llmx routing notes: `~/.claude/rules/llmx-routing.md`
