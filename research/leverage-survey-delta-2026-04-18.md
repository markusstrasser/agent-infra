---
title: "Leverage Survey Delta — Agent Observability, Transcript Analysis, Hook DSLs"
date: 2026-04-18
tags: [leverage, observability, transcript-analysis, inspect-ai, inspect-scout, langfuse]
status: complete
---

# Leverage Survey Delta — Agent Observability, Transcript Analysis, Hook DSLs

**Question:** What packages, DSLs, or libraries could we leverage across adjacent spaces the Mar 19 survey didn't cover: agent observability, structured transcript analysis, session replay, SQLite-native workflow tools, hook-composition DSLs, LLM cost/telemetry, open-source agent harness infrastructure?
**Tier:** Standard | **Date:** 2026-04-18
**Prior art checked (to avoid rediscovery):**
- `leverage-survey-2026-03-19.md` — Python libs, Rust/Go CLIs, stdlib (focus: analytics + data processing)
- `ecosystem-mcp-refresh-2026-04.md` — MCP protocol + enterprise MCP servers
- `meta-harness-leverage-brainstorm.md` — harness provenance + trace fidelity
- `runlog-otel-compatibility.md` — OpenInference/OTel as vocabulary, not dep
- `cognee-technical-assessment.md` — graph substrate (rejected)
- `fastmcp3-integration-plan.md` — FastMCP 3.2.0 Apps status

**Ground truth from prior memos:** Mar 19 survey adopted Datasette, DuckDB, `jaq`, `hl`, `git-cliff`; rejected Rich, pydantic, sqlite-utils-as-lib, Great Expectations, PyMC, Polars-migration, repo-tools MCP, dbt-sqlite. The constitutional filter: **tools that absorb edge cases** (Datasette, DuckDB) beat **tools that add API surface** (Great Expectations, Pydantic).

This memo's scope: categories NOT covered by Mar 19 — observability platforms, transcript-analysis frameworks, Claude-Code-specific community tools, agent eval infrastructure, hook-composition DSLs.

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Inspect Scout (Meridian Labs) ingests Claude Code transcripts natively as a first-class source, alongside Inspect, Arize Phoenix, LangSmith, Logfire, MLFlow, W&B Weave | Docs homepage | HIGH | [SOURCE: meridianlabs-ai.github.io/inspect_scout/] | VERIFIED |
| 2 | Inspect Scout repo is MIT, 33 stars, created Sep 2025, last pushed Apr 17 2026 (1 day ago) | GitHub API | HIGH | [SOURCE: github.com/meridianlabs-ai/inspect_scout] | VERIFIED |
| 3 | Inspect AI (UK AISI) is at 1,912 stars, MIT, actively maintained (pushed Apr 17 2026), stores eval logs in queryable `.eval` + `.json` formats with `read_eval_log_sample` Python API | GitHub API + docs | HIGH | [SOURCE: github.com/UKGovernmentBEIS/inspect_ai, inspect.aisi.org.uk/eval-logs.html] | VERIFIED |
| 4 | Langfuse is 19K+ stars, MIT, but requires PostgreSQL (and ClickHouse for analytics at scale) — no SQLite backend | Multiple sources | HIGH | [SOURCE: langfuse.com/self-hosting, posthog.com/blog/best-open-source-llm-observability-tools] | VERIFIED |
| 5 | Arize Phoenix runs standalone locally without external DB; 8.9K stars; OpenInference/OTel-native; supports live streaming traces | Docs + comparisons | HIGH | [SOURCE: firecrawl.dev/blog/best-llm-observability-tools, zenml.io/blog/langfuse-vs-phoenix] | VERIFIED |
| 6 | LiteLLM is 43.8K stars, nightly v1.83.9 (Apr 17 2026), supports Anthropic provider, but positioned as gateway/proxy — not a local transcript-analysis tool | GitHub | HIGH | [SOURCE: github.com/BerriAI/litellm] | VERIFIED |
| 7 | simonw/claude-code-transcripts (1,449 stars) converts Claude Code sessions to multi-page HTML; last commit Feb 12 2026 — going stale | GitHub API | HIGH | [SOURCE: github.com/simonw/claude-code-transcripts] | VERIFIED |
| 8 | thedotmack/claude-mem (2,230 stars) is a Claude Code plugin that captures sessions and AI-compresses context for reinjection across sessions | ossinsight.io trending | MEDIUM | [SOURCE: github.com/thedotmack/claude-mem] | VERIFIED |
| 9 | claude-trace (Mario Zechner / badlogic) lives inside the `badlogic/lemmy` monorepo; last pushed Aug 13 2025 — stale for 8 months | GitHub API + npm | HIGH | [SOURCE: github.com/badlogic/lemmy, npmjs.com/package/@mariozechner/claude-trace] | VERIFIED |
| 10 | No open-source DSL specifically for composing Claude Code / agent-harness hooks has emerged as of April 2026; pre-commit, lefthook, husky remain the established git-hook frameworks and none target agent event triggers | Perplexity search | MEDIUM | [SOURCE: multi-source, no contradicting hits] | VERIFIED |
| 11 | Inspect Scout scanners include LLM-based and pattern-based detection for "misconfiguration, refusals, evaluation awareness"; parallel processing scales to thousands of transcripts | Docs | HIGH | [SOURCE: meridianlabs-ai.github.io/inspect_scout/] | VERIFIED |
| 12 | Inspect AI is already used by UK AISI, Anthropic, DeepMind for automated evals | Hamel Husain notes | MEDIUM | [SOURCE: hamel.dev/notes/llm/evals/inspect.html] | VERIFIED |

