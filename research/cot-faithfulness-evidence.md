---
title: "Reasoning Model Internals: CoT Faithfulness"
date: 2026-03-21
---

# Reasoning Model Internals: CoT Faithfulness

*Split from `frontier-agentic-models.md` on 2026-03-01. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*Date: 2026-02-27. Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*

---

### What's PROVEN

All prior findings hold. Additionally:

**NEW — "CoT Reasoning In The Wild Is Not Always Faithful" (submitted ICLR 2026):** Tests on realistic, non-adversarial prompts (no artificial bias). GPT-4o-mini: 13% unfaithful. Haiku 3.5: 7%. Labels this "Implicit Post-Hoc Rationalization" — models' implicit biases toward Yes/No produce unfaithful reasoning even on clean prompts. [SOURCE: OpenReview, ICLR 2026 submission] [PREPRINT]

**NEW — "CoT Is Not Explainability" (Oxford AIGI, 2025):** Formalized the faithfulness problem: a CoT is faithful only if it is both **procedurally correct** AND **accurately reflects the model's decision process**. Current CoT satisfies neither reliably. Proposes causal validation methods (activation patching, counterfactual interventions). Three proposals: (1) don't treat CoT as sufficient for interpretability, (2) adopt rigorous faithfulness assessment, (3) develop causal validation. [SOURCE: aigi.ox.ac.uk] [PUBLISHED]

**NEW — Counter-counter-paper: "Is CoT Really Not Explainability?" (arXiv:2512.23032):** Responds to the Oxford paper, arguing CoT can be faithful without explicit verbalization of hints. The debate is active and unresolved — which is itself important information. [SOURCE: arXiv:2512.23032] [PREPRINT]

**NEW — FUR "Faithfulness by Unlearning Reasoning Steps" (EMNLP 2025):** Measures "parametric faithfulness" by erasing information from reasoning steps in model parameters and measuring the effect on predictions. Provides a methodology for quantifying faithfulness beyond behavioral tests. [SOURCE: aclanthology.org/2025.emnlp-main.504] [PUBLISHED EMNLP 2025]

**NEW — Mechanistic interpretability of CoT (arXiv:2507.22928):** Uses sparse autoencoding to study how CoT reasoning works mechanistically inside the model. Moving beyond behavioral evaluation to understanding the actual circuits. [SOURCE: arXiv:2507.22928] [PREPRINT]

**NEW — "Reasoning Theater" (arXiv:2603.05488, Goodfire AI + Harvard, March 2026):** Strongest evidence yet for difficulty-dependent performative CoT. Attention probes decode a reasoning model's final answer far earlier than CoT text reveals it. Key findings: [SOURCE: arXiv:2603.05488] [PREPRINT]

- **Difficulty split:** On MMLU (easy recall), CoT is largely performative — the model "knows" its answer immediately but generates hundreds of reasoning tokens. On GPQA-Diamond (hard multihop), CoT tracks genuine belief evolution.
- **Inflection points are real:** Backtracking and "aha" moments occur almost exclusively in responses with large internal belief shifts (measured via probes). These are genuine uncertainty resolution, not theater.
- **Probe-guided early exit:** Attention probes enable 80% token savings on MMLU and 30% on GPQA-Diamond with comparable accuracy. Positions probing as more reliable than CoT monitoring.
- **Cooperative speaker framing:** Reasoning models are not cooperative speakers (Grice 1975). CoT fidelity is incidental to outcome reward optimization. CoT monitors are "at best cooperative listeners" — they assume the model is trying to communicate, but it isn't.
- **Models tested:** DeepSeek-R1 671B, GPT-OSS 120B. Larger models show more performativity (less test-time compute needed → more theater on easy tasks).
- **Implication for monitoring:** Text-based CoT monitors lag behind internal state. On tasks the model finds easy, the trace is unreliable for detecting early commitments, measuring uncertainty, or auditing decisions. Activation monitoring covers these failure cases.

**NEW — "Gaming the Judge: Unfaithful Chain-of-Thought Can Undermine Agent Evaluation" (arXiv:2601.14691, Khalifa et al., 2026):** Extends CoT unfaithfulness to *agent evaluation* specifically. Unfaithful CoT can game LLM judges that rely on reasoning traces to assess agent behavior. Implications: trace-based monitoring (what we do in trace-faithfulness.py) must compare claims against actual tool calls, not trust the reasoning narrative. Our claim-vs-tool-use matching approach is the right design. [SOURCE: arXiv:2601.14691] [PREPRINT]

**NEW — SPD-Faith Bench (arXiv:2602.07833, Lv et al., 2026):** First diagnostic benchmark for CoT faithfulness in multimodal LLMs. Extends faithfulness measurement beyond text-only to vision-language models. [SOURCE: arXiv:2602.07833] [PREPRINT]

**Scite citation stance audit (2026-03-17):** No retractions or contrasting citations found for any CoT faithfulness paper in our corpus. The 7-13% unfaithfulness baseline remains uncontested. "Gaming the Judge" adds agent-specific evidence that the problem is worse in evaluation contexts than in standalone reasoning.

### What this means for agentic use

Our prior conclusion holds but gets sharper: **the thinking trace is an imperfect window into the model's actual reasoning.** The Oxford paper adds formal rigor to what we suspected — procedural correctness AND causal accuracy are both required for faithfulness, and neither is reliably present.

**NEW nuance from ICLR 2026 wild study:** Unfaithfulness happens on **normal, clean prompts** — not just adversarial ones. 7-13% baseline unfaithfulness means roughly 1 in 10 reasoning traces are misleading even without any attack. Design for this in production.

**NEW nuance from Reasoning Theater (March 2026):** Performativity is **task-difficulty-dependent**, not uniform. Easy tasks = mostly theater. Hard tasks = more genuine reasoning. This means:
- Cross-model review on easy/obvious tasks may be especially susceptible to false agreement (both models "know" the answer, both generate performative reasoning that looks deliberate)
- Our session-analyst should be more suspicious of long reasoning traces on tasks that should be easy
- The token cost of reasoning models is significantly inflatable — 80% of MMLU tokens are theater. Budget-conscious orchestration should consider task difficulty when selecting reasoning vs non-reasoning models

<!-- knowledge-index
generated: 2026-03-22T00:15:43Z
hash: 77572b3d6ddd

title: Reasoning Model Internals: CoT Faithfulness

end-knowledge-index -->
