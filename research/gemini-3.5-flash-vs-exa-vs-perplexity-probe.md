---
title: Head-to-Head Probe — Gemini 3.5 Flash --search vs Perplexity Sonar vs Exa
date: 2026-05-19
tags: [benchmarks, gemini, search, exa, perplexity, llm-routing, probe]
status: active
---

# Gemini 3.5 Flash `--search` vs Perplexity `_ask` vs Exa `web_search_exa` — 5-Query Probe

Same 5 queries through all three systems on launch day for Gemini 3.5 Flash (2026-05-19).
Companion to `gemini-3.5-flash-benchmarks.md` (published numbers survey).
Raw outputs in `/tmp/search-probe-2026-05-19/`.

## Scorecard

| Q | Topic | Gemini 3.5 Flash `--search` | Perplexity `_ask` | Exa `web_search_exa` |
|---|-------|----------------------------|-------------------|---------------------|
| Q1 | FOMC most recent meeting + rate | **A — depth winner.** Apr 28-29, 3.50-3.75% unchanged, 8-4 dissent (Miran wanted cut; Hammack/Kashkari/Logan dissented on easing bias), Powell stays as governor. Matches Fed statement exactly. | **A- — correct, terse.** Date + rate range, no dissent breakdown. Real citations. | **A — primary source.** Returns Fed press release text directly. Raw, authoritative, no synthesis. |
| Q2 | uv latest stable + new feature | **A — correct & fresh.** v0.11.15, Azure request signing + JSON for `uv audit`. Matches GitHub releases (released 2026-05-18). | **F — refused.** "I don't have live access" — Sonar should have searched; didn't. | **B — stale top hit.** Top result is 0.11.14 (May 12). v0.11.15 (May 18) appears further down in releases-page result. Recovers info but agent would need to read more. |
| Q3 | gnomAD v4.1 LOEUF for EBF3 | **F — safety-filter blocked.** `Response blocked by safety filter: None` after 1m44s. No output. Critical finding: routine gene-constraint query blocked. | **A — correct & specific.** "0.17" + the exact gnomAD URL `https://gnomad.broadinstitute.org/gene/ENSG00000108001?dataset=gnomad_r4_1`. | **B — context not answer.** Returns gnomAD v4.1.1 release notes & UCSC track docs; LOEUF threshold guidance but not the per-gene score. |
| Q4 | Sonnet 4.6 pricing + cache | **A — complete.** $3/$15, cache read $0.30, write $3.75 (5m) / $6.00 (1h). Matches Anthropic official page. | **A- — correct, less depth.** $3/$15 + $0.30 cache read. No write tiers. | **A — primary source.** Returns Anthropic docs pricing table directly. |
| Q5 | 2026 paper on AI agents for autonomous science | **C — plausible but obscure.** "Masgent" (RSC Digital Discovery, 10.1039/D6DD00043F) + "Digital materials ecosystem" (10.1039/D5SC09229A). Both plausibly real but minor venues. **Missed the headline Nature papers from today.** DOIs need verification. | **C — unverified.** "From Prompt to Drug" (ACS Central Science, Feb 2026, Insilico/Lilly). No DOI given. Plausible. Also missed Nature. | **A — wins decisively.** Surfaces **two Nature papers published today (2026-05-19)**: "A multi-agent system for automating scientific discovery" (Ghareeb/Chang/Rodriques, DOI 10.1038/s41586-026-10652-y) and "Accelerating scientific discovery with Co-Scientist" (10.1038/s41586-026-10644-y). Plus 3 strong arXiv preprints. The right answers were obvious — only Exa surfaced them. |

## Score Totals (out of 5)

| System | Wins (clear A) | Partial (A-/B) | Failures (F) | Net |
|--------|----------------|---------------|--------------|-----|
| Gemini 3.5 Flash `--search` | 3 (Q1, Q2, Q4) | 1 (Q5 obscure) | **2** (Q3 safety, Q5 missed headline) | 3 / 5 effective |
| Perplexity Sonar `_ask` | 2 (Q3, Q4) | 2 (Q1, Q5 unverified) | **1** (Q2 refusal) | 2 / 5 effective |
| Exa `web_search_exa` | 3 (Q1, Q4, Q5) | 2 (Q2 stale top, Q3 partial) | 0 | **4 / 5 effective** |

## Differential Strengths

**Gemini 3.5 Flash `--search` wins when:**
- Synthesis depth matters — Q1 fused statement + press conference + dissent vote into one answer
- Multi-fact lookup with internal structure — Q4 broke pricing into base/cache/write tiers automatically
- Recent versioned software where the model needs to crawl release notes and pick the latest — Q2

**Gemini 3.5 Flash `--search` loses when:**
- **Safety filter triggers** — Q3 LOEUF query was blocked outright. This is a basic gene-constraint lookup (constraint metrics are published, public, non-clinical). Failure mode is "Response blocked by safety filter: None" with no recoverable output. ~2 min wasted on a 0-byte response.
- Finding a single high-prominence paper among many — Q5 surfaced minor RSC papers and missed the Nature papers that were the obvious answer

