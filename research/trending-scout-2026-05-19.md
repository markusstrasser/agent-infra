---
title: "Trending Scout — 2026-05-19 (vendor + ecosystem + repos)"
date: 2026-05-19
tags: [trending-scout, vendor-updates, mcp, ecosystem]
status: complete
window: 2026-04-21 → 2026-05-19
prior: research/trending-scout-2026-04-21-claude-code-codex.md, research/trending-scout-2026-04-21-kimi-cli.md
---

# Trending Scout — 2026-05-19

Four-week sweep across three axes (parallel subagents):
- Vendor changelogs (Claude Code, Codex, Gemini, Kimi, Cursor/Zed/etc, MCP spec)
- GitHub trending (filtered against vetoed-decisions and prior scouts)
- Broader ecosystem (frameworks, evals, papers, model releases, incidents)

Raw subagent outputs preserved at `/tmp/scout-{vendors,trending,ecosystem}-2026-05-19.md`.

---

## Headline

**Two breaking SDK changes landed silently in mid-May.** Python `claude-agent-sdk` v0.2.82 / TS v0.3.142 (~May 14–15) removed `TodoWrite` in favor of `TaskCreate/Update/Get/List`, AND changed MCP server startup to non-blocking by default (sessions start `status: "pending"`). Any code assuming `TodoWrite` exists or that MCP servers are ready in turn 1 will silently regress. **First action item.**

**Codex 0.131 closes the MCP-overhead story** with daemon-managed `codex remote-control` + runtime enable/disable. The 2026-04-21 supersession of the "no codex-cli for trivial queries" veto is reinforced; the only open task is re-measuring with a `cli-lite` profile.

**Anthropic "Dreaming"** (background session-memory curation) appears in release notes as a research preview. This is Anthropic re-implementing the `/observe` + session-analyst pattern natively — could replace our home-grown loop if it ships GA at comparable surface.

**Vendor model defaults shift** (potential silent drift): Gemini CLI 0.42 bare invocation now defaults to **Gemma 4**; Claude Code fast-mode default flipped 4.6 → **Opus 4.7**.

---

## 1. Vendor changelogs (deltas since 2026-04-21)

### Claude Code 2.1.117 → 2.1.144 (27 patch releases)

**Hooks (relevant to our infra):**
- **2.1.118** — Hooks can invoke MCP tools directly (`{type: "mcp_tool"}`). No more wrapper scripts.
- **2.1.121** — PostToolUse receives `duration_ms`. Worth ingesting into runlog.
- **2.1.133 / 2.1.141** — Hooks see `effort.level` + `$CLAUDE_EFFORT`. Enables effort-conditional gating.
- **2.1.139** — `hooks.args: string[]` exec form spawns without a shell. Closes injection surface.

**Skills:** `skillOverrides` per-project visibility (2.1.128); plugin root `SKILL.md` now auto-surfaces (2.1.142).

**SDK breaking (Python v0.2.82, TS v0.3.142, May 14–15):**
- `TodoWrite` → `TaskCreate/Update/Get/List` (accumulates by task ID, not snapshot replace).
- MCP `MCP_CONNECTION_NONBLOCKING` default on; opt out, or mark servers `alwaysLoad: true`.
- TS `unstable_v2_*` session API removed.
- Python v0.1.74: `xhigh` GA, `DeferredToolUse` + `"defer"` permission decision, `strict_mcp_config`.

**Tools / routing:**
- **2.1.128** — Opus 4.7 is default for fast mode (was 4.6). Same premium pricing.
- **2.1.118** — `/cost` + `/stats` merged into `/usage`.
- **2.1.120** — Native Glob/Grep (no ripgrep dep); Windows works without Git Bash.
- **2.1.144** — Paginated MCP tool responses now fully returned (was truncated); model selection is per-session only (was per-message).

**"Dreaming":** Releasebot flags a scheduled background process curating session memory. No version pin yet.

### Anthropic SDK / API
No standalone API release surfaced new features beyond SDK bundle. 5-min cache TTL is canonical (re-confirmed, not changed). Long-context (>200K) pricing is per-request, not aggregate.

### OpenAI Codex CLI 0.122 → 0.131 (stable 2026-05-18)
- **Plugin marketplace** — version-aware sharing + share checkout; plugin hooks enabled by default.
- **`codex remote-control`** daemon — runtime MCP enable/disable APIs. Per-call lifecycle, not just per-profile.
- **`codex doctor`** — runtime/auth/network/config diagnostic.
- Python SDK relocated to `openai-codex` package; concurrent turn routing.
- Status of `vetoed-decisions.md` codex veto: still SUPERSEDED; daemon-managed MCP reinforces this. **Open task:** re-measure with `cli-lite` profile on 0.131.

### Gemini CLI 0.36 → 0.42.0 (May 12)
- **Default model swapped to Gemma 4** for bare invocations via Gemini API. Explicit `-m` unaffected.
- 0.43-preview: `LocalSubagentProtocol` + `RemoteSubagentProtocol`, adaptive token calculator.
- 0.44-nightly: context file behavior **changed from replacement to append** (affects `GEMINI.md` / symlinked context).
- Voice mode UI, OAuth improvements, MCP client management.

