---
title: Multi-Agent Coordination — Now With Controlled Experiments
date: 2026-03-21
---

# Multi-Agent Coordination — Now With Controlled Experiments

*Split from `frontier-agentic-models.md` on 2026-03-01. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*Date: 2026-02-27. Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*

---

### What's PROVEN

**NEW — Google "Towards a Science of Scaling Agent Systems" (arXiv:2512.08296, Dec 2025):** The first controlled experiment we were waiting for. 180 agent configurations, 5 architectures, 3 LLM families, 4 benchmarks. [SOURCE: arXiv:2512.08296, research.google/blog]

Key findings:
1. **Multi-agent dramatically improves parallelizable tasks (+81%)** but **degrades sequential tasks (-70%).** Coordination benefits are task-contingent.
2. **Error amplification:** Independent agents amplify errors up to **17x**. Centralized coordination limits to **4.4x**. This is why orchestrator-worker beats peer-to-peer.
3. **45% threshold:** Once a single agent hits ~45% success rate, adding agents brings diminishing or negative returns.
4. **Predictive model:** Identifies optimal architecture for 87% of unseen tasks using coordination metrics (efficiency, overhead, error amplification, redundancy). Cross-validated R²=0.513. [SOURCE: arXiv:2512.08296]

**NEW — "Single-agent or Multi-agent? Why Not Both?" (arXiv:2505.18286, May 2025):** MAS benefits over SAS **diminish as LLM capabilities improve**. Frontier LLMs (o3, Gemini 2.5 Pro) have advanced enough in long-context reasoning, memory retention, and tool usage that many MAS motivations are now mitigated. Proposes LLM-based routing: complexity assessment → route to single or multi based on threshold. [SOURCE: arXiv:2505.18286]

**NEW — "Debate or Vote" (arXiv:2508.17536):** Debate is a martingale — no expected correctness improvement. Majority voting alone captures most multi-agent gains. See [agent-reliability-benchmarks.md](agent-reliability-benchmarks.md) for details.

**NEW — MAST Taxonomy "Why Do Multi-Agent LLM Systems Fail?" (arXiv:2503.13657, March 2025, v3 Oct 2025):** 14 failure modes in 3 categories across 1,600+ annotated traces, 7 frameworks. Categories: System Design Issues, Inter-Agent Misalignment, Task Verification. Key finding: agents converge on shared evidence without eliciting unobserved knowledge from each other. Step repetition and conversation history loss are prevalent. Provides granular taxonomy complementing our high-level failure modes. [SOURCE: arXiv:2503.13657] [PUBLISHED]

### What was SPECULATED → NOW RESOLVED

- ~~Whether multi-agent fundamentally outperforms single-agent for complex tasks.~~ → **IT DEPENDS ON TASK STRUCTURE.** Parallelizable → yes (+81%). Sequential → no (-70%). The question was wrong — it's not single vs multi, it's matching architecture to task decomposition structure.
- ~~Whether coordination overhead is worth it.~~ → **Only for parallelizable tasks, and only until the single agent passes 45% success rate.** After that, diminishing or negative returns.

### Engineering implications for us

Our current architecture is validated: **orchestrator (Opus) + worker subagents (Sonnet) with centralized coordination.** The Google study shows centralized coordination limits error amplification to 4.4x vs 17x for independent agents.

**NEW decision:** Route by task structure. Research tasks (multiple independent search axes) → multi-agent parallelization. Sequential analysis tasks (entity investigation, hypothesis testing) → single agent. We're already doing this implicitly with the researcher skill's parallel dispatch — make it explicit.

**NEW finding (Anthropic engineering blog, April 2026):** Token usage explains 80% of quality variance on BrowseComp. Model upgrade (Sonnet 4→4.6) produced larger gains than doubling token budget on older models. Implication: our turn-budget heuristic (70% rule, 15-tool-call ceiling) is a proxy for token allocation. Worth tracking token usage per research subagent to calibrate — but the turn-budget proxy works well enough operationally given we can't read token usage from subagent internals. Also: their explicit "start broad, narrow later" search instruction counters agents' default toward overly-specific queries — adopted into researcher skill. `[SOURCE: anthropic.com/engineering/multi-agent-research-system]`

**NEW risk:** The 45% threshold means for our best tasks (entity refresh, signal scanning), adding agents may already be past diminishing returns. Only parallelize when the single-agent success rate is below 45%.

### NEW — Orchestration-Level Verification (March 2026)

**VMAO (Zhang et al., AWS/HSBC, arXiv:2603.11445, ICLR 2026 Workshop):** Plan-Execute-Verify-Replan framework. DAG decomposition of complex queries into sub-questions, parallel execution, LLM-based verification at the orchestration level (not agent level), and adaptive replanning. On N=25 market research queries: completeness +35% (3.1→4.2), source quality +58% (2.6→4.1) vs single-agent. `[SOURCE: arXiv:2603.11445, read in full]`

Key findings:
1. **Verification at orchestration level is the coordination signal.** Not per-agent self-evaluation — a separate verifier evaluates whether collective results satisfy the original query.
2. **Most replanning = retries, not new questions.** Execution variance (tool failures, insufficient search results) matters more than decomposition quality.
3. **8.5x token cost** (850K vs 100K) — the price of the verification loop. Justified for complex queries, not for simple ones.
4. **Configurable stop conditions:** completeness threshold (80%), high confidence (75% conf + 50% complete), diminishing returns (<5% improvement), token budget, max iterations. Balance quality vs cost.
5. **Single model family (Claude), N=25** — modest evaluation set. Evidence is directional, not definitive.

**DOVA (Shen et al., Berkeley/AWS, arXiv:2603.13327, March 2026):** Deliberation-first orchestration. Meta-reasoning layer decides *whether* to invoke tools before doing so. Three-phase hybrid reasoning: ensemble → blackboard → iterative refinement. Six-level adaptive token budget saves 40-60% on simple tasks while preserving deep reasoning capacity. `[SOURCE: arXiv:2603.13327, read in full]`

Key findings:
1. **Collaboration is highest-impact component** — removing it drops confidence by 0.14 and coverage by 0.25 (largest single ablation effect).
2. **Self-evaluation is second** — without it, refinement rate jumps 18%→35% (low-quality responses reach user).
3. **Deliberation reduces cost** — removing it increases latency 19% and decreases efficiency 27% through unnecessary tool invocations.
4. **Evaluation weakness:** "architectural analysis rather than large-scale benchmarks" (authors' words). Self-assessed confidence, no real benchmark. Ideas are directionally useful, evidence is weak.

**Combined implication for our orchestrator:** Add lightweight orchestration-level verification (VMAO), consider deliberation-before-tool-use (DOVA), but don't over-invest given both papers have small-N evaluations and our pipelines are 3-7 steps (VMAO shows most value at 8-12+ steps).

<!-- knowledge-index
generated: 2026-04-05T18:40:16Z
hash: 2e9f0d19285b

title: Multi-Agent Coordination — Now With Controlled Experiments

end-knowledge-index -->
