---
title: Agent Workflow Orchestration Frameworks — adopt / pattern-extract / already-best?
date: 2026-06-20
status: COMPLETE
question: As of mid-2026, is there an off-the-shelf agent-workflow orchestration framework (multi-step pipelines, fan-out, loops, durable/resumable execution) worth ADOPTING over our two in-harness engines, or is ours best for a single-operator local harness?
prior_coverage:
  - research/2026-06-19-multiagent-orchestrator-tool-survey.md (our internal patterns)
  - research/2026-06-20-research-agent-orchestration-tooling.md (RESEARCH agents only)
  - research/2026-06-12-symphony-orchestrator-reference.md (OpenAI Symphony)
method: GitHub REST API (stars/pushed_at/archived, queried 2026-06-20) + official docs + vendor comparison pages. Every maturity figure dated.
---

# Agent Workflow Orchestration Frameworks — 2026-06-20

## Verdict (bottom line)

**ALREADY-BEST-FOR-OUR-CONTEXT.** No framework here is worth adopting as a dependency for a
single-operator local Claude-Code/Codex/Cursor harness. Every one of them is built for the case we
explicitly are NOT: a *production multi-agent SERVICE* you deploy, host, scale, and operate — a
server/runtime/DB to stand up, a programming model to rewrite into, and (for the durable camp) an
operational surface (Postgres/Cassandra/Elasticsearch/worker fleet) that dwarfs our entire harness.
Our two engines (the in-harness JS Workflow tool + file-bus `just` recipes) already cover the
primitives — fan-out, per-item pipeline, loop-until-dry/budget, background+notify, journal resume —
at $0 with zero deployment.

**ONE pattern worth extracting (not adopting):** the durable-execution camp's **per-step
content-addressed memoization + deterministic replay** is a *stronger* durability contract than our
resume-from-runId journal in one specific way — it survives a crash *mid-step* and re-derives by
replaying the function, not just caching whole `agent()` calls. If we ever run a multi-hour
unattended workflow where a step is expensive and non-idempotent, steal the **"checkpoint after
every step, keyed by deterministic step-id"** idea (DBOS/Inngest model) — ~a journal-granularity
refinement to the Workflow tool, NOT a Temporal/Restate dependency.

**Durable-execution verdict:** the camp offers something *materially better in kind* (crash-safe
mid-workflow, automatic replay) but NOT *better at our scale* — the lightest of them (DBOS) still
demands a Postgres instance and an in-app rewrite into its decorator model; the rest (Temporal,
Restate, Inngest) require a separate server/runtime process. The weight is justified for a 24/7
revenue service, never for one operator's laptop loop. Pattern-extract the memoization granularity;
reject the dependency.

---

## Maturity table — live GitHub, queried 2026-06-20 (REST API: stars / pushed_at / archived)

| Framework | Repo | Stars | Last push | Live? | Camp |
|---|---|---|---|---|---|
| CrewAI | crewAIInc/crewAI | 54,012 | 2026-06-20 | live | agent framework |
| Microsoft Agent Framework | microsoft/agent-framework | 11,493 | 2026-06-20 | live | agent framework (AutoGen+SK successor) |
| AutoGen | microsoft/autogen | 59,086 | **2026-04-15** ⚠ | live but **superseded** | → folded into MAF |
| AG2 (ex-AutoGen fork) | ag2ai/ag2 | 4,694 | 2026-06-19 | live | agent framework |
| LangGraph | langchain-ai/langgraph | 35,261 | 2026-06-19 | live | graph/workflow |
| OpenAI Agents SDK | openai/openai-agents-python | 27,275 | 2026-06-19 | live | agent framework (ex-Swarm) |
| Google ADK | google/adk-python | 20,190 | 2026-06-19 | live | agent framework |
| LlamaIndex (Workflows) | run-llama/llama_index | 50,234 | 2026-06-20 | live | RAG + event Workflows |
| Pydantic AI | pydantic/pydantic-ai | 17,864 | 2026-06-18 | live | typed agent framework |
| Mastra | mastra-ai/mastra | 25,263 | 2026-06-20 | live | TS agent framework |
| Burr | DAGWorks-Inc/burr | (repo **moved/301**) | — | rebranded/moved | state-machine lib (niche) |
| Dapr Agents | dapr/dapr-agents | 695 | 2026-06-19 | live (small) | Dapr-runtime agents |
| **Durable-execution camp** | | | | | |
| Temporal | temporalio/temporal | 21,096 | 2026-06-20 | live | durable exec (server cluster) |
| Restate | restatedev/restate | 4,040 | 2026-06-19 | live | durable exec (single server runtime) |
| DBOS (py) | dbos-inc/dbos-transact-py | 1,428 | 2026-06-19 | live | durable exec (library + Postgres) |
| DBOS (ts) | dbos-inc/dbos-transact-ts | 1,248 | 2026-06-16 | live | durable exec (library + Postgres) |
| Inngest | inngest/inngest | 5,514 | 2026-06-19 | live | durable exec (dev server / cloud) |
| Prefect | PrefectHQ/prefect | 22,649 | 2026-06-20 | live | data-pipeline orchestrator |
| Airflow | apache/airflow | 45,876 | 2026-06-20 | live | data-pipeline orchestrator (heavy) |

