---
title: "Simple Self-Distillation for Code Generation — Lock/Fork Framework"
date: 2026-04-04
tags: [code-generation, self-distillation, temperature, decoding, sampling]
status: complete
---

**Paper:** Zhang et al. (2026). "Embarrassingly Simple Self-Distillation Improves Code Generation." arXiv:2604.01193. Apple.
**Code:** https://github.com/apple/ml-ssd

## Core Finding

Sample from a model at high temperature + truncation (top-k), fine-tune on those raw samples (no verification, no reward model, no correctness signal), get large code generation improvements. Qwen3-30B-Instruct: 42.4% → 55.3% pass@1 on LiveCodeBench v6 (+30% relative). Works across 5 models, two families (Llama, Qwen), three scales (4B–30B), both instruct and thinking variants.

Even near-gibberish training data (T=2.0, no truncation, ~62% samples with no extractable code) improves performance: +5.7pp pass@1.

## The Lock/Fork Framework

The key conceptual contribution. Code generation has two context types:

- **Locks**: Positions where distribution should be sharply peaked (e.g., after `if n==`). One correct token dominates but distractor tails persist.
- **Forks**: Positions where distribution should be broad (e.g., function body start). Multiple plausible solutions legitimately exist.

Fixed decoding temperature cannot satisfy both: low temp sharpens locks but starves forks; high temp enables fork exploration but destabilizes locks. SSD reshapes distributions *context-dependently* — suppresses distractor tails at locks while preserving usable alternatives at forks.

This is why decode-only temperature tuning gives only ~2pp spread while SSD gives ~13pp. Two structural invariants prevent equivalence: base model's cumulative probability curve is fixed, and support ranking is predetermined.

## Key Numbers

| Model | Baseline | SSD | Δ | Hard Δ |
|-------|----------|-----|---|--------|
| Qwen3-30B-Instruct | 42.4% | 55.3% | +12.9pp | +15.3pp |
| Qwen3-4B-Instruct | 26.9% | 34.4% | +7.5pp | — |
| Qwen3-30B-Thinking | 48.0% | 50.1% | +2.1pp | +5.2pp |
| Qwen3-4B-Thinking | 21.5% | 24.8% | +3.3pp | +4.1pp |
| Llama-3.1-8B-Instruct | 27.8% | 31.3% | +3.5pp | — |

Gains concentrated on harder problems (+15.3pp hard vs +6.5pp easy for 30B-Instruct). Thinking models benefit less (+2pp vs +13pp), suggesting CoT already partially resolves the precision-exploration conflict.

## Temperature Composition

T_eff = T_train × T_eval. Optimal ≈ 1.2. R² = 0.75 for quadratic fit. Training-time truncation (top-k=10) raises achievable performance ceiling beyond what temperature alone achieves.

## Practical Details

- ~10K competitive programming problems (rSTARcoder seed, deduplicated)
- Single solution per prompt (N=1 sufficient)
- Minimal filtering (empty/stub removal only)
- 8×B200 GPUs, Megatron-LM, 2500 iterations, AdamW, lr=5e-6
- vLLM v0.11.0 for generation, 128K max seq length

## Tension with Prior Work

The trending scout (2026-03-29) flagged arXiv:2603.24472 "Self-Distillation Degrades Reasoning" — which warns against naive self-distillation for reasoning tasks (suppresses uncertainty expressions). This paper's results are compatible: (1) SSD is specific to code, where lock/fork dynamics dominate; (2) thinking models show much smaller gains, suggesting reasoning chains partially obviate the mechanism; (3) the degradation paper targets general reasoning, not structured-output generation.

## Relevance to Our Systems

**Not directly actionable** — we consume API models, not fine-tune them. SSD requires training infrastructure.

**Conceptually useful:**

1. **Temperature tuning has a hard ceiling.** Decode-only temperature gives ~2pp. Don't over-optimize llmx temperature settings for code generation. The real gains are in the model's training, not our inference knob.

2. **Lock/fork as mental model for prompt design.** When structuring prompts that include code, understand that precision-demanding and exploration-demanding positions coexist. This validates using different temperatures for different task types in llmx dispatch.

3. **Thinking models already partially solve this.** Reinforces our routing: thinking models for hard problems (they've internalized fork exploration via CoT), instruct for routine code.

4. **pass@5 > pass@1 gains validate multi-sample approaches.** SSD preserves solution diversity. Relevant to autoresearch mutation sampling and any generate-then-select pattern.

5. **Autoresearch experiment candidate:** Adding top-k truncation to mutation sampling could improve diversity. Currently autoresearch doesn't set temperature or truncation parameters explicitly — worth probing.

<!-- knowledge-index
generated: 2026-04-04T23:44:24Z
hash: fc9ac1716b30

title: Simple Self-Distillation for Code Generation — Lock/Fork Framework
status: complete
tags: code-generation, self-distillation, temperature, decoding, sampling

end-knowledge-index -->
