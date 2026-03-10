# Agent Scaffolding, Self-Improvement, and Orchestration — March 2026 Landscape

**Date:** 2026-03-10
**Tier:** Deep
**Ground truth:** 65 existing research memos + 92 corpus papers. Extensive coverage of context degradation, reliability benchmarks, multi-agent coordination, CoT faithfulness, tool use/MCP, memory, safety, self-modification, causal reasoning, cross-model review, divergent thinking, search APIs, orchestrator design (Symphony/OpenAI), code structure, epistemic scaffolding.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | MAS fail 41-86.7% of the time across 7 SOTA frameworks | 1600+ annotated traces, κ=0.88 | HIGH | [MAST, arXiv:2503.13657, NeurIPS 2025] | VERIFIED |
| 2 | System design issues cause 44% of MAS failures, not LLM limitations | MAST taxonomy, 14 failure modes | HIGH | [MAST] | VERIFIED |
| 3 | Simple workflow fixes (e.g., CEO final say) yield +9.4% success rate | Case study in MAST | MEDIUM | [MAST] | VERIFIED-SINGLE |
| 4 | ACT (RL for action quality judgment) beats imitation learning by +5.07 pts | ALFWorld/WebShop/ScienceWorld benchmarks | HIGH | [ACT, arXiv:2603.08706, March 2026] | VERIFIED |
| 5 | ACT transfers to general reasoning (MATH-500, GPQA) without reasoning training data | OOD evaluation in ACT paper | MEDIUM | [ACT] | VERIFIED |
| 6 | Mandatory "thinking" can backfire in user-engaged agent scenarios | Study on reasoning models in agent settings | MEDIUM | [arXiv:2602.07796, Feb 2026] | VERIFIED-ABSTRACT-ONLY |
| 7 | In production, 68% of tool failures = incorrect parameters, 21% = wrong tool, 11% = hallucinated data | Production deployment analysis | MEDIUM | [Iterathon blog, 2026] | [SOURCE: blog] |
| 8 | Production agents hit 85-90% task completion ceiling | Year-long deployment report | MEDIUM | [Viqus blog, 2026] | [SOURCE: blog] |
| 9 | Automated failure attribution via Shapley values works for MAS debugging | 50 citations, formalization paper | HIGH | [arXiv:2505.00212] | VERIFIED |
| 10 | Graph-based failure tracing outperforms temporal attribution for cascading errors | GraphTracer, multi-turn search | MEDIUM | [arXiv:2510.10581] | VERIFIED |
| 11 | Confidence-guided MCTS (using log-prob uncertainty) improves web agent efficiency | OpenReview paper | MEDIUM | [OpenReview, 2025] | VERIFIED-ABSTRACT-ONLY |
| 12 | Self-improvement via multi-level reflection (micro/meso/macro) outperforms single-level | SAMULE, EMNLP 2025 | HIGH | [ACL Anthology] | VERIFIED |
| 13 | Self-Challenging: agents generating own training tasks outperforms static curricula | OpenReview 2025 | MEDIUM | [OpenReview] | VERIFIED-ABSTRACT-ONLY |
| 14 | LLMs lack inherent self-refinement ability; iterative self-correction often degrades quality | OpenReview investigation | HIGH | [OpenReview, 2025] | VERIFIED-ABSTRACT-ONLY |
| 15 | ACE (Microsoft): evolving contexts as "playbooks" accumulating strategies via reflection | Microsoft Research publication | MEDIUM | [Microsoft Research, 2026] | VERIFIED-ABSTRACT-ONLY |

## Key Findings

### 1. Agent Failure Taxonomy Is Now Empirically Grounded (NEW)

**MAST** (Berkeley, NeurIPS 2025, 232 citations) is the first rigorous taxonomy of multi-agent system failures. 1600+ traces, 7 frameworks, κ=0.88 inter-annotator agreement.

**14 failure modes in 3 categories:**

| Category | % | Modes |
|----------|---|-------|
| **System Design** | 44.2% | Disobey task spec (15.7%), step repetition (13.2%), disobey role spec (8.2%), loss of conversation history (6.2%), unaware of termination (2.2%) |
| **Inter-Agent Misalignment** | 32.3% | Reasoning-action mismatch (12.4%), information withholding (9.1%), ignored other agent's input (6.8%), fail to ask clarification (1.9%), conversation reset (2.8%), task derailment (7.4%) |
| **Task Verification** | 23.5% | Premature termination (11.8%), no/incomplete verification, incorrect verification |

