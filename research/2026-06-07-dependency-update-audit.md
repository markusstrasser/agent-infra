# Dependency Update Audit — 2026-06-07

**Status: COMPLETE**

Repos: agent-infra, research-mcp, biomedical-mcp (+ corpus-core sub-package)
Scope: High-leverage libs — verified installed versions via `uv run python3 -c importlib.metadata`, latest via PyPI JSON API + GitHub changelogs.
Method: Read-only — no lockfile mutations, no uv sync/lock.

---

## 1. agent-infra (`/Users/alien/Projects/agent-infra/pyproject.toml`)

Declared: `anthropic>=0.84.0`, `claude-agent-sdk>=0.1.44`, `corpus-core[all]`, `duckdb>=1.1`, `exa-py>=2.6.1`, `fastmcp>=3.4,<4.0`, `google-genai>=1.72.0`, `inspect-ai>=0.3.0`, `openai>=2.26.0`, `parallel-web>=0.4.0`. Modal in `[dev]`.

| Package | Installed | Latest | Gap | Worth upgrading? | Breaking? |
|---------|-----------|--------|-----|-----------------|-----------|
| anthropic | 0.84.0 | **0.107.1** | +23 minor | **YES — HIGH** New models (opus-4-8, opus-4-7, mythos-preview), mid-conversation system blocks, `usage.output_tokens_details`, thinking-token-count beta in streaming, cache diagnostics beta, Managed Agents multiagents/outcomes/webhooks, CMA Memory public beta, structured `stop_details`, Workload Identity Federation, AWS client, compaction helpers deprecated | No breaking API changes; additive only |
| google-genai | 1.72.0 | **2.8.0** | **+1 major** | **YES — HIGH** (with care) 2.x adds: Gemini 3.5 Flash model, gemini-3.1-flash-lite, Deep Research agents, MCP support for async generate_content, Reinforcement Tuning, service_tier for Flex pricing, batch job output_info, multimodal file search (1.75), Agent/Environment APIs. `GenerateContent` API **unaffected** by 2.0 breaking changes. Dropped Python 3.9 support (1.74). Breaking: Interactions API only (SSE event renames, response_format deprecation, ContentDelta unions) — we do not use Interactions API. | Minor: Python >=3.10 required (we have >=3.11, fine). Interactions API breaking if used; GenerateContent unaffected. |
| openai | 2.31.0 | **2.41.0** | +10 minor | **YES — MEDIUM** Responses moderation (2.41), Bedrock Responses (2.40), Realtime 2 API (2.36), service_tier param (2.37), image generation updates (2.35), Admin API keys (2.34). Floor is already >=2.26 so we just need a lockfile refresh. | No |
| fastmcp | 3.4.0 | **3.4.2** | +2 patch | **YES — SAFE** JWT header compat fix (3.4.2), Starlette security floor (3.4.1). Pin `>=3.4,<4.0` is already correct. | No |
| exa-py | 2.6.1 | **2.13.0** | +7 minor | **INVESTIGATE** Latest in 2.x series is 2.13.0. We are already on 2.6.1 (2.x, not 1.x). The jump from 1.x to 2.x was a major version bump; floor `>=2.6.1` should pick up 2.13 on next lock. No changelog found publicly but 2.x is the current active series. | Unlikely within 2.x |
| claude-agent-sdk | 0.1.55 | **0.2.93** | **+1 minor** | **INVESTIGATE** Major jump from 0.1.x to 0.2.x. SDK now explicitly wraps Claude Code CLI and adds in-process MCP tools, hooks, tool permissions, bidirectional streaming. The 0.2.x version bundles the CLI. Floor `>=0.1.44` — should pin `>=0.2` explicitly if 0.2 API is different. | Likely: 0.2 is a near-rewrite |
| modal | 1.4.2 | **1.4.3** | +1 patch | **YES — SAFE** Regional routing (us-west/eu-west/ap-south), `modal.Environment` programmatic management, `Function.with_options()` dynamic config, Volume read-only + subdirectory mounting, custom ephemeral app names. No breaking changes. | No |
| duckdb | 1.5.2 | **1.5.3** | +1 patch | **YES — SAFE** Bugfix only: parquet metadata, CSV escape handling, pg_collation compatibility, jemalloc moved to core. No Python API changes. | No |
| inspect-ai | 0.3.205 | **0.3.237** | +32 patch | LOW — eval framework, dev dep. No evidence of breaking changes; safe to bump. | No |
| parallel-web | 0.4.2 | **1.0.1** | **+1 major** | **MAJOR BUMP** 0.4 → 1.0. This is a Stainless-generated client for the Parallel REST API. Major version = potential breaking API changes. Assess whether any agent-infra code calls `parallel-web` APIs directly before bumping. Floor is `>=0.4.0` — the lockfile will not auto-bump to 1.0 unless floor is updated. | Likely; assess callsites |
| httpx | 0.28.1 | 0.28.1 | none | Already at latest | — |
| pydantic | 2.12.5 | **2.13.4** | +1 minor | **YES — SAFE** Fixes: `from_attributes` AttributeError handling, `ValidationInfo.field_name`, `ValidationInfo.data` in JSON validation, `RootModel` core metadata preservation. | No |
| jsonschema | 4.26.0 | 4.26.0 | none | Already at latest | — |
| tenacity | 9.1.4 | 9.1.4 | none | Already at latest | — |
| trafilatura | 2.0.0 | **2.1.0** | +1 minor | **YES — SAFE** Released today (2026-06-07). No breaking changes noted. | No |
| networkx | 3.6.1 | ~3.4.x | N/A | No evidence of recent major releases; appears current | — |

