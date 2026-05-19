---
title: Gemini 3.5 Flash Benchmark Survey — with Exa & Perplexity Search Comparison
date: 2026-05-19
tags: [benchmarks, gemini, search, exa, perplexity, llm-routing]
status: active
---

# Gemini 3.5 Flash — Benchmark Survey

Date: 2026-05-19 (launch day, GA at Google I/O 2026)
Model code: `gemini-3.5-flash`

## Summary

Gemini 3.5 Flash is the first model of the 3.5 family, GA May 19 2026. **Reasoning:** mixed — it BEATS Gemini 3.1 Pro on agentic/coding/tool-use benchmarks (Terminal-Bench 2.1, MCP Atlas, OSWorld-Verified, GDPval-AA, Finance Agent v2) but LOSES to 3.1 Pro on pure reasoning (HLE 40.2 vs 44.4, ARC-AGI-2 72.1 vs 77.1). **Search/grounding:** no published LMArena Search Arena ELO for the 3.5 Flash variant yet — `gemini-3-flash-grounding` was added to the Search leaderboard ~Mar 2026 but a 3.5 entry has not been confirmed at launch (1).

## Filled Table

| Benchmark | Gemini 3.5 Flash | Gemini 3.1 Pro (peer) | Gemini 3 Flash (older Flash) | Source grade |
|---|---|---|---|---|
| MMLU-Pro | [?] not published by Google | 89.5% (user table) | 89% | — |
| GPQA Diamond | [?] not on official card | 94.3% (user table) | 90.4% | — |
| ARC-AGI-2 | **72.1%** | 77.1% | — | A (DeepMind model card) |
| FrontierMath T4 | [?] not published | 16.7% (user table) | — | — |
| Humanity's Last Exam | **40.2%** | 44.4% | 33.7% (no tools) | A (DeepMind) |
| Terminal-Bench 2.1 | **76.2%** | 70.3% | — | A (DeepMind) |
| SWE-Bench Pro (Public) | **55.1%** | 54.2% | — | A (DeepMind) |
| MCP Atlas | **83.6%** | 78.2% | — | A (DeepMind) |
| OSWorld-Verified | **78.4%** | 76.2% | — | A (DeepMind) |
| GDPval-AA (Elo) | **1656** | 1314 (1317 at 3.1 Pro launch) | — | A (DeepMind) |
| Finance Agent v2 | **57.9%** | 43.0% | — | A (DeepMind) |
| CharXiv Reasoning | **84.2%** | 83.3% | — | A (DeepMind) |
| MMMU-Pro (multimodal) | **83.6%** | 80.5% | — | A (DeepMind) |
| MRCR v2 (128k) | 77.3% | 84.9% | — | A (DeepMind) |
| MRCR v2 (1M) | 26.6% | 26.3% | — | A (DeepMind) |
| LMArena main (provisional) | 1480 Elo (#11/116, #6/24 verified) | 1501 (3 Pro #1 across boards) | — | B (BenchLM third-party scrape) |
| LMArena Search Arena | [?] not yet published for 3.5 Flash variant | 1215 (3 Pro Grounding, user table) | gemini-3-flash-grounding entry added Mar 2026, ELO not retrieved | — |
| AA Intelligence Index | **55** (#7 of 147) | — | — | A- (Artificial Analysis) |
| Throughput | 284–289 tok/s ("4x faster than frontier") | — | — | A- (AA / Google claim) |

## Pricing & Specs

| Field | Value | Source grade |
|---|---|---|
| Input | **$1.50 / MTok** | A (multiple — OpenRouter, AA, DeepMind) |
| Output | **$9.00 / MTok** | A |
| Cached input | $0.15 / MTok | A |
| Non-global regions | $1.65 / $9.90 | B (llm-stats) |
| Context window | 1,048,576 input / 65,536 output | A (DeepMind) |
| Knowledge cutoff | **January 2025** (per official DeepMind model page) | A (DeepMind); B-conflict: BenchLM says Jan 2026 — trust DeepMind |

**Pricing vs base 3 Flash ($0.50 / $3):** 3.5 Flash is **3× input, 3× output** — confirms the "~3x base Flash" claim in the user's notes exactly.

**Pricing vs 3.1 Pro ($2 / $12):** 3.5 Flash is 75% of input, 75% of output. Tight gap — when 3.5 Flash beats 3.1 Pro on agentic tasks, 3.1 Pro becomes hard to justify for those workloads.

## Per-Claim Source URLs

| Claim | URL | Grade |
|---|---|---|
| Official benchmark table (Terminal-Bench 2.1, MCP Atlas, ARC-AGI-2, HLE, GDPval-AA, SWE-Bench Pro, MRCR, MMMU-Pro, CharXiv, OSWorld-Verified, Finance Agent v2) | https://deepmind.google/models/gemini/flash/ | A |
| Knowledge cutoff Jan 2025, 1M/64k context | https://deepmind.google/models/gemini/flash/ | A |
| AA Intelligence Index 55 (#7/147), 284 tok/s, blended $3.38/MTok | https://artificialanalysis.ai/models/gemini-3-5-flash | A- |
| Pricing $1.50/$9.00, $0.15 cached, $1.65/$9.90 non-global | https://openrouter.ai/google/gemini-3.5-flash + AA + DeepMind | A |
| Launch date May 19 2026, GA at I/O, "first model of 3.5 family" | https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-5/ | A |
| LMArena main ~1480 Elo, #11/116 provisional, #6/24 verified | https://benchlm.ai/models/gemini-3-5-flash | B (third-party scrape) |
| gemini-3-flash-grounding on Search leaderboard (NOT confirmed 3.5 variant) | https://arena.ai/blog/leaderboard-changelog/ | A for the entry, but applies to 3 Flash, not 3.5 Flash |
| Gemini 3 Flash GPQA Diamond 90.4%, MMLU-Pro 89% (older sibling for context only) | https://blog.google/products/gemini/gemini-3-flash/ + Vellum | A / B |
| Outperforms 3.1 Pro on coding/agentic suite (4x speed claim) | https://interestingengineering.com/ai-robotics/google-gemini-3-5-flash-launch | B (tech press recap of Google claim) |

## Open Questions / Not Yet Published

1. **MMLU-Pro and GPQA Diamond** — absent from Google's official 3.5 Flash card. Google appears to have moved off MMLU-Pro / GPQA as headline benchmarks for the 3.5 generation, replacing them with Terminal-Bench, MCP Atlas, GDPval-AA. Third-party scores (AA, BenchLM) may emerge within 1–2 weeks; not in artificialanalysis.ai/models/gemini-3-5-flash as of 2026-05-19 fetch.
2. **FrontierMath T4** — no published number for 3.5 Flash. 3.1 Pro at 16.7% is the only data point in our table.
3. **LMArena Search Arena ELO for 3.5 Flash specifically** — leaderboard changelog confirms `gemini-3-flash-grounding` (the older 3 Flash variant) was added in March 2026, but no `gemini-3.5-flash-grounding` entry confirmed at launch. Cannot answer "does it beat Grok 4.20 Reasoning at 1226 or sit closer to 3 Pro Grounding at 1215" from public sources today. Likely populates within 7–14 days.
4. **BrowseComp / SimpleQA-Verified** — not on DeepMind model card, not on AA page. Expect AA to publish within ~1 week.
5. **TAU-bench** — not on official card. Google appears to use MCP Atlas + GDPval-AA as their agentic-tool-use replacements.

## Direct Answers to User's Specific Questions

- **Reasoning**: 3.5 Flash trails 3.1 Pro on classical reasoning (HLE 40.2 vs 44.4, ARC-AGI-2 72.1 vs 77.1) but matches or beats it on multimodal reasoning (MMMU-Pro 83.6 vs 80.5, CharXiv 84.2 vs 83.3). Pure-reasoning verdict: **slightly worse than 3.1 Pro, dramatically better than base 3 Flash**. No MMLU-Pro or GPQA Diamond published.
- **Search grounding**: **unanswerable from current sources**. The 3.5 Flash variant has not been entered on LMArena Search Arena as of launch day. The grounding-capable 3 Flash variant has an entry but the ELO was not retrievable from the changelog page.
- **Pricing "~3x base Flash"**: **CONFIRMED EXACTLY**. $1.50/$9.00 is exactly 3× the $0.50/$3.00 of Gemini 3 Flash.
- **Agentic-loop fitness**: Strong. Terminal-Bench 2.1 76.2% (beats 3.1 Pro 70.3%), MCP Atlas 83.6% (beats 3.1 Pro 78.2%), OSWorld-Verified 78.4%, GDPval-AA 1656 Elo (massive step up from 3.1 Pro's 1314). SWE-Bench Pro public 55.1%. No SWE-bench Verified, Terminal-Bench (original), or TAU-bench numbers published — Google has shifted to Terminal-Bench 2.1 / MCP Atlas / GDPval-AA as headline agentic benchmarks.
- **Knowledge cutoff**: **January 2025** per DeepMind official page. One third-party source (BenchLM) claims Jan 2026 — disregard, trust DeepMind. The user's pre-existing context note was correct.

## Caveats

- All ratios "3.5 Flash beats 3.1 Pro" come from Google's own model card. No independent third-party replication yet.
- AA has begun measuring (Intelligence Index 55 published) but full benchmark breakdown not yet on their site.
- LMArena main leaderboard entry of 1480 Elo from BenchLM is a B-grade scrape — verify on lmarena.ai directly before citing externally.

## Exa vs Perplexity vs Gemini Grounding — Search-System Comparison

### Updated Summary (search systems)

For web-grounded answer quality at low latency, **Perplexity Sonar Pro leads on SimpleQA (F=0.858) and ties Gemini 2.5 Pro Grounding on LMArena Search Arena at ~1136-1142 Elo**; **Exa wins on raw quality and latency for semantic retrieval (<200ms TTFT, 64.8% on a 500-query LangSmith eval)**; **Gemini grounding (3.1 Pro) sits at 1215 on Search Arena per user table, but the 3.5 Flash variant has no published Search Arena entry as of launch day**. Pricing models are not comparable: Exa is per-result ($0.001+), Perplexity is per-MTok + per-request fee, Gemini grounding is per-query through Google Search retrieval.

### Filled Comparison Table

| Metric | Exa (`/answer` + neural search) | Perplexity Sonar / Sonar Pro / Sonar Reasoning Pro | Gemini 3.5 Flash w/ Search Grounding | Grade |
|---|---|---|---|---|
| SimpleQA accuracy | 71% (Exa-published eval) | 74% (same eval); Sonar Pro F=0.858, Sonar F=0.773 | not published for 3.5 Flash specifically | B (Exa blog), A- (Perplexity blog), — |
| BrowseComp | not published | listed as eval framework, score not public | not published | — |
| LMArena Search Arena ELO | not on leaderboard | Sonar Reasoning Pro High **1136** (statistically tied #1 with Gemini 2.5 Pro Grounding 1142) | 3.1 Pro Grounding **1215** (user table); 3.5 Flash **[?] no entry confirmed** | A (Perplexity/Arena), B (user table) |
| HLE (search/tools) | not published | Sonar **0.288** for deep research | 3.5 Flash 40.2% (without specifying search tooling) | A- (Perplexity blog), A (DeepMind) |
| LangSmith head-to-head (500q) | **64.8%** | 60.1% | Google grounding cited at 38% on raw SERP-to-LLM (websearchapi.ai) | B (websearchapi.ai blog) |
| TTFT / latency | **<200ms** server-side | ~300ms (Sonar API); 11s end-to-end synthesis (vs Brave 669ms) | not published for 3.5 Flash grounding; throughput 284 tok/s after first token | B (Exa marketing claim) |
| Pricing — search call | **$0.001+ per result** (compounds with content add-ons) | **Sonar:** $1/$1 per MTok + $5-12 per 1k requests by context size. **Sonar Pro:** $3/$15 per MTok + $6-14 per 1k requests. | $1.50/$9.00 per MTok for model + Google Search grounding billed separately (per-query fee through Google AI Studio / Vertex). | A (Exa docs, Perplexity docs), A (DeepMind) |
| Best-fit role | Semantic retrieval, full-text content extraction, domain filtering, low-latency RAG context | Synthesized answer with citations, NLU-heavy questions, deep-research mode | Multimodal grounded answer, ChatGPT-style chat with web context, 1M-token context for long source merges | — |

### Per-Claim Source URLs (search section)

| Claim | URL | Grade |
|---|---|---|
| Exa 71% SimpleQA, Perplexity 74%, Parallel 90%, OpenAI GPT-5 88% | https://exa.ai/blog/api-evals | B (vendor self-published eval) |
| Exa <200ms TTFT, Perplexity ~300ms, latency comparison | https://exa.ai/versus/perplexity | B (vendor comparison page) |
| Perplexity Sonar Pro F=0.858 on SimpleQA, Sonar F=0.773 | https://www.perplexity.ai/hub/blog/introducing-the-sonar-pro-api | A- (vendor) |
| Sonar Reasoning Pro High 1136 Elo, tied with Gemini 2.5 Pro Grounding 1142 | https://www.perplexity.ai/hub/blog/perplexity-sonar-dominates-new-search-arena-evolution | A- (vendor citing public LMArena data) |
| Sonar 0.288 HLE | https://www.perplexity.ai/hub/blog/introducing-the-sonar-pro-api | A- |
| Sonar Pro pricing $3/$15 + $6-14/1k req; Sonar $1/$1 + $5-12/1k req | https://docs.perplexity.ai/docs/getting-started/pricing | A (vendor) |
| Exa pricing from $0.001/result | https://exa.ai/docs/reference/evaluating-exa-search | A (vendor) |
| LangSmith 500q eval: Exa 64.8% vs Perplexity 60.1%, Google SERP-to-LLM 38% | https://websearchapi.ai/blog/compare-tavily-google-search-exa-perplexity | C (third-party tutorial blog, methodology not peer-reviewed) |
| Search-arena changelog: `gemini-3-flash-grounding` added Mar 26 2026 (no 3.5 entry confirmed) | https://arena.ai/blog/leaderboard-changelog/ | A (arena.ai) |

### Direct Answers — Search Comparison

- **Does Gemini 3.5 Flash + `--search` beat Perplexity Sonar Pro?** Unknown. No published 3.5 Flash Search Arena entry. The closest data point: Gemini 2.5 Pro Grounding (1142) was tied with Sonar Reasoning Pro High (1136). 3.5 Flash is a more capable base than 2.5 Pro on agentic tasks but Search Arena correlates with grounding pipeline quality, not just model strength — so transfer is uncertain.
- **Does Exa beat Perplexity on grounded factuality?** Mixed. Exa wins on the LangSmith 500q eval (64.8 vs 60.1) and latency (<200ms vs ~300ms). Perplexity wins on SimpleQA (Sonar Pro F=0.858 dominates Exa's 71%). The asymmetry is real: Exa returns retrievable context, Perplexity returns synthesized answers — they optimize different objectives.
- **Pricing comparison per "search question":**
  - **Exa**: ~$0.001-0.01 per query depending on result count + content depth
  - **Perplexity Sonar**: ~$0.005-0.012 per request + ~$0.003 per typical answer's tokens = **$0.008-0.015 per query**
  - **Perplexity Sonar Pro**: ~$0.006-0.014 per request + ~$0.020 per answer = **$0.026-0.034 per query**
  - **Gemini 3.5 Flash grounded**: model tokens $1.50/$9.00 per MTok + Google Search grounding fee. For a typical ~2k-input/500-output grounded answer: ~$0.003 (input) + $0.0045 (output) + Google grounding (~$0.005/q via Vertex Search retrieval) = **~$0.012 per query** — same ballpark as Sonar base, half of Sonar Pro
- **Latency**: Exa wins, Gemini Flash second (throughput-led: 284 tok/s after TTFT), Perplexity slowest due to synthesis overhead (~11s end-to-end measured).

### What We Would Have to Measure Ourselves

No published head-to-head exists for **Gemini 3.5 Flash grounded** vs Perplexity vs Exa specifically (the 3.5 Flash variant launched today). To position our local `--search` flag against the others, we would need:

1. **A small internal eval set** (~50 questions across factual lookup, multi-hop, recency-sensitive, and adversarial-confusing classes) run through all three.
2. **Same scoring rubric** — LLM-as-judge with a frozen judge model (GPT-5.5 or Claude Opus 4.7 as third-party) for answer correctness + citation grounding.
3. **End-to-end latency captured** (not just TTFT), since synthesis adds 5-10s on Perplexity Sonar Pro.
4. **Per-query cost logged** — Gemini grounding has the murkiest pricing because Google Search retrieval is billed separately and per-query, not per token.
5. **Ablation: Gemini 3.5 Flash grounded vs Gemini 3.5 Flash + Exa-as-tool** — would tell us whether Google's first-party grounding adds value over swapping in Exa context. This is the actual question for our routing table.

Until measured: keep the current heuristic — Exa for retrieval, Perplexity Sonar (cheap tier) for synthesized factual Q&A, and treat Gemini 3.5 Flash grounded as an unverified contender worth probing.

<!-- knowledge-index
generated: 2026-05-19T21:02:23Z
hash: d64d12d96ee9

index:title: Gemini 3.5 Flash Benchmark Survey — with Exa & Perplexity Search Comparison
index:status: active
index:tags: benchmarks, gemini, search, exa, perplexity, llm-routing
table_claims: 20

end-knowledge-index -->