**Star-farm / abandonment screen:** none are star-farms — all the above are multi-year repos from
named orgs (LangChain, OpenAI, Google, Microsoft, Pydantic, CrewAI Inc, Temporal, Restate) with
same-day-to-same-week pushes. The only maturity caveats:
- **AutoGen is winding down** (last push 2026-04-15 vs everything else same-week) — Microsoft Agent
  Framework reached **Release Candidate for .NET + Python ~2026-02-20** (devblogs.microsoft.com) and
  is the *direct successor to both AutoGen and Semantic Kernel*, built by the same teams. Treat
  AutoGen as legacy; if you'd ever benchmark Microsoft's stack, it's MAF.
- **Burr** (DAGWorks) returns HTTP 301 Moved — the org rebranded; it was always a niche
  state-machine lib, not a contender at our scale.

---

## Per-framework: what it does that our two engines do NOT + local-fit

Our baseline (do NOT recommend anything that merely equals this):
- **Workflow tool** (in-harness JS): `agent()` w/ JSON-schema structured output, `parallel()` barrier
  fan-out, `pipeline()` per-item multi-stage (no inter-stage barrier), loop-until-dry / loop-until-
  budget, background + completion notification, **resume-from-runId** (journal: unchanged `agent()`
  calls return cached, only edited/new re-run), concurrency-capped, token-budget-aware.
- **File-bus `just` recipes**: standing fire-and-forget pipelines, inspectable as files on disk, $0.

### Agent frameworks (CrewAI / MAF / OpenAI Agents SDK / Google ADK / Pydantic AI / Mastra / AG2)
- **What they add over us:** higher-level *agent abstractions* — roles/crews, handoffs, group-chat,
  guardrails, provider-agnostic model clients, built-in tracing dashboards, A2A/AG-UI/MCP interop.
  These are SDKs for *building an agent product*. We don't build a product; our "agents" are
  Claude-Code/Codex/Cursor subagents already wired to MCP + skills + hooks.
- **What they do NOT add:** nothing our orchestration *primitives* lack. Fan-out, sequential
  pipeline, loops, conditional routing, human-in-the-loop — all present in both ours and theirs;
  theirs is a code-SDK form, ours is a harness-native form already integrated with our token-budget
  and concurrency caps.
- **Local-fit:** all pip/npm-installable libraries (no server), so "weight" is low — BUT adopting
  one means rewriting our orchestration into *their* model and inheriting their provider-client layer
  (which fights our $0 Claude-subscription routing, since they assume API-key billing). Net: a
  lateral move that costs integration and buys abstractions we don't need. **Reject.**

### LangGraph — the closest "graph workflow" analog
- **Adds:** an explicit graph/state-machine model with a **checkpointer** (in-memory, SQLite, or
  Postgres backends) giving durable state + time-travel + human-in-the-loop interrupts; resume after
  crash at node granularity. SQLite checkpointer = genuinely local, no server.
- **Vs us:** its checkpointer is conceptually our resume-from-runId, with node-level (vs `agent()`-
  call-level) granularity and a pluggable store. That's a *refinement*, not a capability we lack.
- **Local-fit:** YES (library + SQLite, no server) — the most adoptable here. But it brings the
  LangChain dependency surface and a graph-authoring model that duplicates what our JS engine already
  does. **Pattern-note its SQLite-checkpointer granularity; don't adopt the framework.**

### LlamaIndex Workflows — event-driven steps; Dapr Agents — Dapr-runtime
- LlamaIndex Workflows = event/step decorators with optional checkpointing; tied to the LlamaIndex
  universe (RAG-first). Dapr Agents (695★, small) = agents on the Dapr sidecar runtime — assumes a
  Dapr deployment (sidecar process). Both **server-ish or ecosystem-locked**; no fit.

### Prefect / Airflow / Dagster — data-pipeline orchestrators
- Built for *scheduled data pipelines* (ETL/ML), not agent loops. Airflow needs a scheduler +
  webserver + metadata DB (heavy). Prefect is lighter (can run a local server / `prefect server`) but
  is still a workflow *server* with a UI, aimed at recurring data jobs across a team. Our launchd +
  `just` recipes already cover scheduled local jobs at $0. **Wrong tool class. Reject.**

---

## Durable-execution camp — the special-focus question

