---
title: "Trending Scout — Kimi CLI Parity (2026-04-21)"
date: 2026-04-21
tags: [trending-scout, vendor-updates, kimi-cli, parity-matrix]
status: complete
---

# Kimi CLI Update Sweep + Parity Check (2026-04-21)

**Verified local state:** `kimi --version` → **1.37.0** (latest; vendor-versions reading of 1.36.0 was stale — already on latest). `~/.kimi/skills` → `~/Projects/skills` symlink confirmed (set 2026-04-17). `~/.kimi/mcp.json` has: exa, phenome, genomics-consumer, genomics, research, agent-infra, parallel — overlap with Claude Code and Codex configs. Default model `moonshot-ai/kimi-k2.6`, 262K context. Auth: Moonshot API key in `credentials/`.



**Verdict:** Kimi CLI is at **rough feature parity** with Claude Code and Codex CLI on the primitives we use — skills, hooks, subagents, MCP, print mode, plugins. It is genuinely ready for *coding-agent* workloads and could drop into our harness with minimal adaptation. The one real gap: no bundled-subscription auth (Moonshot API key only) and no dedicated sandbox-mode flags like Codex's `workspace-write`/`danger-full-access`. Kimi is ready for **routine code edits, hook-enforced workflows, and MCP-backed research**; not ready as a **Claude/ChatGPT plan substitute** (pay-per-token only) and weaker for **sandbox-sensitive execution** (permission model is binary yolo/prompt).

## Parity Matrix

| Feature | Claude Code 2.1 | Codex CLI 0.122 | Kimi CLI 1.37 |
|---|---|---|---|
| Skills (SKILL.md + YAML frontmatter, auto-invoke) | yes | yes | **yes** |
| Skills discovery paths our symlink hits | `~/.claude/skills` | `~/.agents/skills` | **`~/.kimi/skills` + reads `~/.claude/skills` and `~/.agents/skills` natively** |
| Hooks (Pre/PostToolUse, Stop, SessionStart, UserPromptSubmit) | yes, 5+ events | 5 events (no PostToolUse) | **yes — 13 events** (includes PreCompact/PostCompact, SubagentStart/Stop, Notification) |
| Slash commands | yes, skills auto-register as `/name` | built-ins only | **partial — `/skill:<name>` and `/flow:<name>` namespaced** |
| MCP server support | yes | yes + marketplace | **yes — stdio/http/OAuth, `kimi mcp add/list/auth/test`** |
| Plugin/marketplace | `.claude-plugin` | `.codex-plugin` + marketplace | **`kimi plugin install/list/remove`** (beta, no public marketplace yet) |
| Project instructions file | `CLAUDE.md` | `AGENTS.md` | **reads `.claude/skills`, `.agents/skills`, `.kimi/skills`** — no dedicated project-prompt file documented |
| SDK | Python + TS | CLI + exec-server | **Wire protocol (experimental), ACP server, `kimi acp`** |
| Session resume/fork | yes | yes | **yes — `-r`, `-C`, `/sessions`, `/new`, `/export`, `/import`** (no explicit fork) |
| Sandbox modes | yes | read-only / workspace-write / danger | **no named modes — yolo vs interactive approval only** |
| Headless exec | Agent SDK | `codex exec` | **`kimi --print` with `--output-format stream-json`, exit codes 0/1/75** |
| Subagent / multi-agent | yes (Task tool) | yes | **yes — `Agent` tool, built-ins: `coder`, `explore`, `plan`; YAML-defined custom** |

## Answers to Direct Questions

1. **Native extension surface:** Skills (`SKILL.md` in `~/.kimi/skills/`, `.kimi/skills/` project-level, **plus native discovery of `~/.claude/skills` and `~/.agents/skills`** — our existing symlink at `~/.kimi/skills → ~/Projects/skills` already works). Plugins bundle Skills + custom Tools via `plugin.json`. Hooks via `[[hooks]]` in `~/.kimi/config.toml` with JSON-over-stdin / exit-code protocol (exit 2 = block with stderr fed back to LLM — same pattern as Claude).
2. **Models:** `kimi-k2.6` (default, 262K ctx), `kimi-k2.5`, `kimi-k2-thinking-turbo`, `kimi-k2-turbo-preview`, `kimi-k2-0905-preview`, `kimi-k2-0711-preview` (131K), `kimi-k2-thinking`. All support image-in / video-in / thinking modes. Provider layer also supports Anthropic, OpenAI, Gemini, Vertex — Kimi CLI can front other vendors.
3. **Auth:** Moonshot API key (`/login` → key paste). Local config shows `sk-nooM6y...` direct against `https://api.moonshot.ai/v1`. **No ChatGPT-Plan-equivalent bundled subscription.** `managed:moonshot-ai` provider hints at auto-refresh for managed-list of models (new in 1.37) but still pay-per-token underneath.
4. **1.37.0 notable (Apr 20):** auto-refresh managed models at startup, API `display_name` surfaced, agent-loop kept alive during background tasks, TOML-dotted-model-name doc fix. **No breaking changes** between 1.35 → 1.36 → 1.37. 1.36 bumped `max_steps_per_turn` 100 → 500 and added Opus 4.7 adaptive-thinking support.
5. **Cost:** Pay-per-token via Moonshot API; docs don't list pricing in CLI configuration pages. No free-tier subscription bundled. Rate limits not documented in CLI docs (check Moonshot platform dashboard).
6. **Honest tradeoffs if we route work to Kimi:**
   - **Gain:** free reuse of our entire skills corpus (already symlinked and natively discovered), 13-event hook system (more events than either Claude or Codex), 262K context on K2.6, Anthropic/OpenAI/Gemini pass-through for multi-provider from one CLI.
   - **Give up:** bundled subscription economics; explicit sandbox mode separation (only yolo vs prompt); `CLAUDE.md`-style auto-loaded project instructions (skills are the mechanism — fine, just different convention); slash-command namespace (skills must be invoked as `/skill:name`, not `/name`); mature subagent ecosystem Claude Code has.

## Recommended Use in Our Harness

- Wire Kimi as **third tier** for K2.6-specific work (long context, tool-heavy coding where Moonshot cost per token beats GPT-5.4).
- Our existing symlink `~/.kimi/skills → ~/Projects/skills` is already correct — no config change needed.
- Port a minimal `[[hooks]]` set (bash-loop-guard, unsourced-claim detector) to validate the protocol, then decide on wider adoption.
- Do **not** retire Claude Code or Codex — Kimi's value is additive (cheap long-context K2.6 + Anthropic/GPT pass-through), not replacement.

<!-- knowledge-index
generated: 2026-04-21T16:26:26Z
hash: 7866d8afc1af

title: Trending Scout — Kimi CLI Parity (2026-04-21)
status: complete
tags: trending-scout, vendor-updates, kimi-cli, parity-matrix

end-knowledge-index -->