**Key insight:** The dominant failure category is system design — not LLM capability. Most failures are architectural, not intelligence failures. A simple workflow adjustment (ensuring the CEO agent has final say) improved success rates by +9.4%. This strongly validates our constitutional principle that "architecture over instructions" applies at the agent level too.

**Relevance to us:** Our `agent-failure-modes.md` has 22 modes from real sessions but no systematic taxonomy. MAST provides the validated framework. Cross-reference: our session-analyst already detects several of these (step repetition = "build-then-undo", premature termination = "scope creep"), but we're missing: information withholding, conversation reset, reasoning-action mismatch as explicit detection targets.

### 2. Agent Self-Improvement: Reflection Alone Doesn't Work, But Structured Reflection Does (NEW)

**Critical finding:** LLMs lack inherent self-refinement ability. Iterative self-correction often *degrades* quality (OpenReview 2025). This matches our existing evidence (ReliabilityBench: simpler beats complex under stress).

**What does work:**
- **ACT (Agentic Critical Training):** Train agents to judge which action is better via RL, not to imitate reflections. +5.07 over imitation, +4.62 over RL. Transfers to general reasoning without reasoning-specific data. The mechanism: agents develop *genuine* critical reasoning when rewarded for correct action selection, vs imitating pre-written reflections. [SOURCE: arXiv:2603.08706]
- **SAMULE (multi-level reflection):** Micro-level (per-error), meso-level (error taxonomies across trials), macro-level (strategy evolution). Outperforms single-level reflection. [SOURCE: EMNLP 2025]
- **Self-Challenging:** Agents generate their own training tasks, creating a curriculum from failure cases. [SOURCE: OpenReview 2025]
- **ACE (Microsoft):** Contexts as evolving "playbooks" that accumulate strategies through generation→reflection→selection. [SOURCE: Microsoft Research]
- **ExIt (Bootstrapping Task Spaces):** RL-based self-improvement during inference via recurrent structure. [SOURCE: arXiv:2509.04575]

**Synthesis:** The pattern across all successful approaches is *structured* self-improvement (explicit comparison, multi-level analysis, curriculum generation) vs *naive* self-improvement (just asking "did I do well?"). Our autoresearch engine already follows this pattern (deterministic eval keeps/discards, git reset on regression). ACT's insight — reward correct *judgment* not correct *action* — is architecturally interesting for session-analyst improvements.

### 3. Agent Planning: MCTS and Tree Search Are Gaining Traction (NEW)

Multiple papers applying MCTS/tree search to agent planning:

| Approach | Mechanism | Key Result |
|----------|-----------|------------|
| **Confidence-guided MCTS** | Log-prob uncertainty → adaptive branching | Efficient long-horizon web agent tasks |
| **Tree-GRPO** | RL + tree-structured interactions | Multi-turn agent improvement |
| **EvoPlan** | Evolutionary planning, no execution eval | LLM critics (Logical + Factual) replace costly execution |
| **OLP (Optimizable LLM Planning)** | Branch-and-bound with budget constraints | Explicit planning under compute budget |
| **DR-MCTS** | Doubly robust estimation + MCTS | Better sample efficiency across Go, math, reasoning |
| **WorldCoder** | World model as Python program | Efficient, transferable, interpretable |

**Key tension:** LLMs as world models excel at short-term prediction but degrade significantly over long horizons (OpenReview 2025). World model accuracy drops with planning depth — this is the fundamental limit that MCTS/tree search is trying to work around by keeping plans shallow and re-planning frequently.

**Relevance to us:** Our orchestrator uses flat task queues, not tree-structured planning. For complex multi-step tasks, a lightweight tree-search approach (generate N candidate next-steps, evaluate, prune) could improve task decomposition quality. The EvoPlan approach (LLM critics instead of execution-based eval) is closest to what we could adopt without infrastructure changes.

### 4. Production Deployment Patterns: The 85-90% Ceiling (NEW)

From practitioner reports (Viqus 12-month deployment, Iterathon, enterprise deployments):