Our resume-from-runId journal caches whole `agent()` calls. The durable camp's contract is stronger
*in kind*: **checkpoint after every step, keyed by a deterministic step-id, and on crash REPLAY the
function** — surviving a crash *mid-workflow* and re-deriving state, not just skipping completed
sub-calls. Worth the dependency at our scale? Deployment weight decides it:

| Tool | Runtime model | What it needs locally | Local-fit verdict |
|---|---|---|---|
| **DBOS** | **in-process LIBRARY** (decorators) | **Postgres only** — no daemon/server. ~1 DB write/step + 2/workflow (docs.dbos.dev) | Lightest. Still: a Postgres instance + rewrite into `@workflow/@step` decorators. |
| **Inngest** | event-driven; functions invoked over HTTP by an engine | dev = `npx inngest-cli dev` single binary (in-memory/SQLite); prod designed around **managed cloud** ($75+/mo) or self-host single binary | Medium. Inverts control (engine calls your HTTP fn); cloud-oriented. |
| **Restate** | **separate server runtime** + SDK (TS/Py/Go/Java/Rust) | run a Restate server process alongside the app; Cloud or self-host | Heavy-ish: a standing server. |
| **Temporal** | **server CLUSTER** + worker fleet | self-host = Cassandra/Postgres **+ Elasticsearch + server fleet**; steepest learning curve in the category; opaque Actions billing on Cloud | Heaviest. Explicitly "too heavy for small teams" (wetheflywheel 2026-06-05). |

Sources: docs.dbos.dev/architecture; inngest.com/docs/learn/how-functions-are-executed +
DEVSERVER_ARCHITECTURE.md; docs.restate.dev; inngest.com/compare-to-temporal +
wetheflywheel.com/en/comparisons/temporal-vs-inngest (2026-06-05).

**Why none clear the bar:**
1. Even DBOS — the only true *library* — needs a Postgres instance and a rewrite of our JS engine
   into its decorator model. Our journal already gives crash-resume at `agent()` granularity; the
   *only* delta is mid-step crash recovery via replay, which matters when a single step is long +
   expensive + non-idempotent. Our steps are LLM/subagent calls that are *naturally* re-runnable and
   already journaled — so the marginal durability we'd buy is small.
2. The replay model imposes a **determinism constraint** (your step code must be deterministic given
   inputs) that fights the very thing our steps do (call non-deterministic LLMs). The camp handles
   this by treating LLM calls as "activities/steps" whose *outputs* are checkpointed — which is
   exactly what our journal already does.
3. Temporal/Restate/Inngest all add a server/runtime *process* — a permanent operational surface on
   a single-operator laptop, contradicting our zero-deployment, $0-subscription posture.

**Pattern-extract (the one real steal):** if we ever build a multi-hour unattended Workflow-tool run
where a mid-step crash would waste expensive work, add **per-step content-addressed checkpoints**
(deterministic step-id → cached output) so resume restarts at the failed *step*, not the failed
`agent()` *call*. This is a ~journal-granularity upgrade to our existing engine, gated on a real
incident (no such incident logged yet — default to not building, per Pre-Build #1).

---

## Distinguishing "production service" (not us) from "local harness" (us)

Every framework here optimizes for the production-service axis: provider abstraction (so you can
swap models in a deployed app), observability dashboards (so a team can watch prod runs), durable
servers (so a 24/7 workflow survives infra failure), multi-tenant state stores. We have **one
operator, one machine, ephemeral runs, $0 subscription, and the agent itself as orchestrator** — the
dashboards, provider layers, and durable servers are pure overhead. The frameworks are good; they
solve a problem we don't have.

## Post-synthesis completeness check (every requested tool accounted for)
LangGraph ✓ · CrewAI ✓ · AutoGen (superseded→MAF) ✓ · AG2 ✓ · OpenAI Agents SDK ✓ · Google ADK ✓ ·
LlamaIndex Workflows ✓ · Pydantic AI ✓ · Mastra ✓ · Burr (moved/niche) ✓ · Dapr Agents ✓ ·
Temporal ✓ · Restate ✓ · DBOS ✓ · Inngest ✓ · Prefect ✓ · (Airflow/Dagster as the data-pipeline
class) ✓ · NEW-surfaced: Microsoft Agent Framework (AutoGen+SK successor, RC Feb 2026) ✓.

## Caveats / provenance
- All star/push figures: GitHub REST API, 2026-06-20 (one snapshot; cadence inferred from same-week
  pushes, not full commit-history analysis — bus-factor read is org-backing, not contributor counts).
- Deployment-weight claims sourced to official docs + one vendor comparison (Inngest's own
  Temporal-comparison page is self-interested re: Temporal heaviness — but the *Temporal* self-host
  requirements, DBOS Postgres-only, and Restate separate-server facts cross-check against their own
  docs).
- No framework was run/installed this pass; verdict is architecture-fit, not a benchmark.