**Perplexity Sonar `_ask` wins when:**
- Biomedical precise-number queries — Q3 returned exact LOEUF + URL where Gemini was blocked. Matches the prior N=5 finding (`~/.claude/rules/research-api-routing.md`).

**Perplexity Sonar `_ask` loses when:**
- Search-required queries it should easily handle — Q2 refusal is a hard failure for a tool advertised as web-grounded
- Specificity beats breadth — Q1 answer is correct but lacks the dissent-vote nuance Gemini extracted

**Exa `web_search_exa` wins when:**
- Finding the most prominent / canonical source — Q5 dominance was decisive; Nature papers published the same day were Exa's top results
- Returning raw primary documents — Q1 surfaced the Fed press release text itself
- Pricing/spec lookups where the agent will read further anyway — Q4

**Exa `web_search_exa` loses when:**
- Top-result freshness — Q2 surfaced 0.11.14 above 0.11.15; an agent that stops at result 1 would miss the latest
- One-shot answer needed without further reading — Q3 returns context, not the specific number

## Headline Finding — Gemini Safety Filter Risk

Gemini 3.5 Flash refused a routine biomedical query (gnomAD constraint metric for a public gene). `--search` does NOT bypass the safety filter, and the filter has no surfaced reason (`None`). This is a **disqualifying failure mode for biomedical use cases**:

- The query was: *"What is the gnomAD v4.1 LOEUF score for the human gene EBF3?"* — a vanilla, non-clinical, public-database lookup.
- 1m44s of compute spent before the filter killed the response.
- No way to retry within `--search` to recover.

For our biomedical workflows (phenome / genomics / EBF3-style variant analysis), **Perplexity Sonar or Exa should remain primary; Gemini `--search` cannot be trusted as a sole grounding path on gene/variant lookups until we measure the safety-filter false-positive rate.**

## Routing Recommendation (revised from probe)

| Query class | First choice | Why |
|-------------|--------------|-----|
| Recent macro event (Fed, news) | Gemini 3.5 Flash `--search` | Synthesis depth + dissent/nuance extraction |
| Versioned software state (latest release) | Gemini 3.5 Flash `--search` | Crawls release notes and picks newest correctly |
| Vendor pricing / spec page | Either Gemini `--search` or Exa | Tie; both surface canonical source |
| Biomedical lookup (gene, variant, drug) | **Perplexity Sonar `_ask`** | Gemini safety filter risk; Perplexity has prior N=5 win on biomedical numbers |
| Finding-a-source / paper discovery | **Exa `web_search_exa`** | Decisive win on Q5; surfaces canonical Nature/arXiv hits the answer engines miss |
| Synthesized factual Q&A (when biomedical-safe) | Gemini 3.5 Flash `--search` or Perplexity Sonar | Gemini if depth matters, Perplexity if cost matters |

## Caveats

- **N=5 is small.** Single-probe directional finding, not a statistical claim. Don't extrapolate the safety-filter result without a larger biomedical-query batch.
- **Q5 DOIs not independently verified** — Gemini's Masgent (10.1039/D6DD00043F) and Digital materials ecosystem (10.1039/D5SC09229A) look syntactically plausible but require dx.doi.org check. Perplexity's "From Prompt to Drug" has no DOI claim — only a press release.
- **Cost not measured.** Per-query cost was not tracked in this probe. Approximate from companion memo: Gemini ~$0.012/query, Perplexity Sonar ~$0.008-0.015/query, Exa ~$0.001-0.01/query.
- **Latency not measured uniformly.** Gemini calls took 30s-1m44s (Q3 ran to safety-filter timeout). Perplexity ~3-8s observed. Exa <1s. Not benchmark-quality.

## Reproduce

Raw output files (gitignored, ephemeral):
- `/tmp/search-probe-2026-05-19/queries.txt`
- `/tmp/search-probe-2026-05-19/gemini-Q{1..5}.md` (Q3 is 0 bytes — safety blocked)
- `/tmp/search-probe-2026-05-19/gemini-Q{1..5}.err`
- Perplexity and Exa outputs returned inline in session transcript.

## Open Follow-Ups

1. **Measure Gemini `--search` safety-filter rate on biomedical queries.** Send ~30 gene/variant/disease/drug lookups; count blocks. If >10%, downgrade Gemini `--search` for biomedical work formally in `llmx-routing.md`.
2. **Verify Q5 DOIs** with a `verify_claim` round before citing Masgent or Digital materials ecosystem.
3. **Establish per-query cost telemetry** for Gemini grounding — Google bills the grounding-retrieval call separately from model tokens; need to read Vertex/AI Studio invoice once a real workload runs.

<!-- knowledge-index
generated: 2026-05-19T21:04:29Z
hash: 4f837832c020

index:title: Head-to-Head Probe — Gemini 3.5 Flash --search vs Perplexity Sonar vs Exa
index:status: active
index:tags: benchmarks, gemini, search, exa, perplexity, llm-routing, probe

end-knowledge-index -->
