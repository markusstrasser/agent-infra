---
name: Codex CLI
category: coding-agent
vendor: OpenAI
last_refreshed: 2026-06-11
status: active
---

# Codex CLI

## Current State

- **Version:** 0.139.0 (npm + local; 0.140.0-alpha.4 on 2026-06-10)
- **Latest release date:** ~2026-06-09 (0.139.0)
- **Pricing:** per-token via OpenAI API; GPT-5.5 bundled with ChatGPT subscription (our `--lite bare` $0 path)
- **Transport:** CLI; daemon-managed `codex remote-control` (0.131+); `/app` Desktop handoff (0.138)
- **Models supported:** GPT-5.5 flagship under ChatGPT auth
- **MCP:** runtime enable/disable (0.131); per-server env targeting + OAuth for streamable-HTTP servers + `readOnlyHint` concurrent execution + `$ref`/`$defs` preserved (0.134); `oneOf`/`allOf` preserved (0.139). The 2026-04 "~37K bundled-MCP overhead, no disable flag" state is obsolete
- **Config:** profiles v2 — `--profile` primary selector, legacy `[profiles.]` blocks in config.toml REJECTED, settings live in `$CODEX_HOME/.config.toml` (0.134). Our config verified clean 2026-06-11
- **Hooks:** PreToolUse/PostToolUse etc. via hooks.json; exec-path bug (#25875, hooks silently not firing under `codex exec`) fixed 2026-06-04 — canary verification on 0.139 still pending

## Recent Changes

- 2026-06-11 [trending-scout] 0.132→0.139 sweep: profiles v2 breaking (.134 — verified no local impact); MCP OAuth + readOnlyHint concurrency + schema preservation (.134/.139); multi-agent v2 + remote-control controller grants via app-server v2 RPCs (.137); `/app` desktop handoff + v2 personal access tokens + plugin `--json` (.138); hook exec bug #25875 closed 2026-06-04. https://github.com/openai/codex/releases — full detail: research/trending-scout-2026-06-11.md
- 2026-05-19 [trending-scout] 0.131: daemon-managed `codex remote-control`, runtime MCP enable/disable. research/trending-scout-2026-05-19.md

## Monitoring Triggers

Revisit our llmx routing if any of these change:

- New model supported under ChatGPT auth
- Pricing change on GPT-5.x
- CLI flag changes affecting llmx dispatch behavior
- Exit code semantics change (we rely on exit 6 = billing exhausted, exit 3 = rate limit)
- Hook contract changes (codex_hook_shim.py depends on >=0.137 output contract — see codex-cli-project-parity memory)

## Sources

- GitHub releases: `https://github.com/openai/codex/releases`
- OpenAI API changelog: `https://developers.openai.com/api/docs/changelog`
- Current llmx routing notes: `~/.claude/rules/llmx-routing.md`
