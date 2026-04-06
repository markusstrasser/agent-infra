---
title: "Agent Engineering Delta Refresh — April 2026"
date: 2026-04-05
tags: [agent-scaffolding, coding-agents, benchmarks, practitioner-usage, refresh]
status: complete
---

# Agent Engineering Delta Refresh — April 2026

**Tier:** Standard | **Date:** 2026-04-05
**Scope:** New findings since Mar 21-30 across four stale memos: agent scaffolding, coding agents/long-context, reliability benchmarks, practitioner usage. Excludes material already covered in the Apr 5 memos (CORAL, MS Agent Framework 1.0, Scale Agentic Rubrics, CAID).

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | No coding agent solved any of 20 SlopCodeBench problems end-to-end; best single-checkpoint solve rate was 17.2% (Opus 4.6) | 11 models, 20 iterative problems, full eval | HIGH | [arXiv:2603.24755] | VERIFIED |
| 2 | Agent code structural erosion rises in 80% of trajectories; verbosity rises in 89.8% | SlopCodeBench trajectory analysis | HIGH | [arXiv:2603.24755] | VERIFIED |
| 3 | Agent-generated code is 2.2x more verbose than maintained human repos; quality-aware prompts change intercept but not degradation slope | SlopCodeBench comparison | HIGH | [arXiv:2603.24755] | VERIFIED |
| 4 | Opus 4.6: highest solve rate (17.2% strict) but also highest structural erosion (0.774); GPT 5.4: 11.8% strict, lowest erosion (0.515) | SlopCodeBench Table | HIGH | [arXiv:2603.24755] | VERIFIED |
| 5 | 73.7% of IBM enterprise developers say AI assistants "transformed" their process; 88% perceive productivity gains | Survey, n=57 | MEDIUM | [arXiv:2601.20112, ICSE 2026] | VERIFIED |
| 6 | 65%+ of enterprise developers replaced Google Search/StackOverflow with AI assistants | IBM survey | MEDIUM | [arXiv:2601.20112] | VERIFIED |
| 7 | 80% of enterprise developers rate codebase customization as "somewhat" or "extremely" important | IBM survey | MEDIUM | [arXiv:2601.20112] | VERIFIED |
| 8 | Selective memory (Mem0) achieves 91% lower latency (p95: 1.44s vs 17.12s) with only 6pp accuracy trade-off vs full-context | LOCOMO benchmark | MEDIUM | [mem0.ai/blog/state-of-ai-agent-memory-2026] | VERIFIED |
| 9 | MemMA: multi-agent memory coordination via forward planner + backward retriever + in-situ self-evolution | Microsoft Research, arXiv:2603.18718 | MEDIUM | [arXiv:2603.18718] | VERIFIED-ABSTRACT |
| 10 | "When the Specification Emerges" benchmark: faithfulness loss when spec is progressively disclosed, not given upfront | arXiv:2603.17104, 1 citation | MEDIUM | [arXiv:2603.17104] | VERIFIED-ABSTRACT |
| 11 | 42% of Fortune 500 now run AI agents in production; average AI team size: 14 | Deloitte 2026 State of AI survey, n=2800 | MEDIUM | [agenticcareers.co, citing Deloitte] | CITED-SURVEY |
| 12 | Paper Reconstruction Eval: first framework for quantifying AI-written paper quality and hallucination risk | arXiv:2604.01128 | LOW | [arXiv:2604.01128] | VERIFIED-ABSTRACT |
| 13 | JetBrains Developer Ecosystem Survey (Apr 2026): robust growth in enterprise adoption of coding agents | Cited by multiple sources | MEDIUM | [chatgptaihub.com, citing JetBrains] | CITED-SURVEY |
| 14 | Mem0 ecosystem: 21 framework integrations, 19 vector store backends; voice agents highest-growth memory use case | State of Agent Memory report | MEDIUM | [mem0.ai] | VERIFIED |

---

## 1. Coding Agent Degradation Is Now Measurable (NEW)

### SlopCodeBench (arXiv:2603.24755, UW-Madison/WSU/MIT, Mar 2026)

The most important new benchmark since SWE-bench Pro. SlopCodeBench measures what happens when agents *extend their own code* across multiple iterations — the actual workflow of production software development.

**Setup:** 20 iterative coding problems. Each has multiple checkpoints that progressively add requirements. Agents must build on their own prior code, not start fresh. 11 models tested.

