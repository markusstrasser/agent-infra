---
id: 2026-04-10-agent-entity-surveillance
concept: entity-surveillance
repo: agent-infra
decision_date: 2026-04-10
recorded_date: 2026-04-10
provenance: contemporaneous
status: accepted
initial_leaning: register Websets MCP and wire into trending-scout for entity surveillance
relations: []
---

# 2026-04-10: Clone the entity-refresh pattern for agent entities — do not adopt Websets MCP

## Context

User asked "how and for what can we integrate https://exa.ai/docs/reference/websets-mcp into researcher skills." First-pass pushback narrowed the question to two surviving use cases:

- **(b)** trending-scout entity surveillance — tracking AI agents, coding tools, MCP servers as first-class entities with pricing, context window, transport, release cadence
- **(c)** this decision record regardless of verdict

User authorized both. Second-pass investigation surfaced two facts that change the answer.

### Fact 1 — a prior skip verdict exists, with a revisit trigger that is now technically met

`research/exa-skill-vs-ours.md § Websets API Assessment (2026-03-18)` recorded **verdict: skip** with three revisit conditions:

1. Websets adds MCP tools ← **technically met** as of this session. `https://websetsmcp.exa.ai/mcp?exaApiKey=...` exposes 13 tools: `create_webset`, `list_websets`, `get_webset`, `update_webset`, `list_webset_items`, `get_item`, `create_search`, `get_search`, `cancel_search`, `create_enrichment`, `get_enrichment`, `delete_enrichment`, `cancel_enrichment`, `create_monitor`.
2. We need a zero-maintenance company watchlist that doesn't justify orchestrator pipeline overhead ← **not met**. See Fact 2.
3. Exa adds cross-index verification ← **not met**. Websets is still single-index.

Only condition (1) fired. The underlying architectural objection from the prior memo — "Orchestrator + multi-API triangulation is architecturally stronger than a managed single-index pipeline" — was not addressed by the existence of an MCP; it was addressed by the addition of a transport.

### Fact 2 — the pattern Websets would install already exists in production

`pipelines/entity-refresh.json` runs daily at 06:00 for the intel project:

- reads `analysis/entities/*.md`
- for each entity stale >7 days, calls `web_search_advanced_exa` with `type='deep'` and `additionalQueries` for domain-specific variants, `outputSchema` for structured field extraction
- triangulates with `brave_news_search` (last 7d) and `perplexity_ask` for factual checks
- commits updates with source tags
- budget cap $3.0 per entity refresh cycle, 6 iterations, $8.0 pipeline cap

`pipelines/trigger-monitor.json` complements it — daily 07:00 — reading entity-level checkbox triggers and firing the deep-dive pipeline when conditions hit.

This is the entity surveillance primitive the 2026-03-18 memo said we had. It uses tools we already pay for, produces git-versioned markdown (auditable, diffable, greppable), and supports multi-source triangulation by construction.

**What's missing:** trending-scout does not yet have an equivalent. `pipelines/trending-scout.json` runs `/trending-scout weekly` which produces memo diffs against the prior week's memo. It does not maintain a canonical entity list for coding agents, MCP servers, or frameworks. This is the real gap the user's question exposed — but the cure is cloning intel's pattern, not adopting a new vendor capability.

## Alternatives considered

1. **Register Websets MCP globally in `agent-infra/.mcp.json`, wire into researcher skill.**
   Pros: matches the literal URL the user pointed at. Makes all 13 tools available everywhere.
   Cons: 13-tool schema permanently in every session's MCP prefix (estimated ~1.3K tokens against the 18.7K meta baseline per `.claude/rules/context-budget-principles.md § 7`). Weekly trending-scout usage amortizes across ~52 invocations/year vs a continuous per-session prefix cost. Retrieval-paradox risk — Cao et al. evidence cited twice in `.claude/rules/vetoed-decisions.md` (−40.5% on tool-using agents when retrieval is added alongside native shell tools), killed the knowledge-substrate MCP at 4 reads / 60 writes in 7 days and the repo-tools MCP at zero usage across 4,287 runs. Single-vendor lock-in.

2. **Register Websets MCP scoped to `agent-infra/.mcp.json` only, wire into trending-scout.**
   Pros: prefix cost scoped to meta project sessions.
   Cons: 13 tool schemas still cached in every meta session for a weekly job. Undocumented whether `websetsmcp.exa.ai/mcp` supports a `tools=` allowlist parameter (the regular `mcp.exa.ai/mcp` endpoint does; Websets endpoint not confirmed). Still single-vendor. Still duplicates what `entity-refresh` already does.

3. **Use Websets REST API via a Python script invoked from a pipeline. No MCP registration at all.**
   Pros: zero global context cost. Matches `.claude/rules/native-patterns.md` decision flow: "Can a just recipe + shell compose this from existing tools?" Yes — curl/httpx against the Websets REST endpoints. Uses the same `EXA_API_KEY` already in the env.
   Cons: custom wrapper to maintain. Still single-vendor. Still duplicates `entity-refresh`, just with a different backend.

