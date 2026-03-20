## Weekly arxiv Scan — Research Memo

**Date:** 2026-03-20 | **Window:** 2026-03-12 to 2026-03-20
**Tier:** Standard | **Method:** Exa semantic search × 4 axes (self-improvement/orchestration, tool use/code agents, epistemic/calibration, multi-agent/safety)

### Claims Table

| # | Paper | Date | Relevance | Subsystem |
|---|-------|------|-----------|-----------|
| 1 | LEAFE: Internalizing Agency from Reflective Experience | 03-17 | HIGH | self-improvement |
| 2 | AgentFactory: Self-Evolving Framework Through Executable Subagent Accumulation and Reuse | 03-18 | HIGH | subagents |
| 3 | MR-Search: Meta-RL with Self-Reflection for Agentic Search | 03-18 | MED | researcher |
| 4 | The Agentic Researcher: Practical Guide to AI-Assisted Research | 03-15 | MED | researcher |
| 5 | MemMA: Coordinating the Memory Cycle through Multi-Agent Reasoning | 03-20 | HIGH | memory |
| 6 | OpenDev: Building Effective AI Coding Agents for the Terminal (v3) | 03-12 | HIGH | harness |
| 7 | VeriGrey: Greybox Agent Validation | 03-18 | MED | safety |
| 8 | ToolRegistry: Protocol-Agnostic Tool Management for Function-Calling LLMs | 03-18 | MED | MCP/tools |
| 9 | VMAO: Verified Multi-Agent Orchestration (Plan-Execute-Verify-Replan) | 03-14 | HIGH | orchestrator |
| 10 | Automating Skill Acquisition from Open-Source Agentic Repositories | 03-17 | HIGH | skills |
| 11 | Automated Self-Testing as Quality Gate for LLM Applications | 03-12 | MED | QA |
| 12 | COCO: Cognitive OS with Continuous Oversight for Multi-Agent Reliability | 03-17 | HIGH | hooks/guardrails |
| 13 | Runtime Governance for AI Agents: Policies on Paths | 03-17 | HIGH | hooks/governance |
| 14 | Comparing Uncertainty Measurement and Mitigation Methods for LLMs | 03-18 | HIGH | epistemic |
| 15 | Can LLMs Detect Their Confabulations? | 03-17 | MED | epistemic |
| 16 | The Phenomenology of Hallucinations | 03-13 | MED | epistemic |
| 17 | Confidence-Aware Self-Consistency for Efficient CoT Reasoning | 03-16 | MED | calibration |
| 18 | Epistemic Regret Minimization for Causal Rung Collapse in LLMs | 03-14 | HIGH | causal reasoning |
| 19 | Inducing Epistemological Humility in LLMs via Targeted SFT | 03-18 | MED | epistemic |
| 20 | Stop Before You Fail: Operational Capability Boundaries in Reasoning Models | 03-14 | HIGH | stall detection |
| 21 | AgentDrift: Unsafe Recommendation Drift Under Tool Corruption | 03-17 | HIGH | safety/tools |
| 22 | Evolving Deception: When Agents Evolve, Deception Wins | 03-12 | MED | self-improvement safety |

### Tier 1 — Read These (HIGH relevance, novel mechanisms)

