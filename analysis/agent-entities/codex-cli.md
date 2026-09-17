---
name: Codex CLI
category: coding-agent
vendor: OpenAI
last_refreshed: 2026-09-17
status: active
---

# Codex CLI

## Current State

- **Version:** 0.154.0 (npm, 2026-09-09; local 0.153.4)
- **Latest release date:** 2026-09-09 (0.154.0)
- **Pricing:** per-token via OpenAI API; GPT-6 Astra ($10/$50, GA 2026-09-03) + GPT-5.6 Sol/Terra/Luna bundled with ChatGPT subscription (our `llmx chat --subscription` $0 path). Sol promo $4/$20 through at least 2026-11-21
- **Transport:** CLI; daemon-managed `codex remote-control` (0.131+); `/app` Desktop handoff (0.138)
- **Models supported:** GPT-6 Astra flagship, GPT-5.6 family under ChatGPT auth; reasoning effort now includes `ultra` above `max` (0.149 SDK)
- **MCP:** runtime enable/disable (0.131); per-server env targeting + OAuth for streamable-HTTP servers + `readOnlyHint` concurrent execution + `$ref`/`$defs` preserved (0.134); `oneOf`/`allOf` preserved (0.139). The 2026-04 "~37K bundled-MCP overhead, no disable flag" state is obsolete
- **Config:** profiles v2 — `--profile` primary selector, legacy `[profiles.]` blocks in config.toml REJECTED, settings live in `$CODEX_HOME/.config.toml` (0.134). Our config verified clean 2026-06-11
- **Skills:** open agent skills standard (`SKILL.md`); discovers `~/.agents/skills` + repo `.agents/skills` (we symlink via `codex_parity_sync.py` / `sync_agent_skills.py`). `~/.codex/skills` is left for Codex-bundled `.system/` only — we do not mirror managed skills there. Progressive disclosure; ~8k char skills index budget. No `Skill` tool in agentlogs — loads via `exec_command` reads of SKILL.md. [SOURCE: developers.openai.com/codex/skills]
- **Hooks:** PreToolUse/PostToolUse etc. via hooks.json; exec-path bug (#25875, hooks silently not firing under `codex exec`) fixed 2026-06-04 — canary verification on 0.139 still pending. **0.141 (Jun 18): blocking PostToolUse hooks now correctly reject code-mode tool calls** (previously NOT gated) — re-check `codex_hook_shim.py` enforcement assumptions
- **Tool timeout:** 300s ceiling (0.141)

## Recent Changes

- 2026-09-17 [trending-scout] 0.146→0.154: `codex mcp-server` entry point REMOVED (.154 — no callers here); planning tool off by default, `tools.update_plan.enabled=true` restores (.152); experimental `--worktree`/`/worktree` isolated checkouts (.154); async hooks + MCP-tool hook invocation (.148 — re-run `codex_hook_shim` canary); `Interrupt` hook (.150); `codex queue`/`codex agents`/`codex exec fork` (.148–.149); `--approve-for-me` Guardian LLM-judge approvals (.147+); per-tool MCP `output_token_limit` (.152); `--full-auto` removed (.147); MCP SDK 3.0 w/ opt-in 2026-07-28 protocol (.147); `context_management.experimental_mode` ChatGPT-auth only (.153). research/trending-scout-2026-09-17.md
- 2026-06-19 [trending-scout] 0.139→0.141: blocking PostToolUse now gates code-mode calls + hook-trust persists through `codex exec` resume (.141); per-thread stdio MCP servers (.141); tool timeout→300s (.141); `/usage` daily/weekly/cumulative token views (.140); `codex delete`/`/delete` permanent session deletion (.140 — append-only conflict, do NOT wire); MCP transient-startup retries + corrupt-SQLite auto-rebuild (.140). research/trending-scout-2026-06-19.md
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
- Transport facts: `llmx info` / `~/.claude/cache/llmx-routing.json`; model choice: model-guide skill