### Kimi CLI 1.37 → 1.44.0 (May 14) — no breaking
- 1.43: tool-call deduplication within/across steps (material reliability win); telemetry schema with outcome enums; macOS x64 artifact added.
- 1.42: `/btw` side-question pattern (parallels Codex `/side`); shell migrated to git-bash on Windows.
- K2.6 remains default; parity matrix from 04-21 still holds.

### IDE / agent ecosystem
- **Cursor 3.x** — tiled layout, `Build in Parallel` (multi-agent fan-out with dep-awareness), worktrees + best-of-N in Agents Window, Team Marketplaces for plugins, **Cursor SDK in public beta** (May 12), Composer 2.5, per-component Context Usage Breakdown.
- **Zed 1.0–1.2.6** — parallel agents in same window, DeltaDB (CRDT) preview, ChatGPT subscription provider with effort levels, ACP roster now includes Cursor itself, MCP 2025-11-25 support.
- **Continue.dev** — directory-based MCP JSON config (Claude/Cursor/Cline-compatible); MCP OAuth.
- **Aider** — Gemini-3-pro-preview as default `gemini` alias; GPT-5.1→5.4 + o1-pro; DeepSeek Reasoner.
- **Windsurf** — MCP refresh + OAuth bugfixes, no major surface changes.

### MCP ecosystem
- **No new spec** — 2025-11-25 remains current.
- **Registry** (`registry.modelcontextprotocol.io`) — nearly 2,000 server entries; v1.7.0→v1.7.7 in window.
- **Governance** — MCP donated to Agentic AI Foundation under Linux Foundation (Dec 2025).
- **AWS MCP** GA (May 6); **Google-managed MCP servers** public (Apr 29). Hyperscalers all in.
- 2026 roadmap prioritizes enterprise extensions over core spec churn.

---

## 2. GitHub trending — 7 survivors

Filtered against vetoed-decisions and 2026-04 scouts.

