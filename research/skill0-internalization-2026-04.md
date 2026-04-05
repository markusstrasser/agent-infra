---
title: "SKILL0: In-Context Agentic RL for Skill Internalization"
date: 2026-04-05
tags: [skills, reinforcement-learning, internalization, context-efficiency, ALFWorld]
paper: "arXiv:2604.02268"
authors: "Lu, Yao, Wu, Han, Gu et al. (Zhejiang U / Meituan / Tsinghua)"
tier: Standard
verdict: extract-pattern
---

## SKILL0: In-Context Agentic RL for Skill Internalization

**Question:** Can SKILL0's approach of internalizing skills into model parameters inform our prompt-level skill injection architecture (43 SKILL.md files in `~/Projects/skills/`)?

**Tier:** Standard | **Date:** 2026-04-05

**Ground truth:** Our skills are markdown files with frontmatter + instructions, injected into Claude Code's context at invocation time. No fine-tuning. No RL. Context cost is real (~2-8K tokens per skill loaded). We cannot modify model weights.

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | SKILL0 achieves 87.9% on ALFWorld (3B) | Table 1, single benchmark | HIGH | arXiv:2604.02268 | VERIFIED |
| 2 | 5.8x token reduction vs skill-augmented inference | Table 1 (2.21K vs 0.38K tokens/step) | HIGH | arXiv:2604.02268 | VERIFIED |
| 3 | Progressive withdrawal produces +1.6pp positive transfer | Table 4 ablation, [6,3,0] vs with-skills | HIGH | arXiv:2604.02268 | VERIFIED |
| 4 | Static full skills create -13.3pp dependency | Table 4 ablation, [6,6,6] w/ vs w/o | HIGH | arXiv:2604.02268 | VERIFIED |
| 5 | Skill ranking is the critical curriculum component (+13.7pp) | Table 2 ablation | HIGH | arXiv:2604.02268 | VERIFIED |
| 6 | 7B SKILL0 outperforms GPT-4o/Gemini-2.5-Pro on ALFWorld | Table 5 | MEDIUM | arXiv:2604.02268 | VERIFIED (single benchmark, apples-to-oranges) |
| 7 | Filtering unhelpful skills improves our selection | [INFERENCE] from ablation | MEDIUM | -- | INFERENCE |

### What SKILL0 Does

SKILL0 (Lu et al., April 2026) trains vision-language models (Qwen2.5-VL 3B/7B) to absorb procedural skills into their parameters via curriculum-based reinforcement learning, eliminating the need for runtime skill retrieval entirely. Skills are provided as in-context visual guidance during training rollouts but progressively withdrawn across three curriculum stages. By inference time, the model operates zero-shot with no skill context at all. The motto: "skills at training, zero at inference." On ALFWorld, this achieves 87.9% success (3B) vs 79.9% for the RL baseline without skills, while using 5.8x fewer tokens per step than skill-augmented inference. [SOURCE: arXiv:2604.02268]

### Skill Representation

Skills are **structured markdown files** organized in a hierarchical directory: `skills/{task_name}/{skill_category}.md`. Each file stores related skills sharing the same task and category.

Two levels:
- **General skills** -- universal strategic principles (exploration patterns, goal-tracking)
- **Task-specific skills** -- domain-specialized knowledge (action sequences, preconditions, object relationships)

Concrete examples from ALFWorld (Table 7 in paper):
- "Systematic Exploration": search every plausible surface exactly once before revisiting
- "Immediate Acquisition": take required objects as soon as visible
- "Receptacle Priority": check expected receptacles before exhaustive search

For Search-QA:
- "Decompose Then Search": break multi-hop questions into sub-questions with targeted queries

**Observation:** Their skill format is structurally identical to ours -- markdown files with natural language instructions, organized by category. The content is imperative/procedural ("do X when Y"), not demonstrations or code. The key difference: they have 6 skill files for ALFWorld vs our 43, and theirs are used as training curriculum rather than inference-time context. [SOURCE: arXiv:2604.02268, Table 7]

### Internalization Mechanism

