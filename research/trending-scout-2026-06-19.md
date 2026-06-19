---
title: "Trending Scout — 2026-06-19 (4-day diff)"
date: 2026-06-19
tags: [trending-scout, claude-code, codex, cursor, mcp, vendor-updates]
status: complete
window: 2026-06-15 → 2026-06-19
prior: research/trending-scout-2026-06-15.md
---

# Trending Scout — 2026-06-19

**Window:** 2026-06-15 → 2026-06-19 (4 days)
**Sources:** vendor-versions.py, CC changelog, Agent SDK ts/py releases, Codex releases + changelog, openai-agents-python, Cursor changelog, Gemini API/CLI, modelcontextprotocol, arxiv/alphaXiv (403), GitHub trending
**Findings:** 6 infra-relevant (3 evaluate, 2 adopt-on-upgrade, 1 extract-pattern), 7 version bumps, Cursor CLI `/review` still NOT shipped (watch unchanged)

---

## Headline

**Active vendor window on the harness layer — model layer quiet.** Claude Code shipped 6 point releases (2.1.177→2.1.183) with two genuinely useful primitives: **`Tool(param:value)` permission rules** (e.g. `Agent(model:opus)` to block Opus subagents — a settings-level model-routing/cost gate that could replace a hook) and **native destructive-git blocking in auto mode** (overlaps our pre-commit guards — check for double-block). Codex 0.140/0.141 changed **PostToolUse code-mode gating** — directly touches our `codex_hook_shim.py` enforcement assumptions. mcp-py 1.28 is the **last v1.x before v2** and removed the experimental Tasks API from the spec — pin `<2`. No new frontier text model in-window (Fable 5 was Jun 9, pre-window; Sonnet 4 / Opus 4 legacy IDs retired Jun 15 — verified no live pin in our repos).

---

## New Findings (ranked by value − maintenance)

### 1. Claude Code `Tool(param:value)` permission rules (CC 2.1.178, Jun 15)