---

## Ranked Shortlist

Scoring rule: Apply Mar 19's filter (maintenance burden > creation cost) + our constitutional principle 8 (filter by maintenance, not effort) + principle 11 (architecture over API surface).

### Tier 1 — Probe Candidates (genuinely new, concrete fit)

**1. Inspect Scout (Meridian Labs)** — PROBE
- **What:** Transcript-analysis framework with LLM + pattern scanners. Reads Claude Code JSONL natively. MIT, from the Inspect AI core team. [github.com/meridianlabs-ai/inspect_scout, 33★, pushed 1 day ago]
- **Concrete use here:** Currently, `session-analyst` dispatches Gemini with compressed summaries (the Meta-Harness paper calls this the wrong design — raw traces beat summaries 50% → 34.9%). Scout could host pattern scanners directly against the JSONL traces in `~/.claude/projects/`, producing structured detections that feed `improvement-log.md`. This is the trace-fidelity upgrade the meta-harness memo identified (Tier 1 item 1c) with plumbing already written.
- **Maturity:** Low absolute stars (33) but from the right team, MIT, and actively developed. The low stars are the risk — not battle-tested, may churn.
- **Why not just build it:** Claude Code transcripts are a stated first-class source. We'd be reimplementing claude-code JSONL parsing + scanner orchestration + result storage. Scout absorbs that edge-case handling.
- **Gate:** Run one probe — point Scout at `~/.claude/projects/-Users-alien-Projects-agent-infra/` and see whether scanners produce usable output vs `session-features.py`. If the detection quality rivals `session-analyst`, we have a replacement. If it requires heavy custom scanner authoring, the leverage is lost.
- **Risk of waiting:** Low. Project is new. Watching for 1-2 months costs nothing.

### Tier 2 — Adopt the Pattern, Not the Tool

**2. Inspect AI (UK AISI)** — REFERENCE ARCHITECTURE, defer direct adoption
- **What:** Production eval framework (1,912★, MIT). Used by Anthropic, DeepMind, UK AISI. Clean `.eval` log format with programmatic readers (`read_eval_log_sample`).
- **Concrete use here:** Meta-Harness leverage memo calls for a "harness-outcome correlation dashboard" (Tier 2 item 2a). Inspect's `Task → Solver → Scorer` primitives map cleanly onto this. BUT — we don't have a clean benchmark yet. The meta-harness memo correctly deferred a formal benchmark suite ("synthetic benchmarks would diverge from actual usage").
- **Gate:** Defer until we have one task we can actually grade automatically (e.g., "given a session transcript, detect build-then-undo"). Then Inspect is the obvious host.
- **Pattern to extract now:** Their eval log schema (`.eval` format, compression, incremental sample access) is a good reference for how `runlogs.db` could evolve.

**3. OpenInference + OpenTelemetry GenAI semconv** — ALREADY FLAGGED
- **What:** Vocabulary for spans: `llm.invocation_parameters`, `llm.input_messages`, `llm.output_messages`, tool spans. Cross-vendor.
- **Concrete use here:** `runlog-otel-compatibility.md` already concluded: borrow vocabulary, do not adopt SDK. That holds. No change.
- **Status:** Treated correctly. No action.