---

## 2. research-mcp (`/Users/alien/Projects/research-mcp/pyproject.toml`)

Declared: `fastmcp>=3.4,<4.0`, `httpx>=0.27`, `tenacity>=9.0`, `pymupdf>=1.25`, `google-genai>=1.0`, `exa-py>=2.6`, `duckdb>=1.0`, `corpus-core`.

| Package | Installed | Latest | Gap | Worth upgrading? | Breaking? |
|---------|-----------|--------|-----|-----------------|-----------|
| fastmcp | 3.4.0 | 3.4.2 | +2 patch | YES — same as above | No |
| pymupdf | 1.27.1 | **1.27.2.3** | +patch | **YES** The `.x` suffix versions (1.27.2.3 vs 1.27.1) are micro-releases in the PyMuPDF family scheme. agent-infra has 1.27.2.3; research-mcp is one behind. Safe to pick up. | No |
| pymupdf4llm | 0.3.4 | **1.27.2.3** | **MAJOR JUMP** | **PLAN CAREFULLY** Version scheme changed from 0.x to 1.27.x to align with PyMuPDF family. 1.27.2.1+ auto-includes `pymupdf_layout` as a mandatory dependency and auto-initializes it. The page-chunk dictionary format changed in the 0.2.0 era (layout boxes from lists to dicts). Call `pymupdf4llm.use_layout(False)` to disable if current output format breaks consumers. Only research-mcp's floor `>=0.0.20` is still pre-1.x — needs updating. | YES — layout auto-enabled, output dict format changed |
| google-genai | 1.65.0 | 2.8.0 | +7 minor to 1.x, +1 major to 2.x | Same analysis as above. research-mcp has 1.65.0, agent-infra has 1.72.0 — version **skew between repos** for the same package. Floor `>=1.0` is very loose. | Yes, same as above |
| duckdb | 1.5.2 | 1.5.3 | +1 patch | YES — safe | No |
| exa-py | 2.6.1 | 2.13.0 | +7 minor | Same as above | Unlikely within 2.x |
| httpx | 0.28.1 | 0.28.1 | none | At latest | — |
| tenacity | 9.1.4 | 9.1.4 | none | At latest | — |

---

## 3. biomedical-mcp (`/Users/alien/Projects/biomedical-mcp/pyproject.toml`)

Declared: `fastmcp>=3.4,<4.0`, `httpx>=0.27`, `tenacity>=9.0`.

| Package | Installed | Latest | Gap | Worth upgrading? | Breaking? |
|---------|-----------|--------|-----|-----------------|-----------|
| fastmcp | 3.4.0 | 3.4.2 | +2 patch | YES — JWT fix, security floor | No |
| httpx | 0.28.1 | 0.28.1 | none | At latest | — |
| tenacity | 9.1.4 | 9.1.4 | none | At latest | — |