4. **Clone `pipelines/entity-refresh.json` as `pipelines/agent-entity-refresh.json`. Track AI tools, agents, MCP servers, and frameworks as entities in `analysis/agent-entities/` using the same `web_search_advanced_exa` + `outputSchema` + `brave_news_search` + `perplexity_ask` primitives. Wire `trending-scout` Phase 0 to read from these entity files.**
   Pros: zero new dependencies. Reuses a proven production pattern. Multi-source triangulation (Exa + Brave + Perplexity) beats Websets' single-index by the 2026-03-18 memo's own argument. Entity files are git-versioned markdown — auditable, diffable, greppable, and covered by existing knowledge-index hooks. Same budget/iteration/cost controls as intel's entity-refresh. Orchestrator already handles scheduling, cost caps, and stop conditions.
   Cons: does not use Websets. Initial setup cost of defining the entity schema and seed list (Claude Code, Codex CLI, Aider, Cursor, Cline, Windsurf, a selection of MCP servers, a selection of frameworks).

## Decision

Adopt **Option 4**. Clone the `entity-refresh` pattern for agent-infra entities. Reject Websets MCP integration at any scope.

### What this means

- New directory `analysis/agent-entities/` with one markdown file per tracked entity. Seed set: Claude Code, Codex CLI, Aider, Cursor, Cline, Windsurf, a selection of MCP servers from the ecosystem, a selection of agent frameworks. Schema includes pricing, context window, transport, latest version, release cadence, notable recent changes.
- New pipeline `pipelines/agent-entity-refresh.json` — daily or semi-weekly refresh using `web_search_advanced_exa` with `type='deep'` + `outputSchema` for typed fields, `brave_news_search` for release announcements, `perplexity_ask` for spot checks. Budget caps mirroring `entity-refresh.json`.
- `trending-scout` SKILL.md Phase 0 updated to read `analysis/agent-entities/` as an additional baseline source. Phase 1 uses version deltas from entity files to detect bumps (augmenting the `vendor-versions.py` output). Phase 3 writes findings back to entity files when they're more current than the last refresh.

### What this does not change

- `/research` skill tool routing — unchanged.
- `researcher` subagent tool surface — unchanged.
- `/research-ops cycle` — unchanged.
- Paper discovery workflow — unchanged.
- No MCP servers added to `agent-infra/.mcp.json` or any other `.mcp.json`.

## Evidence

- **Prior verdict** — `research/exa-skill-vs-ours.md § Websets API Assessment (2026-03-18)`: "Orchestrator + multi-API triangulation is architecturally stronger than a managed single-index pipeline. The inline verification is the only novel piece, and it doesn't justify single-vendor lock-in."
- **Live pattern** — `pipelines/entity-refresh.json` and `pipelines/trigger-monitor.json`. Production for intel, daily schedule, uses Exa deep search + Brave + Perplexity. The exact architecture the 2026-03-18 memo argued for.
- **Context budget baseline** — `.claude/rules/context-budget-principles.md § 7`: meta always-loaded at 18.7K tokens (max 29.5K with all rules triggered). 13 new tool schemas is a non-negligible permanent addition.
- **Retrieval-paradox evidence** — `research/wiki-vs-flat-for-agents.md` (Cao et al., −40.5% on tool-using agents when retrieval is layered on top of native shell tools). Cited twice in `.claude/rules/vetoed-decisions.md` for the retired repo-tools MCP (2026-03-20, zero usage across 4,287 runs) and the retired knowledge-substrate MCP (2026-03-24, 4 reads / 60 writes in 7 days).
- **Websets async shape** — `exa.ai/docs/websets/overview`: "Websets is asynchronous. Poll for status, use webhooks for real-time updates, or just check the dashboard." Same polling shape as `deep_research`; no unique transport advantage.
- **Websets monitor cadence constraint** — `exa.ai/docs/websets/api/monitors`: cron expression, "schedule must trigger at most once per day." Daily floor. Compatible with a weekly scan but not uniquely enabling.
- **Tool allowlist support** — undocumented for `websetsmcp.exa.ai/mcp`. The regular `mcp.exa.ai/mcp` endpoint supports `tools=` allowlist (confirmed in `agent-infra/.mcp.json`). Cannot safely rely on the same capability for Websets without testing.
- **Base Exa pricing** (from `exa.ai/pricing`, verified this session): Search $7/1k, Deep Search $12/1k, Monitors $15/1k, Answer $5/1k, Contents $1/1k. Websets plan pricing not stated — requires dashboard login to see.

## Revisit if

- Cloned `agent-entity-refresh` pattern fails to scale — e.g., manual entity file maintenance becomes the dominant cost, or multi-source triangulation produces too much noise for the refresh agent
- Exa adds cross-index verification to Websets (still-open revisit condition from the 2026-03-18 assessment)
- Websets documents a `tools=` allowlist so we can register 3-4 tools instead of 13
- Websets publishes concrete per-call pricing that is competitive with the base Exa API ($7/1k search floor)
- A use case appears that genuinely requires in-pipeline AI criteria verification that post-hoc `verify_claim` cannot serve
- MCP schema compression lands in Claude Code (anthropics/claude-code#32105 tracked in `research/claude-code-native-features-deferred.md`) and cuts per-tool overhead by ≥10×
- We actively run ≥3 entity-tracking workflows where single-vendor lock-in is acceptable and the Websets inline verification measurably beats `verify_claim` on false-positive rate

## Supersedes

This decision supersedes the narrow "skip" verdict in `research/exa-skill-vs-ours.md § Websets API Assessment (2026-03-18)` for the specific revisit trigger that MCP tools now exist. The broader skip conclusion from that memo stands — this decision reaffirms it with new evidence about the live `entity-refresh` pattern in intel.
