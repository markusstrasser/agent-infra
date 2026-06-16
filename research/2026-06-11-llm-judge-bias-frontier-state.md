# LLM-Judge Bias — Frontier State (2026)

**RESEARCH IN PROGRESS** — stub written 2026-06-11. Appending as verification completes.

## Scope
Four open questions on LLM-as-judge bias, frontier-2026-specific (GPT-5.x, Gemini 3.x, Claude Opus 4.x/Fable):
1. Position/order/recency bias on current reasoning models — solved on easy cases vs ambiguous ties?
2. Verbosity/length/self-preference bias on 2026 frontier — persists/worsens (RLHF-induced) vs mitigated?
3. Goodhart/reward-hacking specific to pairwise-LLM-judge RANKING (IFBench 7.0→6.4 generalized).
4. Bradley-Terry aggregation of CORRELATED judges → false precision / overconfident CIs? Effective-sample-size correction?

## Already-verified priors (do NOT re-derive)
- Kim et al. ICML 2025 (arXiv:2506.07962) — same provider/arch/size → higher error correlation; judges inflate weaker same-family models.
- Panickssery et al. 2024 (arXiv:2404.13076) — self-preference CAUSALLY driven by perplexity/familiarity → extends to same-FAMILY. ~60% agreement-on-wrong cross-provider.
- "Nine Judges" (internal, 2026-05) — multi-judge panels collapse to ~2 effective votes.
- AA / GDPval-AA (arXiv:2511.13029) — single LLM judge (Gemini 3.1 Pro), blind pairwise + Bradley-Terry; human-human agreement 71%; intelligence ≠ calibration.

## Findings

### Q1 — Position/order bias on 2026 reasoning models

**[HIGH] `lechmazur/position_bias` benchmark (GitHub, snapshot 2026-04-21).** Directly measures order-flip when the SAME two candidate answers are shown in opposite order. Story-pair task (taste/quality-adjacent, the ambiguous regime). 193 verified story pairs, 27 judge models, 386 prompts/model.
- **Model-average first-shown pick rate = 63.3%** (50% = unbiased). **Median model flips its underlying choice in 44.8% of decisive swapped-order case pairs.** Model-average order-flip rate 44.0%.
- Reasoning models are NOT exempt — they are often the WORST: **GPT-5.4 (high reasoning) is the single most position-biased model**: 82.3% first-shown pick rate, +32.3pp first-lift, 66.3% order-flip, +0.505 rating bonus. **GPT-5.4 Mini (xhigh reasoning)** 75.7% first-pick / 88.1% flip. **Gemini 3.1 Pro Preview** 66.0% first-pick / +16.0pp / 92.2% flip / +0.288.
- Claude Opus 4.6 (high reasoning) 65.0% first-pick / +15.0pp / 60.1% flip — better than GPT-5.4 but still strongly first-biased.
- Frontier-tag: CURRENT 2026 frontier (GPT-5.4, Gemini 3.1, Opus 4.6, Grok 4.20). **This DIRECTLY REFUTES "position bias is gone on thinking models" on ambiguous pairs.** Note: dev's exact versions (GPT-5.x, Gemini 3.x, Opus 4.x) are the ones measured.

**[HIGH] "More Thinking, More Bias: Length-Driven Position Bias in Reasoning Models" (arXiv:2605.06672v1).** MCQ-QA (MMLU/ARC-Challenge/GPQA), 13 reasoning-mode configs incl. DeepSeek-R1 671B.
- KEY MECHANISM: within any reasoning model, **per-question position bias scales with the LENGTH of the reasoning trajectory** (partial ρ(length,PBS|accuracy) 0.11–0.41, all p<0.05; 12/13 configs positive). Truncation intervention = causal: later continuation points shift toward position-preferred option (16%→32% for R1-Qwen-7B).
- Scale anchor: at 671B aggregate PBS collapses to 0.019 BUT the length effect still appears in the longest quartile (PBS=0.071). Interpretation: **accuracy GATES expression of the bias, does not eliminate the mechanism.** "More thinking is not, on its own, a debiasing intervention."
- Reconciles with lechmazur: on EASY items (big quality gap, high accuracy) position bias is near-zero; on HARD/ambiguous items (where reasoning trace runs long) it re-emerges, worse for more reasoning.

**[HIGH] "Assessing Judging Bias in Large Reasoning Models" (arXiv:2504.09946).** LRMs vs LLMs as judges, within-family.
- (1) LRMs still significantly vulnerable to position/bandwagon/authority bias; (2) LRMs MORE robust than LLMs on FACT-related content; (3) LRMs consistently prefer LATER-position options (note: opposite sign to lechmazur's first-bias on story pairs — task/format dependent); (4) novel "superficial reflection bias" — inserting "wait, let me think about it" between options boosts preference for the later answer.

**[MEDIUM] "Judging the Judges: Systematic Study of Position Bias" (ACL/IJCNLP 2025, 2025.ijcnlp-long.18).** 15 judges, MT-Bench+DevBench, 150K instances. Pre-frontier judges but the STRUCTURAL finding is scale-independent and directly answers the easy-vs-tie question: **position bias is "strongly affected by the quality gap between solutions"** — weak when one answer clearly wins, strong on close pairs. >80% of 15 judges agree on >half the dataset (easy); <2% are hard (disagreement≥8) — and the hard ones are where position bias concentrates. This is the mechanism behind "solved on easy, alive on ties."

[PENDING] — Q2/Q3/Q4 underway.