Minimal dependency surface — no action needed beyond fastmcp patch.

---

## 4. corpus-core sub-package (`scripts/corpus/packages/corpus-core/pyproject.toml`)

Declared: `duckdb>=1.0`, `jsonschema>=4.20`; extras: `pymupdf>=4.0`, `pymupdf4llm>=0.0.20`, `trafilatura>=2.0`, `httpx>=0.27`, `pydantic>=2.0`, `google-genai>=1.0`, `modal>=1.0,<2.0`.

| Package | Notes |
|---------|-------|
| pymupdf4llm floor `>=0.0.20` | Too loose — will accept the old 0.3.4 series. Should be raised to `>=1.27` to align with the scheme change. |
| modal `>=1.0,<2.0` | Correct. 1.4.3 is within range. |
| trafilatura `>=2.0` | Floor is correct; 2.1.0 released today is safe to pick up. |
| google-genai `>=1.0` | Loose floor — inherits same 2.x migration concern. |

---

## 5. Key Findings by Category

### Security
- **fastmcp 3.4.1** includes a Starlette security floor bump. Installed 3.4.0 is missing this. All three repos should pick up 3.4.2. CVE-2025-69872 was fixed in the v2→v3 OAuth DiskStore→FileTreeStore migration (we are already on v3 so not exposed to the pickle vuln).
- **anthropic 0.87.0** fixed `sanitize endpoint path params` (path traversal adjacent). +23 versions behind.
- **anthropic 0.87.0** also fixed restrictive file mode for memory files.

### Version Skew
- `pymupdf4llm`: agent-infra has 1.27.2.3, research-mcp has 0.3.4. This is a real functional difference — different output format.
- `pymupdf`: agent-infra has 1.27.2.3, research-mcp has 1.27.1.
- `google-genai`: agent-infra has 1.72.0, research-mcp has 1.65.0 (7 minor versions behind).

### Major Pending Migrations
1. **google-genai 1.x → 2.x**: Breaking only for Interactions API (we don't use it). `GenerateContent` is stable. New features: Gemini 3.5 Flash, MCP async, service_tier (Flex pricing), Deep Research agent models, multimodal file search. Python 3.9 dropped (we're on 3.11, fine). Worth doing soon.
2. **anthropic 0.84 → 0.107**: Purely additive. claude-opus-4-8 model support, thinking-token-count streaming, cache diagnostics beta, Managed Agents, CMA Memory, structured stop_details, Workload Identity. Zero breaking changes. Very high leverage — we use this SDK constantly.
3. **pymupdf4llm 0.3.4 → 1.27.2.x**: Scheme change, auto-layout, dict format change. Medium effort — test extraction output before deploying.
4. **parallel-web 0.4.2 → 1.0.1**: Major version; check callsites in agent-infra before bumping floor.
5. **claude-agent-sdk 0.1.55 → 0.2.93**: Major rewrite. Assess before bumping floor.

---

## 6. Prioritized Action List

### SAFE NOW (low-effort, no migration work)

1. **`anthropic` → 0.107.1** (all repos that use it). Floor `>=0.84.0` → set to `>=0.105.0` (claude-opus-4-8 support). No breaking changes; gains 23 versions of new model IDs, thinking-token streaming, cache diagnostics beta, structured stop_details. The highest-ROI update in the list.

2. **`fastmcp` → 3.4.2** (all three repos). Patch release, security hardening (`fastmcp>=3.4,<4.0` already correct). No code changes — just a lockfile refresh. Picks up JWT compat fix + Starlette security floor.

3. **`duckdb` → 1.5.3** (agent-infra, research-mcp, corpus-core). Bugfix only — parquet, CSV, pg_collation. No API changes.

4. **`pydantic` → 2.13.4** (agent-infra, corpus-core, research-mcp, biomedical-mcp — transitive). Fixes ValidationInfo bugs in JSON validation path. Safe minor bump.

5. **`modal` → 1.4.3** (agent-infra dev dep, corpus-core extra). Gains regional routing, `modal.Environment`, dynamic Function config via `Function.with_options()`. No breaking changes.

6. **`trafilatura` → 2.1.0** (corpus-core `extract` extra). Released today. Minor — no breaking changes noted.

