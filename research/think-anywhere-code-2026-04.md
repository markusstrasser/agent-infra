---
title: "Think Anywhere in Code Generation — Token-Level Reasoning Interleaved with Code"
date: 2026-04-05
tags: [reasoning, code-generation, RL, thinking-models, routing]
paper: "arXiv:2603.29957 (Jiang et al., Peking University + Tongyi Lab / Alibaba, March 2026)"
verdict: note
---

## Think Anywhere in Code Generation — Research Memo

**Question:** What is the THINK-ANYWHERE mechanism for token-level reasoning during code generation, and does it change our guidance on when to use extended thinking for code tasks?
**Tier:** Standard | **Date:** 2026-04-05

### What Think Anywhere Does

Think Anywhere (Jiang et al., arXiv:2603.29957, March 2026) enables LLMs to insert reasoning blocks at arbitrary token positions *during* code generation, rather than requiring all reasoning to occur before code output begins. The model learns — via a cold-start SFT phase followed by GRPO reinforcement learning — to autonomously identify high-entropy positions where code generation is uncertain and insert short `<thinkanywhere>` blocks (avg 22-23 tokens each). The executable code is extracted by stripping all thinking blocks. This contrasts with standard "plan-then-code" (upfront thinking / extended reasoning) where the model reasons exhaustively before emitting any code.

### Mechanism: How Reasoning Gets Interleaved with Code Tokens

**Architecture:** No architectural changes to the base LLM. The mechanism is purely a learned generation strategy trained via:

1. **Cold-start SFT (~5K samples):** Strong reasoning LLM (Gemini 2.5 Flash) generates solutions with interleaved `<thinkanywhere>` blocks. These examples teach the model the *pattern* of inserting reasoning mid-code. LoRA fine-tuning. [SOURCE: arXiv:2603.29957]

2. **RLVR (GRPO):** The model then autonomously discovers *where* to think via reward-driven exploration. Hierarchical reward: structure reward (at least one `<thinkanywhere>` block present) + correctness reward (code passes test cases). 128 batch size, 14K problems, 8 rollouts per problem, max 4096 tokens. [SOURCE: arXiv:2603.29957]

**What triggers a thinking block:** Learned, not rule-based. Analysis shows the model inserts thinking at high-entropy positions — where it anticipates uncertainty in the next code tokens. Syntactically, blocks concentrate at assignment statements (complex computations) and return statements (correctness verification). Average 6-11 blocks per solution depending on benchmark difficulty (HumanEval: 6.15, LeetCode: 11.26). [SOURCE: arXiv:2603.29957]

**Special token variant:** The paper also tests a variant using dedicated trigger tokens with semantic-aware initialization (`0.5·mean(e_think, e_any, e_where) + 0.5·e_<im_start>`) instead of text-based delimiters. Results are "comparable" but slightly lower — limited post-training data constrains learning the new token semantics. [SOURCE: arXiv:2603.29957]

### Benchmark Results

**Base model:** Qwen2.5-Coder-7B-Instruct throughout, unless noted.

| Benchmark | Base | GRPO (upfront) | Think Anywhere | Delta vs base |
|-----------|------|----------------|----------------|---------------|
| LeetCode | 50.6% | 63.3% | **69.4%** | +18.8pp |
| LiveCodeBench | 34.3% | 36.9% | **37.2%** | +2.9pp |
| HumanEval | 88.4% | 90.9% | **91.5%** | +3.1pp |
| MBPP | 70.7% | 81.7% | **82.9%** | +12.2pp |
| **Average** | 61.0% | 68.2% | **70.3%** | +9.3pp |

[SOURCE: arXiv:2603.29957, Table 2]

**Cross-model generalization:**

| Model | Base | Think Anywhere | Delta |
|-------|------|----------------|-------|
| Qwen2.5-Coder-7B | 61.0% | 70.3% | +9.3pp |
| Qwen2.5-Coder-1.5B | 40.6% | 54.5% | +13.9pp |
| LLaMA-3.1-8B | 38.4% | 43.8% | +5.4pp |

[SOURCE: arXiv:2603.29957, Table 4]

**Cross-domain generalization (math, trained only on code):**

