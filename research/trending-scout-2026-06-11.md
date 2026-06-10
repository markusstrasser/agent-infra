---
title: "Trending Scout — 2026-06-11 (vendor + ecosystem + repos + papers)"
date: 2026-06-11
tags: [trending-scout, vendor-updates, mcp, ecosystem, papers]
status: complete
window: 2026-05-19 → 2026-06-11
prior: research/trending-scout-2026-05-19.md
---

# Trending Scout — 2026-06-11

**Window:** 2026-05-19 → 2026-06-11 (~3.3 weeks)
**Sources:** Exa, Brave, official changelogs (WebFetch), GitHub releases, S2/arxiv (alphaXiv blocked, HTTP 403)
**Findings:** 9 new, 6 version bumps, ~10 already known (filtered)
**Raw subagent outputs:** `/tmp/scout-{anthropic,openai,google,ecosystem,research}-2026-06-11.md` (ephemeral)

---

## Headline

**Most of what the scan surfaced as "big" was already captured by the 2026-06-07 feature-delta and 2026-06-09 Fable-5 memos** — MessageDisplay hook, reloadSkills, server-side-fallback beta, MCP 2026-07-28 stateless RC all pre-known. The filter worked; the genuinely new residue is small and operational.

**Genuinely new, adopt-grade:** Stop/SubagentStop hooks can now return `hookSpecificOutput.additionalContext` (2.1.163) — a clean continuing-feedback channel for our advisory Stop gates, replacing the error-label hack. And `--safe-mode` (2.1.169) gives a zero-config clean-room (no CLAUDE.md/skills/hooks/MCP) for single-variable harness debugging.

**Structural finding:** the `agent-entity-refresh` pipeline this skill's Phase 0 depends on died with the orchestrator (eradicated 2026-06-07). All 3 entity files were still unpopulated seeds from April. Scout runs are now the only refresher — this run populated claude-code.md and codex-cli.md for the first time.

**Paper meta-signal:** a "harness as first-class engineering object" cluster crystallized this window (3 independent groups + known Harness-1). External confirmation of this repo's core bet.

---

## New Findings (ranked by value − maintenance)

### 1. Stop/SubagentStop `hookSpecificOutput.additionalContext` (Claude Code 2.1.163)

| Field | Content |
|-------|---------|
| Source | code.claude.com/docs/en/changelog |
| What it does | Stop-family hooks can return continuing feedback as additional context without raising a blocking error |
| Why relevant | Our Stop research-gate and stop-progress-check are advisory; today advisory feedback has to either block (exit 2) or be silent. This is the missing middle channel |
| Integration path | Adopt — rework advisory Stop hooks to emit `additionalContext` instead of stderr-as-error |
| Current overlap | `stop-research-gate.sh`, `stop-progress-check.sh` |
| Maintenance cost | Low — output-shape change in existing hooks |
| Verdict | **Adopt** (V4/M1) |

### 2. `--safe-mode` / `CLAUDE_CODE_SAFE_MODE` (Claude Code 2.1.169)

| Field | Content |
|-------|---------|
| Source | code.claude.com/docs/en/changelog |
| What it does | Disables all CLAUDE.md, plugins, skills, hooks, MCP for a session |
| Why relevant | Clean-room repro for "is the harness causing this?" — complements the single-variable-commit discipline (constitution: isolate harness changes) |
| Integration path | Adopt as debugging practice; mention in session-forensics rule |
| Current overlap | None — previously required manual settings surgery |
| Maintenance cost | Zero |
| Verdict | **Adopt** (V3/M0) |

### 3. Harness-engineering paper cluster (3 new preprints)

| Field | Content |
|-------|---------|
| Source | arXiv 2606.06324 (harness flaws as root cause, diagnose/repair at harness layer), 2605.23950 (position: harness is the dominant variable on long-horizon tasks; undisclosed-harness comparisons are broken), 2606.08348 (skill revision as posterior updating, not single-observation overwrite) |
| What it does | Independent groups converge on scaffolding-layer-as-primary-lever |
| Why relevant | 2606.06324 is a diagnostic complement to our hook/session-forensics/buildthenundo loop; 2606.08348 is directly relevant to the session-learning loop's skill-rewriting phase (one observed failure ≠ overwrite the skill — weight it) |
| Integration path | Read 2606.06324 + 2606.08348 before session-learning Phases 1–4 resume |
| Current overlap | Harness-1 (2606.02373) already in constitution; this extends it |
| Maintenance cost | Read-only |
| Verdict | **Extract pattern** (V4/M1). Frontier-tested status unverified on all three (flagged, not asserted) |

### 4. jfrog/agent-belt — eval against the actual CLI binary