**Quantified failure modes in production:**
- 85-90% task completion ceiling is common
- Tool call failures: 68% incorrect parameters, 21% wrong tool selection, 11% hallucinated data
- Rate limits are per-account, not per-API-key (catches teams off guard)
- Subtle failures (incorrect but plausible outputs) harder to detect than crashes

**Architecture pattern that works:**
- Small specialized agents (3-5 tools each) + lightweight orchestrator
- NOT: monolithic agents with 20+ tools
- NOT: complex multi-agent debates for routine tasks

**Cost management:**
- Per-task cost budgets, not per-session
- Token routing/cascading (cheap model for classification, expensive for synthesis)
- Proactive rate limiting with exponential backoff per-account

**Relevance to us:** Our orchestrator already follows the specialized-agent + orchestrator pattern. The 3-5 tools heuristic validates our hook-based approach (each hook is a specialized micro-agent). The 85-90% ceiling is worth tracking as a baseline — are our orchestrated tasks hitting this?

### 5. Mandatory Thinking Can Backfire (NEW)

"Thinking Makes LLM Agents Introverted" (Feb 2026): When reasoning models (extended thinking) are used in user-engaged agent scenarios, the mandatory thinking step can cause agents to over-deliberate, miss social cues, and become less responsive to user intent. The "introversion" effect — the agent retreats into internal reasoning when it should be acting or asking.

**Relevance to us:** This is directly relevant to our extended thinking usage. We should not default to extended thinking for interactive tasks. Reserve it for genuine reasoning tasks (causal DAGs, complex synthesis) and use standard mode for interactive/tool-heavy workflows.

### 6. Automated Failure Attribution Is Becoming Tractable (NEW)

Three complementary approaches:

- **Shapley-value attribution** (arXiv:2505.00212, 50 citations): Game-theoretic credit assignment — which agent and which step caused failure? Formalized as cooperative game theory problem.
- **GraphTracer** (arXiv:2510.10581): Graph-based failure tracing for multi-turn deep search. Builds causal graph of agent actions, traces failures through edges. Outperforms temporal (linear) attribution.
- **AgenTracer** (arXiv:2509.03312, 16 citations): Pinpoints failure sources in complex multi-model agentic systems.

**Relevance to us:** Our session-analyst does post-hoc pattern detection but not causal failure attribution. GraphTracer's approach (build dependency graph of actions, trace failures through it) could enhance session-analyst's ability to identify root causes vs symptoms.

### 7. Long-Horizon Agent Persistence Patterns (NEW)

Converging pattern from multiple implementations:

| Pattern | Mechanism | Example |
|---------|-----------|---------|
| **Filesystem-as-state** | Save progress, decisions, artifacts to files | Trinity Pattern (.trinity directory) |
| **Checkpoint/resume** | Progress files + session architecture | Agent Factory, our `.claude/checkpoint.md` |
| **Database-backed memory** | Deterministic, lossless context management | Volt (Martian Engineering) |
| **Overnight loops** | Filesystem checkpointing + recovery + cost tracking | "Ralph Loop" |