| Benchmark | Base | GRPO | Think Anywhere |
|-----------|------|------|----------------|
| AIME 2024 | 5.3% | 6.0% | **17.3%** |
| AIME 2025 | 4.0% | 4.7% | **17.7%** |
| HMMT 2025 | 0.0% | 0.3% | **14.4%** |

[SOURCE: arXiv:2603.29957]

**Token efficiency (upfront thinking tokens + code tokens):**

| Benchmark | CoT | GRPO (upfront) | Think Anywhere |
|-----------|-----|----------------|----------------|
| HumanEval | 348.8 | 309.4 | **238.1** (215.6 code + 22.5 think) |
| LeetCode | 577.0 | 440.7 | **305.9** (283.0 code + 22.9 think) |

Think Anywhere uses 30-47% fewer total tokens than CoT while achieving higher accuracy. [SOURCE: arXiv:2603.29957]

### Ablation Studies

| Variant | LeetCode pass@1 | Delta |
|---------|-----------------|-------|
| Full Think Anywhere | 69.4% | — |
| Cold-start SFT only (no RL) | 47.9% | -21.5pp |
| RLVR only (no cold-start) | 63.4% | -6.0pp |
| Line-level thinking (not token-level) | 67.2% | -2.2pp |
| No upfront thinking (inline only) | 66.6% | -2.8pp |
| Padding thinking (random tokens in blocks) | 67.6% | -1.8pp |

[SOURCE: arXiv:2603.29957, Table 5]

Key insights from ablations:
- **RL is essential.** SFT alone drops 21.5pp. The cold-start teaches format; RL teaches *when and what* to think.
- **Token-level beats line-level** by 2.2pp. Granularity matters.
- **Upfront thinking still helps** (-2.8pp without it), but most gains come from inline blocks.
- **Padding ablation** (-1.8pp): reasoning content matters, but merely *pausing* at the right position also provides value. This is reminiscent of "pause tokens" / filler token findings.

### When It Helps vs Doesn't

**Helps most:**
- Harder problems: LeetCode (+18.8pp) >> HumanEval (+3.1pp). The harder the problem, the more thinking blocks inserted (11.26 avg on LeetCode vs 6.15 on HumanEval) and the larger the gain.
- Small models: 1.5B gains +13.9pp vs 7B gaining +9.3pp. Weaker models benefit more from being taught to pause and reason.
- Math cross-domain transfer: 3-4x improvement on AIME despite zero math training data.

**Helps less:**
- Easy problems where upfront thinking is already sufficient (HumanEval is near ceiling at 88.4% base).
- LiveCodeBench shows smallest gain (+2.9pp) — possibly because it tests more diverse, recent problems where the RL training distribution matters more.

**Limitations not addressed:**
- No models > 8B tested. Unknown whether frontier models (70B+, or models with native extended thinking like o3/Claude) already capture this behavior implicitly.
- Only code benchmarks (competitive programming style). No evaluation on real-world software engineering tasks (SWE-bench, Commit0, etc.).
- No analysis of failure modes — when does interleaved thinking produce worse code than upfront thinking?
- Trained on 14K competitive programming problems with test-case verification. Unclear how well this transfers to open-ended code generation without binary correctness signals.

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Think Anywhere improves avg pass@1 by 9.3pp over base on 4 benchmarks | Table 2, 4 benchmarks | HIGH | arXiv:2603.29957 | VERIFIED |
| 2 | Uses 30-47% fewer tokens than CoT | Token counts in paper | HIGH | arXiv:2603.29957 | VERIFIED |
| 3 | RL is essential (SFT-only drops 21.5pp) | Ablation Table 5 | HIGH | arXiv:2603.29957 | VERIFIED |
| 4 | Token-level > line-level by 2.2pp | Ablation Table 5 | HIGH | arXiv:2603.29957 | VERIFIED |
| 5 | Transfers to math without math training | AIME/HMMT results | MEDIUM | arXiv:2603.29957 | VERIFIED (single paper) |
| 6 | Model places thinking at high-entropy positions | Entropy analysis | MEDIUM | arXiv:2603.29957 | VERIFIED (correlational) |
| 7 | Padding thinking still helps somewhat | Ablation Table 5 | HIGH | arXiv:2603.29957 | VERIFIED |

### Implications for Reasoning Routing

