# New Multi-Agent Orchestration / Durable-Agent Developments  
Date anchor: 2026-06-20. Search used Exa MCP only; no Brave, no Perplexity.

## Ranked Findings

1. **Cloudflare Agents SDK + Flue durable harness layer**  
Primary URL: https://blog.cloudflare.com/agents-platform-flue-sdk/ | Date: 2026-06-17  
Claim: Cloudflare is turning durable execution, durable filesystem, dynamic workflows, and sandboxed code execution into base primitives for arbitrary agent harnesses, with Flue as first framework.  
Demonstrated vs asserted: **Demonstrated in merged SDK/docs + official launch**, not just a pitch; `runFiber()`, `stash()`, `onFiberRecovered()` are documented and release-backed.  
Maturity: `cloudflare/agents` repo: ~5.1K stars, last push 2026-06-18, latest release 2026-06-17 per Exa.  
Why it matters locally: steal the **fiber checkpoint API shape** even if not using Cloudflare: durable turn row + explicit stash + recovery hook is the right small primitive for local Claude/Codex runs.

2. **Cloudflare detached sub-agent completion hook proposal**  
Primary URL: https://github.com/cloudflare/agents/pull/1758 | Date: June 2026 PR  
Claim: Adds detached sub-agent runs with durable exactly-once-ish completion delivery across Durable Object eviction, budget, cancel, and finish notification.  
Demonstrated vs asserted: **Partly demonstrated as concrete PR/RFC**, but not treated as shipped unless merged.  
Maturity: Same repo: ~5.1K stars; PR-level maturity, not stable API.  
Why it matters locally: maps directly to the local harness problem: background scouts need **run id, durable terminal slot, lease/claim delivery, idempotent callback**, not polling glue.

3. **Vercel Eve**  
Primary URL: https://vercel.com/blog/introducing-eve | Date: 2026-06-17  
Claim: Filesystem-first TypeScript agent framework where every conversation is a durable workflow with checkpointed steps, sandboxed compute, approvals, subagents, evals, and channels.  
Demonstrated vs asserted: **Official public beta**, with docs and package workflow; durability relies on Vercel Workflow SDK.  
Maturity: Public beta; `eve@0.11.4` latest noted 2026-06-19; GitHub exists at `vercel/eve`, stars not surfaced by Exa.  
Why it matters locally: the steal is **agent-as-directory** plus conventional files for instructions/tools/skills, not the hosted Vercel runtime.

4. **OpenRath session-graph runtime**  
Primary URL: https://github.com/Rath-Team/OpenRath | Date: repo published 2026-05-04; article coverage 2026-06-18  
Claim: Reframes orchestration around `Session -> Session` transformations, with session graph lineage, sandbox placement, memory, tools, and workflows tied to the session rather than agent-local message lists.  
Demonstrated vs asserted: **Repo/package exists; design mostly asserted in docs**, needs hands-on validation.  
Maturity: PyPI `openrath v1.2.1`; GitHub stars/last-push not surfaced by Exa.  
Why it matters locally: strong conceptual steal: make the **session/workspace/sandbox binding** the principal state object so tool execution cannot drift silently across agents.

5. **AuctorAI `durable_agents`**  
Primary URL: https://github.com/AuctorAI/durable_agents | Date: 2026-05-11  
Claim: Demonstrates agents as workflows that write child workflows: model steps and tools lower to Temporal activities; subagents lower to child workflows; PTC remains workflow-native.  
Demonstrated vs asserted: **Demonstrated demo + pytest suite**, but explicitly omits production policy gates and failover drills.  
Maturity: 21 stars, last push 2026-05-14.  
Why it matters locally: useful lowering rule: **normal tools become activities; orchestration tools stay workflow-native**. That avoids wrapping `spawn`/`run_ptc` as opaque side effects.

6. **Overseer**  
Primary URL: https://github.com/nikitavivat/Overseer | Date: 2026-05-13  
Claim: Reliable multi-agent workflow runtime where verifier nodes, retry/halt policies, snapshots, event bus, UI, and intervention are part of the execution graph.  
Demonstrated vs asserted: **MVP repo; much is README-level**, but the primitives are concrete and local-friendly.  
Maturity: v0.1 MVP; stars/last-push not surfaced by Exa.  
Why it matters locally: the steal is **verifier as a first-class node**, not a post-hoc report. This matches local harness gates better than another observability dashboard.

