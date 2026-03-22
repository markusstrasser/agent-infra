# Search API Integration Landscape — Brave, Firecrawl, Perplexity

**Date:** 2026-03-02
**Purpose:** Full inventory of capabilities across new search APIs, mapped to project needs. Companion to individual deep dives (brave-search-api-deep-dive.md, firecrawl-api-deep-dive.md, perplexity-sonar-api-landscape.md, agentic-search-api-comparison.md).

---

## Configuration

All three APIs configured as of 2026-03-02:
- **Brave** → user scope (global, all projects). MCP: `@brave/brave-search-mcp-server`. 6 tools.
- **Perplexity** → user scope (global, all projects). MCP: `@perplexity-ai/mcp-server`. 4 tools.
- **Firecrawl** → intel only. MCP: `firecrawl-mcp`. 14 tools.
- **Exa** → user scope (global, migrated from per-project duplication). 8+ tools.
- **Shared MCPs also migrated to user scope:** research, meta-knowledge, paper-search, context7.

---

## Full API Service Inventory

### Brave Search (6 MCP tools + 2 API-only)

| Service | MCP tool? | What it does | Best for |
|---------|-----------|-------------|----------|
| **Web Search** | `brave_web_search` | Standard search, 20 results, Goggles reranking | Fallback/triangulation |
| **LLM Context** | **NO** (gap) | Pre-extracted page content (text, tables, code, JSON+LD). Token-budget controlled. One call replaces search→fetch→parse. | RAG grounding — needs custom wrapper |
| **News Search** | `brave_news_search` | Dedicated news, default last 24h, 50 results | Intel news monitoring |
| **Image Search** | `brave_image_search` | Up to 200 images | Low priority |
| **Video Search** | `brave_video_search` | Video metadata + thumbnails | Low priority |
| **Summarizer** | `brave_summarizer` | AI summary of search results (two-step, older) | Superseded by Answers |
| **Answers** | **NO** (API only) | OpenAI SDK-compatible grounded answers with citations. 94.1% SimpleQA F1. | SAFE-lite triangulation, quick verification |
| **Goggles** | Via params on web_search | Custom source reranking (boost/suppress domains) | Domain-specific research |
| **Local/Place** | `brave_local_search` | 200M+ POI locations | Not relevant |

**Key gap:** LLM Context and Answers — the two most interesting Brave services — are NOT in the MCP server.

**Pricing:** $5/1K searches (Search plan), $4/1K + $5/M tokens (Answers). $5/mo free credit. 50 QPS.

### Firecrawl (14 MCP tools)

| Service | MCP tool | What it does | Best for |
|---------|----------|-------------|----------|
| **Scrape** | `firecrawl_scrape` | URL → markdown/JSON/HTML/screenshot. JS rendering, browser actions, anti-bot. | JS-heavy financial sites |
| **Scrape + JSON** | `firecrawl_scrape` (format=json) | Structured extraction with JSON Schema from single page | Parse earnings pages, company profiles |
| **Crawl** | `firecrawl_crawl` | Recursive async site crawl with depth/limit | Crawl investor relations, filing indexes |
| **Map** | `firecrawl_map` | Fast URL discovery from sitemap + SERP | Discover all pages on a company site |
| **Search** | `firecrawl_search` | Google-wrapper search + optional scraping | Redundant (Brave/Exa better) |
| **Extract** | `firecrawl_extract` | LLM extraction across URLs/wildcards with JSON Schema | **Intel killer feature**: SEC filings → structured data |
| **Agent** | `firecrawl_agent` | Autonomous research agent (Spark-1 models) | Alternative deep researcher for extraction |
| **Browser** | `firecrawl_browser_*` | Persistent cloud browser sessions | Automate dynamic financial sites |
| **Change Tracking** | Via scrape params | Git-diff on page changes | Monitor company pages for material changes |
| **Branding** | Via scrape format | Design system extraction | Not relevant |

**Pricing:** Credit-based. Free: 500 one-time. Standard: $83/mo for 100K credits (1 credit = 1 scrape, 2 = search). Agent: 5 free daily runs.

### Perplexity (4 MCP tools + Agent API)

| Service | MCP tool | What it does | Best for |
|---------|----------|-------------|----------|
| **Search** | `perplexity_search` | Raw ranked web results, no LLM, $5/1K | Third search source |
| **Ask (Sonar)** | `perplexity_ask` | Grounded LLM answer with citations via sonar-pro | Quick factual lookups ("What was X's Q3 revenue?") |
| **Research** | `perplexity_research` | Deep multi-search research via sonar-deep-research | Comprehensive reports |
| **Reason** | `perplexity_reason` | Chain-of-thought reasoning + search via sonar-reasoning-pro | Complex analysis ("Why did X drop 15%?") |
| **Agent API** | Not in MCP | Multi-provider gateway (GPT-5.2, Claude, Gemini) + web_search. No markup. Fallback chains. | Potential llmx complement |
| **Embeddings** | Not in MCP | Standard + contextualized embeddings | We have our own pipeline |

