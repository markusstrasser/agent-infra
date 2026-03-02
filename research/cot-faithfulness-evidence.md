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

### What this means for agentic use

Our prior conclusion holds but gets sharper: **the thinking trace is an imperfect window into the model's actual reasoning.** The Oxford paper adds formal rigor to what we suspected — procedural correctness AND causal accuracy are both required for faithfulness, and neither is reliably present.

**NEW nuance from ICLR 2026 wild study:** Unfaithfulness happens on **normal, clean prompts** — not just adversarial ones. 7-13% baseline unfaithfulness means roughly 1 in 10 reasoning traces are misleading even without any attack. Design for this in production.
