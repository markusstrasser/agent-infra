---
title: "Agent Knowledge Consumption & Navigation — Frontier Sweep"
date: 2026-04-04
tags: [agents, knowledge, context-engineering, memory, tools]
status: complete
---

## Agent Knowledge Consumption & Navigation — Frontier Sweep (March 21 – April 4, 2026)

**Tier:** Quick | **Date:** 2026-04-04
**Scope:** NEW papers/preprints on how AI agents consume, navigate, and retain knowledge
**Exclusions:** Cao et al. 2603.20432, Gloaguen et al. 2602.11988, ByteRover 2604.01599, AGENTIF 2505.16944, "One Tool Is Enough" 2512.20957, Context Inlining 2601.00376
**Method:** 8 Exa advanced searches (category: research paper, startPublishedDate: 2026-03-21)

---

### Full Findings Table

| # | Title | ID | Date | Finding | Relevance |
|---|-------|-----|------|---------|-----------|
| 1 | **Context Engineering: Architectures and Strategies for Next-Gen AI Systems** | arXiv:2603.09619v2 | 2026-03-30 | Introduces CE as a standalone discipline beyond prompting. Proposes architectures for managing context across agent lifecycles — context selection, compression, routing, and lifecycle management as first-class concerns. v2 updated 3/30. | HIGH |
| 2 | **MemMA: Coordinating the Memory Cycle through Multi-Agent Reasoning and In-Situ Self-Evolution** | Microsoft Research | 2026-03-26 | Multi-agent system where specialized agents coordinate the full memory cycle (encode, store, retrieve, update). In-situ self-evolution — memory agents improve their own memory management over time. | HIGH |
| 3 | **Experiential Reflective Learning (ERL) for Self-Improving LLM Agents** | arXiv:2603.24639 | 2026-03-27 | Agents reflect on past task trajectories to generate transferable heuristics, then retrieve them for new tasks. Self-improvement through experience persistence — directly comparable to our improvement-log pattern. | HIGH |
| 4 | **Knowledge Access Beats Model Size: Memory Augmented Routing for Persistent AI Agents** | arXiv:2603.23013 | 2026-03-24 | Core thesis: persistent knowledge access through memory-augmented routing matters more than raw model capability. Smaller models with good knowledge access outperform larger models without it. | HIGH |
| 5 | **OpenTools: Open, Reliable, and Collective Framework for Tool-Using AI Agents** | arXiv:2604.00137 | 2026-04-02 | Addresses both invocation accuracy AND intrinsic tool correctness. Key insight: the field optimizes tool selection but nobody checks if tools themselves produce correct outputs. Standardized schemas + automated testing for tool reliability. | HIGH |
| 6 | **SkillRouter: Retrieve-and-Rerank Skill Selection for LLM Agents at Scale** | arXiv:2603.22455 | 2026-03-23 | Retrieve-and-rerank for routing agents to correct skills when library grows large. Directly relevant to our skill routing problem as skill count increases. | HIGH |
| 7 | **SlopCodeBench: Benchmarking How Coding Agents Degrade Over Long-Horizon Iterative Tasks** | arXiv:2603.24755 | 2026-03-25 | 20 problems, 93 checkpoints. No agent solves any problem end-to-end (11 models). Quality degrades: erosion rises in 80% of trajectories, verbosity in 89.8%. Agent code is 2.2x more verbose than human. Prompt intervention improves initial quality but does NOT halt degradation. | HIGH |
| 8 | **Trace2Skill: Distill Trajectory-Local Lessons into Transferable Agent Skills** | arXiv:2603.25158 | 2026-03-26 | Distills lessons from agent execution traces into reusable, transferable skills. Complementary to ERL (#3) — ERL reflects on whole trajectories, Trace2Skill extracts local lessons from trace segments. | HIGH |
| 9 | **On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents** | arXiv:2601.20404v2 | 2026-03-30 | v2 update (originally Jan 2026). Studies efficiency impact of AGENTS.md — reduces runtime and token usage significantly without hurting task completion. Contrast with Gloaguen (excluded) who found context files reduce success rates. These two papers conflict: one says AGENTS.md helps efficiency, the other says it hurts success. | HIGH |
| 10 | **The Specification Gap: Coordination Failure Under Partial Knowledge in Code Agents** | arXiv:2603.24284 | 2026-03-25 | Identifies coordination failures when agents have partial knowledge of the codebase. Gap between what the spec says and what the agent understands drives failures. | MEDIUM |
| 11 | **Epistemic Compression: The Case for Deliberate Ignorance in High-Stakes AI** | arXiv:2603.25033 | 2026-03-26 | Argues for deliberate knowledge pruning in agents — not all information helps. Sometimes agents perform better with less knowledge, deliberately filtered. Resonates with the AGENTS.md distraction finding. | HIGH |
| 12 | **TED: Training-Free Experience Distillation for Multimodal Reasoning** | arXiv:2603.26778 | 2026-03-25 | Training-free, context-based experience distillation. Extracts reusable reasoning patterns without fine-tuning. Applicable to resource-constrained settings. | MEDIUM |
| 13 | **Formal Semantics for Agentic Tool Protocols: A Process Calculus Approach** | arXiv:2603.24747 | 2026-03-27 | First formal foundation for agent-tool interaction using process calculus. Proves correctness properties — could enable formal verification of tool protocol implementations. | MEDIUM |
| 14 | **ToolComp: A Multi-Tool Reasoning & Process Supervision Benchmark** | Scale Labs | 2026-03-29 | Evaluates intermediate tool use steps, not just final answers. Process supervision for multi-tool reasoning chains. | MEDIUM |
| 15 | **Act While Thinking: Accelerating LLM Agents via Pattern-Aware Speculative Tool Execution** | Microsoft Research | 2026-03-26 | Speculative execution — predicts next tool calls and executes them before the LLM finishes reasoning. Pattern-aware parallelism for latency reduction. | MEDIUM |
| 16 | **Agentic Rubrics as Contextual Verifiers for SWE Agents** | Scale Labs | 2026-04-02 | Rubrics as structured knowledge for agent self-verification. Contextual verification that goes beyond test-pass/fail. | MEDIUM |
| 17 | **Recursive Knowledge Crystallization (RKC)** | Medium/Google Cloud | 2026-04-02 | "Crystallizes" learned knowledge to overcome catastrophic forgetting, zero-shot transfer. Framework, not peer-reviewed paper. | MEDIUM |
| 18 | **Context Window Utilization / Memory Degradation Curves** | Stabilarity Hub | 2026-03-22 | Effective context utilization = 50-65% of advertised window. Accuracy degrades as context grows. Analysis articles, not peer-reviewed papers. | MEDIUM |
| 19 | **STEM Agent: Self-Adapting, Tool-Enabled, Extensible Architecture** | arXiv:2603.22359 | 2026-03-22 | Multi-protocol agent self-adaptation architecture. | LOW |
| 20 | **The Evolution of Tool Use in LLM Agents: From Single-Tool to Multi-Tool Orchestration** | arXiv:2603.22862 | 2026-03-24 | Survey paper tracing tool-use evolution. | LOW |

**Additional resource discovered:** [VoltAgent/awesome-ai-agent-papers](https://github.com/VoltAgent/awesome-ai-agent-papers) — curated 2026-only arXiv papers on agents, organized by topic (memory, RAG, tooling, safety). Good ongoing surveillance source.

---

### Synthesis: Five Themes

**1. The Instruction Paradox Deepens**

Two papers directly conflict on whether repository context files help agents:
- arXiv:2601.20404v2 (v2 March 30): AGENTS.md reduces runtime and token usage without hurting completion.
- Gloaguen arXiv:2602.11988 (excluded, already known): context files reduce success rates by 0.5-3% and increase cost by 20%+.

The likely resolution: efficiency gains (fewer tokens, faster) coexist with success rate drops (broader exploration, instruction-following overhead). Epistemic Compression (arXiv:2603.25033) adds a theoretical frame — deliberate ignorance can outperform full information. This supports our existing practice of minimal, focused CLAUDE.md rather than exhaustive documentation.

**Implication for meta:** Continue current approach — thin rules files focused on invariants and routing, not comprehensive documentation. The weight of evidence says more instructions --> more compliance but less success.

**2. Experience Distillation Is the Hot Pattern**

Three independent papers in 6 days (March 25-27) all address extracting reusable knowledge from agent execution traces:
- **ERL** (arXiv:2603.24639): whole-trajectory reflection --> transferable heuristics
- **Trace2Skill** (arXiv:2603.25158): local trace segments --> transferable skills
- **TED** (arXiv:2603.26778): training-free context-based distillation

Our improvement-log + session-analyst pipeline is structurally similar to ERL. Trace2Skill's local-segment approach maps to our "extract patterns from individual tool calls" aspiration. Neither of our current systems does automated distillation — we manually curate findings.

**Implication for meta:** The session-analyst already does trace analysis; the gap is automated skill/rule extraction from findings. Not urgent to build — the manual curation is working — but this is where the field is converging.

**3. Quality Degrades Inevitably Over Long Horizons**

SlopCodeBench (arXiv:2603.24755) is the most rigorous evidence yet that agents produce progressively worse code over iterative tasks. Key numbers:
- 0% end-to-end solve rate across 11 models
- 80% of trajectories show rising structural erosion
- 89.8% show rising verbosity
- Agent code 2.2x more verbose than human
- **Prompt intervention improves initial quality but does not halt degradation**

This confirms what we see in long sessions: compaction loss, context rot, growing slop. The finding that prompt intervention doesn't halt degradation is sobering — it suggests architectural solutions (fresh contexts, modular tasks) are needed, not better prompts.

**Implication for meta:** Validates our subagent isolation strategy and per-task context patterns. Fresh context per logical unit > long-lived context with accumulated state. SlopCodeBench could be used to evaluate our own mitigation strategies.

**4. Knowledge Access > Model Size**

arXiv:2603.23013 ("Knowledge Access Beats Model Size") and MemMA (Microsoft) both argue that how an agent accesses and manages knowledge matters more than the underlying model's raw capability. SkillRouter (arXiv:2603.22455) addresses the practical problem of routing to the right knowledge/skill as the library grows.

**Implication for meta:** Our investment in structured knowledge access (research-mcp, meta-knowledge MCP, rules files, research index) is directionally correct. The next bottleneck is routing — as skill/rule count grows, the agent needs better selection, not just more knowledge.

**5. Tool Correctness Is Underinvestigated**

OpenTools (arXiv:2604.00137) makes an underappreciated point: the field optimizes tool selection (does the agent pick the right tool?) but ignores tool correctness (does the tool produce correct output?). This echoes our AgentDrift finding — agents never question tool data reliability.

**Implication for meta:** Our tool output provenance awareness (CLAUDE.md note, cross-source checks) is ahead of the field. OpenTools' standardized testing approach could inform how we validate MCP tool outputs.

---

### Search Log

| Query | Tool | Results | New Papers Found |
|-------|------|---------|-----------------|
| "context engineering" agents 2026 | Exa advanced | 11 | 3 (#1, #5, #6) |
| agent memory persistence across sessions | Exa advanced | 11 | 3 (#2, #3, #4) |
| tool documentation format effectiveness agents | Exa advanced | 10 | 4 (#7, #8, #9, #13) |
| instruction scaling laws agents hurt | Exa advanced | 8 | 2 (#12, #18) |
| agentic retrieval knowledge grounding | Exa advanced | 8 | 1 (#4 dup, #17) |
| agent file navigation codebase structure | Exa advanced | 10 | 1 (#10) |
| CLAUDE.md AGENTS.md context file study | Exa advanced | 8 | 1 (#9 v2 update) |
| knowledge compression distillation agents | Exa advanced | 9 | 3 (#11, #8 dup, #12) |

**Total:** 8 searches, 20 distinct items catalogued, 11 rated HIGH relevance.

<!-- knowledge-index
generated: 2026-04-04T18:12:00Z
hash: 6a7cab6425fd

title: Agent Knowledge Consumption & Navigation — Frontier Sweep
status: complete
tags: agents, knowledge, context-engineering, memory, tools

end-knowledge-index -->