### Tier 3 — Skip With Reason

**4. Langfuse** — SKIP
- 19K+ stars, MIT, but PostgreSQL required (ClickHouse for analytics). This violates the SQLite-native, file-first substrate of this repo. Adopting it would mean running two databases to watch traces that already land in `~/.claude/runlogs.db`. The infrastructure footprint is ~5x what Datasette gives us on top of existing SQLite.
- **Why not adopt:** "Tools that absorb edge cases" vs "tools that add API surface" — Langfuse is the latter. Postgres, ClickHouse, dashboard service, auth, user accounts. Not designed for single-user local-first use.

**5. Arize Phoenix** — MARGINAL, SKIP for now
- 8.9K★, runs standalone locally, no external DB. Closer fit than Langfuse.
- **Why not adopt now:** Uses OpenInference/OTel as the canonical trace shape. Our transcripts are native Claude/Codex/Gemini JSONL. Using Phoenix would mean first *converting* our transcripts to OTel spans, then viewing them in Phoenix. That's adapter work that buys us… another UI. Datasette over `runlogs.db` already covers the "I want to browse traces" need. Revisit only if we start exporting spans for an external consumer.

**6. LiteLLM proxy** — SKIP
- 43.8K★, active. But it's a *gateway* — positioned between application and providers. We don't broker LLM calls; Claude Code does. Our non-Claude dispatch is via `llmx`, which already handles routing + cost. LiteLLM would replace llmx with a proxy (Docker, network hop, different config surface) for marginal gain. Don't migrate working transport.
- **Note:** If we ever expose an MCP or Agent SDK endpoint to external callers, reconsider.

**7. Helicone** — SKIP
- Requires ClickHouse + Kafka for self-hosting. Same verdict as Langfuse, heavier. Not a local-first fit.

**8. AgentOps** — SKIP
- Vendor-hosted-centric; 400+ framework support is mostly cloud SDK integrations. The self-hosted story isn't there yet.

### Tier 4 — Claude-Code Community Tools (evaluate for ideas, not dependency)

**9. simonw/claude-code-transcripts** — EXTRACT IDEA, don't depend
- 1,449★, but last commit Feb 12 2026 — 2 months stale. Converts sessions to multi-page HTML with Gist publishing. Our `runlog.py` + Datasette already covers the "browse sessions" UX for SQLite data; this covers JSONL. Worth scanning for rendering ideas for a session-detail view.

**10. thedotmack/claude-mem** — PROBE IF CONTEXT REINJECTION BECOMES A PAIN
- 2,230★, trending. Plugin that captures sessions and AI-compresses context for reinjection across sessions. Interesting because it sits between our `.claude/checkpoint.md` convention and Anthropic's native memory feature.
- **Current assessment:** Our checkpoint convention + post-compaction verification rule covers the main failure mode (hallucinated completed work). Don't add a plugin dependency until we have concrete evidence our checkpoints aren't enough.

**11. claude-trace (badlogic/lemmy monorepo)** — SKIP
- 1,523★ on parent repo, but pushed Aug 13 2025 — 8 months stale. Proxy-based HTTP logger. Our `runlog_adapters` already parses transcripts from all three vendors directly. No reason to insert a proxy layer and maintain a staler upstream.

### Tier 5 — Hook DSLs (niche, no leverage available)

**12. Hook composition DSLs** — NO LEVERAGE
- Established: pre-commit, lefthook, husky — all scoped to git lifecycle. No Claude-Code-hook-composition DSL has emerged. Our `.claude/settings.json` + bash hooks + `pretool-*.sh` pattern IS the current SOTA. There is no third-party to adopt from.
- **Non-finding has value:** Confirms the hook architecture doesn't need rethinking at the DSL layer — only at the measurement layer (which `.claude/settings.json` + hook telemetry already covers).

---

## Key Findings

1. **One genuinely new leverage point emerged since Mar 19: Inspect Scout.** It's young (33★, 7 months old) but from the team behind Inspect AI, MIT, actively developed, and explicitly lists Claude Code transcripts as a first-class input source. This is the only candidate that passes the "absorbs edge cases" filter AND fills a gap we currently handle with custom Python.

