# Brave Search API — Deep Dive for Agent/LLM Integration

**Date:** 2026-03-02
**Tier:** Deep
**Ground truth:** We use Exa as primary search MCP. Existing comparison at `research/agentic-search-api-comparison.md` covers Brave vs 5 competitors. This memo goes deeper on Brave's API surface, LLM Context endpoint, MCP server, and unique capabilities.

---

## 1. Complete API Surface

Base URL: `https://api.search.brave.com`
Auth: `X-Subscription-Token` header with API key.

### Search Plan Endpoints ($5/1K requests, 50 QPS)

| Endpoint | Path | Method | What It Returns |
|----------|------|--------|-----------------|
| **Web Search** | `/res/v1/web/search` | GET | URLs, titles, descriptions, page age, metadata, schema-enriched results. Optional: extra alternate snippets, local results, knowledge graph, Goggles reranking. Up to 20 results per request. |
| **LLM Context** | `/res/v1/llm/context` | GET, POST | Pre-extracted page content (text chunks, tables, code blocks, structured data) — not links/snippets. Relevance-scored, token-budget-controlled. Designed for direct LLM consumption without scraping. |
| **Image Search** | `/res/v1/images/search` | GET | Image results with metadata, SafeSearch filtering. Up to 200 results per request. |
| **Video Search** | `/res/v1/videos/search` | GET | Video results with metadata, thumbnails. Up to 50 results per request. |
| **News Search** | `/res/v1/news/search` | GET | News articles from trusted sources. Up to 50 results per request. Default freshness: last 24 hours. |
| **Suggest/Autocomplete** | `/res/v1/suggest/search` | GET | Query autocompletion with entity recognition. Rich mode adds images and entity metadata. |
| **Spellcheck** | `/res/v1/spellcheck/search` | GET | Spelling corrections for queries. |
| **Summarizer** | `/res/v1/summarizer/search` | GET | AI summaries of search results. Sub-endpoints: `/summarizer/summary`, `/summarizer/summary_streaming`, `/summarizer/title`, `/summarizer/enrichments`, `/summarizer/followups`, `/summarizer/entity_info`. Two-step: first search with `summary=1`, then call summarizer with the returned key. |