**Headline results:**
- Zero models completed any problem end-to-end across all checkpoints
- Best single-checkpoint strict solve rate: Opus 4.6 at 17.2%
- Structural erosion (complexity concentration) rose in 80% of trajectories
- Verbosity (redundant/duplicated code) rose in 89.8%
- Agent code is 2.2x more verbose than maintained human repositories
- Mean max cyclomatic complexity: 27.1 (start) to 68.2 (end)
- Mean count of high-complexity functions: 4.1 to 37.0

**Model comparison:**

| Model | Strict (%) | Core (%) | Erosion | Verbosity |
|-------|-----------|----------|---------|-----------|
| Opus 4.6 | 17.2 | 53.8 | 0.774 | — |
| GPT 5.4 | 11.8 | — | 0.515 | 0.286 |
| Sonnet 4.6 | 8.5 | 45.1 | — | — |
| GLM 4.7 | 4.3 | — | — | — |

**Critical finding for us:** Quality-aware prompts (instructions to write clean code) improve the initial quality ("intercept") but do NOT reduce the rate of degradation ("slope"). The decay is structural, not instruction-followable. This is direct evidence that instructions alone cannot prevent code rot — consistent with our constitutional principle "architecture over instructions."

**Implication:** For multi-session agent work, periodic human architectural review is not optional overhead — it's the only known mitigation for structural erosion. Automated refactoring passes between agent iterations might help but have not been tested.

[SOURCE: arXiv:2603.24755, full text verified]

### Specification Emergence Benchmark (arXiv:2603.17104, Mar 2026)

Complementary to SlopCodeBench: measures faithfulness loss when the specification is *progressively disclosed* through interaction (as in real research coding), rather than given upfront. Agents must track durable design commitments across long sessions. Published Mar 21, 1 citation.

**Relevance:** Our interactive sessions with `/loop` are exactly this pattern — spec emerges through conversation. This benchmark may quantify the degradation we observe qualitatively.

[SOURCE: arXiv:2603.17104, abstract only]

---

## 2. Agent Memory Architecture Convergence (NEW)

### State of AI Agent Memory 2026 (Mem0, Apr 2026)

Mem0 published a landscape report showing architectural convergence in the agent memory space.

**Key findings:**
- **Selective memory wins on latency:** Mem0 achieves 91% lower p95 latency (1.44s vs 17.12s) with only 6pp accuracy loss vs full-context on LOCOMO benchmark. Full-context is 72.9% accurate but 17.12s latency — production-hostile.
- **Memory scope taxonomy converged:** The field standardized on `user_id`, `agent_id`, `run_id`, `org_id` scoping. This maps directly to our L1/L2/L3 + session-scoped memory.
- **Async-first consensus:** Memory writes should not block response latency.
- **Voice agents drive memory:** Highest-growth use case because users cannot scroll back.
- **Ecosystem scale:** 21 framework integrations, 19 vector store backends.

**Open problems flagged:** Memory staleness detection, cross-device identity, privacy governance.

**Relevance to us:** Our file-based memory (MEMORY.md + daily logs + session checkpoints) achieves the "selective" architecture naturally — context is loaded on-demand from descriptive file names. We don't have the latency problem (no vector search roundtrip) but we do have the staleness problem (90-day decay model in MEMORY.md header). The report's "actor-aware multi-agent memory" pattern — tagging memories by source — is something we lack when orchestrator and interactive sessions produce overlapping memories.

[SOURCE: mem0.ai/blog/state-of-ai-agent-memory-2026]

### MemMA (Microsoft Research, arXiv:2603.18718, Mar 2026)

Treats memory construction, retrieval, and utilization as an integrated cycle rather than isolated subroutines. Three agents: forward planner (what to remember), backward retriever (what to recall), in-situ evolver (how to update). Addresses "strategic blindness" where agents store everything without judging utility.

**Relevance:** Our improvement-log and session-analyst serve a similar function to the "in-situ evolver" — reviewing past memories for continued relevance. But we have no "forward planner" equivalent that decides what to remember *at write time*. Our memory writes are currently reactive (user says "remember X" or agent notices something important) rather than strategic.

[SOURCE: arXiv:2603.18718, abstract verified]

---

## 3. Enterprise Practitioner Data (NEW)

### IBM Enterprise Study (arXiv:2601.20112, ICSE 2026, n=57)

