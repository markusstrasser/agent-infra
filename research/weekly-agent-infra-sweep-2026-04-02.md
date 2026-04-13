---
title: Weekly agent-infrastructure sweep
date: 2026-04-02
tags: [agents, weekly-sweep, skills, mcp, verification, coding-agents, enterprise]
---

## Agent Infrastructure Sweep — Research Memo

**Question:** What new papers and official posts from March 26, 2026 through April 2, 2026 materially change our view of agent infrastructure?  
**Tier:** Standard  
**Date:** 2026-04-02  
**Ground truth:** Meta already leaned toward progressive disclosure, verification-before-output, native search over retrieval, and skepticism of bloated MCP/tool surfaces. [SOURCE: /Users/alien/Projects/meta/research/practitioner-agent-usage-2026-03.md] [SOURCE: /Users/alien/Projects/meta/research/coding-agents-long-context-2026-03.md] [SOURCE: /Users/alien/Projects/meta/research/claude-code-internals.md]

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Skill compression is now supported by direct empirical evidence, not just practitioner anecdote: one preprint reports 48% description compression and 39% body compression with a small quality gain. | Preprint on 55,315 skills + benchmark eval | MEDIUM-HIGH | [SOURCE: https://arxiv.org/pdf/2603.29919.pdf] | VERIFIED |
| 2 | Verification is becoming the central design pattern for deep-research agents at training and inference time, not an optional post-hoc add-on. | Verification-centric 8B deep-research pipeline | MEDIUM | [SOURCE: https://arxiv.org/pdf/2603.28376.pdf] | VERIFIED |
| 3 | Long-horizon agent performance is still bottlenecked by memory persistence and reasoning-to-action consistency; scratchpad use was the strongest predictor in YC-Bench. | Benchmark over 12 models in long-horizon startup simulation | MEDIUM | [SOURCE: https://arxiv.org/pdf/2604.01212.pdf] | VERIFIED |
| 4 | Real-world coding-agent output appears less stable than human code over time: a 110k-PR study found more churn and lower retention for agent-authored code. | Longitudinal GitHub PR mining study | MEDIUM-HIGH | [SOURCE: https://arxiv.org/pdf/2604.00917.pdf] | VERIFIED |
| 5 | Python comprehension burden from agents may be driven more by volume/review load than by exotic syntax: >90% of constructs in one wild-study were A1/A2 level. | Wild PR study over 5,027 Python files | MEDIUM | [SOURCE: https://arxiv.org/pdf/2604.00299.pdf] | VERIFIED |
| 6 | MCP-connected agents remain highly vulnerable on privilege misuse in realistic settings; one sandbox study reports attack success rates around 80-95% depending on mode/model. | Real-world MCP server security benchmark | MEDIUM | [SOURCE: https://arxiv.org/pdf/2603.28166.pdf] | VERIFIED |
| 7 | MCP benchmarking is maturing from protocol discussion into domain benchmarks, but current results are still narrow and task-family-specific. | Financial MCP benchmark with 65 tools / 613 samples | MEDIUM | [SOURCE: https://arxiv.org/pdf/2603.24943.pdf] | VERIFIED |
| 8 | Terminal/API-first agents have now been directly argued and benchmarked against web and MCP agents in enterprise settings, with strong cost-performance claims for the simple stack. | Enterprise benchmark across ServiceNow, GitLab, ERPNext | MEDIUM | [SOURCE: https://arxiv.org/pdf/2604.00073.pdf] | VERIFIED |
| 9 | Vendors are converging on the same architecture we already favor: docs-MCP plus skills/progressive disclosure as the standard way to reduce stale knowledge and token waste. | Official Google posts and eval claims | HIGH | [SOURCE: https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-docsmcp-agent-skills/] [SOURCE: https://developers.googleblog.com/developers-guide-to-building-adk-agents-with-skills/] | VERIFIED |
| 10 | Production coding-model training is shifting toward real-time RL on user interactions, with explicit monitoring for reward hacking and rapid checkpoint rollout. | Official Cursor research post | MEDIUM-HIGH | [SOURCE: https://www.cursor.com/blog/real-time-rl-for-composer] | VERIFIED |

### Key Findings

1. **New evidence in favor of skills as compression architecture.** We already had practitioner evidence that skills compress MCP/tool usage; this week adds a direct preprint showing the same effect at corpus scale, plus a first-party Google writeup pushing progressive disclosure as the default architecture. This strengthens the case for investing in skill linting, skill slimming, and negative-scope descriptions rather than expanding monolithic instructions. [SOURCE: https://arxiv.org/pdf/2603.29919.pdf] [SOURCE: https://developers.googleblog.com/developers-guide-to-building-adk-agents-with-skills/] [INFERENCE]

2. **Verification is no longer just epistemic hygiene; it is becoming core architecture.** Marco DeepResearch bakes verification into data synthesis, trajectories, and test-time scaling. This is aligned with our existing “verify before finalizing” position and suggests the next leverage is explicit verifier roles, not just stronger prompts. [SOURCE: https://arxiv.org/pdf/2603.28376.pdf] [SOURCE: /Users/alien/Projects/meta/research/ai-scientist-patterns.md] [INFERENCE]

3. **Autonomy is still bounded by coherence, not raw intelligence.** YC-Bench’s most useful result is not model ranking; it is the failure decomposition: perceive -> record -> retrieve -> act remains brittle. That fits our current skepticism of “fully autonomous” framing and supports short-burst autonomy with persistent memory and checks between loops. [SOURCE: https://arxiv.org/pdf/2604.01212.pdf] [SOURCE: /Users/alien/Projects/meta/research/practitioner-agent-usage-2026-03.md] [INFERENCE]

4. **There is now better empirical grounding for “comprehension debt.”** The wild PR paper says agent code churns more; the Python-proficiency paper says the code is usually not syntactically advanced. Together this suggests the maintenance problem is not mostly obscure language tricks. It is change volume, broad edits, and weaker durability. That argues for measuring post-merge churn and survival, not just static code quality or benchmark scores. [SOURCE: https://arxiv.org/pdf/2604.00917.pdf] [SOURCE: https://arxiv.org/pdf/2604.00299.pdf] [INFERENCE]

5. **MCP should remain narrow and high-leverage.** GrantBox and FinMCP-Bench both make MCP more concrete, but neither justifies broad CRUD-mirror MCP design. The stronger lesson is the opposite: privilege surfaces are dangerous, multi-tool orchestration is brittle, and evaluation has to be domain-specific. This is consistent with our current “data gateways, not API mirrors” stance. [SOURCE: https://arxiv.org/pdf/2603.28166.pdf] [SOURCE: https://arxiv.org/pdf/2603.24943.pdf] [SOURCE: /Users/alien/Projects/meta/research/claude-code-internals.md] [INFERENCE]

6. **Terminal-first got stronger this week.** The ServiceNow paper is not definitive, but it materially strengthens the argument that when stable APIs exist, direct terminal/API interaction may beat both GUI stacks and heavy MCP wrappers on cost-performance. This is a meaningful update because it is a direct head-to-head, not a philosophical preference. [SOURCE: https://arxiv.org/pdf/2604.00073.pdf] [INFERENCE]

7. **Vendor convergence is visible.** Google is explicitly pairing docs-MCP with skills and reporting a 96.3% pass rate plus 63% fewer tokens per correct answer than vanilla prompting. Cursor is explicitly training on production interaction data. OpenAI pricing now makes prompt size, AGENTS footprint, and MCP count visible cost levers for users. Anthropic’s Australia report suggests mature usage skews collaborative rather than delegated and less coding-heavy than the global mix. [SOURCE: https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-docsmcp-agent-skills/] [SOURCE: https://www.cursor.com/blog/real-time-rl-for-composer] [SOURCE: https://developers.openai.com/codex/pricing/] [SOURCE: https://www.anthropic.com/research/how-australia-uses-claude] [INFERENCE]

### What Changed My Mind

- The strongest genuinely new paper signal is **SkillReducer**. We no longer have to rely mainly on practitioner anecdotes for “skills as compression architecture.” [SOURCE: https://arxiv.org/pdf/2603.29919.pdf]
- The strongest genuinely new systems signal is **terminal agents vs MCP/web agents in enterprise**. We had prior intuition; now there is at least one direct benchmark making the case. [SOURCE: https://arxiv.org/pdf/2604.00073.pdf]
- The most useful operational delta is that **agent-code quality should be tracked longitudinally**. Churn/survival looks more diagnostic than “can it solve the benchmark?” [SOURCE: https://arxiv.org/pdf/2604.00917.pdf]

### What Mostly Confirms Existing Meta Beliefs

- Progressive disclosure beats monolithic prompt stuffing. [SOURCE: https://developers.googleblog.com/developers-guide-to-building-adk-agents-with-skills/] [SOURCE: /Users/alien/Projects/meta/research/claude-code-internals.md]
- Verification should happen before final output. [SOURCE: https://arxiv.org/pdf/2603.28376.pdf] [SOURCE: /Users/alien/Projects/meta/research/ai-scientist-patterns.md]
- Native search / direct interaction remains preferable to extra retrieval layers when the environment already exposes strong primitives. [SOURCE: https://arxiv.org/pdf/2604.00073.pdf] [SOURCE: /Users/alien/Projects/meta/research/coding-agents-long-context-2026-03.md]

### What’s Uncertain

- Most academic findings here are still preprints and need replication. [PREPRINT]
- The terminal-agent enterprise results may partly reflect weak off-the-shelf MCP tooling rather than a permanent advantage of terminal-only designs. [INFERENCE]
- Google’s and Cursor’s numbers are first-party vendor claims and should be treated as directional unless independently reproduced. [SOURCE: https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-docsmcp-agent-skills/] [SOURCE: https://www.cursor.com/blog/real-time-rl-for-composer]

### Net

The week’s evidence pushes in one direction: **fewer abstractions, better verification, slimmer skills, narrower MCPs, and longitudinal quality metrics**. It does not support building fatter agent stacks.
