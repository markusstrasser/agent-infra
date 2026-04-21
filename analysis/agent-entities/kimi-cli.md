---
name: Kimi CLI
category: coding-agent
vendor: Moonshot AI
last_refreshed: 2026-04-21
status: active
---

# Kimi CLI

## Current State

- **Version:** 1.37.0 (PyPI latest as of 2026-04-21)
- **Latest release date:** 2026-04-20 (1.37.0)
- **Pricing:** Pay-per-token via Moonshot API. No bundled-subscription auth. See `research/kimi-k2.6-release-2026-04-20.md` for current rates (K2.6: $0.95 / $0.16 cached / $4.00 per MTok, long-context tier).
- **Context window:** 262,144 tokens on K2.6.
- **Transport:** CLI (Python, installed via `uv tool install kimi-cli`). Experimental wire protocol + ACP server (`kimi acp`) for editor integration.
- **Models supported (K2.6-family):** `kimi-k2.6` (canonical). Pre-K2.6 legacy: `kimi-k2-0905-preview`, `kimi-k2-thinking`, `kimi-k2-turbo-preview`, `kimi-k2-thinking-turbo`, `kimi-k2-0711-preview`. Thinking is a runtime flag (`chat_template_kwargs.thinking`) on K2.6, not a separate model ID. Provider layer also fronts Anthropic, OpenAI, Gemini, Vertex.
- **Hook events:** 13 — `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `UserPromptSubmit`, `Stop`, `StopFailure`, `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact`, `Notification`. Protocol: JSON over stdin, exit 2 = block, regex `matcher` per hook. Same contract as Claude Code (verified from `kimi_cli/hooks/events.py`).
- **Skills:** Native SKILL.md + YAML frontmatter (open agentskills.io standard). Discovery roots: `$REPO/.kimi/skills/`, `~/.kimi/skills/`, plus native discovery of `~/.claude/skills/` and `~/.agents/skills/`.
- **Local wiring:** `~/.kimi/skills` → `~/Projects/skills` symlink (2026-04-17). `~/.kimi/mcp.json` has 14 servers (exa, phenome, genomics, genomics-consumer, research, agent-infra, parallel, context7, brave-search, biomedical, biomcp, paperclip, perplexity, scite). `~/.kimi/config.toml` `[[hooks]]` registers SessionStart (Session-ID trailer) and PreToolUse:Write|Edit (append-only-guard).

## Our Integration Status (2026-04-21)

- **agentlogs adapter:** `src/agentlogs/adapters/kimi.py` ingests `~/.kimi/sessions/` (both new UUID.jsonl and old UUID/context.jsonl layouts). Launchd watcher includes `~/.kimi/sessions`. Probe ingest: 89 sources / 13,864 events / 0 failures.
- **Commit attribution:** SessionStart hook writes `kimi:<session_id>` to `.claude/current-session-id`; `prepare-commit-msg-session-id.sh` picks it up.
- **Hook probe:** `/tmp/kimi-hook-probe.log` captures first 5 SessionStart invocations for protocol verification. Remove after confirming.

## Recent Changes

- **2026-04-20 (1.37.0):** auto-refresh managed models at startup, API `display_name` surfaced, agent-loop kept alive during background tasks, TOML-dotted-model-name doc fix.
- **2026-04-17 (1.36.0):** `max_steps_per_turn` 100 → 500; Opus 4.7 adaptive-thinking support.
- **2026-04-15 (1.35.0):** `show_thinking_stream=true` default.
- **2026-04-20:** Kimi K2.6 model GA (1T MoE, 32B active, 262K context, native video-in, SWE-Bench Verified 80.2%, HLE 54% #1, Terminal-Bench 2.0 66.7%). See `research/kimi-k2.6-release-2026-04-20.md`.

## Monitoring Triggers

Revisit our harness integration if any of these change:

- New hook event type added (Kimi currently strictly more hookable than Claude/Codex; widen coverage if a high-value event appears).
- Custom slash command authoring surface ships (currently only `/skill:name` / `/flow:name` namespaced — closing this gap would make Kimi drop-in interchangeable with Claude).
- Named sandbox modes (currently binary yolo/prompt; Codex-style `read-only / workspace-write / danger-full-access` would enable trust-calibrated execution).
- Bundled-subscription auth (currently API key only — would change cost-routing math).
- K2.6 API parameter changes (thinking flag, reasoning field names) — broke once on 2026-04-20 when `enable_thinking` → `chat_template_kwargs.thinking`.
- Breaking changes in `kimi_cli/hooks/events.py` event payload shape.

## Sources

- PyPI: `https://pypi.org/project/kimi-cli/`
- Moonshot platform: `https://platform.moonshot.ai` and `https://platform.kimi.ai/docs/`
- Hook protocol (source of truth): `~/.local/share/uv/tools/kimi-cli/lib/python3.13/site-packages/kimi_cli/hooks/`
- Our integration memos: `research/trending-scout-2026-04-21-kimi-cli.md`, `research/kimi-k2.6-release-2026-04-20.md`
