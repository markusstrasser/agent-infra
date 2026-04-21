---
title: "Trending Scout — Claude Code + Codex CLI (2026-04-21)"
date: 2026-04-21
tags: [trending-scout, vendor-updates, claude-code, codex-cli]
status: complete
---

# Trending Scout — Claude Code + Codex CLI (2026-04-21)

**Window:** 2026-04-05 (last full scout) → 2026-04-21
**Sources:** code.claude.com/docs/en/changelog; GitHub releases for anthropics/claude-agent-sdk-{python,typescript}, openai/codex; issues #32105, #17588, Agent Teams cluster.
**Baseline:** Claude Code 2.1.92 → **2.1.116** (24 patch releases). Codex CLI (unknown prior) → **0.122.0** (4 stable releases: 0.119, 0.120, 0.121, 0.122).

---

## Headline

Both vendors shipped genuinely consequential changes in the window, not just patch noise.

- **Anthropic:** PreCompact hook can now block (exit 2 / decision:block); default effort was silently bumped medium→high on API-key/Bedrock/Vertex/Team/Enterprise (token-spend leak); 1h prompt cache is now opt-in; Agent Teams is still not stable (multiple open architectural issues); tool-output-compression #32105 still OPEN.
- **OpenAI:** **#17588 closed** — MCP / plugin / app disable flags via `-c` and profiles are now honored. **This invalidates the "37K-token veto" in `vetoed-decisions.md`** until we re-measure. Plugin marketplace system (0.121-0.122) is a major new surface. ChatGPT-auth model list reshuffled on 2026-04-14: `gpt-5.2-codex` and 5.1.x family deprecated; `o3` / `gpt-4.1` still unsupported.

---

## Claude Code v2.1.93 → v2.1.116

### Hooks (highest priority for our infra)
- **2.1.105 — PreCompact is now blockable** via `exit 2` / `{"decision":"block"}`. Actionable: guard compactions before `checkpoint.md` write.
- **2.1.110** — fixed `PreToolUse additionalContext` being silently dropped on tool failure; `PermissionRequest updatedInput` now re-checked against `permissions.deny`.
- **2.1.101** — `permissions.deny` rules now override `PreToolUse` hooks' `permissionDecision:"ask"` (hooks could previously downgrade deny → prompt). Audit our deny rules post-upgrade.
- **2.1.94** — `hookSpecificOutput.sessionTitle` on `UserPromptSubmit`; plugin skill hooks in YAML frontmatter no longer silently ignored.
- **2.1.105 → 2.1.110** — stdio MCP servers were briefly disconnected on first stray stdout line (regression 2.1.105, fix 2.1.110). Re-verify `agent_infra_mcp.py` stdout discipline.
- **2.1.116** — agent-frontmatter `hooks:` fire under `--agent`.

### Skills
- **2.1.105** — description cap 250 → 1,536 chars.
- **2.1.101** — `context: fork` and `agent` frontmatter fields finally honored (relevant for skill isolation).
- **2.1.110** — `disable-model-invocation: true` now works with `/<skill>` mid-message.
- **2.1.94** — plugin `"skills": ["./"]` uses frontmatter `name` not dir basename.

### SDK
- **Python v0.1.57–v0.1.64** — `"auto"` PermissionMode; `exclude_dynamic_sections`; top-level `skills` option; `setting_sources=[]` no longer silently dropped; **full `SessionStore` protocol** (append/load/list/delete/list_subkeys) with reference S3/Redis/Postgres adapters + conformance harness; `list_subagents()` / `get_subagent_messages()`; TRACEPARENT propagation.
- **TS v0.2.111** shipped a **breaking `options.env` overlay change** that v0.2.113 flipped back to replacing. Watch for env regressions on any TS SDK bump.

### Pricing / routing
- **2.1.108 — `ENABLE_PROMPT_CACHING_1H`** opt-in on API key / Bedrock / Vertex / Foundry. Real cost win for long sessions.
- **2.1.94 — default effort bumped medium → high** on API-key / Bedrock / Vertex / Team / Enterprise. **Silent token-spend increase** unless `/effort` is pinned. Audit.
- **2.1.111** — Opus 4.7 `xhigh` GA; Auto mode GA for Max subs.