2. **Langfuse / Helicone / LiteLLM are infrastructure platforms, not libraries.** They assume an enterprise deployment context that doesn't match a single-user, SQLite-native, file-first substrate. The prior constitutional filter (principle 8: filter by maintenance, not effort) correctly excludes them.

3. **The Claude Code community tooling space is shallow and stale.** claude-code-transcripts (Feb), claude-trace (Aug 2025) — both high-star projects have gone dormant. Only claude-mem (2,230★) appears actively maintained. This suggests the "just build it" threshold is low because the ecosystem hasn't consolidated yet.

4. **No hook-composition DSL exists for agent harnesses.** pre-commit/lefthook stopped at git. Nobody has shipped a declarative harness-hook framework. Our ad-hoc bash + `settings.json` approach isn't a gap — it's the frontier.

5. **The deepest real leverage is architectural, not packaged.** The Meta-Harness leverage memo identified the highest-ROI item as "feed raw traces to the analyst, not summaries" (+15pp expected). Inspect Scout is the packaged version of that pattern. Everything else is noise.

---

## What's Uncertain

1. **Inspect Scout's scanner ergonomics.** 33★ means almost nobody has built real scanners with it. The cost of authoring a useful scanner (vs writing Python against JSONL directly) is unknown until we try.

2. **Inspect Scout's parser fidelity.** Does it handle our three-vendor runlog variance (Claude, Codex, Gemini)? The docs only mention "Claude Code" — Codex and Gemini transcripts may need the capture/import APIs.

3. **Will the Inspect ecosystem consolidate further?** Inspect AI + Scout + Evals is a coherent product family. If Meridian Labs or UK AISI rolls Scout into Inspect core, the adoption calculation shifts.

4. **What Anthropic will ship natively.** Native Claude Code session analysis / replay tooling is a plausible Anthropic product. If it lands in 3-6 months, third-party tools like Scout become interstitial.

---

## Recommendation

Single action: **Run a one-session probe of Inspect Scout against `~/.claude/projects/-Users-alien-Projects-agent-infra/`.**

- Install via `uvx`, point it at the transcript directory, run one built-in scanner, compare output quality to `session-features.py` + `session-analyst`.
- Time-box: 90 minutes. If scanner authoring is painful or the parser chokes on our runlog variance, walk away — cost is the 90 minutes.
- If output quality is real, promote to a `/improve maintain` experiment: run Scout weekly, feed detections into `improvement-log.md`.

Everything else stays skip/defer. The Mar 19 survey's conclusions (Datasette, DuckDB, `jaq`, `hl`) remain the right ones, and no candidate in the adjacent spaces surveyed here beats the "build nothing" baseline except Scout.

---

## Search Log

| Query | Tool | Hits | Notes |
|-------|------|------|-------|
| Leading OSS LLM/agent observability tools April 2026 (Langfuse, Phoenix, OpenLLMetry, LiteLLM, AgentOps, Inspect AI, claude-trace) | perplexity_ask | high | Langfuse/Phoenix/OpenLLMetry covered; LiteLLM + Inspect AI + claude-trace gaps |
| Open-source DSL for composing shell/git/agent hooks 2026; Claude Code transcript replay and session analyzer repos with stars | perplexity_ask | high | pre-commit/lefthook remain SOTA; surfaced claude-mem, simonw/claude-code-transcripts, dreampulse/claude-code-logger, es617/claude-replay |
| Inspect AI + Inspect Scout + LiteLLM + claude-trace concrete specifics | perplexity_ask | high | Inspect Scout ingests Claude Code transcripts; claude-trace location confusion resolved (badlogic/lemmy) |
| Inspect Scout docs | WebFetch | 1 | Multi-source ingestion confirmed |
| LiteLLM repo | WebFetch | 1 | 43.8K★, v1.83.9-nightly, Anthropic supported |
| GitHub API verify stars + freshness | Bash (curl) | 4 | Inspect Scout 33★ MIT fresh; claude-code-transcripts 1449★ stale Feb; badlogic/lemmy 1523★ stale Aug |

## Revisions

(None yet — initial memo)

<!-- knowledge-index
generated: 2026-04-19T04:06:58Z
hash: 9e53feb35059

title: Leverage Survey Delta — Agent Observability, Transcript Analysis, Hook DSLs
status: complete
tags: leverage, observability, transcript-analysis, inspect-ai, inspect-scout, langfuse
table_claims: 12

end-knowledge-index -->