"Internalization" = curriculum-based PPO that progressively removes skill context during RL training, forcing the model to absorb the knowledge into its weights. This is **not standard fine-tuning on skill text** -- it's RL with a dynamic skill curriculum.

**The pipeline:**

1. **Offline:** Organize skills into a SkillBank. Partition validation tasks so each maps to a skill file.

2. **Online training (3 stages, 180 steps total on 4x H800):**
   - Stage 1: All 6 skills provided in context (M=6)
   - Stage 2: Top 3 skills by measured helpfulness (M=3)
   - Stage 3: Zero skills (M=0) -- model must perform from parameters alone

3. **Skill selection within stages** (the dynamic curriculum):
   - **Filter:** Evaluate each skill's helpfulness as `delta_k = Acc_with_skill - Acc_without_skill`. Remove skills where delta <= 0 (unhelpful or harmful).
   - **Rank:** Sort remaining skills by descending helpfulness.
   - **Select:** Take top-M(s) skills for current stage budget.

4. **Visual compression:** Text skills are rendered as RGB images and encoded via a vision encoder, producing compressed visual embeddings. The policy jointly generates task actions AND compression ratios.

5. **Composite reward:** `r_tilde = r_task + lambda * ln(c_t)` where c_t is the compression ratio. Success is rewarded; compression efficiency is incentivized.

6. **PPO update** with KL divergence penalty against reference model.

**Budget decay:** `M(s) = ceil(N * (N_S - s) / (N_S - 1))`. Linear decay from full to zero. [SOURCE: arXiv:2604.02268, Algorithm 1, Equations 2-6]

### Token Cost Analysis

The 5x claim is real and comes from two sources:

| Setting | Tokens/step | Source |
|---------|------------|--------|
| SkillRL (skills at inference), 3B, ALFWorld | 2.21K | Table 1 |
| **SKILL0 (zero-shot), 3B, ALFWorld** | **0.38K** | Table 1 |
| **Ratio** | **5.8x reduction** | |
| SkillRL, 3B, Search-QA | 0.87K | Table 1 |
| SKILL0, 3B, Search-QA | 0.18K | Table 1 |
| Ratio | 4.8x reduction | |

**Where the savings come from:**
1. **Skill elimination at inference** (primary) -- no retrieved skill text in the context window at all
2. **Visual compression during training** -- rendering text as images and encoding them produces more compact representations than raw tokens

The visual compression is a training-time mechanism (not available to us), but the core insight -- that skills occupy significant context budget at inference -- is directly relevant. [SOURCE: arXiv:2604.02268, Table 1]

### ALFWorld Results

**SKILL0 vs baselines (3B model, success rate %):**

| Method | Type | Avg | Tokens/step |
|--------|------|-----|-------------|
| GRPO (RL baseline) | No skills | 79.9% | 0.38K |
| AgentOCR | No skills | 78.2% | 0.38K |
| SkillRL | Skills at inference | 82.4% | 2.21K |
| **SKILL0** | **Skills internalized** | **87.9%** | **0.38K** |

Delta: +8.0pp over GRPO, +5.5pp over SkillRL, at same token cost as no-skill methods.

**7B model:** SKILL0 reaches 89.8% vs GRPO 81.8% (+8.0pp).

**Per-task breakdown (3B):**
- Clean: 100% (SKILL0) vs 70.6% (GRPO) -- +29.4pp, strongest gain
- Heat: 86.7% vs 73.3% (AgentOCR) -- +13.4pp
- Pick2: 75.2% vs 65.0% (GRPO) -- +10.2pp
- Look: 80.4% vs 85.7% (GRPO) -- -5.3pp (regression on this task type)

**Comparison to memory-augmented methods (7B, Table 5):**

| Method | Success Rate |
|--------|-------------|
| ExpeL | 46.3% |
| SimpleMem | 62.5% |
| Mem0 | 54.7% |
| MemRL | 21.4% |
| GPT-4o | 48.0% |
| Gemini-2.5-Pro | 60.3% |
| **SKILL0 (7B)** | **89.8%** |

