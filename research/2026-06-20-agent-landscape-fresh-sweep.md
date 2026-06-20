---
title: "Agent Landscape Fresh Sweep — 12-axis gpt-5.5-low fan-out (the NON-RSI delta)"
date: 2026-06-20
tags: [trending, agent-frameworks, mcp, memory, coding-agents, evals, observability, local-models]
status: COMPLETE
method: 12 parallel codex-exec gpt-5.5-low scouts, web-grounded via exa MCP, $0 ChatGPT-subscription path. exa-primary (no Brave/Perplexity contention). Primary URLs only (GitHub/arXiv/official blogs); listicles rejected.
cost: "$0 (subscription; ~38K MCP-overhead tokens/call × 12 = uncounted sub tokens). Wall: ~9 min, 2 waves of 6. Yield: 12/12 axes non-empty, 6-10KB each, ~120 raw findings."
prior_coverage:
  - research/2026-06-19-rsi-sota-synthesis-what-to-integrate.md  # RSI axis — this sweep is the COMPLEMENT
  - research/2026-06-20-agent-workflow-orchestration-frameworks.md
  - research/2026-06-20-research-agent-orchestration-tooling.md
  - research/trending-scout-2026-06-19.md
raw: research/sweep-raw-2026-06-20/*.md  # 12 per-axis scout outputs (provenance)
---

# Agent Landscape Fresh Sweep — 2026-06-20

Complement to the 06-19 RSI sweep, which was self-improvement-focused. This pass covered the
axes that one **skipped**: general frameworks, coding agents, MCP/tool ecosystem, memory,
evals, local models, observability, practitioner blogs, context-engineering. 12 gpt-5.5-low
scouts via codex-exec + exa.

## Verdict

**The field keeps re-deriving our architecture; the value is ~8 NEW bolt-on mechanisms + 3 NEW
eval-instrument classes, none a dependency to adopt.** Same meta-finding as the RSI sweep, now
triangulated from the *product/framework* side: durable-execution, single-writer-many-readers,
git-as-store, verifier-as-first-class-node, typed-context-lifecycle, harness-on-frozen-model are
all independently converged. Nothing here is a rebuild. **The genuinely new, high-fit steals are
the ones our 296-memo corpus did NOT already hold** (deduped below).

## Already-covered (do NOT re-research — flagged so novelty claims stay honest)

| Surfaced this sweep | Already in corpus |
|---|---|
| Claude Code Dynamic Workflows | the Workflow tool itself + `agent-workflow-orchestration-frameworks` |
| OpenAI Symphony (ticket-as-state) | `2026-06-12-symphony-orchestrator-reference` |
| OpenAI self-improving tax agents | `rsi-sota-synthesis` (existence proof) |
| A2H / Adaptive Auto-Harness (2606.01770) | `rsi-sota-synthesis` (the accretion through-line) |
| MCP 2026-07-28 RC stateless, pin `<2` | `tool-use-mcp-4w` + `trending-scout-2026-06-19` |
| Cognition "Multi-Agents: single-writer" | `multi-agent-coordination-4w` + `multiagent-state-coordination-prior-art` |
| Steering Claude Code (instruction surfaces) | `vendor-binary-skill-archaeology`, `agent-extensibility-surfaces` |
| BM25/grep beats memory systems (opsem) | `why-grep-stays-winning`, `long-context-memory-4w` |
| Context Ledger / git-as-store | `state-externalization-lens`, `git-native-tooling-anchors` |
| EFC, AHE, Bayesian-Agent, GEPA, Hermes, ShinkaEvolve, eve, FAMOU | the 4 RSI delta memos (06-19) |
| Terminal-Bench / SWE-bench-Pro yardsticks | `agentic-coding-swe-4w`, `benchmark-leaderboard-methodology-critique` |

## NEW delta — ranked by fit to OUR system (act-drain/blindspot loop · session-trace · skills/rules/hooks · /eval · emb-over-agentlogs)

| # | Steal | Source (NEW) | Maps onto | Confidence |
|---|-------|--------------|-----------|------------|
| **1** | **Typed trace-IR before diagnosis** — normalize failed trajectories + harness code into a Harness-aware Trace IR, diagnose against the IR not raw transcripts (15.2–50% held-out gains) | **HarnessFix/HTIR, arXiv:2606.06324** (Jun 4) | our `session-trace` recipe + act-drain reviews RAW transcripts today → add a typed-IR layer | MED (paper, needs repro) |
| **2** | **Decompose uncertainty to decide when to ASK** — split action-confidence from request-uncertainty; ask clarification only when task is underspecified, esp. before irreversible edits | **Uncertainty Decomposition, arXiv:2606.19559** (Jun 17, demonstrated on 5 backbones) | our measured **over_caution=63 / over-ask** blindspot; feeds the behavioral over-caution testground (synthesis #5) with an actual METHOD | MED-HIGH |
| **3** | **Typed skill graph** — replace flat skill/rule lists with typed edges: depends-on / conflicts-with / **supersedes** / **duplicate-of** | **SkillDAG, arXiv:2606.03056** (32★) + ReSkill (Amazon, 12★) | direct counter to our #1 measured risk (accretion / "policy maze"); supersedes/duplicate-of edges enable pruning flat lists can't express | MED |
| **4** | **Raw-trace adjacency for condensed lessons** + **pre-action judgment gate** — agents demonstrably misuse condensed experience and rely on raw; keep raw-trace pointers next to every distilled lesson; gate actions against past failures before repeating | **"Not Always Faithful Self-Evolvers" arXiv:2601.22436v3** (Jun 12) + **PROJECTMEM arXiv:2606.12329** (event-sourced local + judgment gate) | sharpens append-only MEMORY + composes with predict-then-falsify gate (synthesis #1); we already keep agentlogs raw — make the *link* first-class | MED-HIGH |
| **5** | **Measure model×HARNESS, not model alone** — co-eval benchmarks where the harness gap rivals a model upgrade | **PawBench** (2606, model×harness×task grid) · **WildClawBench arXiv:2605.10912** (tests Claude Code/Codex/Hermes harnesses!) · **WeaveBench arXiv:2606.09426** (trajectory-aware judging) | `/eval` + our "harness on frozen model" thesis (P1); WildClawBench is direct prior-art for a harness-eval we could run | HIGH (repos+leaderboards live) |
| **6** | **Tool-call-PAIR compaction** — evict whole tool-call/result pairs + small summaries, keep last-N full; 71→91.6% task completion, ~63% fewer tokens | **Less Context Better Agents, arXiv:2606.10209** (50 live tasks, CIs) | our compaction hooks evict by age/size; switch to recoverability/dependency units (also pi-cwl 2606.11213, ACDL 2605.01920) | MED (narrow ERP domain) |
| **7** | **Objective-simulator evals > LLM-judge** — derive harm/score from state transitions, not prose judging; also eval **patience** (agents overreward action) | **NRT-Bench arXiv:2606.20408** + **SentinelBench arXiv:2606.05342** | reconfirms our env-ground-truth-fitness principle; SentinelBench "miss patience/cost" = measurable face of our over-action | HIGH (principle) / MED (repos early) |
| **8** | **Intention-aware tool discovery** — expose a compact capability graph, load exact schemas only when task state warrants (99.8% schema-exposure cut) | **SING arXiv:2606.16591v2** (Jun 17) | validates our deferred-tools / ToolSearch design; the *graph-first then load* shape is a refinement | MED |

### Watch / lower-fit (NEW but not for us now)
- **Durable-execution frameworks** (Cloudflare Agents+Flue fiber API · Vercel Eve agent-as-directory · AuctorAI durable_agents · OpenRath session-graph · Overseer verifier-node) — all converge on the "per-step checkpoint + recovery" steal already named in `agent-workflow-orchestration-frameworks`. Cloudflare's `runFiber()`/`stash()`/`onFiberRecovered()` is the cleanest API shape if we ever harden Workflow-tool mid-step durability. **Pattern, not dependency** (all are hosted-runtime-shaped).
- **Observability**: Datadog-labs **Trajectory** (local Claude/Codex/Cursor trace tool, 4★), Braintrust **Topics** (cluster→regression-dataset), Phoenix span-annotation, Azure AgentOps **error taxonomy** (grader-execution-error vs quality-failure — cheap steal for our /eval gate status contract). Mostly SaaS; steal the *patterns*.
- **New open models** (Jun): Kimi **K2.7 Code**, **GLM-5.2** (1M ctx, TB2.1 63.5→81.0 vendor-run), **Qwen Code v0.17** (built-in computer-use, shipped+inspectable), **MiniMax M3**. **DeepSeek V4-Pro: CAISI/NIST says ~8 months behind frontier** — useful corrective to vendor parity claims. Update `frontier-model-releases-delta` (05-27, now stale). All MCP/SWE numbers are harness-confounded vendor-run → screen-only, never promote without our own workload eval (= steal #5).
- **HF "Is it agentic enough?"** (Jun 18) — local model×repo-revision×task eval on your own tooling; the methodology = our /eval discipline, good reference.
- **FlowBank (2606.11290)** workflow-portfolio+router, **OrchRM (2606.13598)** artifact-scored orchestration reward, **Beyond Commitment Boundary (2606.13603)** early-exit-when-answer-committed stop rule, **HyperTool (2606.13663)** executable meta-tool (flagged risky w/o sandbox), **Socratic-SWE (2606.07412)** / **OpenSkill (2606.06741)** trace→skill+verification-anchors — all align with directions we already hold; queue, don't chase.

## Recommended actions (cheap, local, autonomous-eligible)
1. **Steal #2 (uncertainty decomposition) into the behavioral over-caution testground** — it's the missing METHOD for our largest measured blindspot; composes with synthesis #1/#5.
2. **Steal #4 (raw-trace adjacency)** — make condensed MEMORY/lesson entries carry a raw agentlogs pointer; near-zero cost, we already store raw.
3. **Update `frontier-model-releases-delta`** (05-27 → stale) with the Jun open-model wave + the CAISI DeepSeek corrective.
4. **#5 (model×harness eval)** — log WildClawBench/PawBench as prior-art in `/eval` before we build any harness-comparison eval.

## Confidence grading (AI-relayed; gpt-5.5-low scouts, exa-grounded — NOT independently body-verified)
All findings are scout-relayed from primary URLs the scouts cite but I did NOT open each PDF/repo.
HIGH (repo+leaderboard live, triangulated): #5 benchmarks, #7 principle, the convergent-validation meta-finding.
MED (single paper, asserted rates, needs repro before citing a number): #1, #3, #6, #8, EFC-class rates.
**Verify-before-cite:** any specific % (HTIR 15-50%, Less-Context 71→91.6%, SING 99.8%, GLM-5.2 TB2.1) is vendor/paper-reported and harness-confounded — screen-only.
