---
title: "Model-Task Routing: Empirical Observations from Multi-Modal Phenotype Extraction"
date: 2026-04-05
status: active
tags: [model-routing, vision, gemini, gpt, cost, empirical]
summary: "Empirical model strengths from 7 dispatches: vision (Flash vs 3.1 Pro), text mining (Gemini vs GPT-5.4), structured extraction"
---

# Model-Task Routing: Empirical Observations

*From a media phenotype extraction session (2026-04-05). 7 model dispatches across vision and text tasks, 2 models compared head-to-head on identical inputs.*

## 1. Vision: Batch Image Assessment

**Task:** 91 face images (selfies + Photo Booth), year-grouped, clinical dermatological scoring (0-3 severity).

### Gemini 2.5 Flash

- **Floor effect.** Rated every year at severity 1/3 (mild). Cannot distinguish clear skin (0) from actual mild redness (1).
- **Adequate for:** binary detection (redness present/absent), counting, categorization.
- **Cost:** ~€2 for 91 images across 15 API calls.

### Gemini 3.1 Pro

- **Discriminates severity levels.** Scored 0, 0.5, 1, 1.5 across years. Found most years clear (0), identified 2023 as peak (1.5).
- **Adds clinical nuance:** "intermittent flares returning to baseline" vs "persistent mild erythema."
- **Cost:** ~€60 for 91 images. Thinking tokens dominate — each image generates thousands of reasoning tokens before visible output.

### Routing Rule

Flash for screening at 1/30th the cost. Pro for the 2-3 ambiguous years or for synthesis across Flash findings. Never batch >10 images to Pro. Probe with 3 images before committing to a batch.

## 2. Text: Large Corpus Pattern Mining

**Task:** 6,136 AI conversation titles (Claude + ChatGPT), 86K tokens, phenotype trajectory extraction.

### Gemini 3.1 Pro

- **Completed in ~90s** on 86K token input.
- Found specific clinical correlations: reactive arthritis pattern from STI queries, fludrocortisone → facial bloating connection, medication escalation timeline.
- Narrative-heavy output. Editorializes and interprets (sometimes over-interprets — e.g., inferring psychological state shifts from topic choices).
- Strengths: volumetric processing, pattern detection across large context, clinical pattern matching.

### GPT-5.4

- **Failed twice** on 83K token input via llmx (returned empty/1-byte output). Context ceiling through llmx appears to be ~50K tokens practical max.
- **Succeeded on 48K tokens** (selfie descriptions). Produced the most useful single artifact: a year-by-year 1-10 functional trajectory score that correlated with wearable data.
- Strengths: structured output, clinical coding scales, tabular assessment, systematic scoring.
- Weakness: context size via llmx, slower processing.

### Routing Rule

Gemini Pro for >50K token text mining (GPT can't handle it via llmx). GPT-5.4 for structured clinical scoring on <50K token inputs — its tabular output format is consistently better.

## 3. Text: Photo Description Analysis (~360K tokens)

All dispatches used Gemini 3.1 Pro (only model that fits 360K).

### Prompt Design Matters More Than Model

The *same model* with different prompts produced very different quality:

| Prompt Style | Output Quality | Novel Findings |
|-------------|----------------|----------------|
| "Open-ended pattern mining" | Good — found cognitive ergonomics shift, camera roll medicalization | Yes |
| "Ethnographic lens" | Interesting but unfalsifiable — "tourist of life," absent domesticity | Marginal |
| "Decision archaeology" (ask for numbers) | Best — book trajectory with counts, whiteboard death (21→3), 87 dating screenshots | Yes |
| "Clinical affect coding" (GPT-5.4) | Most actionable — 1-10 functional score per year | Yes |

**Takeaway:** "Give me numbers" prompts beat narrative prompts. The best outputs were structured (GPT's scoring table, Gemini's decision counts), not narrative (ethnographic analysis, clinical interpretation).

## 4. Description vs Direct Vision: Compound Error

A key finding: Gemini's text descriptions of photos (from the media extraction pipeline) **exaggerated** skin severity compared to what Gemini vision found looking at the actual images.

- Text descriptions: "prominent band of red, irritated skin," "significant redness"
- Vision on actual images: severity 0-0.5 (clear to very mild)

**Mechanism:** The multi-angle extraction was prompted to be descriptively rich. "Rich description" → "notice and emphasize any redness" → over-reporting. When a second model analyzed these descriptions, it took the drama at face value.

**Rule:** For any finding derived from LLM-generated descriptions, verify against the source (actual image, actual text) before treating as ground truth. Two layers of LLM interpretation compound errors.

## 5. Cost Summary

| Dispatch | Model | Input | Cost (approx) | Value |
|----------|-------|-------|-------|-------|
| Selfie timeline | Gemini Pro | 76K tok text | ~€1 | High — appearance chronology |
| Open mining | Gemini Pro | 361K tok text | ~€3 | Medium — some novel, some noise |
| Skin (Flash) | Gemini 2.5 Flash | 91 images | ~€2 | Low — floor effect |
| Skin (Pro) | Gemini 3.1 Pro | 91 images | ~€60 | Medium — better scores but 30x cost |
| Ethnographic | Gemini Pro | 368K tok text | ~€3 | Low — interesting but not actionable |
| Affect coding | GPT-5.4 | 48K tok text | ~€2 | **High** — best structured output |
| Text mining | Gemini Pro | 86K tok text | ~€1 | High — medication trajectory |
| Decision archaeology | Gemini Pro | 368K tok text | ~€3 | Medium-high — concrete numbers |

**Total: ~€75.** The €60 skin-Pro run was the clear waste. Same information at 95% quality from Flash at €2. Best ROI: the €2 GPT-5.4 affect coding dispatch.

## 6. Routing Cheat Sheet

| Task Type | First Choice | Fallback | Avoid |
|-----------|-------------|----------|-------|
| Batch image screening (>10) | Gemini Flash | — | Pro on batch |
| Clinical image assessment | Gemini 3.1 Pro (2-3 images) | Flash + Pro synthesis | Pro on >10 |
| Large text mining (>50K tok) | Gemini 3.1 Pro | — | GPT-5.4 (context fails) |
| Structured scoring/coding | GPT-5.4 (<50K tok) | Gemini Pro | — |
| Negative space / absence detection | Gemini 3.1 Pro | — | — |
| Numbers-first analysis | Gemini Pro + "give counts" prompt | — | Narrative prompts |

<!-- knowledge-index
generated: 2026-04-06T01:38:50Z
hash: d1878f2b1013

title: Model-Task Routing: Empirical Observations from Multi-Modal Phenotype Extraction
status: active
tags: model-routing, vision, gemini, gpt, cost, empirical

end-knowledge-index -->
