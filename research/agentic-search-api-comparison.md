# Agentic Search API Comparison — Brave, Exa, Tavily, Firecrawl, Perplexity Sonar, Parallel

**Date:** 2026-03-02
**Tier:** Deep
**Ground truth:** We use Exa extensively (MCP configured in all projects). Aware of Tavily/Brave/Perplexity from training data. Parallel Search was new to this research.

---

## 1. AIMultiple Benchmark (Feb 2026)

**Source:** https://aimultiple.com/agentic-search [C2 — trade press, plausible but single-source]

**Methodology:**
- 100 real-world queries sourced from "top 500 organic search queries in the AI/LLM domain"
- 5 results per query per API (~4,000 total results evaluated)
- 6 query categories: Research (24), Factual Verification (20), Technical Documentation (20), Real-time Events (10), Comparative (16), Tool Discovery (10)
- **LLM judge:** GPT-5.2 via OpenRouter, temperature=0
- Each result assessed for: relevance (boolean), quality (1-5 scale, 5 = authoritative), noise (boolean), source type
- **Agent Score = Mean Relevant x Quality**
- 10% of judgments (~400 results) manually reviewed to validate rating accuracy
- Hardware: Contabo VPS (France), Ubuntu 24.04.3, Python 3.11+

**Results:**

| Rank | API | Agent Score | Latency (median) |
|------|-----|------------|-------------------|
| 1 | **Brave Search** | 14.89 | 669 ms |
| 2 | **Firecrawl** | 14.58 | 1,335 ms |
| 3 | **Exa AI** | 14.39 | ~1,200 ms |
| 4 | **Parallel Search Pro** | 14.21 | 13,600 ms |
| 5 | **Tavily** | 13.67 | 998 ms |
| 6 | **Parallel Search Base** | 13.50 | ~2,900 ms |
| 7 | **Perplexity** | 12.96 | 11,000+ ms |
| 8 | **SerpAPI** | 12.28 | 2,400 ms |

Firecrawl's sub-score: Mean Relevant = 4.30, Quality = 3.39 (only API with both figures reported).

**Credibility assessment:**
- (+) 4,000 evaluated results is decent N
- (+) 10% human review of LLM judgments
- (+) Controlled for position bias with double evaluation
- (-) Single LLM judge (GPT-5.2) — known to have its own biases
- (-) Queries all from AI/LLM domain — not representative of general search
- (-) Latency measured from single VPS in France — not representative of global P50
- (-) Trade press (AIMultiple) — their business model is vendor comparison/referrals, so conflicts of interest are possible
- **Overall: [C2]** — useful directional data but don't treat exact scores as ground truth

---

## 2. Brave's Own Benchmark

**Source:** https://brave.com/blog/most-powerful-search-api-for-ai/ [D2 — self-interested source, but methodology is reasonably transparent]

**Methodology:**
- 1,500 real-world queries
- Benchmark conducted November 30, 2025
- **LLM judges:** Claude Opus 4.5 + Claude Sonnet 4.5, majority-vote system
- All pairwise comparisons evaluated twice to control for position bias
- Compared "Ask Brave" (Qwen3 open-weight model + Brave LLM Context API) against ChatGPT, Perplexity, Google AI Mode, Grok

**Results:**

| Model | Absolute Rating (1-5) | Win Rate | Loss Rate |
|-------|----------------------|----------|-----------|
| Grok | 4.71 | 59.87% | 10.05% |
| **Ask Brave** (Qwen3 + LLM Context) | 4.66 | 49.21% | 15.82% |
| Google AI Mode | 4.39 | 27.07% | 38.17% |
| ChatGPT | 4.32 | 23.87% | 42.22% |
| Perplexity | 4.01 | 10.51% | 64.26% |

**Key claim:** "Less powerful open-weights models can outperform closed frontier models if they incorporate high-quality grounding data."