**Our current guidance** (from `reasoning_mode` in global CLAUDE.md): Reserve extended thinking for genuine reasoning tasks (causal DAGs, complex synthesis, multi-step proofs, architectural design). Use standard mode for interactive/tool-heavy workflows.

**What this paper implies:**

1. **Upfront thinking is suboptimal for code.** The paper's core finding: exhaustive upfront reasoning wastes tokens and misses complexity that only emerges during implementation. Think Anywhere's 9.3pp average improvement over GRPO (which already uses upfront RL-based thinking) and 30-47% token reduction are strong evidence that interleaved reasoning > front-loaded reasoning for code generation specifically.

2. **This is about small open-source models, not frontier.** All results are on 1.5B-8B models. Frontier models with native extended thinking (o3, Claude Opus with ultrathink) likely already exhibit some form of interleaved reasoning implicitly — their thinking traces often revisit and correct mid-implementation. The paper's contribution is showing this can be trained into small models, not that it's a novel capability for frontier.

3. **The "pause and think" insight is real.** The padding ablation (random tokens in thinking blocks still help by 1.8pp less than real reasoning) confirms that pausing at uncertainty points has independent value. This aligns with the "pause tokens" literature and suggests that even without explicit thinking content, allocating compute at decision points matters.

4. **Competitive-programming-only scope limits transferability.** All benchmarks are algorithmic puzzle solving with test cases. Real-world code generation (SWE-bench, agent coding) involves architecture decisions, API integration, error handling — tasks where the upfront planning phase may matter more than inline reasoning about algorithmic details.

5. **No evidence this changes routing for tool-using agents.** Our routing guideline is about when to use extended thinking mode in an agent workflow. This paper is about training a different generation strategy into small models. The two are orthogonal: we route thinking mode at the *session* level; they modify generation at the *token* level. A tool-using agent that pauses between tool calls to reason is already doing "think anywhere" at a coarser granularity.

### Verdict: NOTE

**Does not change our reasoning routing guidance.** The finding is scientifically interesting — interleaved reasoning beats upfront reasoning for code generation on small models by meaningful margins. But it doesn't change when we should invoke extended thinking mode:

- Our routing operates at session/task granularity (use thinking for complex reasoning, standard for interactive). Think Anywhere operates at token granularity within a single generation.
- Frontier models with extended thinking likely already exhibit some implicit interleaving. The paper doesn't test this.
- The competitive programming scope doesn't generalize to agent-style code generation where planning, tool use, and iterative refinement dominate.

**What IS worth noting for future reference:**
- The padding ablation validates that compute allocation at uncertainty points matters independently of reasoning content. If we ever fine-tune or train models, interleaved thinking is a better training target than pure upfront thinking.
- The 1.5B model gaining +13.9pp suggests this technique is especially powerful for small/local models. Relevant if we ever deploy local code generation models.
- The math transfer result (3-4x improvement on AIME from code-only training) suggests interleaved reasoning teaches a general capability, not just a code-specific pattern.

### What's Uncertain

- Whether frontier models (70B+, o3, Claude) already capture interleaved reasoning implicitly
- Whether the technique transfers to real-world software engineering tasks (SWE-bench, etc.)
- Whether the technique works at scale or has diminishing returns with model size
- Replication status: single paper, single lab (Peking University + Alibaba), no independent replication yet [PREPRINT]

### Search Log

| Query | Tool | Result |
|-------|------|--------|
| "Think Anywhere code generation token-level reasoning" | S2 search_papers | Found paper d30eb0ca... |
| "arxiv 2603.29957 Think Anywhere" | Exa web_search | Found arxiv page + news coverage |
| Full HTML extraction (mechanism, benchmarks) | WebFetch arxiv HTML | Comprehensive extraction |
| Detail extraction (triggers, ablations, limitations) | WebFetch arxiv HTML | Filled gaps |
| "Think Anywhere" interleaved reasoning | scite search_literature | Not indexed yet (too recent) |
| "interleaved thinking reasoning code generation" | S2 search_papers | Timed out |

<!-- knowledge-index
generated: 2026-04-05T23:09:49Z
hash: 0bd534586e2c

title: Think Anywhere in Code Generation — Token-Level Reasoning Interleaved with Code
tags: reasoning, code-generation, RL, thinking-models, routing
table_claims: 7

end-knowledge-index -->