First rigorous enterprise-internal study of AI coding assistant adoption at a large tech company (IBM Research). Published Jan 2026 but accepted ICSE 2026 (Apr publication).

**Key findings:**
- 73.7% report AI assistants "transformed" their development process
- 88% perceive productivity gains; 77% report at least 25% improvement
- 65%+ replaced Google Search and StackOverflow with AI assistants
- 80% rate codebase customization as "somewhat" or "extremely" important
- Division-specific motivations: Research → productivity; Global Sales → security
- Less experienced developers report higher adoption and larger gains
- Notable absence of studies on agentic workflows (Cursor, Windsurf, Claude Code)

**Top requirements:** Full-repository context awareness, Git/CI/CD integration, style/convention customization.

**Relevance:** The 80% customization demand validates our heavy investment in CLAUDE.md/rules/skills. The "prompting overhead" challenge (some found prompting harder than coding) explains why our skill system works — skills encapsulate the prompting patterns so the user doesn't pay the overhead.

[SOURCE: arXiv:2601.20112, full text verified]

### Enterprise Adoption Benchmarks (Multiple Sources, Mar-Apr 2026)

From Deloitte 2026 State of AI survey (n=2,800), cited by aggregators:
- 42% of Fortune 500 now run AI agents in production [CITED-SURVEY, agenticcareers.co citing Deloitte]
- Average enterprise AI team size grown to 14

JetBrains Developer Ecosystem Survey (Apr 2026) reportedly shows "robust growth" in enterprise adoption of coding agents, though specific numbers were behind paywall.

**Caution:** Both cited via aggregator blogs, not primary. The Deloitte 42% number is plausible given Stack Overflow 2025 showing 55% developer agent usage, but should be verified against the primary report before using as authoritative.

[CITED-SURVEY, secondary sources]

---

## 4. Scaffolding and Framework Landscape (NEW)

### Microsoft Agent Framework 1.0 (Apr 2, 2026)

Already covered in depth in `ms-agent-framework-1.0-2026-04.md`. Delta summary: unifies Semantic Kernel + AutoGen, 24 Python packages, ClaudeAgent SDK integration, A2A protocol, YAML declarative layer. 8,892 stars.

### Chanl.ai Framework Comparison (Mar 31, 2026)

An independent comparison of 9 agent frameworks' shipping track records. Not fetched (redirect chain), but the title "Which Ones Ship?" signals an increasingly practitioner-oriented evaluation lens — what actually works in production, not what has the best benchmark numbers.

### CORAL Multi-Agent Evolution (Apr 2, 2026)

Already covered in `coral-multi-agent-2026-04.md`. Key delta for scaffolding landscape: filesystem-based shared memory (Hub), git worktree isolation per agent, SOTA on 8/11 benchmark tasks with 3-10x improvement rates.

### Mem0 State of Agent Memory (Apr 1, 2026)

See Section 2 above. Confirms that memory has graduated from research to "first-class engineering discipline" with measurable production trade-offs.

---

## 5. Benchmark Landscape (NEW)

### New Benchmarks Since Mar 21

| Benchmark | What it Measures | Key Finding | Source |
|-----------|-----------------|-------------|--------|
| **SlopCodeBench** | Iterative code extension degradation | 0% end-to-end; 80% structural erosion | arXiv:2603.24755 |
| **Spec Emergence** | Faithfulness when spec is progressively disclosed | Faithfulness loss over long sessions | arXiv:2603.17104 |
| **Paper Reconstruction Eval** | Quality/hallucination in AI-written papers | First systematic framework | arXiv:2604.01128 |
| **ALE-Bench** | Long-horizon algorithm engineering | Score-based optimization problems | arXiv:2506.09050 |
| **UltraHorizon** | Ultra long-horizon scenarios (software, investment, discovery) | Most evals focus on short-horizon | arXiv:2509.21766 |

**Pattern:** The benchmark field is converging on *long-horizon iterative* tasks as the frontier. SWE-bench (single-issue) is accepted as saturated. The new benchmarks all share a thesis: agents that pass single-shot tests collapse on sustained multi-step work. This matches our operational experience exactly.

**Gap we identified previously:** No biomedical routing benchmark, no abstention scoring standard (from `epistemic-eval-research-2026-04.md`). Still no progress on either.

---

## 6. What's Unchanged Since the Original Memos