The gap over closed-source models is striking -- a 7B model with internalized skills outperforms GPT-4o and Gemini-2.5-Pro by 30-40pp on this benchmark. The paper notes memory-augmented methods store "raw trajectories" which are "lengthy, redundant, and noisy" vs structured skills. [SOURCE: arXiv:2604.02268, Tables 1, 5]

**Search-QA (out-of-domain transfer, Table 6):**

| Method | HotpotQA | Bamboogle | Musique | Avg |
|--------|----------|-----------|---------|-----|
| Search-R1 | 43.0% | 26.5% | 18.6% | 38.5% |
| EvolveR | 47.5% | 54.4% | 18.2% | 43.1% |
| **SKILL0 (7B)** | **47.1%** | **66.9%** | **19.2%** | **44.4%** |

Strong on Bamboogle (+12.5pp over EvolveR), demonstrating out-of-domain generalization. [SOURCE: arXiv:2604.02268, Table 6]

### Key Ablation Findings

**1. Budget schedule matters enormously (Table 4):**

| Budget | w/ Skills | w/o Skills (inference) | Transfer |
|--------|-----------|----------------------|----------|
| [6,3,0] (linear decay) | 86.3% | **87.9%** | **+1.6pp** |
| [6,6,6] (always full) | 85.9% | 72.6% | **-13.3pp** |
| [3,3,3] (always low) | -- | 78.9% | ~0 |
| [0,0,0] (no skills) | -- | 78.9% | baseline |