7. **Google AX / Agent Executor**  
Primary URL: https://github.com/google/ax | Date: 2026-03-30  
Claim: Distributed agent runtime with a single controller, event log, resumable executions, isolated local/remote actors, auditing, and policy.  
Demonstrated vs asserted: **Early open-source runtime; docs assert active protocol churn**.  
Maturity: Exa surfaced ~1 star and active contributor list; last-push not cleanly surfaced. Interfaces expected to change.  
Why it matters locally: reinforces the local architecture bias: **single-writer controller + append event log** beats peer mesh coordination for recoverability and audit.

8. **Open Multi-Agent**  
Primary URL: https://github.com/open-multi-agent/open-multi-agent | Date: 2026-03-31; latest release 2026-06-19  
Claim: Goal-first TypeScript coordinator decomposes a goal into a runtime task DAG, parallelizes independent tasks, supports checkpoint/resume and consensus/verify hooks.  
Demonstrated vs asserted: **Active repo with examples/docs**, but dynamic DAG quality needs empirical checking.  
Maturity: ~640 stars, last push 2026-06-20, latest release v1.8.0 on 2026-06-19.  
Why it matters locally: steal cautiously: runtime task DAG generation is useful for **research fan-out**, but code-writing should still keep one writer.

9. **CycGraph orchestrator**  
Primary URL: https://github.com/wmcmahan/cycgraph/tree/main/packages/orchestrator | Date: 2026-03-09  
Claim: TypeScript cyclic state graph orchestrator with event-sourced replay, snapshots, verifier/reflection/voting/evolution nodes, human gates, MCP integration, and optional Postgres persistence.  
Demonstrated vs asserted: **Repo package with claimed 2,400+ tests**, but maturity metadata not surfaced by Exa.  
Maturity: `@cycgraph/orchestrator` status 0.2.0; stars/last-push not surfaced.  
Why it matters locally: steal the **node taxonomy** only where it maps to clear local needs: verifier, approval, map, synthesizer, subgraph.

10. **AgentRearrange / Swarms v12 primitive**  
Primary URL: https://github.com/The-Swarm-Corporation/AgentRearrange-Paper | Date: 2026-06-01  
Claim: Tiny flow DSL using `->` and `,` expresses sequential/concurrent multi-agent topologies, reducing separate sequential/concurrent workflow classes to one primitive.  
Demonstrated vs asserted: **Technical report + examples**, weaker than a runtime with tests.  
Maturity: GitHub paper repo; no stars/last-push surfaced by Exa.  
Why it matters locally: limited steal: a tiny topology grammar can make static scout plans readable, but avoid shared-conversation execution for coding work.

## Lower-Relevance / Watchlist

- **Piotr Wachowski `durable-agents`**: https://github.com/piotrwachowski/durable-agents | 2026-05-30 | Temporal-backed DeepAgents-style loop, alpha, 1 star. Interesting but less mature than AuctorAI for the same Temporal lowering idea.  
- **Sarmakska `agent-orchestrator`**: https://github.com/sarmakska/agent-orchestrator | 2026-05-03 | Postgres/Drizzle/Redis/BullMQ deterministic replay, hard budgets, inspector. 0 stars, last push 2026-06-15. Looks like a solo product scaffold, not yet evidence.  
- **Google “Towards a science of scaling agent systems”**: https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/ | 2026-01-28 | Not last-4-weeks, but useful evidence: centralized orchestration helps parallelizable tasks; independent agents amplify errors. Not pre-frontier, but still paper/blog evidence rather than local harness proof.

## Top Steals

1. **Fiber model:** local `run_id` row + checkpoint stash + recovery callback + poison-row aging for every long agent turn.  
2. **Detached subagent delivery:** background scout runs need durable terminal records with claim/lease/idempotent notification, not polling.  
3. **Session graph as truth:** bind transcript, workspace, sandbox, lineage, budgets, and verifier outcomes to one session object; derive flat messages from it.