[SOURCE: https://api-dashboard.search.brave.com/documentation, https://brave.com/api]

### Answers Plan Endpoints ($4/1K searches + $5/M tokens, 2 QPS)

| Endpoint | Path | Method | What It Returns |
|----------|------|--------|-----------------|
| **Answers (Chat Completions)** | `/res/v1/chat/completions` | POST | OpenAI SDK-compatible. Direct AI-generated answers with inline citations (XML-style tags). Streaming supported. Single-search or multi-search (research mode). |

The Answers endpoint is OpenAI SDK-compatible — you point the OpenAI client at `base_url="https://api.search.brave.com/res/v1"` and it works. [SOURCE: https://api-dashboard.search.brave.com/documentation/services/answers]

**Answers vs Summarizer:** Answers is the newer, more powerful service (OpenAI-compatible, streaming, citations). Summarizer is the older two-step approach (search first, then summarize). Brave recommends Answers for new integrations. [SOURCE: https://api-dashboard.search.brave.com/documentation/services/answers]

### Additional

| Endpoint | Path | What It Returns |
|----------|------|-----------------|
| **Place Search** | (not publicly documented in detail) | Location-based POI data for 200M+ locations. Integrated into LLM Context via `enable_local`. |

---

## 2. LLM Context API — The Key Differentiator

**Endpoint:** `GET/POST https://api.search.brave.com/res/v1/llm/context`
**Launched:** February 12, 2026
**Cost:** Part of Search plan ($5/1K requests)
**Powers:** 22 million answers/day internally in Brave Search (Ask Brave)

### How It Works (3-step pipeline)

1. **Standard web search** on Brave's independent 40B-page index
2. **Real-time HTML-to-smart-chunks conversion** — extracts clean text, JSON+LD schemas, tables, code blocks, forum discussions, YouTube captions from raw HTML
3. **Relevance ranking** via in-house trained system — ranks chunks by query relevance, compiles per user-configured token budget

### Parameters

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `q` | required | 1-400 chars, max 50 words | Search query |
| `count` | 20 | 1-50 | Number of results to consider |
| `maximum_number_of_urls` | 20 | 1-50 | Max URLs in response |
| `maximum_number_of_tokens` | 8192 | 1024-32768 | Total token budget |
| `maximum_number_of_tokens_per_url` | 4096 | 512-8192 | Per-URL token limit |
| `maximum_number_of_snippets` | 50 | 1-100 | Max snippets total |
| `maximum_number_of_snippets_per_url` | 50 | 1-100 | Max snippets per URL |
| `context_threshold_mode` | balanced | strict/balanced/lenient/disabled | Relevance filtering aggressiveness |
| `goggles` | none | URL or inline definition | Custom source reranking |
| `enable_local` | null (auto) | true/false/null | Location-aware POI results |
| `country` | us | 2-char code | Result country |
| `search_lang` | en | 2+ char code | Language preference |

### Response Schema

```json
{
  "grounding": {
    "generic": [
      {
        "url": "string",
        "title": "string",
        "snippets": ["string"]  // Pre-extracted content chunks
      }
    ],
    "poi": { ... },   // Point-of-interest data (when enable_local=true)
    "map": [ ... ]    // Map results (when enable_local=true)
  },
  "sources": {
    "url_key": {
      "title": "string",
      "hostname": "string",
      "age": ["date_string", "iso_date", "relative_time"]
    }
  }
}
```

### How It Differs from Regular Web Search

| Aspect | Web Search (`/web/search`) | LLM Context (`/llm/context`) |
|--------|---------------------------|------------------------------|
| **Returns** | URLs, titles, snippets (meta-description level) | Pre-extracted page content (full text chunks, tables, code) |
| **LLM readiness** | Need to fetch + parse each URL yourself | Ready-to-use content, no scraping needed |
| **Token control** | None (fixed snippet length) | Fine-grained: total budget, per-URL budget, snippet count |
| **Relevance filtering** | Traditional ranking | Configurable threshold modes (strict/balanced/lenient) |
| **Latency** | ~500ms | <600ms p90 (only ~130ms overhead over web search) |
| **Use case** | Traditional search results display | RAG pipelines, AI agents, chatbots |

**The key insight:** LLM Context replaces the search-then-scrape pattern. One API call gives you what would normally require: (1) web search, (2) fetch top N URLs, (3) parse HTML, (4) extract relevant text, (5) truncate to token budget. [SOURCE: https://api-dashboard.search.brave.com/documentation/services/llm-context]

### Token Budget Guidelines (from Brave docs)

| Task Type | Suggested `count` | Suggested `max_tokens` |
|-----------|--------------------|------------------------|
| Simple factual | 5 | 2048 |
| Standard queries | 20 | 8192 |
| Complex research | 50 | 16384 |

[SOURCE: https://api-dashboard.search.brave.com/documentation/services/llm-context]

---

## 3. Pricing (Post-Feb 12, 2026 Restructuring)

On Feb 12, 2026, Brave eliminated the free tier and moved to metered billing with monthly credits. [SOURCE: https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing]

### Current Plans

| Plan | Cost | Rate Limit | Free Credit | Includes |
|------|------|------------|-------------|----------|
| **Search** | $5 per 1,000 requests | **50 QPS** | $5/month (~1,000 free searches) | Web Search, LLM Context, Images, News, Video, Suggest, Spellcheck, Summarizer |
| **Answers** | $4 per 1,000 searches + $5 per 1M input/output tokens | **2 QPS** | $5/month | AI Answers with citations, streaming, OpenAI SDK compatible |
| **Spellcheck** | $5 per 10,000 requests | not specified | $5/month | Standalone spellcheck |
| **Autocomplete** | $5 per 10,000 requests | not specified | $5/month | Suggest with rich entity data |
| **Enterprise** | Custom pricing | Custom | N/A | Zero Data Retention, custom NDAs, invoicing, enterprise support |

**Total free credits: $5/month per plan, up to $20/month across all 4 plans.** Credit cards required (previously not for free tier). [SOURCE: https://brave.com/api, https://brave.com/blog/most-powerful-search-api-for-ai/]

### Cost Comparison with Exa (what we use)

| Scenario | Brave | Exa |
|----------|-------|-----|
| 1,000 basic web searches | $5.00 | $7.00 |
| 1,000 searches + content extraction | $5.00 (LLM Context includes content) | $7.00 + $1.00/1K for contents = $8.00 |
| 1,000 grounded answers | $4.00 + ~$0.50 tokens = $4.50 | $5.00 (/answer endpoint) |
| Free monthly allowance | 1,000 searches | 1,000 requests |

Brave is 28-40% cheaper than Exa for equivalent operations. The LLM Context API is particularly cost-effective because content extraction is included in the search price — no separate crawl/fetch step.

---

## 4. Rate Limits

| Endpoint Group | QPS Limit | Notes |
|----------------|-----------|-------|
| **Search Plan** (all search endpoints) | **50 QPS** | Shared across Web, LLM Context, Images, News, Video |
| **Answers Plan** | **2 QPS** | Separate from search quota |
| **Enterprise** | Custom | Negotiated |

**Comparison:**
- Exa: 10 QPS (/search), 100 QPS (/contents), 10 QPS (/answer), 15 concurrent (Research)
- Tavily: not publicly documented per-tier QPS
- Brave's 50 QPS for search is the highest among these APIs

[SOURCE: https://brave.com/api]

---

## 5. MCP Servers — Two Exist

### A. Official Brave MCP Server (recommended)

- **Package:** `@brave/brave-search-mcp-server`
- **Version:** v2.0.75 (as of 2026-02-26)
- **Repo:** https://github.com/brave/brave-search-mcp-server (699 stars, MIT license)
- **Author:** Brave Software, Inc.
- **Downloads:** 14.3K weekly
- **Transport:** STDIO (default since v2.x) or HTTP (`--transport http`)

**Tools exposed (6):**

| Tool | What It Does |
|------|-------------|
| `brave_web_search` | Web search with pagination, filtering, freshness, SafeSearch. Up to 20 results. |
| `brave_local_search` | Location-based business/place discovery. Falls back to web if no local results. |
| `brave_image_search` | Image discovery. Up to 200 results. SafeSearch defaults to strict. |
| `brave_video_search` | Video discovery with metadata/thumbnails. Up to 50 results. |
| `brave_news_search` | Current news. Freshness defaults to last 24 hours. Up to 50 results. |
| `brave_summarizer` | AI summary from web results. Requires `summary: true` on a prior web search to get a summary key. |

**Notable: NO `brave_llm_context` tool.** The official MCP server does not yet expose the LLM Context API (launched Feb 12, 2026 — the MCP server may not have been updated yet). This is a significant gap. The OpenClaw issue #14992 requests exactly this. [SOURCE: https://github.com/brave/brave-search-mcp-server, https://github.com/openclaw/openclaw/issues/14992]

**Config env vars:**
- `BRAVE_API_KEY` (required)
- `BRAVE_MCP_TRANSPORT` — "stdio" (default) or "http"
- `BRAVE_MCP_PORT` — HTTP port (default 8000)
- `BRAVE_MCP_ENABLED_TOOLS` — whitelist specific tools
- `BRAVE_MCP_DISABLED_TOOLS` — blacklist specific tools
- `BRAVE_MCP_STATELESS` — HTTP stateless mode (required for Amazon Bedrock)

**Install:**
```bash
npx -y @brave/brave-search-mcp-server --transport stdio
```

### B. Anthropic Reference MCP Server (legacy)

- **Package:** `@modelcontextprotocol/server-brave-search`
- **Version:** v0.6.2 (last published Dec 2024)
- **Author:** Anthropic, PBC
- **Tools:** Only 2 — `brave_web_search` and `brave_local_search`
- **Status:** Superseded by Brave's official server. Simpler, fewer features.

**Use the official `@brave/brave-search-mcp-server`.** The Anthropic reference implementation is minimal and hasn't been updated since Dec 2024.

---

## 6. Benchmark Results

### AIMultiple Agentic Search Benchmark (Feb 2026) [C2]

100 real-world AI/LLM queries, 5 results per query, GPT-5.2 as LLM judge, 10% human verification, bootstrap CI.

| Rank | API | Agent Score | Quality (1-5) | Mean Relevant (/5) | Median Latency |
|------|-----|------------|---------------|---------------------|----------------|
| 1 | **Brave Search** | **14.89** | 3.63 | 4.10 | 669 ms |
| 2 | Firecrawl | 14.58 | 3.39 | 4.30 | 1,335 ms |
| 3 | Exa AI | 14.39 | ~3.6 | ~4.0 | ~1,200 ms |
| 4 | Parallel Search Pro | 14.21 | ~3.55 | ~4.0 | 13,600 ms |
| 5 | Tavily | 13.67 | ~3.5 | ~3.9 | 998 ms |
| 6 | Parallel Search Base | 13.50 | ~3.5 | ~3.85 | ~2,900 ms |
| 7 | Perplexity | 12.96 | ~3.5 | ~3.7 | 11,000+ ms |
| 8 | SerpAPI | 12.28 | ~3.5 | ~3.5 | 2,400 ms |

**Agent Score = Mean Relevant x Quality.** Brave wins on both speed (669ms, fastest by 2x) and score. BUT: top 4 APIs are "statistically indistinguishable" per bootstrap CI. The meaningful gap is between the top 4 cluster and Tavily/below.

**Methodology caveats:**
- All 100 queries are AI/LLM domain — not representative of general search
- Single VPS in France — latency not representative of global distribution
- GPT-5.2 as sole LLM judge — model-specific biases
- AIMultiple is a vendor comparison/referral site — potential COI

[SOURCE: https://aimultiple.com/agentic-search]

### Brave's Own Benchmark (Nov 2025) [D2]

1,500 queries, Claude Opus 4.5 + Sonnet 4.5 as dual judges, pairwise comparisons.

| System | Rating (1-5) | Win Rate | Loss Rate |
|--------|-------------|----------|-----------|
| Grok | 4.71 | 59.87% | 10.05% |
| Ask Brave (Qwen3 + LLM Context) | 4.66 | 49.21% | 15.82% |
| Google AI Mode | 4.39 | 27.07% | 38.17% |
| ChatGPT | 4.32 | 23.87% | 42.22% |
| Perplexity | 4.01 | 10.51% | 64.26% |

Key claim: open-weight Qwen3 + Brave LLM Context data beats ChatGPT and Google. [D2 — self-published, but methodology is more transparent than most vendor benchmarks]

### SimpleQA F1 Scores

| API/System | SimpleQA F1 | Source |
|------------|------------|--------|
| Brave AI Grounding (multi-search) | 94.1% | Brave blog [D2] (verified via Exa /answer) |
| Brave AI Grounding (single-search) | 92.1% | Brave blog [D2] |
| Exa (self-reported) | 89.77% | Exa blog [D2] |
| Google SERP (Exa-reported) | 86.27% | Exa blog [D2] |
| Brave (Exa-reported) | 81.64% | Exa blog [D2] |

Note the discrepancy: Brave self-reports 94.1% on SimpleQA; Exa reports Brave at 81.64%. The difference is likely that Brave's 94.1% includes their AI reasoning layer (Answers endpoint), while Exa's measurement is of raw search results quality. These are measuring different things.

---

## 7. Unique Capabilities — What Brave Does That Others Can't

### 7a. Independent Web Index

Brave owns one of only 3 independent Western web indexes (with Google and Bing). After Bing's API shutdown in Aug 2025 and Google's action against SerpAPI, Brave is the only commercially available independent index via open API.

**Why this matters for agents:** If your agent uses Exa + Google (via WebSearch) as sources, adding Brave gives you a genuinely independent third perspective. Three different indexes means actual triangulation, not three views of the same upstream. [B2 — confirmed by multiple sources]

### 7b. Goggles (Custom Search Reranking)

Brave Goggles let you programmatically control which domains get boosted or suppressed in search results. You can:
- Create custom reranking rules (boost domain X, suppress domain Y)
- Apply community-created Goggles (e.g., "no Pinterest", "academic only")
- Use Goggles with LLM Context to control which sources ground your LLM

No other search API offers this level of result-set customization. Exa has domain inclusion/exclusion filters, but Goggles go further with weighted boosting and community-shared configurations. [SOURCE: https://search.brave.com/help/rerank]

### 7c. LLM Context's Single-Call Content Extraction

LLM Context replaces the search-then-fetch-then-parse pipeline with one API call. Exa requires separate `/search` + `/contents` calls (or `includeText` parameter which increases cost). Tavily includes content snippets but not full page extraction. Brave extracts tables, code blocks, JSON+LD, and forum discussions — not just text. [SOURCE: https://api-dashboard.search.brave.com/documentation/services/llm-context]

### 7d. OpenAI SDK Compatibility (Answers)

The Answers endpoint at `/res/v1/chat/completions` is a drop-in replacement for OpenAI's API. Change `base_url` and `api_key`, and existing OpenAI SDK code works. No other search API offers this level of SDK compatibility for grounded answers. [SOURCE: https://api-dashboard.search.brave.com/documentation/services/answers]

### 7e. Privacy / Zero Data Retention

Brave is the only search API that offers full-funnel Zero Data Retention (Enterprise plan). For privacy-sensitive applications (healthcare, legal, financial), this is a differentiator. Exa, Tavily, and others do not make comparable privacy guarantees. [SOURCE: https://brave.com/api]

### 7f. Speed

669ms median in AIMultiple benchmark — fastest by 2x over next competitor (Tavily at 998ms). LLM Context adds only ~130ms overhead over web search. For agent tool calls where latency compounds across steps, this matters. [SOURCE: https://aimultiple.com/agentic-search, https://brave.com/blog/most-powerful-search-api-for-ai/]

---

## 8. What Brave CANNOT Do That Exa/Tavily Can

| Capability | Brave | Exa | Tavily |
|-----------|-------|-----|--------|
| **Semantic/neural search** | No (keyword + ranking) | Yes (embedding-based, trained on link prediction) | Yes (AI-optimized ranking) |
| **Find similar URLs** | No | Yes (`find_similar` endpoint) | No |
| **Company research** | No | Yes (dedicated endpoint) | No |
| **People search** | No | Yes (dedicated endpoint) | No |
| **Category filtering** | Via Goggles (manual) | Built-in (research paper, company, news, github, tweet, etc.) | Via `topic` parameter |
| **Date filtering** | Via `freshness` parameter | Via `startPublishedDate`/`endPublishedDate` (ISO 8601) | Via `days` parameter |
| **Deep research (multi-step)** | No (single-search only) | Yes (Research endpoint, agentic) | Yes (Research API, mini + pro) |
| **Crawl specific URLs** | No | Yes (`crawling_exa`) | Yes (`/extract`) |

**The gap:** Brave is a traditional search engine with AI bolted on top. Exa is an AI-native search engine built from scratch for LLM consumption. For discovery, semantic queries, and research workflows, Exa remains superior. Brave's strengths are index independence, speed, content extraction (LLM Context), and cost.

---

## 9. Recommendations for Our Setup

We currently use Exa as primary search (MCP configured in all projects).

**Action: Add Brave LLM Context as secondary search tool.** Rationale:
1. **Triangulation** — independent index gives genuinely different results than Exa
2. **Cost** — $5/1K vs Exa's $7-8/1K for search + content
3. **Speed** — 669ms vs Exa's ~1,200ms
4. **LLM Context** eliminates the search-then-fetch pattern for grounding

**Implementation options:**
1. **Direct API call** via a simple Python wrapper — the LLM Context API is a single GET/POST request
2. **Official MCP server** (`@brave/brave-search-mcp-server`) — BUT it doesn't expose LLM Context yet. The `brave_web_search` tool returns standard search results, not pre-extracted content.
3. **Custom MCP tool** wrapping the LLM Context endpoint — most useful option until Brave's MCP server adds it
4. **WebSearch tool** — our built-in WebSearch may already use a search provider; adding Brave gives an independent alternative

**Caveat:** The MCP server gap is a blocker for out-of-box LLM Context integration. Either wait for Brave to add it (they ship ~weekly: 87 releases, v2.0.75 as of Feb 26) or build a thin wrapper.

---

## 10. What's Uncertain

1. **LLM Context quality vs Exa contents** — No independent head-to-head of extracted content quality. Brave's benchmark compares end-to-end answer quality (model + retrieval), not extraction quality alone.

2. **Goggles effectiveness for agent use** — Goggles are powerful but designed for human search customization. Unclear how well agent-authored Goggles would work vs Exa's category filters.

3. **Answers endpoint cost at scale** — $4/1K searches + $5/M tokens. For complex multi-search queries, token costs could add up unpredictably. No published cost-per-answer benchmarks.

4. **MCP server LLM Context timeline** — The OpenClaw issue (#14992) was filed Feb 12, same day as launch. No official response from Brave on timeline.

5. **SimpleQA discrepancy** — Brave self-reports 94.1%, Exa reports Brave at 81.64%. The difference is likely raw search vs full pipeline, but neither vendor explains the gap.

---

## Sources

| Source | URL | Grade |
|--------|-----|-------|
| Brave API pricing page | https://brave.com/api | [B2] |
| Brave LLM Context docs | https://api-dashboard.search.brave.com/documentation/services/llm-context | [B2] |
| Brave Answers docs | https://api-dashboard.search.brave.com/documentation/services/answers | [B2] |
| Brave API launch blog | https://brave.com/blog/most-powerful-search-api-for-ai/ | [D2] |
| Brave AI Grounding blog | https://brave.com/blog/ai-grounding/ | [D2] |
| Brave API growth blog | https://brave.com/blog/search-api-growth/ | [D2] |
| Brave MCP server (GitHub) | https://github.com/brave/brave-search-mcp-server | [B2] |
| Brave MCP server (npm) | https://npmjs.com/package/@brave/brave-search-mcp-server | [B2] |
| Anthropic MCP server (npm) | https://www.npmjs.com/package/@modelcontextprotocol/server-brave-search | [B2] |
| AIMultiple benchmark | https://aimultiple.com/agentic-search | [C2] |
| Brave free tier removal | https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing | [C2] |
| Data4AI Brave vs Tavily | https://data4ai.com/blog/vendors-comparison/brave-vs-tavily/ | [C2] |
| Firecrawl Best APIs 2026 | https://www.firecrawl.dev/blog/best-web-search-apis | [D2] |
| OpenClaw LLM Context issue | https://github.com/openclaw/openclaw/issues/14992 | [B2] |
| OpenClaw free tier issue | https://github.com/openclaw/openclaw/issues/16629 | [B2] |
| Brave SimpleQA 94.1% F1 | Verified via Exa /answer | [B1] |

## Search Log

| # | Query/Action | Tool | Result |
|---|-------------|------|--------|
| 1 | Brave Search API docs endpoints LLM Context 2025 | Exa web_search | Found blog + docs + OpenClaw issue |
| 2 | Brave API documentation page | WebFetch | 403 (dashboard requires auth) |
| 3 | Brave launch blog full content | WebFetch | Full methodology + benchmark extracted |
| 4 | LLM Context API docs | WebFetch | Complete params + response schema |
| 5 | AI Grounding blog | WebFetch | SimpleQA 94.1%, single vs multi-search details |
| 6 | Brave pricing + rate limits | Exa web_search | Found pricing page + free tier removal news |
| 7 | Brave MCP server | Exa web_search | Found official + Anthropic packages |
| 8 | Brave MCP server README | WebFetch (GitHub) | Full tool inventory + config |
| 9 | AIMultiple benchmark details | WebFetch | Full table + methodology |
| 10 | Data4AI Brave vs Tavily | WebFetch | Feature comparison (pre-LLM Context) |
| 11 | Brave API pricing page | WebFetch | Confirmed $5/1K, 50 QPS |
| 12 | Firecrawl best APIs 2026 | WebFetch | Feature matrix, Brave characterization |
| 13 | Brave endpoint paths code context | Exa get_code_context | All endpoint paths confirmed |
| 14 | Brave Goggles + Answers details | Exa web_search | Goggles reranking, Answers OpenAI compat |
| 15 | Grounding API docs | WebFetch | Confirmed = Answers endpoint, not separate |
| 16 | Anthropic MCP server details | Exa crawling | v0.6.2, 2 tools only, last updated Dec 2024 |
| 17 | SimpleQA 94.1% verification | verify_claim | Confirmed by 6+ sources |

<!-- knowledge-index
generated: 2026-03-22T00:13:50Z
hash: e35c6016662d

cross_refs: research/agentic-search-api-comparison.md
sources: 2
  D2: — self-published, but methodology is more transparent than most vendor benchmarks
  B2: — confirmed by multiple sources

end-knowledge-index -->
