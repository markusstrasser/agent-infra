---
title: "SKILL0: Skill Internalization via In-Context Agentic RL"
date: 2026-04-05
tags: [skills, reinforcement-learning, token-efficiency, training]
status: complete
---

# SKILL0: In-Context Agentic RL for Skill Internalization (arXiv:2604.02268)

**Authors:** Zhengxi Lu + 9 co-authors (ZJU-REAL)
**Source:** [arxiv.org/abs/2604.02268](https://arxiv.org/abs/2604.02268) (519 views on alphaXiv)

## What SKILL0 Does

Framework for internalizing agent skills from in-context demonstrations into model parameters via curriculum-based reinforcement learning. Skills start as full context injections, then are progressively withdrawn during RL training until the model performs zero-shot without any runtime skill retrieval. Achieves +9.7% on ALFWorld, +6.6% on Search-QA, with <0.5K tokens per step (vs multi-K with skill injection).

## Skill Representation

Skills are "structured packages of procedural knowledge and executable resources that agents dynamically load at inference time." In practice: interaction history rendered with skill context as compact visual demonstrations. Grouped offline by category for curriculum batching.

## Internalization Mechanism

**Not fine-tuning on skill text.** Instead, curriculum-based RL with progressive skill withdrawal:

1. **Phase 1:** Full skill context injected during RL episodes (model learns with training wheels)
2. **Phase 2:** Dynamic curriculum evaluates each skill's on-policy helpfulness, retaining only skills the model still benefits from
3. **Phase 3:** Linearly decaying budget removes remaining skill context
4. **Result:** Model performs zero-shot — skill knowledge is "in the weights"

The key insight: the RL reward signal teaches the model to internalize the *behavior* that skills encode, not memorize the skill text. The curriculum prevents catastrophic forgetting by withdrawing skills only when the model no longer needs them.

## Token Cost Analysis

The 5x reduction (from alphaXiv summary) comes from eliminating runtime skill retrieval entirely:
- **With skills:** Multi-K tokens per step for skill context injection + retrieval noise
- **After SKILL0:** <0.5K tokens per step, zero retrieval needed
- The cost is paid once at training time, then amortized over all inference

## Results

| Benchmark | SKILL0 vs baseline | Notes |
|-----------|-------------------|-------|
| ALFWorld | +9.7% over standard RL | Household task completion |
| Search-QA | +6.6% over standard RL | Information retrieval tasks |
| Token efficiency | <0.5K tokens/step | vs multi-K with skill injection |

## Relevance to Our Skills Architecture

Our skills are SKILL.md files injected into Claude Code's context at invocation. We don't have fine-tuning access, so SKILL0's core mechanism (RL-based internalization) is not directly applicable.

**What transfers at the prompt level:**

1. **Progressive skill disclosure** — SKILL0's curriculum starts with full context and withdraws. We could implement a lighter version: skills that start verbose for new tasks and compress for familiar patterns. The MS Agent Framework's 3-level skill disclosure (advertise/load/read-resources) is the practical analog.

2. **Skill helpfulness evaluation** — SKILL0 dynamically evaluates whether each skill is still helping. We could measure: does injecting skill X actually change behavior? If a skill's instructions are already in the model's training data, injection is pure token waste. A/B test: run tasks with/without specific skills and compare.

3. **Skill grouping by category** — SKILL0 batches skills by category for curriculum. Our skills are invoked individually. Category-based skill bundles (e.g., "research toolkit" = researcher + epistemics + source-grading) could reduce invocation friction.

**What doesn't transfer:**
- The RL training loop (requires fine-tuning access)
- The progressive withdrawal mechanism (requires training-time control)
- Zero-shot inference (our skills add domain knowledge not in training data)

## Verdict: **Watch — validates skill architecture direction**

SKILL0 confirms that skills-as-context-injection is the right intermediate step before skills-as-parameters. The practical takeaway is skill helpfulness measurement: which of our ~40 skills actually change agent behavior vs just burning tokens? This is measurable without fine-tuning access.

The 3-level skill disclosure pattern (from MS Agent Framework, independently validated by SKILL0's curriculum) is the nearest actionable item. Deferred to skill architecture review.

<!-- knowledge-index
generated: 2026-04-05T23:40:21Z
hash: 81997df80c07

title: SKILL0: Skill Internalization via In-Context Agentic RL
status: complete
tags: skills, reinforcement-learning, token-efficiency, training

end-knowledge-index -->