These findings from the Mar 21-30 memos were NOT contradicted or superseded:

- **Princeton reliability study** (arXiv:2602.16666): Still no follow-up including Opus 4.6/GPT-5.4/Gemini 3.1 Pro. Reliability lags capability (r=0.02) remains the best evidence.
- **MAST failure taxonomy** (arXiv:2503.13657): 14 failure modes, 44% system design. No new taxonomy proposed.
- **85-90% production ceiling** (practitioner reports): SlopCodeBench 0% end-to-end further validates this for iterative work.
- **The Great Consolidation** (more agents =/= better): CORAL's success with autonomous agents doesn't contradict this — CORAL agents operate on independent evaluation cycles, not shared conversation context.
- **Context engineering as primary skill** (Seroter 87-98% token savings): IBM study's 80% customization demand independently validates.
- **METR 50% time horizon** doubling: No new data points for frontier models.

---

## 7. Implications for Our Infrastructure

### Confirmed
1. **Architecture over instructions** — SlopCodeBench proves quality-aware prompts don't prevent structural degradation. Confirmed.
2. **CLAUDE.md/skills investment** — IBM 80% customization demand validates. The practitioner convergence on "context engineering is the skill" is independently confirmed.
3. **File-based selective memory** — Mem0 report shows selective memory is the production winner (91% faster, 6pp accuracy cost). Our approach is architecturally aligned.
4. **Long-horizon is the real benchmark** — SlopCodeBench, Spec Emergence, UltraHorizon all point the same direction. Our multi-session `/loop` work is the actual hard case.

### New Concerns
1. **Structural erosion accumulates silently** — Our sessions produce code that passes tests but may be accumulating complexity mass. No mitigation in place beyond human review.
2. **Memory source attribution** — Multi-agent writes to shared memory without source tagging creates "inference cascades" (Mem0 report term). Our orchestrator + interactive sessions can produce conflicting MEMORY.md entries. Actor-tagging is a potential fix.
3. **No agent refactoring loop** — SlopCodeBench suggests that periodic automated refactoring between agent iterations could mitigate erosion. We don't have this.

### Potential Actions (not implementing — research memo output)
- Add cyclomatic complexity monitoring to post-commit analysis (SlopCodeBench metrics are computable with radon/lizard)
- Tag memory entries with source agent/session (Mem0 "actor-aware" pattern)
- Evaluate "specification emergence" benchmark methodology for our interactive session quality

---

## Search Log

| Query | Tool | Results | Signal |
|-------|------|---------|--------|
| "new agent framework architecture release 2026" | Exa advanced, research paper category, post-Mar-21 | 10 results | MS Agent Framework, MemMA, Mem0 report, Chanl comparison |
| "coding agent benchmark SWE-bench results 2026" | Exa advanced, research paper, post-Mar-25 | 10 results | SlopCodeBench (dominant), Scale Agentic Rubrics (already covered) |
| "how developers use AI coding agents enterprise 2026" | Exa advanced, post-Mar-21 | 8 results | IBM ICSE study, enterprise adoption benchmarks, JetBrains survey |
| "SlopCodeBench coding agent degradation" | S2 search | 5 results | SlopCodeBench + Spec Emergence + UltraHorizon + ALE-Bench |
| "agent reliability evaluation benchmark 2026" | S2 search | 8 results | Paper Reconstruction Eval, domain-specific benchmarks |
| "MemMA multi-agent memory coordination" | S2 search | 5 results | MemMA, G-Memory, EvoGit |
| "IBM ICSE 2026 AI coding assistants" | Brave | 5 results | IBM study confirmed, related Panto statistics |
| SlopCodeBench full text | fetch_paper + ask_papers | Full paper | All claims verified from text |
| IBM ICSE study full text | fetch_paper + ask_papers | Full paper | All claims verified from text |
| Mem0 State of Agent Memory | WebFetch | Report content | Key findings extracted |

**Not searched (budget constraint):** Specific framework release changelogs (LangGraph, CrewAI, etc.), Reddit/HN practitioner threads, conference proceedings beyond ICSE.

<!-- knowledge-index
generated: 2026-04-06T06:29:43Z
hash: 76080d06bf27

title: Agent Engineering Delta Refresh — April 2026
status: complete
tags: agent-scaffolding, coding-agents, benchmarks, practitioner-usage, refresh
table_claims: 14

end-knowledge-index -->