| Field | Content |
|-------|---------|
| Source | github.com/jfrog/agent-belt |
| What it does | Reproducible evals run against the real agent CLI (not a model API): multi-judge consensus, pass^k variance, paraphrase families, worktree/Docker isolation |
| Why relevant | Closest external match to `~/Projects/evals/` — and it tests the harness+model composite, which our evals don't |
| Integration path | Evaluate-as-dependency first (per evals-macvb-home: survey ~/Projects/evals before building); extract the test-the-real-binary pattern if dep fails due diligence |
| Current overlap | evals judge_v1, calibration, judge panels — all API-level |
| Maintenance cost | Medium if adopted as dep |
| Verdict | **Evaluate** (V4/M2) |

### 5. Codex 0.132→0.139 deltas (3 operationally relevant)

| Field | Content |
|-------|---------|
| Source | github.com/openai/codex/releases (rust-v0.134.0…0.139.0) |
| What it does | (a) 0.134 profiles v2: legacy `[profiles.]` config REJECTED, settings move to `$CODEX_HOME/.config.toml` — **verified locally: we have no legacy blocks, not affected**. (b) 0.134 MCP: OAuth for streamable-HTTP servers, `readOnlyHint` tools run concurrently, `$ref`/`$defs` preserved; 0.139 preserves `oneOf`/`allOf`. (c) Hook exec-path bug #25875 (hooks silently not firing under `codex exec`) closed 2026-06-04 — fix predates local 0.139.0 |
| Why relevant | (b) removes schema-downgrade pain for our MCP servers under Codex; (c) touched our codex_hook_shim.py surface during the window |
| Integration path | 5-min canary verification that hooks fire under `codex exec` 0.139 (shim doesn't log invocations — add a canary or a one-line invocation log to the shim) |
| Current overlap | codex-cli-project-parity memory, codex_hook_shim.py |
| Maintenance cost | Low |
| Verdict | **Evaluate** (V3/M1) — action: hook-firing canary |

### 6. `disallowed-tools` skill frontmatter (Claude Code 2.1.152)

| Field | Content |
|-------|---------|
| Source | github.com/anthropics/claude-code/releases/tag/v2.1.152 |
| What it does | Skill-level tool removal via frontmatter |
| Why relevant | Skills governance — e.g., analysis skills could declare no-commit at the skill layer instead of prose ("Analysis subagents must not commit") |
| Integration path | Evaluate during next skill-authoring pass; candidate for /observe, /critique, /analyze |
| Current overlap | Prose rules + subagent-gate hooks |
| Maintenance cost | Low |
| Verdict | **Evaluate** (V3/M1) |

### 7. OpenAI prompt caching default flip (2026-05-29)

| Field | Content |
|-------|---------|
| Source | developers.openai.com/api/docs/changelog |
| What it does | Non-ZDR orgs default to `prompt_cache_retention=24h` (was `in_memory`) on responses/chat/batch |
| Why relevant | Improves cache economics for our GPT-5.5 API dispatches; the wakeup-cadence 5-min-TTL reasoning is Anthropic-specific and unaffected |
| Integration path | FYI — no code change; llmx benefits automatically |
| Verdict | **FYI** (V2/M0) |

### 8. ADK 2.2.0 silent default-model change (2026-06-04)

| Field | Content |
|-------|---------|
| Source | github.com/google/adk-python/releases |
| What it does | `LlmAgent` default model silently changed to `gemini-3-flash-preview` (a preview model) |
| Why relevant | We don't run ADK in live code (only a dead `pipelines/vendor-google.json` reference) — but the *pattern* (vendor silently swapping a stable default for a preview) is the silent-drift class we watch |
| Verdict | **FYI** (V1/M0) |

### 9. TS Agent SDK 0.3.162 breaking: native builds default to embedded bash find/grep

| Field | Content |
|-------|---------|
| Source | github.com/anthropics/claude-agent-sdk-typescript/releases |
| What it does | Grep/Glob tools no longer default-enabled in native SDK builds; must be named in `tools`/`allowedTools` |
| Why relevant | Only if we build TS SDK harnesses (we don't currently; orchestrator dead) |
| Verdict | **FYI** (V1/M0) |

---

## Version Bumps

| Tool | Previous (05-19) | Current | Notable Changes |
|------|------------------|---------|-----------------|
| Claude Code | 2.1.144 | 2.1.172 (changelog documented to .170) | additionalContext on Stop hooks (.163), --safe-mode (.169), disallowed-tools + /reload-skills (.152), MCP stdio env `CLAUDE_CODE_SESSION_ID` (.154), MCP reconnect summarizes tools (.147) |
| Agent SDK (py) | 0.2.82 | 0.2.96 | incremental; notes before 0.2.87 unverifiable |
| Agent SDK (ts) | — | 0.3.172 | 0.3.162 breaking (Grep/Glob opt-in on native builds). NB: `@anthropic-ai/sdk` 0.104.1 is the raw API client — separate versioning; vendor-versions.py conflates them |
| Codex CLI | 0.131 | 0.139.0 | profiles v2 (.134, verified no local impact), MCP OAuth + readOnlyHint concurrency + schema preservation (.134/.139), multi-agent v2 + remote-control grants (.137), /app desktop handoff (.138) |
| google-genai | 2.4.0 | 2.8.0 | already audited (commits 6e526d2, 2b52b1c); 2.8 adds Agent-Platform MCP in async generate_content |
| google-adk | 1.34/2.0 | 2.2.0 | 2.0 GA at I/O 05-19; 2.2 silent default-model change (finding 8) |

**Model lifecycle:** `gemini-2.0-flash`(-lite) shut down 2026-06-01; image `-preview` models die 2026-06-25. **Verified benign locally:** only hits are an llmx alias that *remaps* the dead ID to `gemini-3-flash-preview` (llmx/providers.py:283) and a fake-metadata string in a claim_bench test. Gemini 3.5 Flash GA'd at I/O (05-19) — already our default cosigner since 2026-05-24; exact pricing/context window still unpublished in official sources (do not assume 3.1 parity).

---

## Status Checks on Tracked Items

- **Issue #32105 (built-in tool output compression): CLOSED in window**, but no corresponding feature in any 2.1.145–170 changelog entry → most likely closed-declined/stale, NOT shipped (unverified — closing comment inaccessible). Deferred-items memo trigger NOT met; annotated.
- **Agent Teams:** still research preview, no GA in window.
- **Managed Agents:** scheduled (cron) deployments + vault-backed env vars in public beta (Jun 9). Still **defer** — cloud agents can't read local files (schedule-is-cloud-not-local); our launchd jobs are zero-API by design.
- **Antigravity 2.0 / `agy`:** Go-based Gemini-CLI successor; forced migration reportedly wiped user setups, compute pricing opaque (all damage claims community-blog only). Still **defer** as transport.
- **"Dreaming":** dynamic-workflows GA'd (2.1.154 + blog); Dreaming itself not GA'd in window.

## Already Known (filtered out)

MessageDisplay hook, `reloadSkills`, `mcp_tool` hook type, 31 hook events (all in `2026-06-07-claude-code-codex-feature-delta.md`); `server-side-fallback-2026-06-01` + `fallback-credit` beta headers (in `2026-06-09-fable-5-mythos-5-harness-impact.md`); MCP 2026-07-28 stateless RC (in `2026-05-27-tool-use-mcp-4w.md` + `2026-06-07-biomcp-fastmcp-upstream-delta.md` + fastmcp3 plan watch banner); Gemini 3.5 Flash (adopted pre-GA); google-genai 2.8 migration (dep-audit); Codex remote-control (prior scout); Dynamic Workflows (feature-delta memo + native in current harness); memory/context-compression solo repos (we have agentlogs + append-only memory); Mastra/HarnessForge/nano-step eval-harness noted as pattern references in raw outputs (HarnessForge: arXiv 2606.01779, fault-guided harness tailoring — citable evidence for the improvement-log loop, results unverified beyond abstract).

## Search Log

- Exa + Brave per-axis (5 parallel subagents) — productive on all axes.
- Official changelogs via WebFetch: Claude Code (documented only to 2.1.170; npm at .172 — gap noted), Codex GitHub releases, ai.google.dev changelog, developers.openai.com changelog — all reachable.
- **alphaXiv /explore: HTTP 403** (blocked for automated fetch) — no view-count ranking this scan; papers came from S2/arxiv searches instead. Consider dropping alphaXiv from the skill or noting the block.
- Meta-noise signal: flood of near-zero-star "agent-harness" scaffold repos this window — harness engineering went mainstream; ignored individually.
- Stale-search artifacts filtered: gpt-4.5/o3-mini/DALL·E "removals" misattributed to window by search engines; Agents SDK "breaking changes" list predates window.

## Infrastructure Notes (from this run)

1. **agent-entity-refresh pipeline is dead** — it was orchestrator-scheduled; orchestrator eradicated 2026-06-07. All 3 entity files were unpopulated April seeds. This run populated claude-code.md + codex-cli.md; kimi-cli.md left seed (no Kimi axis this scan; pypi 1.47.0 vs local 1.43.0 noted). The skill's Phase 0 step 4 text needs updating — there is no out-of-band refresher anymore.
2. **vendor-versions.py** tracks `@anthropic-ai/sdk` but not `@anthropic-ai/claude-agent-sdk` (TS) — add it; the two were conflated in this scan's baseline.
3. **trending-scout is not symlinked into `~/.claude/skills/`** — invocable only by path. Symlink if it should be a slash command.