| Field | Content |
|-------|---------|
| Source | [code.claude.com/docs/en/changelog](https://code.claude.com/docs/en/changelog) — 2.1.178 |
| What it does | Permission rules now match a tool's input parameters with `*` wildcard, e.g. `Agent(model:opus)` blocks Opus subagents; `Bash(git push:*)` etc. |
| Why relevant | A **settings-level model-routing / cost gate** — could enforce "no Opus subagent for trivial dispatch" as a permission rule instead of a PreToolUse hook. Aligns with our dispatch-economics + turn-budget enforcement. |
| Current overlap | PreToolUse agent dispatch turn-budget hook; model-guide Dispatch Economics. No `Agent(model:)` rule present in settings today (verified). |
| Maintenance | Low — declarative settings, no script. |
| Verdict | **Evaluate** — probe `Agent(model:…)` as a cost-routing rule vs the existing hook; single-variable settings commit if it works. |

### 2. Codex PostToolUse code-mode gating change (codex 0.141, Jun 18)

| Field | Content |
|-------|---------|
| Source | [github.com/openai/codex/releases](https://github.com/openai/codex/releases) — 0.141.0 |
| What it does | "Blocking PostToolUse hooks now correctly reject code-mode tool calls"; hook-trust bypass persists through `codex exec` thread start/resume. |
| Why relevant | Code-mode tool calls were previously **not** gated by blocking PostToolUse — our `codex_hook_shim.py` / Codex parity enforcement assumed they were. This is a correctness check, not a feature. |
| Current overlap | `decisions/2026-06-02-codex-cli-project-parity.md`, `codex_hook_shim.py`, `[[codex-cli-project-parity]]`. |
| Maintenance | One-time audit. |
| Verdict | **Evaluate** — hands-on check that our blocking PostToolUse guards actually fire on Codex code-mode calls after 0.141. |

### 3. Claude Code native destructive-git blocking in auto mode (CC 2.1.183, Jun 19)

| Field | Content |
|-------|---------|
| Source | [code.claude.com/docs/en/changelog](https://code.claude.com/docs/en/changelog) — 2.1.183 |
| What it does | "Improved auto mode safety with destructive git command blocking." |
| Why relevant | Vendor now ships what our hooks enforce (commit-time guard, `git add -A` block). Risk is **double-block / conflict** or false sense of redundant coverage. |
| Current overlap | `[[commit-time-guard-backstop]]`, git-rules destructive-op guards, invariants.md #5. |
| Maintenance | Verify no conflict; possibly relax a hook if vendor coverage is sufficient (don't — keep ours, vendor blocking is mode-conditional). |
| Verdict | **Evaluate** — confirm no double-prompt; keep our guards (they survive Codex + non-auto mode). |

### 4. NousResearch hermes-agent-self-evolution (GEPA trace→variant→gate→PR)

| Field | Content |
|-------|---------|
| Source | [github.com/NousResearch/hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) |
| What it does | Evolutionary harness: GEPA optimizer (DSPy, ICLR 2026) reads **execution traces** to diagnose why a skill/prompt/tool failed → generates variants → gates through **constraint gates (tests, size, benchmarks)** → opens a **PR against the agent repo**. No GPU, pure API. Pulls eval data from session DBs (Claude Code/Copilot/Hermes). |
| Why relevant | Closest external analog to our RSI loop + skill-graduation + `/observe`→improvement-log. Does something we don't: **trace-grounded mutation with a hard constraint-gate before the PR**. Maps onto our agentlogs embed-once layer → skill-opt path. |
| Current overlap | `[[skillopt-vs-autobrowse-veto]]` (gated on scored evals), `2026-06-12-agents-rsi-gap-sweep.md`, reflect/improve loop. |
| Maintenance | Study only — DSPy is NOT a dep we adopt. |
| Verdict | **Extract pattern** — read the trace→variant→constraint-gate→PR loop; compare its gate to our promote/cut heuristic before next reflect-eval. Do NOT adopt DSPy. |

### 5. OpenAI Agents SDK pre-approval tool-input guardrails (v0.17.6, Jun 19)

| Field | Content |
|-------|---------|
| Source | [github.com/openai/openai-agents-python/releases](https://github.com/openai/openai-agents-python/releases) — v0.17.6 |
| What it does | Native PreToolUse-style input gate inside the SDK; plus SDK-only custom data on tool outputs (out-of-band metadata). |
| Why relevant | Parallels our PreToolUse hook enforcement and provenance-attestation-on-output pattern — a vendor-native shape worth comparing, not adopting (we're not on this SDK). |
| Maintenance | N/A unless we use the SDK. |
| Verdict | **Watch** — design reference for the guardrail/metadata shape. |

### 6. mcp-py SDK 1.28.0 — last v1.x, Tasks API removed (Jun 16)

| Field | Content |
|-------|---------|
| Source | [github.com/modelcontextprotocol/python-sdk/releases](https://github.com/modelcontextprotocol/python-sdk/releases) — 1.28.0 |
| What it does | Final v1.x before v2 beta. Python 3.14 support. Deprecates WebSocket transport (never in spec) and the **experimental Tasks API (removed from the MCP spec entirely)**. |
| Why relevant | A `mcp>=2` auto-jump would be a breaking surprise for research-mcp / agent_infra_mcp. We use stdio/HTTP, so WebSocket deprecation is a non-issue; grep confirms no Tasks-API reliance. |
| Maintenance | One-line constraint. |
| Verdict | **Adopt-on-upgrade** — pin `mcp>=1.27,<2` in MCP server deps to avoid silent v2 jump. |

---

## Version Bumps

| Tool | Prev (Jun 15) | Current | Notable |
|------|---------------|---------|---------|
| Claude Code | 2.1.177 | **2.1.183** | `Tool(param:value)` rules, nested `.claude/skills` loading, `/config key=value`, destructive-git block in auto mode, `attribution.sessionUrl` |
| Agent SDK (ts) | — | **0.3.183** | typed permission-denial reasons (`safetyCheck`/`asyncAgent`), `disallowedTools` server-level fix (was silent no-op), `SDKRateLimitInfo` credit fields |
| Agent SDK (py) | 0.2.105 | **0.2.105** | CLI-bundle bumps only, no API change |
| anthropic-py | 0.109 | **0.111** | — |
| codex-cli | 0.139 | **0.141** | PostToolUse code-mode gating fix, per-thread stdio MCP, tool timeout→300s, `/usage` token views, `codex delete` (append-only conflict — note, don't wire) |
| openai-agents-py | — | **0.17.6** | pre-approval tool-input guardrails, SDK-only output metadata |
| mcp-py | 1.27 | **1.28** | last v1.x; Tasks API + WebSocket deprecated |
| Gemini CLI | 0.46 | **0.47** | Antigravity migration commands only |

## Already Known / Filtered

- **Cursor CLI `/review` — STILL NOT SHIPPED.** Only the Jun 10 Bugbot entry ("CLI coming soon"). Status unchanged from Jun 15 baseline → `risky-diff-review` SHADOW promote/cut decision (~Jun 21) does not get a vendor-supersession signal this window. Cursor did ship `/automate` GitHub triggers (Jun 18) + cloud subagents `/in-cloud` (Jun 17) — vendor analogs to our event-driven RSI + worktree isolation; evaluate-only, not build triggers.
- **Sonnet 4 / Opus 4 (`*-20250514`) retired Jun 15** — verified: no live pin in agent-infra/intel/phenome/genomics/skills/research-mcp (one string ref in a phenome benchmark doc, not a config).
- **Fable 5, `code_execution_20260521`, web_search `response_inclusion`, Managed Agents scheduled deploys** — all Jun 9–11, **pre-window**; search aggregators conflated them into "June 2026 news."
- **google-genai 2.9** — vendor-versions shows 2.8→2.9 but NOT corroborated by the ai.google.dev changelog in-window; treat as unconfirmed pypi bump.
- Gemini API in-window = image/video deprecations (Imagen 4, Veo 2/3) + TTS streaming — not in our dispatch path.
- MCP spec draft churn (elicitation transport, error-code framework −32002, Security Interest Group charter) — draft-stage, ignore.

## Search Log

- 4 parallel researcher agents (Anthropic / OpenAI+Codex / Google+Cursor / Ecosystem+research). All returned in <90s.
- alphaxiv.org/explore → **403** (known JS-block; don't retry).
- S2 rate-limited (1 result). GitHub trending via Exa dominated by 0–1 star skill-scaffold repos — dropped.
- Entity files refreshed: claude-code, codex-cli. Not covered this run: kimi-cli (no in-window signal; Kimi CLI 1.43→1.47 local lag noted only).