Critical finding: Static full skill provision **creates dependency** (-13.3pp when removed). Only progressive withdrawal produces positive transfer (+1.6pp improvement when skills are removed vs when they're present). [SOURCE: arXiv:2604.02268, Table 4]

**2. Dynamic curriculum components (Table 2):**
- Ranking skills by helpfulness: **+13.7pp** (critical)
- Filtering out unhelpful skills: **+2.7pp**
- Both together: +16.4pp vs no curriculum

**3. Validation interval (Table 3):** d=10 steps optimal. Too frequent (d=5) adds overhead; too sparse (d=20) loses -9.8pp. [SOURCE: arXiv:2604.02268, Tables 2-3]

### Relevance to Our Skills Architecture

Our situation differs fundamentally: we cannot fine-tune Claude's weights. We operate entirely in the "skills at inference" paradigm that SKILL0 is designed to surpass. However, several findings are directly transferable at the prompt engineering level.

**Directly actionable patterns (ranked by expected ROI):**

**1. Empirical skill helpfulness measurement (HIGH ROI).** SKILL0's most impactful component is measuring per-skill helpfulness (`delta_k = Acc_with - Acc_without`) and removing unhelpful skills. We could implement this: run the same tasks with and without each of our 43 skills loaded, measure success rate delta, and prune skills with negative or zero delta.
- *Implementation:* Run N tasks twice (with/without skill X). Compare success. Skills with delta <= 0 are candidates for removal or rewriting.
- *Evidence:* Filtering alone gave +2.7pp; ranking gave +13.7pp. The curriculum does most of its work through selection quality, not the RL training.
- *Estimated effort:* Moderate (need task suite + evaluation harness). Expected payoff: high (both token savings and quality improvement).

**2. Ranked skill loading (HIGH ROI).** Rather than loading all potentially-relevant skills, rank by expected helpfulness for the current task and load only top-K. This directly reduces token cost (each SKILL.md is 2-8K tokens; loading 5 unnecessary skills wastes 10-40K tokens).
- *Implementation:* Behavioral router (cf. Memento-Skills' +28pp Recall@1 over BM25 for skill routing) or simpler keyword/category matching against the task description.
- *Our existing state:* Skills are loaded via explicit invocation (`/skill-name`) or rule-based triggers. No helpfulness-based ranking exists.

**3. Dependency detection (MEDIUM ROI).** The [6,6,6] ablation's -13.3pp dependency effect likely applies to us: if agents always see skills in context, they may over-rely on literal instructions rather than developing robust strategies. Periodically test with skills withheld.
- *Test:* Run a subset of tasks with skills deliberately withheld. If performance doesn't degrade (or improves), the skill is either already in the model's training data or counterproductive.
- *Insight:* Some of our skills may encode behavior Claude already knows from training. Those skills burn tokens for zero benefit.

**4. Progressive skill compression (LOW ROI, watch).** Even without RL, we can apply the curriculum idea at the prompt level. For a new skill: initially provide full detail, then compress to a summary, then test if the model performs without it. This gives a "skill maturity" lifecycle.
- *Relevance:* Mostly theoretical for us since we can't control training. But the principle -- verbose for unfamiliar tasks, compressed for familiar ones -- could inform skill document design.

**Not transferable (requires weight modification):**
- The RL internalization mechanism itself (PPO + curriculum)
- Visual compression of text context (vision-language model specific)
- Composite reward design (no reward signal to optimize)
- Zero-shot inference without any context (our skills add domain-specific knowledge)

**Indirect validation:**
- Their skill format (markdown, imperative, categorical) validates our existing architecture. The fact that this format works for RL internalization suggests it's a good representation for procedural knowledge generally.
- The 5.8x token reduction is the prize we cannot claim through internalization, but we can partially capture through better skill selection (loading 2 relevant skills instead of 8 irrelevant ones is a practical 2-4x reduction).

### What's Uncertain

- **Benchmark specificity.** ALFWorld is a narrow interactive environment (6 task types, household domain). Whether these findings transfer to the breadth of tasks our 43 skills cover (research, code review, causal analysis, epistemics) is unknown. Search-QA transfer is encouraging but still narrow.
- **Scale of skill library.** SKILL0 uses 6 skills for ALFWorld. We have 43. The ranking dynamics may not scale -- evaluating 43 skills per-task requires substantial infrastructure.
- **No replication.** April 2026 preprint, zero citations, single group. Ablation results are internally consistent but unconfirmed externally.
- **ALFWorld saturation.** Memory-augmented baselines (ExpeL 46%, Mem0 55%) are suspiciously weak. The SKILL0 numbers may partly reflect ALFWorld being a good fit for structured skills rather than a general advantage.
- **The -5.3pp Look regression** suggests internalization isn't uniformly beneficial. Some task types may degrade. This parallels our concern about skill interference.

### Verdict: Extract Pattern

**Do not adopt** the SKILL0 framework -- it requires fine-tuning, RL infrastructure, and vision-language models we don't use.

**Extract three patterns:**

1. **Empirical skill helpfulness measurement.** Run A/B evaluations on each of our 43 skills. Identify and prune/rewrite skills with delta <= 0. This is the single highest-ROI extraction from the paper.

2. **Ranked skill loading.** Implement a lightweight relevance scorer that loads top-K (K=3-5) for any given task. Direct token cost reduction of 2-5x for multi-skill tasks.

3. **Dependency testing.** Periodically run tasks with skills withheld to detect over-reliance. If removing a skill doesn't hurt, either the model has already internalized it from training data or the skill was never helping.

**Watch:** If the curriculum idea gets replicated or extended to text-only models, the progressive withdrawal pattern could become a prompt engineering technique (full instructions -> compressed -> hints -> nothing) for skill maturity management.

### References

- Lu, Z., Yao, Z., Wu, J., Han, C., Gu, Q., Cai, X., Lu, W., Xiao, J., Zhuang, Y., & Shen, Y. (2026). SKILL0: In-Context Agentic Reinforcement Learning for Skill Internalization. arXiv:2604.02268.

## Revisions

- **2026-04-05:** Rewrote from full paper text (prior version based on abstract + alphaXiv summary only). Added: per-task breakdown, all ablation tables, budget decay formula, composite reward mechanism, Search-QA transfer results, Look regression note. Changed verdict from "watch" to "extract-pattern" based on ablation evidence strength.

<!-- knowledge-index
generated: 2026-04-05T23:50:20Z
hash: f4f3c523d039

title: SKILL0: In-Context Agentic RL for Skill Internalization
tags: skills, reinforcement-learning, internalization, context-efficiency, ALFWorld
table_claims: 7

end-knowledge-index -->