**Credibility assessment:**
- (+) 1,500 queries is good N
- (+) Dual-judge majority vote with position bias control is reasonable methodology
- (+) They publish win/loss rates, not just overall scores
- (-) **Self-published benchmark** — vendor-run evals are inherently suspect
- (-) They're benchmarking the end-to-end answer quality (model + retrieval), not the search API alone. The claim is that their grounding data is the differentiator, but they don't ablate search quality from model quality
- (-) Grok beats them — they don't explain why (Grok likely uses Google/X data)
- (-) No independent replication
- (-) Claude as judge may have specific biases toward certain answer styles
- **Overall: [D2]** — interesting signal but cannot be taken at face value. The methodology is better than most vendor benchmarks, but the fundamental conflict of interest means you should weight this lightly.

---

## 3. Other Benchmarks Found

### Exa's SimpleQA Evaluation
**Source:** https://exa.ai/blog/evals-at-exa [D2 — vendor-published]

- Exa reports highest performance on SimpleQA (RAG grading — LLM answers questions using search results, graded against expected answers)
- Also tested on 5K in-the-wild queries, 10K MS MARCO queries, ~500 "Olympiad" hand-crafted queries
- Claims highest LLM-graded relevance scores across all three datasets
- **No specific competitor scores published** — just visual charts showing Exa ahead
- Their own page claims SimpleQA accuracy: Exa 89.77%, Google (SERP) 86.27%, Bing (deprecated) 85.41%, Brave 81.64%

### Exa's Vertical Search Benchmarks
**Source:** https://exa.ai (homepage) [D3 — vendor marketing, no methodology disclosed]

| Vertical | Exa | Parallel | Brave |
|----------|-----|----------|-------|
| Company Search (800 queries) | 62% | 37% | 36% |
| People Search (1,400 queries) | 63% | 30% | 27% |
| Code Search | 73% | — | 65% |

No methodology published for these. Accuracy definition unclear.

### You.com Benchmark
**Source:** https://you.com/resources/search-api-for-the-agentic-era [D2 — vendor-published]

- Tested on SimpleQA, FreshQA, MS MARCO
- You.com claims 77.84% accuracy on SimpleQA (95% CI: 76.60%-79.08%)
- P50 latency: 445ms
- Competitor-specific numbers not disclosed (just "higher/lower")

### Tavily's Benchmark Claims
**Source:** https://www.tavily.com/blog/how-we-built-the-fastest-web-search-in-the-world [D2 — vendor-published]

- Tested on SealQA-hard and SimpleQA
- Claims "fastest web search" with sub-second results
- Specific numbers are in charts (images), not in text — could not extract

**Meta-observation on benchmarks:** Every vendor publishes benchmarks where they win. None of these are truly independent. The AIMultiple benchmark is the closest to independent, and even it has vendor-referral incentives. There is no equivalent of LMSYS Chatbot Arena for search APIs. [INFERENCE]

---

## 4. Feature Matrix

| Feature | Brave | Exa | Tavily | Firecrawl | Perplexity Sonar | Parallel |
|---------|-------|-----|--------|-----------|-----------------|----------|
| **Semantic/neural search** | No (keyword + ranking) | Yes (embeddings-based, trained on link prediction) | Yes (AI-optimized ranking) | Unclear (likely keyword + reranking) | Yes (RAG pipeline) | Yes (AI-native, proprietary) |
| **Structured extraction** | No (returns JSON but no schema-matching) | **Yes** (deep search `outputSchema` with per-field grounding + confidence) | No (returns ranked snippets) | **Yes** (natural language -> JSON schema via /extract) | No | **Yes** (Task API with structured output) |
| **Deep/autonomous research** | No | **Yes** (Research endpoint, agentic multi-step) | **Yes** (Research API, mini + pro models) | **Yes** (/agent endpoint, multi-step) | **Yes** (Sonar Deep Research) | **Yes** (Task API, asynchronous, up to 2hr) |
| **Grounded answers** | **Yes** (Answers endpoint with citations) | **Yes** (Answer endpoint) | No (returns search results, not synthesized answers) | No | **Yes** (core product — synthesized + cited) | **Yes** (Chat API with citations) |
| **News search** | **Yes** (dedicated endpoint) | **Yes** (category filter) | **Yes** (topic="news") | **Yes** (news category) | **Yes** (real-time web) | Unclear |
| **Image search** | **Yes** (dedicated endpoint) | No | No | **Yes** (image search + screenshots) | No | No |
| **Academic/paper search** | No | **Yes** (category="research paper") | No | **Yes** (category filter for research) | **Yes** (indexes academic sources) | Unclear |
| **Company research** | No | **Yes** (company_research_exa endpoint) | No | No | Partial (via general query) | Partial (via Task API) |
| **Find similar** | No | **Yes** (find_similar endpoint — given URL, find related) | No | No | No | No |
| **Crawl specific URLs** | No | **Yes** (crawl endpoint) | **Yes** (/extract endpoint for URLs) | **Yes** (core feature — /scrape, /crawl) | No | **Yes** (Extract API) |
| **MCP server available** | **Yes** (official, also in Omnisearch) | **Yes** (official: mcp.exa.ai) | **Yes** (official, also in Omnisearch) | **Yes** (official, also in Omnisearch) | **Yes** (community: sergekostenchuk) | **Yes** (official: Search MCP + Task MCP) |