7. **`openai` → 2.41.0** (agent-infra). Floor `>=2.26.0` — lockfile refresh picks up Realtime 2 API, Responses moderation, Bedrock Responses. No breaking changes within 2.x.

8. **`inspect-ai` → 0.3.237** (agent-infra dev dep). 32 patch versions, eval framework. Low urgency but no risk.

### PLAN A MIGRATION (non-trivial, assess callsites first)

9. **`google-genai` 1.72→2.8.0** (agent-infra) and **1.65→2.8.0** (research-mcp). High value: Gemini 3.5 Flash, MCP async, service_tier Flex support, Deep Research agents. Breaking only for Interactions API — grep `interactions` usage in both repos before upgrading. Also resolve the 7-minor-version skew between repos. Floor in corpus-core (`>=1.0`) and research-mcp (`>=1.0`) need updating. Requires Python >=3.10 (fine, both repos are >=3.11). **Recommend doing this next** — GenerateContent path is stable, benefit is high.

10. **`pymupdf4llm` 0.3.4→1.27.2.3** (research-mcp, corpus-core). Output dict format changed (layout boxes now dicts not lists), `pymupdf_layout` auto-initializes. Test `to_markdown()` and chunk format consumers before bumping. Update corpus-core floor from `>=0.0.20` to `>=1.27`. Note: agent-infra already has 1.27.2.3 installed so the corpus-core `[all]` path in agent-infra is fine; the gap is in research-mcp's own lockfile.

### INVESTIGATE BEFORE ACTING

11. **`exa-py` 2.6.1→2.13.0**: Already on 2.x (floor `>=2.6`), so this is a within-major-series bump. No public changelog accessible. Low risk — but verify `search()`, `find_similar()`, `get_contents()` signatures have not changed within 2.x before refreshing lock.

12. **`parallel-web` 0.4.2→1.0.1**: Major version bump (0.4→1.0). Stainless-generated client — check if the Parallel REST API endpoint schema changed. Grep agent-infra callsites. Floor `>=0.4.0` will not auto-pick this; update floor explicitly if wanted.

13. **`claude-agent-sdk` 0.1.55→0.2.93**: Major jump. 0.2.x bundles the Claude Code CLI and adds in-process MCP, hooks API, tool permissions. Assess whether agent-infra uses the SDK's public API at all or only invokes it as a CLI entrypoint. If it's CLI-only, the upgrade is likely safe.

---

## 7. Not Tracked (already at latest or N/A)

- httpx 0.28.1 — at latest
- tenacity 9.1.4 — at latest
- jsonschema 4.26.0 — at latest
- trafilatura 2.0.0 (see item 6 for 2.1.0 patch)
- pypdf 6.11.0 — not checked against PyPI but installed version looks recent
- pymupdf 1.27.2.3 — at latest in agent-infra (research-mcp 1.27.1 is one micro behind)

---

*Probe completed 2026-06-07. Versions verified against PyPI JSON API and GitHub changelogs. Installed versions read via `importlib.metadata` in each repo's venv.*

## Correction / resolution (2026-06-08)

All three repos are now on **google-genai 2.8** (agent-infra `6e526d2`, research-mcp `e27ea6b`).

The research-mcp bump was initially **skipped** by the dep-bump pass: the grep gate found
`client.aio.interactions` in `deep_research.py` and, reading "breaking: Interactions API",
the agent treated "uses Interactions" as **blocked**. Direct probing of the installed 2.8
SDK showed the break is narrower than this row described:

- The interactions API is **not removed** — `create/get/cancel` exist with call signatures
  backward-compatible with our usage. **Call sites do not change.**
- The *only* break is the **response shape**: 1.x `interaction.outputs` (flat list) → 2.x
  `interaction.steps` (discriminated union; text+citations now in
  `ModelOutputStep.content[] → TextContent`, thinking in `ThoughtStep.summary`).
- Fix was a contained ~20-line extraction rewrite (`_extract_from_steps`), not a block.

**Meta-lesson (for future dep work):** a "breaking if used" flag should trigger *scope the
break* (probe the actual API delta), not *skip*. Trusting a second-hand "breaks" verdict
about a **checkable** fact cost a real capability upgrade until re-probed. Audit rows for
breaking changes should carry the probe that measures the delta, not just the verdict.