### Tool behavior
- **2.1.105** — `WebFetch` strips `<style>`/`<script>`; API streams abort after 5min no-data + retry non-streaming.
- **2.1.110** — Bash enforces documented max timeout; subagents stalled mid-stream fail after 10min.
- **2.1.98** — multiple Bash permission-bypass patches (backslash-escaped flags, compound commands, env-var prefixes, `/dev/tcp` redirects). Audit allow rules.
- **2.1.98** — new `Monitor` tool for streaming background scripts; `--exclude-dynamic-system-prompt-sections`; `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`.
- **2.1.113** — `ToolSearch` ranking fix (pasted MCP tool names now resolve correctly).

### Tracked issues
- **#32105 tool-output compression → OPEN** (enhancement, area:hooks). No merge. Our mitigations (`isolation:"worktree"`, grep-over-read) remain load-bearing.
- **Agent Teams → not stable.** Open: #39699 (stale-message feedback loop), #36670 (teammates don't inherit `[1m]` context window from leader), #35072 (no interrupt mechanism). 2.1.114 fixed one permission-dialog crash only. **Defer building workflows on Agent Teams.**

---

## Codex CLI 0.119–0.122

### MCP overhead — materially improved ★
- **Issue #17588** ("Config/profile disables for connectors, apps, plugins ignored") **closed completed 2026-04-13**, within the 0.121 window.
- `-c mcp_servers.<name>.enabled=false`, `apps.<name>.enabled=false`, `plugins."<name>".enabled=false` via `-c` or profile blocks are now honored.
- **0.121** added namespaced MCP registration + parallel-call opt-in + sandbox-state metadata.
- **0.122** added inline enable/disable toggles in plugin workflows.
- **Action:** re-measure codex-cli token overhead on 0.122.0 with a `cli-lite` profile (all MCPs disabled). If overhead is now <5K, retire the "not for trivial queries" veto in `vetoed-decisions.md`.

### ChatGPT-auth model list (post-2026-04-14)
- **Supported:** `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex`, `gpt-5.3-codex-spark` (Pro only), `gpt-5.2`.
- **Deprecated/removed:** `gpt-5.2-codex`, `gpt-5.1-codex-{mini,max}`, `gpt-5.1-codex`, `gpt-5.1`, `gpt-5`.
- **Still unsupported:** `o3`, `gpt-4.1`. `llmx-routing.md` routing stays correct.

### Plugin marketplace (major new surface)
- **0.121** — `codex marketplace add <source>` (GitHub / git URL / local dir / direct `marketplace.json`).
- **0.122** — tabbed browsing, inline enable/disable, remote + cross-repo marketplaces.
- **Potential alternative** to our skills-symlink distribution across projects — worth a probe memo if we revisit skills propagation.

### Flags / exit codes
- `--search`, `--max-tokens`, `--stream` unchanged.
- Exit 3 (rate limit) / exit 6 (billing exhausted) unchanged — llmx-routing semantics hold.
- New: `codex exec-server` experimental (0.119), isolated `codex exec` ignoring user config (0.122), `codex marketplace add`.

### Other notable
- **Plan Mode fresh-context handoff** (0.122) — shows context usage before deciding carry-forward. Possibly replaces our `.claude/plans/` handoff convention for Codex sessions.
- **TUI `/side` conversations** (0.122) — side questions without touching main thread.
- **Queued slash commands + `!` shell while running** (0.122).
- **Realtime v2 background agent streaming** (0.119–0.120) — relevant to orchestrator model.
- **Secure devcontainer profile with bubblewrap** (0.121) — hermetic runs.
- **SessionStart hook distinguishes `/clear` vs fresh startup** (0.120).

### Pricing
- No GPT-5.x API pricing changes surfaced.
- ChatGPT Business $25 → $20/seat (separate product). Codex-only pay-as-you-go seats now available on Business/Enterprise.

---

## Action Items (ranked)

