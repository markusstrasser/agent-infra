---
title: "Markdown Formatting Effects on Frontier LLMs — Evidence Audit"
date: 2026-04-05
---

## Markdown Formatting Effects on Frontier LLMs — Evidence Audit

**Question:** Do specific markdown formatting choices (admonitions, ventilated prose, HTML comments, diff blocks, mermaid, XML tags, numbered lists) measurably affect frontier LLM behavior?
**Tier:** Standard | **Date:** 2026-04-05
**Ground truth:** Two prior memos (`structured-vs-prose-for-agents.md`, `opus-46-prompt-structure.md`) found zero frontier-model evidence as of March 2026. This audit adds 6 new sources from Feb–April 2026.

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | GitHub admonitions (`> [!CAUTION]`) cause models to weight content more than bold/blockquotes | None found | ZERO | — | **UNSOURCED** |
| 2 | Ventilated prose (one sentence per line) improves per-sentence reasoning | None found | ZERO | — | **UNSOURCED** |
| 3 | HTML comments in markdown are visible to and processed by models | Architectural tautology — models receive raw text tokens | HIGH | [INFERENCE] | **TRUE (architectural)** |
| 4 | Diff blocks (` ```diff `) are parsed structurally by models | None found directly; markdown structural awareness demonstrated by "Last Fingerprint" | LOW | [INFERENCE from training data exposure] | **PLAUSIBLE but unmeasured** |
| 5 | Mermaid diagrams are reliably parsed by frontier models | Generation demonstrated (Together AI); parsing reliability unmeasured | LOW | [SOURCE: together.ai/blog/open-deep-research] | **PARTIAL — generation ≠ parsing** |
| 6 | Pipe-delimited uses ~40% fewer tokens than markdown tables (2-col) | Measured: 37% fewer tokens (43 vs 27, cl100k_base, 5-row 2-col) | HIGH | [DATA: tiktoken measurement] | **VERIFIED (37%)** |
| 7 | XML tags improve instruction following | Anthropic docs recommend XML. Delimiter Hypothesis: XML and Markdown equally effective on Opus 4.6 (both 100% on trojan injection test). Only MiniMax showed Markdown vulnerability. | HIGH (as practice) LOW (as differential) | [SOURCE: systima.ai, Anthropic docs] | **VERIFIED but effect is negligible on frontier** |
| 8 | Numbered constraints followed more reliably than prose paragraphs | Factorial experiment: format factor F=0.0, p=1.000. Gemini Pro 6/6 regardless of format. Han et al.: bullet points "generally better" but no frontier models tested. | MEDIUM (pre-frontier) LOW (frontier) | [SOURCE: kircerta.com factorial, Han et al. 2025] | **CONTRADICTED on frontier** |

### Key Findings

**1. The dominant pattern: formatting effects shrink with model capability.**

Every study tells the same story:

| Study | Weaker model | Stronger model | Format effect |
|-------|-------------|----------------|---------------|
| Delimiter Hypothesis (2026) | MiniMax M2.5: Markdown 84%, XML 96.4% | Opus 4.6: 100% all formats | Vanishes on frontier |
| Braun et al. (2025) | GPT-4o: robust but low accuracy | GPT-4.1: +20pp with structure | Present but model-dependent |
| Factorial experiment (2026) | Flash-Lite: improved with examples | Gemini Pro: 6/6 all conditions | Zero format effect on capable model |
| He et al. (2024) | GPT-3.5: up to 40% variation | GPT-4: more robust | Shrinks with scale |
| MDSpin (2026) | — | GPT-4o: Markdown 4.6/5, PDF 3.1/5 | Document format matters, not markdown syntax |

**Implication for Opus 4.6:** The Delimiter Hypothesis tested Opus 4.6 directly. Result: 100% boundary compliance on XML, Markdown, AND JSON. No format advantage. The model simply doesn't care about delimiter choice.

**2. What DOES matter (measured):**

- **Document format** (Markdown vs PDF vs HTML vs DOCX): MDSpin measured 85% vs 52% RAG accuracy, 37% fewer tokens. This is about converting documents TO markdown, not about markdown syntax choices within a document.
- **Content** (examples, task clarity): The factorial experiment found Factor B (examples) at F=8.0, p=0.012; Factor A (format) at F=0.0, p=1.000. What you say matters; how you format it doesn't.
- **Model capability**: Factor C (model) at F=32.0, p<0.001. Overwhelms all formatting effects.

**3. XML vs Markdown: a settled question on frontier.**

The Delimiter Hypothesis tested 4 frontier models × 3 formats × 600 calls. Results:
- Round 1 (basic): XML 98.4%, Markdown 98.4%, JSON 98.8% — identical
- Round 2 (stress): XML 96.3%, Markdown 93.3%, JSON 96.3% — gap driven entirely by MiniMax M2.5's Markdown vulnerability
- Opus 4.6 specifically: 100% compliance on all formats including trojan injection

Anthropic's recommendation to use XML tags is still sound practice (clear section delineation), but the MEASURED differential on Opus 4.6 is zero. XML tags are organizational hygiene, not a performance lever. [SOURCE: systima.ai/blog/delimiter-hypothesis]

**4. My original suggestions: mostly folk wisdom.**

| Suggestion | Verdict |
|-----------|---------|
| GitHub admonitions | **Folk wisdom.** No evidence. Probably irrelevant on frontier (delimiter hypothesis logic). |
| Ventilated prose | **Folk wisdom for LLM accuracy.** Genuine benefits for git diffs and Edit tool targeting are ENGINEERING benefits, not LLM comprehension benefits. |
| HTML comments as metadata | **True but trivial.** Models see raw text; comments are text. Whether they ACT on comments depends on prompt design, not the comment syntax. |
| Diff blocks | **Plausible but unmeasured.** Models have markdown training exposure. No evidence of differential structural parsing. |
| Mermaid diagrams | **Overstated.** Models can generate mermaid. Parsing reliability for reasoning is untested. |
| Token efficiency | **Verified.** 37% fewer tokens for pipe-delimited vs markdown tables (2-col). |
| XML tags | **Sound practice, zero differential on frontier.** Organizational benefit, not compliance benefit. |
| Numbered vs prose | **Contradicted on frontier.** Factorial: F=0.0, p=1.000. Format is noise. |

### What Actually Helps (Evidence-Backed)

1. **Convert documents to Markdown before feeding to LLMs** — MDSpin: +33pp RAG accuracy vs PDF, -37% tokens. This is the only large, robust formatting effect.
2. **Provide examples** — Factorial: F=8.0, p=0.012. One compliant example helps weaker models. Frontier models don't need it but it doesn't hurt.
3. **Use a more capable model** — Factor C dominates all formatting effects. The best prompt formatting trick is using a better model.
4. **Clear content** — Task clarity, not delimiter choice, drives compliance.

### What's Uncertain

- Whether admonitions have an attention-weighting effect below the threshold of existing benchmarks (the Delimiter Hypothesis measured boundary compliance, not content recall within sections)
- Whether ventilated prose helps models with long-context retrieval specifically (no study tests this)
- Mermaid parsing reliability in reasoning chains (no study)
- Whether any of this changes with Claude 5.x / GPT-6 (plausible that format-agnosticism continues to improve)

### Disconfirmation

- Searched explicitly for "markdown formatting LLM accuracy" criticism, "prompt format does not matter" evidence
- Factorial experiment (kircerta.com) provided the strongest disconfirmation: format factor had ZERO statistical effect (F=0.0, p=1.000)
- Delimiter Hypothesis confirmed: format rarely matters, and when it does, it's a model bug (MiniMax), not a format property

### Sources

| Source | Type | Key contribution |
|--------|------|-----------------|
| systima.ai "Delimiter Hypothesis" (2026) | Practitioner benchmark (600 calls, 4 frontier models) | **Primary evidence.** XML/Markdown/JSON tested on Opus 4.6, GPT-5.2. Format ≈ negligible. |
| kircerta.com factorial experiment (2026) | Practitioner experiment (24 runs, ANOVA) | Numbered list vs CoT format: F=0.0, p=1.000. Model capability dominates. |
| MDSpin benchmark (2026) | Practitioner benchmark (4 formats, RAG + quality) | Markdown vs PDF/HTML/DOCX: +33pp RAG accuracy, -37% tokens. |
| Braun et al. 2025 (arXiv:2505.12837) | Peer-reviewed (4 citations) | Legal docs: GPT-4.1 sensitive to structure (+20pp); GPT-4o robust. Markdown highest at 79pp. |
| Han et al. 2025 (arXiv:2503.06926) | Peer-reviewed (1 citation) | Bullet points "generally better" than plain English. Pre-frontier models. |
| "Last Fingerprint" (arXiv:2603.27006) | Peer-reviewed | Markdown training leaves structural traces (em dash signature). 12 models, 5 providers. |
| He et al. 2024 (170 citations) | Peer-reviewed | Up to 40% variation on GPT-3.5/4. Larger models more robust. Pre-frontier. |
| Perplexity synthesis (2026-04-05) | AI-grounded search | Confirmed: "minimal empirical evidence" for specific formatting claims. |
| tiktoken measurement | Primary data | 37% fewer tokens for pipe-delimited vs markdown tables (2-col, cl100k_base). |

### Papers in Corpus

- He et al. 2024 "Does Prompt Formatting Have Any Impact?" (S2: 113873a4e58e2ff15ce3523ee9fb629ff6dddfe4)
- Liu et al. 2025 "Beyond Prompt Content" (S2: 4607a529dfb8b64a5767e53fd482bfccd23cfc20)
- Braun et al. 2025 "The Hidden Structure" (S2: 6ac58407e30a548782fbd9f2e54799467411b7fd)
- Han et al. 2025 "Effect of Selection Format" (S2: 7bb7a0f8b280f6b97c64dca51712cac4dee8bd48)
- Sclar et al. 2023 "Quantifying Sensitivity to Spurious Features" (S2: 17a6116e5bbd8b87082cbb2e795885567300c483)

<!-- knowledge-index
generated: 2026-04-06T02:02:10Z
hash: 9cf3447926d5

title: Markdown Formatting Effects on Frontier LLMs — Evidence Audit
sources: 2
  INFERENCE: from training data exposure
  DATA: tiktoken measurement
table_claims: 8

end-knowledge-index -->