**Synthesis:** Everyone is converging on the same solution — externalize state to filesystem/database, not context window. Our `.claude/checkpoint.md` approach is architecturally aligned with industry practice. The more sophisticated approaches (Volt's LCM, Trinity Pattern) add structure (typed state, associative links) that we could adopt.

## What's Uncertain

1. **ACT's generality beyond small models.** ACT was tested on fine-tunable models. Whether the "train to judge actions" paradigm works for frontier models via prompting alone is unknown.
2. **MAST taxonomy completeness.** Authors explicitly note it may not cover every failure pattern. Our 22 failure modes from real sessions include some not in MAST (e.g., sycophancy, over-engineering).
3. **Production ceiling vs model capability.** The 85-90% ceiling is from 2025-early 2026 deployments. Whether frontier models (Opus 4.6, GPT-5.4) break this ceiling is not yet measured.
4. **Self-refinement negativity.** The "self-refinement degrades quality" finding may be model-generation-dependent. Needs frontier model validation.
5. **MCTS overhead.** Tree search adds latency and cost. Whether the quality improvement justifies the overhead for production agents is empirically unresolved.

## Disconfirmation

**Searched for:** "agent scaffolding doesn't work", "agent limitations criticism", "why agents fail". Found:

- **"The Planning Rubicon" (Feb 2026):** Most "agents" are expensive chatbots — pattern-matching loops generating plausible but incorrect plans without genuine goal-directed behavior. Valid criticism of the bottom of the market, less relevant to well-architected systems.
- **Laminar "To Scaffold or Not to Scaffold" (Jan 2026):** Some problems (negotiation, real-time debugging, dynamic environments) inherently require scaffolding regardless of model capability — models won't dissolve these. Correct and useful framing.
- **Fundamental limits argument:** Token-level probabilistic prediction → inherent inability to reliably handle computation, error recognition, safety-critical decisions. Valid as a ceiling argument, but doesn't invalidate scaffolding as the mitigation.

**Assessment:** The criticism is valid for naive agent deployments but doesn't contradict the empirical evidence that *structured* scaffolding (MAST-guided fixes, ACT training, MCTS planning) measurably improves outcomes. The key word is "structured" — reflexive loops and chain-of-thought alone don't help; architectural interventions do.

## What We're Missing (Gaps for Future Research)

1. **Agent evaluation for our specific use case.** MAST tests coding/math/general. No benchmark exists for "agent that improves its own infrastructure" — our meta use case. We'd need to build this.
2. **Cost-performance Pareto frontiers.** No paper systematically maps where cheaper interventions (workflow fixes, better prompts) vs expensive ones (MCTS, multi-agent) sit on the Pareto frontier.
3. **Temporal degradation in self-improving agents.** How does agent performance change over months of self-modification? Our `temporal-epistemic-degradation.md` covers session-level, but system-level drift over months is uncharted.
4. **Human-agent handoff protocols.** Surprisingly thin research. Enterprise blog posts mention it, but no rigorous framework for when to escalate, how to transfer context, how to measure handoff quality.

## Sources Saved

Papers saved to corpus:
- "Why Do Multi-Agent LLM Systems Fail?" (MAST) — `c83b6a023a5c5ec71b44920a41b41fc007266c44`
- "Where LLM Agents Fail and How They can Learn From Failures" — `9e386aa8a670bda468b5ee81137dedc4e4c151e3`
- "Aegis: Taxonomy and Optimizations for Agent-Environment Failures" — `ba66d6bd0cace53cc81028b385dc755b22508527`
- "Automated Failure Attribution of LLM Multi-Agent Systems" — `a0d37ec77dc2acddb223d9a7ac4f23ca10e2908f`
- "Thinking Makes LLM Agents Introverted" — `8b82fa412642816f7db5deaed364a836ebdd201d`
- "GraphTracer: Graph-Guided Failure Tracing" — `887adc77f1e4373e0ebabb4975241a1fb11d45d4`

## Search Log

| Query | Tool | Hits | Signal |
|-------|------|------|--------|
| Agent planning MCTS tree search 2025 | Exa advanced (neural, research) | 10 | HIGH — EvoPlan, conf-MCTS, Tree-GRPO, OLP, DR-MCTS |
| Production agent deployment lessons 2025 | Exa advanced (neural) | 10 | MEDIUM — blog posts, practitioner reports |
| Agent evaluation benchmark beyond SWE-bench | Exa advanced (neural, research) | 10 | HIGH — MAST, AgentErrorTaxonomy, VitaBench, AGENTIF, Hell or High Water |
| LLM agent planning MCTS RL 2025 | S2 | 10 | MEDIUM — RepoQA, TreeMind, CheMatAgent |
| Agent failure taxonomy error classification | S2 | 10 | HIGH — MAST (232 cites), AgenTracer (16), attribution (50), Aegis (5) |
| LLM agent skill acquisition tool learning | arXiv | 10 | LOW — mostly irrelevant (prompt tuning, federated learning) |
| Long-horizon multi-session persistent state | Exa advanced (neural) | 8 | MEDIUM — Volt, Trinity Pattern, Ralph Loop, ACE |
| Agent self-improvement loop automated correction | Exa advanced (neural, research) | 8 | HIGH — SAMULE, Self-Challenging, ExIt, ACE, AgentDebug |
| Agent limitations criticism scaffolding doesn't work | Exa advanced (neural) | 6 | MEDIUM — Planning Rubicon, Laminar, fundamental limits |