1. **Re-measure Codex CLI MCP overhead on 0.122.0** with `-c mcp_servers.*.enabled=false` or a `cli-lite` profile. If ≪37K, update `vetoed-decisions.md` — the veto may no longer apply.
2. **Audit `/effort` default** on Claude Code post-2.1.94 bump (medium → high). Likely silent token-spend increase on API-key sessions. Either pin `medium` for routine work or accept the cost.
3. **Enable `ENABLE_PROMPT_CACHING_1H=1`** for API-key sessions (2.1.108). Cost win on long sessions.
4. **Add PreCompact hook guard** against compaction before `checkpoint.md` is written (2.1.105 capability).
5. **Verify `agent_infra_mcp.py` stdout discipline** — never print non-JSON to stdout. The 2.1.105 regression was fixed in 2.1.110 but strict stdio is the safe contract.
6. **Do not migrate workflows to Claude Code Agent Teams yet** — #39699, #36670, #35072 all open. Message-delivery and context-inheritance are architecturally broken.
7. **Populate entity files** — `analysis/agent-entities/claude-code.md` and `codex-cli.md` are still seed state. This sweep has enough data to fill Current State + Recent Changes. Hand off to the next `agent-entity-refresh` pipeline run.
8. **Probe Codex plugin marketplace** as a skills-distribution alternative — separate research memo.

---

## Addendum: Codex Skills & Plugins — Are They Compatible With Ours?

**Verdict: yes, already compatible. No fork needed.**

- Codex adopted the same `SKILL.md` + YAML-frontmatter contract as Claude Code (agentskills.io "open agent skills standard"). Same auto-invocation via `description`.
- Discovery roots (from `codex-rs/core-skills/src/loader.rs`): `$REPO/.agents/skills/`, `$HOME/.agents/skills/`, `/etc/codex/skills`, embedded system skills.
- **`~/.agents/skills` → `~/Projects/skills` symlink already exists** (set up 2026-03-04). Our corpus is already available to Codex sessions.
- Codex's marketplace loader (`codex-rs/core-plugins/src/marketplace.rs`) reads **both** `.agents/plugins/marketplace.json` AND `.claude-plugin/marketplace.json` — explicitly targets Claude-compatible layouts.
- Plugin format (`.codex-plugin/plugin.json`) is the *distribution wrapper*: `{manifest + skills/ + .mcp.json + .app.json + interface metadata}`. Skills do the work; plugin is for marketplace + install UX.

**Feature-parity deltas:**

| Axis | Claude Code | Codex | Impact |
|------|-------------|-------|--------|
| Slash-invocation | `/skill-name` auto | `$skill-name` or `/skills` picker | cosmetic |
| Hooks | PreToolUse, PostToolUse, Stop, SessionStart, UserPromptSubmit | SessionStart, UserPromptSubmit, PreToolUse, **PermissionRequest** (new v0.121), Stop | **no PostToolUse** in Codex — our unsourced-claim hook won't run in Codex sessions |
| Custom slash commands | every skill auto-registers as `/name` | built-ins only | Codex UX regression for explicit invocation |
| Plugin manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` | similar shape, not drop-in identical |
| Marketplace | `.claude-plugin/marketplace.json` | reads both paths | Codex is strictly more permissive |

**Action:** Test one skill in a Codex session to confirm end-to-end loading from the existing symlink. Wrap as `.codex-plugin/plugin.json` only if we publish externally. Track whether Codex adds custom-slash-command authoring — would close the last UX gap. Accept the PostToolUse gap in Codex sessions or replicate logic as a `Stop` hook.

---

## Search Log

- WebFetch code.claude.com/docs/en/changelog ✓
- GitHub API: claude-agent-sdk-python, claude-agent-sdk-typescript, openai/codex releases ✓
- Issue check: #32105 (still open), #17588 (closed 2026-04-13), Agent Teams cluster (#39699, #36670, #35072 all open) ✓
- OpenAI platform changelog: 403 (blocked) — used GitHub release notes + The Tech Outlook model-deprecation article as fallback.
- Not searched: alphaXiv, arxiv (scoped to vendor sweep).

<!-- knowledge-index
generated: 2026-04-21T16:23:41Z
hash: 822aec226191

title: Trending Scout — Claude Code + Codex CLI (2026-04-21)
status: complete
tags: trending-scout, vendor-updates, claude-code, codex-cli
cross_refs: analysis/agent-entities/claude-code.md
table_claims: 3

end-knowledge-index -->