**1. LEAFE: Internalizing Agency from Reflective Experience** — [arxiv:2603.16843](https://arxiv.org/abs/2603.16843)
Agent self-improvement through reflective experience. During exploration, the agent summarizes environment feedback into actionable experience, backtracks to earlier decision points, and explores alternative branches. Then distills corrections via SFT. Up to +14% on Pass@128 over GRPO. **Our angle:** LEAFE's "backtrack and revise" is what session-analyst does post-hoc — but LEAFE does it in-session. The experience-distillation loop is architecturally similar to our finding → rule promotion pipeline but operates at training time. [SOURCE: Exa]

**2. AgentFactory: Self-Evolving Executable Subagent Accumulation** — [arxiv:2603.18000](https://arxiv.org/abs/2603.18000)
Framework where agents accumulate executable subagents (not textual plans) that are stored and reused. Unlike text-based approaches, the subagents are runnable code. **Our angle:** We already do something like this with skills — but skills are prompt templates, not executable code. AgentFactory suggests storing *executable* subagent specs could be more robust than prompt-only skills. [SOURCE: Exa]

**3. VMAO: Verified Multi-Agent Orchestration** — [arxiv:2603.11445](https://arxiv.org/abs/2603.11445)
Plan-Execute-Verify-Replan loop with multiple specialized agents. Verification is built into the orchestration loop, not bolted on. **Our angle:** Our orchestrator runs tasks sequentially without in-loop verification. VMAO's verify step between execute and next-plan could inspire a "verify-before-next-step" gate in pipeline execution. [SOURCE: Exa]

**4. COCO: Cognitive OS with Continuous Oversight** — [arxiv:2508.13815v2](https://arxiv.org/abs/2508.13815)
Decoupled architecture for continuous oversight and error correction in multi-agent workflows. Oversight is a separate process from execution. **Our angle:** This is essentially what our hooks + session-analyst do — decoupled oversight. Worth reading to see if their oversight architecture surfaces patterns we haven't formalized. [SOURCE: Exa]

**5. Runtime Governance for AI Agents: Policies on Paths** — [arxiv:2603.16586](https://arxiv.org/abs/2603.16586)
Formal framework for runtime policy enforcement on agent action sequences (paths). Goes beyond single-action checks to reason about trajectories. **Our angle:** Our hooks check individual actions. Path-level governance would catch patterns like "3 failed searches followed by fabrication" that single-action hooks miss. Directly relevant to our hook architecture. [SOURCE: Exa]

**6. Epistemic Regret Minimization for Causal Rung Collapse** — [arxiv:2602.11675v2](https://arxiv.org/abs/2602.11675)
Builds on the Causal Rung Collapse result we already track (research/causal-reasoning-evidence.md). New contribution: epistemic regret framework that lets models know *when* they're achieving correct answers via superficial correlations rather than causal reasoning. **Our angle:** Directly relevant to our causal-dag and causal-check skills. The regret minimization framework could inform how we validate DAG construction quality. [SOURCE: Exa]

**7. Stop Before You Fail: Operational Capability Boundaries** — [arxiv:2509.24711v3](https://arxiv.org/abs/2509.24711)
Reasoning models learn to detect when they're outside their operational boundary and stop rather than produce garbage. **Our angle:** This is the stall-detection problem. Our orchestrator uses timeout-based stall detection (600s). This paper suggests models can self-detect capability boundaries — could inform when to abort vs retry. [SOURCE: Exa]

**8. AgentDrift: Tool Corruption Hidden by Ranking Metrics** — [arxiv:2603.12564](https://arxiv.org/abs/2603.12564)
Shows that corrupted tools cause agent recommendations to drift unsafely while aggregate metrics look fine. **Our angle:** Our MCP tools are trusted by default. AgentDrift shows that even subtly corrupted tool outputs can cascade. Relevant to our "fail open" philosophy — we should verify tool outputs more, not just tool access. [SOURCE: Exa]

**9. Automating Skill Acquisition from Agentic Repositories** — [arxiv:2603.11808](https://arxiv.org/abs/2603.11808)
Mines open-source agent repos to extract reusable skills automatically. **Our angle:** We wrote our suggest-skill tool that detects repeated workflows within our sessions. This paper does it across public repos. Could inform a "community skill import" pipeline. [SOURCE: Exa]

**10. MemMA: Coordinating Memory Cycle through Multi-Agent Reasoning** — [arxiv:2603.18718](https://arxiv.org/abs/2603.18718)
Multi-agent framework for memory construction, retrieval, and in-situ self-evolution. Addresses the full memory lifecycle, not just storage. **Our angle:** Our memory is files + git. MemMA's "in-situ self-evolution" of memory items could inform how we handle stale memories. The multi-agent coordination of memory reads/writes is relevant to our 4-agent environment. [SOURCE: Exa]

### Tier 2 — Skim / Reference

**11. OpenDev v3** — [arxiv:2603.05344v3](https://arxiv.org/abs/2603.05344) — Terminal-native coding agent. Updated version with scaffolding/harness/context engineering lessons. Direct comparison point to our Claude Code harness.

**12. Comparing Uncertainty Measurement Methods for LLMs** — [arxiv:2504.18346v3](https://arxiv.org/abs/2504.18346) — Systematic review. May surface methods we haven't considered for calibration-canary.

**13. Can LLMs Detect Their Confabulations?** — [arxiv:2508.08139v3](https://arxiv.org/abs/2508.08139) — Models can partially detect their own confabulations through uncertainty measures. Relevant to safe-lite-eval — could we use self-assessed confidence as a pre-filter?

**14. The Phenomenology of Hallucinations** — [arxiv:2603.13911](https://arxiv.org/abs/2603.13911) — "Contrary to common beliefs" about why hallucinations happen. May update our mental model.

**15. Confidence-Aware Self-Consistency** — [arxiv:2603.08999v2](https://arxiv.org/abs/2603.08999) — Dynamic sampling budget based on confidence. Could apply to our multi-model review: don't always pay for cross-model if confidence is high enough.

**16. Inducing Epistemological Humility** — [arxiv:2603.17504](https://arxiv.org/abs/2603.17504) — SFT approach to make models recognize knowledge limits. Training-time solution to what we address with prompting (epistemic skill).

**17. VeriGrey: Greybox Agent Validation** — [arxiv:2603.17639](https://arxiv.org/abs/2603.17639) — Security testing of tool-using agents. Could inform how we think about MCP security.

**18. ToolRegistry: Protocol-Agnostic Tool Management** — [arxiv:2507.10593v2](https://arxiv.org/abs/2507.10593) — Modular tool registration. Relevant to MCP proliferation management.

**19. Automated Self-Testing as Quality Gate** — [arxiv:2603.15676](https://arxiv.org/abs/2603.15676) — Evidence-driven release management for LLM apps. Relevant to our fix-verify pipeline.

**20. MR-Search: Meta-RL for Agentic Search** — [arxiv:2603.11327v2](https://arxiv.org/abs/2603.11327) — Agents learning search strategy from experience. Could inform researcher skill's search heuristics.

**21. Evolving Deception** — [arxiv:2603.05872v2](https://arxiv.org/abs/2603.05872) — Self-evolving agents converge on deception in competitive settings. Safety-relevant for self-improvement loops. Not directly applicable (we're not competitive/adversarial) but worth tracking.

**22. The Agentic Researcher** — [arxiv:2603.15914](https://arxiv.org/abs/2603.15914) — Practical guide to AI-assisted research in math/ML. May have workflow patterns relevant to our researcher skill.

### What's Novel vs Known

**Already covered in our research:**
- Causal Rung Collapse (#18 extends it with regret minimization — genuine novelty)
- CoT faithfulness concerns (#15, #16 add data but no paradigm shift)
- Multi-agent coordination evidence (VMAO and COCO are new instantiations of known patterns)

**Genuinely new to us:**
- **Path-level governance** (#5, Runtime Governance) — we think about hooks as point checks, not trajectory checks
- **Executable subagent accumulation** (#2, AgentFactory) — skills as code, not prompts
- **Tool corruption as invisible drift** (#8, AgentDrift) — we trust tool outputs; this challenges that
- **Self-detected capability boundaries** (#7, Stop Before You Fail) — better than timeout-based stall detection
- **Skill mining from repos** (#9) — automated skill discovery at ecosystem scale

### Suggested Deep Reads (priority order)

1. **Runtime Governance** (2603.16586) — path-level policies could upgrade our hook architecture
2. **VMAO** (2603.11445) — verify-in-loop orchestration pattern
3. **AgentDrift** (2603.12564) — tool output verification gap
4. **Stop Before You Fail** (2509.24711v3) — self-detected stall, better than timeout
5. **LEAFE** (2603.16843) — experience distillation loop comparison to our session-analyst

### What's Uncertain

- Whether path-level governance is practical without massive overhead (Runtime Governance paper may assume capabilities we don't have in hook architecture)
- Whether AgentFactory's executable subagents work outside their benchmark environments
- Whether self-detected capability boundaries generalize across model families (tested on specific reasoning models)
- All summaries are from Exa snippets, not full paper reads — claims about mechanisms need verification via fetch_paper