**Pricing:** Search: $5/1K. Sonar: $1/$1 per M tokens + $5-6/1K search fee. Deep Research: $2/$8/M tokens. Agent API: provider pricing, no markup.

---

## Genuinely New Capabilities (vs Exa alone)

| Capability | Status before | New source | Impact |
|-----------|--------------|-----------|--------|
| Independent index triangulation | Exa + WebSearch (same Google upstream?) | **Brave** (confirmed independent, 40B pages) | Real triangulation for verification |
| Content in search call | Exa needs /search + /contents | **Brave LLM Context** (one call, token-budgeted) | Fewer API calls, lower latency |
| Structured extraction | None | **Firecrawl Extract** (JSON Schema → structured data) | Parse financial filings at scale |
| Browser automation | None | **Firecrawl Browser** (persistent sessions) | Navigate JS-heavy sites |
| Recursive crawling | None | **Firecrawl Crawl** (async, depth/limit) | Ingest entire site sections |
| URL discovery | None | **Firecrawl Map** (sitemap + SERP enum) | Find all pages before crawling |
| Reasoning with search | None | **Perplexity Reason** (CoT + grounded search) | Complex analytical queries |
| Quick grounded answers | Exa /answer (structured verdict) | **Perplexity Ask** (conversational), **Brave Answers** (94.1% F1) | Multiple verification sources |
| Change monitoring | None | **Firecrawl Change Tracking** (git-diff) | Material change detection |
| Multi-provider + search | llmx (no search integration) | **Perplexity Agent API** | Cross-model with grounding |
| Dedicated news search | Exa category filter | **Brave News** (dedicated endpoint, 24h default) | Faster news monitoring |
| Custom source reranking | Exa domain include/exclude | **Brave Goggles** (weighted boost/suppress) | Domain-specific research profiles |

---

## Project Needs Matrix

| Capability | Meta | Intel | Selve | Genomics |
|-----------|------|-------|-------|----------|
| Search triangulation | Medium (SAFE-lite) | High (cross-source verification) | Low | Low |
| Grounded answers | Medium (claim verification) | High (quick factual lookups) | Low | Low |
| Structured extraction | Low | **Critical** (filings, earnings) | Low | Low |
| Browser automation | Low | High (JS financial sites) | Low | Low |
| News monitoring | Low | **Critical** (event-driven research) | Low | Low |
| Deep research | High (agent infra research) | High (company deep dives) | Medium (topic research) | Medium (variant literature) |
| Reasoning with search | Medium | High (thesis analysis) | Low | Low |
| Change tracking | Low | High (material change detection) | Low | Low |
| Recursive crawling | Low | High (IR sections, filing indexes) | Low | Low |

---

## Index Independence (for triangulation)

| Source | Own index? | Confidence |
|--------|-----------|------------|
| **Exa** | Yes (neural, trained on link prediction) | [B2] |
| **Brave** | Yes (40B pages, independent crawler) | [B2] |
| **WebSearch** (built-in) | Likely Google | [C3] |
| **Perplexity** | Hybrid (own crawler + unclear upstream post-Bing) | [C3] |
| **Firecrawl** | No (Google wrapper for /search) | [C2] |

**For real triangulation:** Exa + Brave are the only confirmed-independent pair. Adding Perplexity gives a possible third but with less confidence in independence.

---

## MCP Server Gaps

| API | Key feature NOT in MCP | Workaround |
|-----|----------------------|------------|
| **Brave** | LLM Context (pre-extracted content) | Custom Python MCP wrapper or direct API call |
| **Brave** | Answers (grounded answers with citations) | OpenAI SDK call (compatible endpoint) |
| **Perplexity** | Agent API (multi-provider + search) | Direct SDK call (`pip install perplexityai`) |
| **Perplexity** | Embeddings | Direct API call (low priority) |
| **Firecrawl** | All features exposed | No gaps |

---

## Sources

- `research/brave-search-api-deep-dive.md` — full Brave API surface
- `research/firecrawl-api-deep-dive.md` — full Firecrawl API surface
- `research/perplexity-sonar-api-landscape.md` — full Perplexity API surface
- `research/agentic-search-api-comparison.md` — benchmarks, pricing, feature matrix, index independence

<!-- knowledge-index
generated: 2026-03-22T00:13:52Z
hash: 1eef3418617d

cross_refs: research/agentic-search-api-comparison.md, research/brave-search-api-deep-dive.md, research/firecrawl-api-deep-dive.md, research/perplexity-sonar-api-landscape.md
table_claims: 7

end-knowledge-index -->