---

## 5. Pricing Comparison

Normalized to cost per 1,000 basic web searches (standard/default settings, 10 results per query).

| API | Cost per 1K searches | Free tier | Notes |
|-----|---------------------|-----------|-------|
| **Brave** | **$5.00** | $5/month credit (= 1,000 free searches/month) | Flat rate. Includes Web, LLM Context, Images, News, Video. Answers plan: $4/1K searches + $5/M tokens. |
| **Exa** | **$7.00** (neural) / **$15.00** (deep) | 1,000 requests/month free | Neural: $7/1K for 1-10 results. Deep: $15/1K (1-25 results), $75/1K (26-100). +$1 per additional result beyond 10. Contents: extra $1/1K pages. Answer: $5/1K. Research: usage-based (~$0.13/task typical: $5/1K searches + $5-10/1K pages + $5/1M reasoning tokens). |
| **Tavily** | **$8.00** (PAYG) / **$5.00-$7.50** (plans) | 1,000 credits/month free | 1 credit = 1 basic search. $0.008/credit PAYG. Plans: $30/4K credits ($7.50/1K) down to $500/100K credits ($5.00/1K). Advanced search = 2 credits. Research: 15-250 credits/request. |
| **Firecrawl** | **~$3.20** (Standard) / **$9.00** (Hobby) | 500 credits one-time | 2 credits per search (10 results). Hobby: 3K credits at $16/mo = ~$10.67/1K searches. Standard: 100K credits at $83/mo = ~$1.66/1K searches. Extra credits: $1.34/1K (Standard). |
| **Perplexity Sonar** | **$5.00** (search only) / **$1.00+/M tokens** (synthesis) | None for API | Raw search: $5/1K requests. Sonar (synthesized): $1/$1 per M tokens (input/output). Sonar Pro: $3/$15 per M tokens. Deep Research: $2/$8/M tokens + $5/1K searches. |
| **Parallel** | **$5.00** | 20,000 requests free | $5/1K searches (10 results). +$1/1K additional results. Extract: $1/1K URLs. Chat: $5-25/1K. Task: $5-150+/1K depending on processor. |

**Cheapest for pure search volume:** Firecrawl at Standard tier ($1.66/1K equivalent), but you're paying $83/month minimum. For PAYG, Brave at $5/1K with free monthly credit is the best value.

**Most expensive at scale:** Exa at $7/1K, though their free tier and startup grants ($1,000 credit) help with initial usage.

---

## 6. Latency Comparison

Best available data, compiled from AIMultiple benchmark + vendor claims:

| API | P50 / Typical Latency | Source |
|-----|----------------------|--------|
| **Brave** | ~669 ms (search), <600 ms p90 (LLM Context, vendor claim) | AIMultiple benchmark; Brave blog |
| **Exa** | ~1,200 ms (neural), 2-5s (deep), sub-200 ms (instant), 45-90s p50 (Research API) | AIMultiple; Exa pricing page; Exa docs |
| **Tavily** | ~998 ms (basic), 0.4-1.2s (vendor claim), sub-second for "fast" depth | AIMultiple; Tavily blog |
| **Firecrawl** | ~1,335 ms | AIMultiple |
| **Perplexity Sonar** | 11,000+ ms (includes synthesis), 1.52s TTFT (Artificial Analysis, token generation) | AIMultiple; artificialanalysis.ai |
| **Parallel** | 1-3s (Search), 5s-30min (Task), <5s (Chat) | Parallel docs |

**Note:** The AIMultiple latency numbers are from a single VPS in France — your mileage will vary by region. Perplexity's high latency is because it synthesizes an answer, not just returns links. Comparing raw search latency (Brave, Exa, Tavily) against answer-synthesis latency (Perplexity, Parallel Pro) is apples to oranges.

No p95/p99 data was found from any independent source. Exa claims 100-1,200ms range. Brave claims <600ms p90 for LLM Context.

---

## 7. Index Independence

This is the most important axis for triangulation. Two Google wrappers are not two independent sources.

| API | Own Index? | Details |
|-----|-----------|---------|
| **Brave** | **YES — fully independent** | 40 billion page index, built from own web crawler. One of only 3 independent Western web indexes (alongside Google and Bing). Bing API shut down Aug 2025. Brave explicitly markets this as key differentiator. [B2 — confirmed by multiple independent sources] |
| **Exa** | **YES — fully independent** | Built from scratch: distributed crawling/parsing, custom embedding + reranking models, custom vector database. Neural search trained on link prediction (predicting which URLs would be linked given a description). Not a Google/Bing wrapper. [B2] |
| **Parallel** | **YES — independent** | "Built on our proprietary web index" per their launch blog. Custom web crawler and index. Claims to be "AI-native" from the ground up. [D2 — vendor claim only, newer company, less external verification] |
| **Tavily** | **UNCLEAR / HYBRID** | Describes itself as having an "agent-native index" but does not explicitly claim to crawl the web independently. Uses "dynamic caching." The phrasing suggests they have some proprietary indexing/ranking but likely rely on upstream search providers for raw web coverage. Multiple third-party descriptions say Tavily provides "AI-optimized snippets" which suggests post-processing of results from another source. [F3 — cannot determine from available evidence] |
| **Firecrawl** | **NO — wrapper** | Firecrawl's core product is scraping/extraction, not search. Their /search endpoint performs a web search (likely via an upstream provider like Google/SerpAPI) and then scrapes the results. They do not claim an independent index anywhere. The SearchMCP comparison explicitly calls their search "an add-on to its core scraping." [C2] |
| **Perplexity Sonar** | **HYBRID** | Perplexity has its own web crawler/indexer for real-time content but also uses external search providers (historical reliance on Bing, which is now deprecated). Their Sonar models are built on Llama architectures with custom RAG pipelines. They index news sites, academic papers, and general web data. Degree of index independence vs. external provider reliance is unclear post-Bing shutdown. [C3] |

**For triangulation purposes:** Brave + Exa are the only two APIs you can confidently say provide independent search results from different indexes. Parallel is likely independent but newer/less verified. Tavily, Firecrawl, and Perplexity have varying degrees of dependency on upstream providers.

---

## 8. Overlap Analysis — Who's Differentiated vs. Commoditized

### Genuinely differentiated:

**Exa** — The only API with true semantic/neural search trained on link prediction. "Find similar" (given URL, find related) is unique. Company research and people search verticals have no equivalent elsewhere. Best for: discovery, RAG, research, finding non-obvious connections.