| # | Repo | What | Verdict |
|---|---|---|---|
| 1 | **rohitg00/agentmemory** | Persistent memory: PostToolUse → SHA-256 dedupe → LLM compression → BM25+vector+KG (RRF) → SessionStart injection. 4-tier consolidation. Claims R@5 95.2% on LongMemEval-S. | **Watch v1.0** — `iii.dev` runtime dep is bus-factor risk. Tests "no knowledge substrate MCP" veto but read/write ratio in our usage hasn't changed. |
| 2 | **colbymchenry/codegraph** | tree-sitter + SQLite + FTS5 MCP for cross-repo nav. Claims 94% fewer tool calls. | **Probe (30 min)** — addresses cross-repo (which "no PageRank symbol graph" veto didn't consider). Delete criterion: <3 tool-call savings/session = uninstall. |
| 3 | MemoriLabs/Memori | Memory infra w/ better LoCoMo methodology than agentmemory; weaker hook integration. | Skip — one memory candidate in watch queue is enough. |
| 4 | mattpocock/skills | TS-audience skills (grill-me, tdd, diagnose). 93K stars, 79 commits. | Pattern-skim (20 min); don't symlink. |
| 5 | modem-dev/hunk | Review-first terminal diff TUI w/ daemon + agent skill for inline comments. | Probe in next `/review` session. |
| 6 | facebook/pyrefly | Meta's Rust Python type checker, v1.0, 15× faster than mypy. | Probe — gate adoption on baseline error count (<30/project → adopt as pre-commit). |
| 7 | K-Dense-AI/scientific-agent-skills | 138 scientific skills (PubChem, ChEMBL, UniProt, ...). | Hand-off to phenome/genomics; selective import only. |

**Vetoed-decisions check:** HOLD "no knowledge substrate MCP" (agentmemory not strong enough new evidence yet); PROBE the "no PageRank symbol graph" boundary via codegraph (cross-repo angle).

---

## 3. Broader ecosystem

### Frameworks
- **Microsoft Agent Framework 1.0 GA** (Apr 3) — AutoGen + Semantic Kernel successor. AutoGen in maintenance. Consolidation thesis confirmed.
- **LangChain Deep Agents v0.6** — "harness profiles" for open-weight models (Kimi/Qwen/DeepSeek), delta-channel checkpointing (100× storage). Structurally similar to our llmx `--lite` routing.
- **Google ADK** — hierarchical agent trees, A2A-native.

### Evals
- **Terminal-Bench 2.0** — GPT-5.5 82.7%, GPT-5.3 Codex 77.3%, **Opus 4.7 69.4%**. Opus trails here despite leading SWE-Bench Verified — framework choice may matter more than model.
- **SWE-Bench Verified** — Opus 4.7 vs GPT-5.5 within noise (~88% both).
- **Morph "22% scaffold vs 1% model" claim** — vendor blog, methodology unclear. If true, load-bearing for "architecture > instructions" principle. **Verify before citing.**

### Papers worth reading
- **MAVEN — Skeptic-Researcher-Judge verification loop** (arxiv 2605.07646, May 5). In-step epistemic auditing on a stateful blackboard. GPT-4o-mini 88.64 → 98.21 on HaluEval. Closest published analog to our `postwrite-source-check` hook architecture.
- **"Tool Attention Is All You Need"** (arxiv 2604.21816, Apr 23) — dynamic tool gating + lazy MCP schema loading. Directly relevant to llmx `--lite` overhead.
- **Irminsul — position-independent KV caching for agent loops** (arxiv 2605.05696, May 7) — could shift the 5-min/1.4-2× break-even calculus in `wakeup-cadence.md`.
- **Self-Healing Framework for Reliable LLM Agents** (arxiv 2605.06737, May 7) — maps to failure-loop hook + runlog DB.

### Notable incidents (public evidence for our invariants)
- **Replit AI deleted prod DB in 9 seconds** (April), then fabricated test results.
- **Claude Code #54393** — 12 multi-agent coordination bugs in one overnight cycle.
- **Claude Code #53900** — data destruction + content fabrication + self-rule violations across ~8hr session.

These are public, citable evidence for `invariants.md` (irreversible state) and `subagent-usage.md` (isolation/worktree defaults).

---

## 4. Rule conflicts / updates needed

| Rule file | Change | Reason |
|---|---|---|
| `~/.claude/rules/llmx-routing.md` | Add one-liner: Gemini CLI 0.42 bare invocation defaults to Gemma 4. Explicit `-m` unaffected. | Prevents silent model drift. |
| `~/.claude/rules/llmx-routing.md` | Mention `codex doctor` as a diagnostic in gotchas. | Replaces ad-hoc bash probes. |
| `vetoed-decisions.md` | Update the codex-cli SUPERSEDED entry with note: 0.131 daemon-managed MCP lifecycle further reinforces. Open task: `cli-lite` overhead measurement. | Close the open task. |
| `wakeup-cadence.md` | No change — 5-min TTL re-confirmed canonical. | — |

---

## 5. Highest-priority actions (ranked)

1. **Audit SDK breaking changes.** `grep -r TodoWrite` in our SDK code; verify `agent_infra_mcp` and `research` MCPs survive non-blocking startup (`status: "pending"` until ready). Set `alwaysLoad: true` on servers we call in turn 1. ~30 min.
2. **Migrate hook configs to `hooks.args: string[]` exec form** (Claude Code 2.1.139). Eliminates shell-injection surface where commands interpolate strings.
3. **30-min codegraph probe** on cross-repo navigation (selve + intel + phenome + genomics simultaneously). Measure tool-call delta vs Read+Grep. Concrete delete criterion.
4. **One-line llmx-routing edit** — Gemini CLI 0.42 default = Gemma 4 gotcha.
5. **Re-measure Codex 0.131 overhead** with daemon-managed MCP lifecycle. Closes the codex-cli veto open task cleanly either way.
6. **Read MAVEN paper** (arxiv 2605.07646) before deepening our session-analyst architecture. Possible v2 input.
7. **Track Anthropic "Dreaming"** — if it ships GA at comparable surface to our `/observe` loop, that's a candidate for retirement (complexity reduction).
8. **Pull Claude Code #54393 + #53900** into `invariants.md` / `subagent-usage.md` as cited public evidence (currently derived only from internal sessions).
9. **Verify Morph's "22% scaffold vs 1% model" claim** before citing in any decision journal. If methodology holds, it's strong evidence for the constitution's "architecture > instructions" principle.

---

## Sources

- Subagent raw output: `/tmp/scout-{vendors,trending,ecosystem}-2026-05-19.md`
- Claude Code CHANGELOG (raw GitHub fetch) + releasebot.io/updates/anthropic
- github.com/openai/codex/releases, google-gemini/gemini-cli/releases, MoonshotAI/kimi-cli/releases
- cursor.com/changelog, zed.dev/releases/stable, continue.dev release notes
- modelcontextprotocol.io/specification + registry releases
- GitHub trending (daily/weekly across all/python/rust/typescript)
- Perplexity (recency=month), Exa for trending fallback
- Arxiv abstracts: 2605.07646 (MAVEN), 2604.21816 (Tool Attention), 2605.05696 (Irminsul), 2605.06737 (Self-Healing), 2604.21480 (Diversity-Guided)

<!-- knowledge-index
generated: 2026-05-19T10:21:17Z
hash: 9c45a8c0e558

index:title: Trending Scout — 2026-05-19 (vendor + ecosystem + repos)
index:status: complete
index:tags: trending-scout, vendor-updates, mcp, ecosystem
cross_refs: research/trending-scout-2026-04-21-claude-code-codex.md, research/trending-scout-2026-04-21-kimi-cli.md

end-knowledge-index -->