**Brave** — Only commercially available independent index (post-Bing shutdown, Google doesn't offer open API). Privacy/zero-data-retention is unique. Best for: baseline web search, independent source for triangulation, privacy-sensitive applications.

**Firecrawl** — Not really a search API. It's a scraping/extraction platform that added search. The /extract endpoint with natural-language-to-JSON-schema structured extraction is unique and powerful. /agent endpoint for multi-step browser automation is unique. Best for: content extraction, structured data from web pages, agent-driven browsing.

### Partially differentiated:

**Parallel** — Independent index + Task API for deep asynchronous research (up to 2 hours). Positioned between Exa (search) and Firecrawl (extraction). SOC2 certified. Best for: enterprise deep research, enrichment workflows, monitoring.

**Perplexity Sonar** — The answer-synthesis capability is well-developed (citations, multi-model). But as a raw search API, it's slow and expensive compared to alternatives. Best for: getting synthesized answers, not for feeding results into your own LLM.

### Commoditized / overlapping:

**Tavily** — Fills the same niche as Exa (search for AI agents) but with weaker differentiation. Main advantage: LangChain/LlamaIndex ecosystem integration (historical first-mover). Pricing is mid-range. Index independence is unclear. Recently acquired by Nebius (cloud infra company). The Research API (multi-step) puts it closer to Exa/Parallel territory. **Tavily vs. Exa is the key head-to-head** — Exa wins on semantic quality and unique features; Tavily wins on ecosystem integration and simplicity.

### If you already have Exa (which we do):

What Exa doesn't do well that others fill:
- **Brave:** Independent index for triangulation (different results than Exa)
- **Firecrawl:** Structured extraction from specific URLs (Exa's crawl is basic)
- **Perplexity Sonar:** Pre-synthesized answers with citations (saves LLM calls if you just need an answer)

What's redundant:
- **Tavily:** Largely overlaps with Exa for agentic search use cases
- **Parallel:** Overlaps with Exa's Research endpoint, though Task API's 2hr async is unique
- **SerpAPI/Serper:** Google wrappers, useful only if you specifically need Google SERP data

---

## 9. What's Uncertain

1. **Tavily's actual index independence** — They say "agent-native index" but never claim independent crawling. This matters for knowing whether Tavily + Exa gives you two independent views or two post-processed views of the same upstream.

2. **Firecrawl's upstream search provider** — Confirmed it's a wrapper, but which provider? Likely Google (via SerpAPI or direct), but not verified.

3. **Perplexity post-Bing** — Bing API deprecated Aug 2025. How much of Perplexity's retrieval now relies on their own index vs. other providers?

4. **Benchmark comparability** — Every benchmark uses different query sets, different evaluation criteria, different judges. The AIMultiple scores are NOT comparable to Exa's SimpleQA scores or Brave's pairwise win rates. There is no universal search quality benchmark.

5. **Latency at tail** — No p95/p99 data from any independent source. The AIMultiple medians are single-datacenter measurements.

6. **Parallel's index quality** — Newest entrant. Claims independent index but limited external verification. Their AIMultiple scores (14.21 Pro) are competitive but at much higher latency (13.6s).

---

## 10. Empirical Benchmark: Academic vs Websearch vs Combined (2026-03-03)

**Our own test.** Ran 3 Sonnet agents on the same genomics VUS question (EBF3 p.Pro263Leu clinical significance) with different tool restrictions. 15 turns each, $6.93 total. Comparison scored by a 4th Sonnet agent with PMID verification.

**Source:** `meta/benchmarks/comparison-report.md` (full report), `meta/benchmarks/output-*.md` (raw outputs), `meta/pipelines/research-api-benchmark.json` (orchestrator pipeline).

### Results

| Strategy | Tools | Score | Cost | Hallucinations |
|----------|-------|-------|------|----------------|
| Combined | S2 + PubMed + arXiv + Exa + Brave + Perplexity | 83/100 | $2.18 | 1 (wrong journal/page) |
| Academic | S2 + PubMed + arXiv + bioRxiv + Google Scholar | 80/100 | $1.29 | 0 |
| Websearch | Exa + Brave + Perplexity | 75/100 | $1.65 | 3 (PDB ID, 2 year errors) |

### What each strategy uniquely found

- **Websearch:** UniProt domain boundary (Pro263 = exact IPT/TIG N-terminus), domain clustering disconfirmation (all pathogenic EBF3 missense in DBD, none in IPT/TIG), mosaic carrier mother case
- **Academic:** Batie 2023 urological HADDS, EBF1 TIG dimerization interface 490 Å², zero citation errors
- **Combined:** Deisseroth 2022 fly rescue assay (functional spectrum data), PP3 inflation caveat, ZNF hotspot specificity, Zhu 2023 Chinese cohort

### Hallucination analysis

- Academic: zero factual errors. Imprecise domain boundaries (inferred from EBF1 homology instead of querying EBF3 UniProt) — methodological gap, not hallucination.
- Websearch: hallucinated PDB 3MUJ (doesn't correspond to cited paper), two year errors (online-2016 vs print-2017), self-contradiction on IPT/TIG pathogenic variants.
- Combined: "Harms et al. 2017 (Am J Hum Genet 100:117)" — real author, wrong journal/page. Harms is in Human Mutation (PMID 28736989). AJHG 100:117 is Chao et al.

### Key finding

Websearch's domain clustering finding — no documented pathogenic EBF3 missense in IPT/TIG domain — was the single strongest disconfirmatory evidence and was **missed by academic entirely**. Academic concluded "TIG is structurally significant" without checking domain-level pathogenic variant precedent. This is a protocol gap: domain importance ≠ domain clustering.

### Limitations

N=1 query, single model (Sonnet), single domain (genomics variant interpretation). Sonnet self-scored Sonnet with no ground truth oracle. Equal turns ≠ equal budget (academic needs 3 turns per paper vs 1 per websearch query). Combined had access to academic's saved corpus papers (shared research MCP).

---

## 11. Exa Deep Search & Research API (updated 2026-03-04)

Exa now offers two tiers of agentic search beyond basic neural/auto:

### Search endpoint: `type: "deep"` and `type: "deep-reasoning"`

Available on the same `/search` endpoint. Synchronous, returns inline.

**How it works:** Query expansion → parallel sub-searches → smart ranking → per-result summaries. The agent decomposes your query into multiple search variations automatically. You can also supply your own via `additionalQueries`.

**Key parameters:**
- `type: "deep"` — light deep search (auto query expansion + summaries)
- `type: "deep-reasoning"` — base deep search (adds reasoning step)
- `additionalQueries: [...]` — supply your own query variations (better than auto-expansion if you have domain knowledge)
- `outputSchema: {...}` — JSON Schema for structured output. Response includes `output.content` (structured JSON) + `output.grounding` (per-field citations + confidence)

**Structured output with grounding** is the killer feature. Example response shape:
```json
{
  "output": {
    "content": {"ceo": "Sam Altman", "title": "CEO"},
    "grounding": [
      {"field": "ceo", "citations": [{"url": "...", "title": "..."}], "confidence": "high"},
      {"field": "title", "citations": [...], "confidence": "high"}
    ]
  },
  "results": [...]
}
```

Each field gets independent confidence (low/medium/high) and source citations. This is what Firecrawl's `/extract` does but over search results instead of a single URL.

**Cost:** $0.015/request (1-25 results) vs $0.005 for neural. 3x premium but includes summaries + ranking that would otherwise require separate LLM calls.

**Latency:** ~2-5s typical (slower than neural ~1.2s, faster than Research API 45-180s).

**When to use deep search:**
- Entity enrichment with structured extraction (company details, people profiles, financial data)
- High-recall queries where auto query expansion beats single-query neural
- When you need per-result summaries without paying for separate summary calls
- When you can define a JSON schema for what you want — structured output + grounding is more reliable than post-hoc LLM extraction

**When NOT to use:**
- Simple factual lookups (use `type: "auto"` or `type: "instant"`)
- High-throughput batch queries where 3x cost matters
- When you need >100 results (same limit as neural)

### Research API: `/research/v1` (async)

Separate endpoint. Asynchronous — submit, get `researchId`, poll until complete.

**How it works:** Planning (LLM decomposes task) → Searching (multiple agent-driven search rounds) → Reasoning & synthesis (structured output or markdown report).

**Models:**
| Model | p50 | p90 | Page read cost |
|-------|-----|-----|----------------|
| `exa-research` (default) | 45s | 90s | $5/1K pages |
| `exa-research-pro` | 90s | 180s | $10/1K pages |

**Usage-based pricing:** $5/1K searches + $5-10/1K pages read + $5/1M reasoning tokens. Typical task ~$0.13.

**Key constraints:** ≤8 root fields in schema, ≤5 levels deep. Instructions <4096 chars.

**When to use Research API vs deep search:**
- Research API: multi-step investigation requiring iterative search refinement, questions where the agent needs to read full pages (not just snippets), complex synthesis across many sources
- Deep search: single-round structured extraction, entity enrichment, when you need results in <5s not 45-180s

### What this means for our tools

Our Exa MCP already exposes all of this:
- `web_search_advanced_exa` supports `type: "deep"` via the `type` parameter
- `deep_researcher_start` / `deep_researcher_check` = the Research API

**Routing guidance for orchestrator pipelines:**

| Task | Tool | Type |
|------|------|------|
| Quick fact lookup | `web_search_exa` | auto |
| Entity enrichment (company, person) | `web_search_advanced_exa` | deep + outputSchema |
| Literature discovery | papers-mcp (S2/PubMed) | — |
| Websearch for database pages (UniProt, gnomAD) | `web_search_advanced_exa` | deep |
| Deep autonomous research | `deep_researcher_start` | exa-research |
| Triangulation / independent source | Brave / Perplexity | — |

**For `additionalQueries`:** When an orchestrator task or researcher skill has domain context, generate 2-3 query variations and pass them via `additionalQueries` rather than relying on Exa's auto-expansion. Our domain knowledge (genomics, finance) will produce better variations than Exa's general-purpose LLM.

---

## 12. Recommendations for Our Setup

We currently use Exa as primary search. Based on this analysis:

1. **Add Brave as secondary/triangulation source.** Independent index, fastest latency, cheapest at scale. $5/1K with $5 free monthly credit. Different index than Exa = genuine triangulation. WebSearch (our built-in tool) likely uses Google or a similar provider, so Brave gives us a third independent perspective. **Empirical (§10):** Brave contributed to websearch strategy's unique findings (domain clustering).

2. **Keep Exa as primary for research.** Semantic search quality is genuinely differentiated. Company/people search verticals are unique. Research endpoint handles deep queries.

3. **Don't add Tavily.** Overlaps too much with Exa. Index independence is unclear. Acquisition by Nebius introduces platform risk.

4. **Consider Firecrawl only for structured extraction.** If we need to extract data from web pages into specific JSON schemas, Firecrawl is the tool. We don't need it for search.

5. **Perplexity as synthesis engine, not search.** `perplexity_ask` and `perplexity_reason` useful for one-call grounded answers (contributed to websearch strategy). `perplexity_research` for deep topic surveys. Not a search replacement — a synthesis layer on top of search.

6. **Watch Parallel.** Independent index, competitive quality, but newer. If they prove stable, they're a better Tavily alternative with clearer index independence.

7. **Websearch for database lookups, academic for literature (empirical, §10).** S2/PubMed are the wrong tool for querying UniProt, gnomAD, MaveDB, ClinVar — they return papers *about* databases, not the data. Exa/Brave/Perplexity reach the actual web databases. Conversely, websearch hallucinated PDB IDs and citation details at 3x the rate of academic tools. **Instruction-based routing in the researcher skill is sufficient** — don't build a multi-tier pipeline orchestrator for this.

8. **Use `type: "deep"` for entity enrichment and high-recall queries (added 2026-03-04).** Our MCP already supports it. Pass `outputSchema` for structured extraction with per-field grounding. Supply `additionalQueries` from domain context rather than relying on auto-expansion. Cost: $0.015/req vs $0.005 neural (3x). See §11 for full routing guidance.

9. **S2 API key (added 2026-03-03).** Semantic Scholar with API key gives dedicated 1 RPS (vs shared pool). 220M+ papers, structured metadata, citation graph. No date filtering — use Exa `web_search_advanced_exa` with `category: "research paper"` for recency. Key set via `S2_API_KEY` in `~/.env`, propagated through `.mcp.json` env blocks.

---

## Sources Saved

| Source | URL | Type |
|--------|-----|------|
| AIMultiple Agentic Search Benchmark | https://aimultiple.com/agentic-search | [C2] |
| Brave LLM Context API Launch | https://brave.com/blog/most-powerful-search-api-for-ai/ | [D2] |
| Brave Search API Growth | https://brave.com/blog/search-api-growth/ | [D2] |
| Firecrawl Best Web Search APIs | https://www.firecrawl.dev/blog/best-web-search-apis | [D2] |
| Exa Evaluations Blog | https://exa.ai/blog/evals-at-exa | [D2] |
| Exa Bing Migration Page | https://exa.ai/bing-api-deprecation | [D3] |
| Tavily 101 Blog | https://www.tavily.com/blog/tavily-101-ai-powered-search-for-developers | [D2] |
| Tavily Fastest Search Blog | https://www.tavily.com/blog/how-we-built-the-fastest-web-search-in-the-world | [D2] |
| Parallel Search Launch Blog | https://parallel.ai/blog/introducing-parallel-search | [D2] |
| Parallel Pricing Docs | https://docs.parallel.ai/getting-started/pricing | [D2] |
| You.com API Benchmark | https://you.com/resources/search-api-for-the-agentic-era | [D2] |
| Firecrawl vs Serper (SearchMCP) | https://searchmcp.io/blog/firecrawl-vs-serper-search-api | [C2] |
| Tavily Credits & Pricing Docs | https://docs.tavily.com/documentation/api-credits | [B2] |
| Artificial Analysis Sonar | https://artificialanalysis.ai/models/sonar/providers | [B2] |
| Exa Pricing | https://exa.ai/pricing | [B2] |
| Brave Search API | https://brave.com/search/api/ | [B2] |
| Firecrawl Pricing | https://www.firecrawl.dev/pricing | [B2] |

## Search Log

| # | Query/Action | Tool | Result |
|---|-------------|------|--------|
| 1 | AIMultiple agentic search page | WebFetch | Full benchmark table extracted |
| 2 | Brave LLM Context API benchmark | Exa | Found blog posts |
| 3 | Agentic search API comparison 2025-2026 | Exa Advanced | Found Firecrawl comparison article, multiple sources |
| 4 | Brave blog full content | WebFetch | Methodology + results extracted |
| 5 | Tavily pricing/features | Exa | Pricing docs + blog found |
| 6 | Firecrawl pricing/features | Exa | Third-party reviews + pricing |
| 7 | Perplexity Sonar pricing | Exa | Multiple pricing sources |
| 8 | Exa pricing page | WebFetch | Full pricing extracted |
| 9 | Parallel Search API | Exa | Pricing docs + launch blog |
| 10 | Brave index independence | Exa | Confirmed independent |
| 11 | Firecrawl best web search APIs | WebFetch | Feature matrix extracted |
| 12 | Exa index independence | Exa | Confirmed independent |
| 13 | Tavily index infrastructure | Exa | Unclear — "agent-native index" |
| 14 | Exa SimpleQA blog | Exa | Found eval methodology |
| 15 | You.com benchmark | WebFetch | Partial numbers extracted |
| 16 | Firecrawl search wrapper verification | verify_claim | Confirmed wrapper |
| 17 | MCP server availability | Exa | All 6 have MCP servers |
| 18 | Firecrawl upstream provider | Exa | Not definitively identified |
| 19 | Brave API pricing | WebFetch | Full pricing |
| 20 | Firecrawl pricing | WebFetch | Full credit breakdown |
| 21 | Perplexity Sonar latency | Exa | Artificial Analysis data |
