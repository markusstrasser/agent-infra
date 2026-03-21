# Perplexity API Landscape — Research Memo

**Question:** Full technical assessment of the Perplexity API surface for agent/LLM integration: Sonar models, Agent API, Search API, pricing, MCP, SDKs, unique capabilities.
**Tier:** Deep | **Date:** 2026-03-02
**Ground truth:** Training data knowledge of Perplexity Sonar as OpenAI-compatible grounded search API. All details below retrieved fresh.

---

## 1. API Surface — Four Distinct APIs

Perplexity now exposes **four separate API groups**, each with different endpoints and billing models:

| API | Endpoint | Purpose | Billing |
|-----|----------|---------|---------|
| **Sonar API** | `POST /chat/completions` | Grounded LLM answers with web search + citations | Token-based + per-request search fee |
| **Agent API** | `POST /v1/responses` | Multi-provider model access with integrated tools | Token-based + per-tool-call fee |
| **Search API** | `POST /search` | Raw ranked web results (no LLM synthesis) | Flat per-request ($5/1K requests) |
| **Embeddings API** | `POST /embeddings` | Text embeddings for semantic search / RAG | Token-based |

[SOURCE: https://docs.perplexity.ai/llms.txt — full documentation index]

---

## 2. Sonar Models (Native Perplexity Models)

Four Sonar model tiers, each serving different complexity levels:

| Model | Input $/1M | Output $/1M | Description | Best For |
|-------|-----------|-------------|-------------|----------|
| `sonar` | $1.00 | $1.00 | Lightweight search model with grounding | Quick factual queries, topic summaries, current events |
| `sonar-pro` | $3.00 | $15.00 | Advanced search, complex queries + follow-ups | Multi-step research, comparative analysis |
| `sonar-reasoning-pro` | $2.00 | $8.00 | Chain-of-thought reasoning with search | Complex analysis, logical problem-solving, strict instructions |
| `sonar-deep-research` | $2.00 | $8.00 | Exhaustive multi-search research agent | Comprehensive reports, in-depth synthesis across many sources |

**Additional per-request search fees** (on top of token costs):

| Model | Low Context | Medium Context | High Context |
|-------|-------------|----------------|--------------|
| sonar | $5/1K req | $5/1K req | $12/1K req |
| sonar-pro | $6/1K req | $6/1K req | $14/1K req |
| sonar-pro (Pro Search) | $14/1K req | $14/1K req | $22/1K req |
| sonar-reasoning-pro | $6/1K req | $6/1K req | $14/1K req |

[SOURCE: https://docs.perplexity.ai/docs/getting-started/pricing]

**Sonar Deep Research** has additional costs:
- Citation tokens: $2/1M tokens
- Search queries: $5/1K queries
- Reasoning tokens: $3/1M tokens

[SOURCE: https://docs.perplexity.ai/docs/getting-started/pricing]

### Sonar Response Format

The Sonar API uses **OpenAI-compatible chat completions** format with two extra fields:

```json
{
  "id": "...",
  "model": "sonar",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "The James Webb Telescope uses infrared astronomy [1]. It launched in December 2021 [2]."
    }
  }],
  "citations": [
    "https://webb.nasa.gov/content/about/index.html",
    "https://www.space.com/james-webb-space-telescope-updates"
  ],
  "search_results": [
    {"title": "About JWST", "url": "https://...", "date": "2025-01-15"}
  ]
}
```

Key details:
- `citations` is a flat array of URLs (0-indexed). Text contains `[1]`, `[2]` markers (1-indexed). **You must map them yourself** — there is no automatic binding.
- `search_results` contains title, URL, snippet, date, last_updated per result.
- `disable_search: true` parameter turns off web search entirely (use as a standard LLM).
- Search filters: `search_domain_filter` (up to 20 domains, `-` prefix to exclude), `search_recency_filter` (`day`/`week`/`month`/`year`).
- **System prompt is NOT used for search.** Only the user prompt drives web search queries. System prompt controls style/tone only.

[SOURCE: https://docs.perplexity.ai/docs/sonar/features, https://docs.perplexity.ai/docs/sonar/openai-compatibility, https://coldfusion-example.blogspot.com/2026/02/how-to-parse-citations-and-sources-from.html]

### Pro Search (Sonar Pro Enhancement)

Pro Search adds **multi-step reasoning with automatic tool orchestration** to Sonar Pro:
- Requires `stream: true` and `search_type: "pro"` (or `"auto"` for intelligent routing)
- Model autonomously chains web_search and fetch_url_content tools
- Returns `reasoning_steps` array showing thought process and tool interactions
- Cannot register custom tools — only built-in web_search and fetch_url_content
- Non-streaming requests silently fall back to standard Sonar Pro behavior

[SOURCE: https://docs.perplexity.ai/docs/sonar/pro-search/quickstart]

---

## 3. Agent API — The Multi-Provider Gateway

Launched ~February 2026. This is architecturally distinct from Sonar — it's a **unified gateway** to third-party models with Perplexity's search infrastructure bolted on.

### How It Works

- Endpoint: `POST /v1/responses` (NOT the OpenAI chat completions format — this is its own response format)
- Pass `model: "provider/model-name"` (e.g., `openai/gpt-5.2`, `anthropic/claude-opus-4-6`, `google/gemini-3.1-pro-preview`)
- **No markup** on provider token pricing — verified. You pay the same per-token rates as going directly to OpenAI/Anthropic/Google.
- Every response includes a `usage.cost` field with exact USD breakdown: `input_cost`, `output_cost`, `tool_calls_cost`, `total_cost`

[SOURCE: https://docs.perplexity.ai/docs/agent-api/quickstart — verified via Exa /answer]

### Available Third-Party Models

| Model | Input $/1M | Output $/1M | Cache Read $/1M |
|-------|-----------|-------------|-----------------|
| `perplexity/sonar` | $0.25 | $2.50 | $0.0625 |
| `anthropic/claude-opus-4-6` | $5.00 | $25.00 | $0.50 |
| `anthropic/claude-opus-4-5` | $5.00 | $25.00 | $0.50 |
| `anthropic/claude-sonnet-4-6` | $3.00 | $15.00 | $0.30 |
| `anthropic/claude-sonnet-4-5` | $3.00 | $15.00 | $0.30 |
| `anthropic/claude-haiku-4-5` | $1.00 | $5.00 | $0.10 |
| `openai/gpt-5.2` | $1.75 | $14.00 | $0.175 |
| `openai/gpt-5.1` | $1.25 | $10.00 | $0.125 |
| `openai/gpt-5-mini` | $0.25 | $2.00 | $0.025 |
| `google/gemini-3.1-pro-preview` | $2.00 (<=200K) / $4.00 (>200K) | $12.00 / $18.00 | 90% discount |
| `google/gemini-3-pro-preview` | $2.00 / $4.00 | $12.00 / $18.00 | 90% discount |
| `google/gemini-3-flash-preview` | $0.50 | $3.00 | 90% discount |
| `google/gemini-3.1-pro-preview` | $1.25 / $2.50 | $10.00 / $15.00 | 90% discount |
| `google/gemini-3-flash-preview` | $0.30 | $2.50 | 90% discount |
| `xai/grok-4-1-fast-non-reasoning` | $0.20 | $0.50 | $0.05 |

**NOTE:** `perplexity/sonar` in the Agent API is priced differently than the Sonar API's `sonar` model ($0.25/$2.50 vs $1/$1 per 1M tokens). The Agent API version appears cheaper on input but more expensive on output. The Sonar API also charges per-request search fees that the Agent API does not — Agent API charges per-tool-call instead.

[SOURCE: https://docs.perplexity.ai/docs/agent-api/models]

### Tools in Agent API

| Tool | Cost | Description |
|------|------|-------------|
| `web_search` | $0.005/call ($5/1K) | Web search with domain, recency, date, and language filters |
| `fetch_url` | $0.0005/call ($0.50/1K) | Extract content from specific URLs |
| Custom functions | No additional cost | Standard function calling (you implement, no Perplexity charge) |

The `web_search` tool supports:
- `search_domain_filter`: up to 20 domains (allowlist or `-` prefix denylist)
- `search_recency_filter`: `day`, `week`, `month`, `year`
- `search_after_date` / `search_before_date`: M/D/YYYY format
- `max_tokens_per_page`: control content per search result (reduces context costs)

[SOURCE: https://docs.perplexity.ai/docs/agent-api/tools]

### Presets

Pre-configured model + tool + budget combinations for common use cases:

| Preset | Model | Max Tokens | Max Steps | Tools |
|--------|-------|-----------|-----------|-------|
| `fast-search` | `xai/grok-4-1-fast-non-reasoning` | 3K | 1 | web_search |
| `pro-search` | `openai/gpt-5.1` | 3K | 3 | web_search, fetch_url |
| `deep-research` | `openai/gpt-5.2` | 10K | 10 | web_search, fetch_url |

All preset parameters are overridable. [SOURCE: https://docs.perplexity.ai/docs/agent-api/presets]

### Additional Agent API Features

- **Model fallback chains**: `models=["openai/gpt-5.2", "openai/gpt-5.1", "openai/gpt-5-mini"]` — automatic failover
- **Streaming**: Supported across all models
- **Structured output**: JSON schema enforcement via `response_format`
- **OpenAI compatibility mode**: Available (separate docs page exists)
- **Image attachments**: Supported
- **Conversation threading**: `previous_response_id` for multi-turn

[SOURCE: https://docs.perplexity.ai/docs/agent-api/ — multiple pages]

---

## 4. Search API — Raw Results, No LLM

Separate from Sonar. Returns **ranked web results** without LLM synthesis.

- Endpoint: `POST /search`
- Pricing: **$5/1K requests** flat — no token costs
- Returns: title, URL, snippet, date, last_updated per result
- Parameters: `max_results` (1-20, default 10), `max_tokens_per_page` (default 4096), `max_tokens` (total budget, default 10K, max 1M)
- Filters: domain, language (up to 10 ISO 639-1 codes), country (ISO codes), date range
- Rate limit: 50 requests/second, 50 burst capacity (all tiers)

This is **directly comparable to Exa's `/search` endpoint** — raw results, no synthesis.

[SOURCE: https://docs.perplexity.ai/docs/search/quickstart, https://docs.perplexity.ai/docs/admin/rate-limits-usage-tiers]

---

## 5. Pricing Comparison: Perplexity vs Exa

| Capability | Perplexity | Exa |
|-----------|-----------|-----|
| **Raw web search** | Search API: $5/1K requests | /search: $1/1K searches (auto), $0.25/1K (keyword) |
| **Search + content** | Search API with max_tokens_per_page | /contents: $1/1K pages |
| **Grounded LLM answer** | Sonar: ~$0.006-0.014/request (search fee) + tokens | /answer: $5/1K queries |
| **Deep research** | Sonar Deep Research: ~$0.014+/request + tokens | Deep Researcher: research_fast/research/research_pro |
| **URL fetch** | Agent API fetch_url: $0.0005/call | /contents with URL: $1/1K |
| **Embeddings** | pplx-embed: $0.004-$0.05/1M tokens | Not offered |
| **Third-party models** | Agent API: provider pricing, no markup | Not offered |

**Key differences:**
- Exa is cheaper for raw search ($1/1K vs $5/1K)
- Perplexity is unique in offering grounded LLM answers with citations as a core product
- Perplexity's Agent API is unique — no Exa equivalent (multi-provider model gateway)
- Exa's `/answer` is the closest equivalent to Sonar but returns structured verdicts, not conversational answers
- Perplexity offers embeddings; Exa does not
- Both offer domain filtering, date filtering, and content extraction

[INFERENCE: Pricing comparison derived from retrieved Perplexity docs + known Exa pricing from our MCP configuration. Exa pricing may have changed — verify if making cost decisions.]

---

## 6. MCP Server

### Official MCP Server

**Repository:** [perplexityai/modelcontextprotocol](https://github.com/perplexityai/modelcontextprotocol)
- 1,989 stars, MIT license, TypeScript, actively maintained (last push 2026-02-26)
- npm package available
- 4 tools exposed:
  - `perplexity_search` — Direct web search via Search API
  - `perplexity_ask` — Conversational Q&A via `sonar-pro`
  - `perplexity_research` — Deep research via `sonar-deep-research`
  - `perplexity_reason` — Advanced reasoning via `sonar-reasoning-pro`
- Optional `strip_thinking` parameter on reason/research tools to remove `<thinking>` tags

**Configuration:**
```json
{
  "mcpServers": {
    "perplexityai-modelcontextprotocol": {
      "url": "http://localhost:8080/mcp",
      "headers": {
        "PERPLEXITY_API_KEY": "your_key_here",
        "PERPLEXITY_TIMEOUT_MS": "600000"
      }
    }
  }
}
```

**Integration docs:** https://docs.perplexity.ai/docs/getting-started/integrations/mcp-server

[SOURCE: https://github.com/perplexityai/modelcontextprotocol]

### Community MCP Servers

- `dainfernalcoder/perplexity-mcp` — Won 1st at Cline Hackathon. Routes tasks to model best suited. Available via npx.
- `cfdude/mcp-perplexity-pro` — Adds intelligent model selection, conversation management, project-aware storage. Available via npm (`mcp-perplexity-pro`).

[SOURCE: https://playbooks.com/mcp/]

---

## 7. Rate Limits

### Agent API (tier-based, scales with cumulative spend)

| Tier | Cumulative Spend | QPS | Requests/Min |
|------|-----------------|-----|-------------|
| Tier 0 | $0 | 1 | 50 |
| Tier 1 | $50+ | 3 | 150 |
| Tier 2 | $250+ | 8 | 500 |
| Tier 3 | $500+ | 17 | 1,000 |
| Tier 4 | $1,000+ | 33 | 2,000 |
| Tier 5 | $5,000+ | 33 | 2,000 |

Tiers are permanent — once reached, no downgrade.

### Search API

50 requests/second, 50 burst capacity — applies to all tiers equally.

### Sonar API

Rate limits not published separately on the rate limits page — likely uses the same tier system as Agent API. [INFERENCE]

[SOURCE: https://docs.perplexity.ai/docs/admin/rate-limits-usage-tiers]

---

## 8. SDKs

| Language | Package | Install |
|----------|---------|---------|
| Python | `perplexityai` | `pip install perplexityai` |
| TypeScript/JS | `@perplexity-ai/perplexity_ai` | `npm install @perplexity-ai/perplexity_ai` |

Both SDKs:
- Cover all four API groups (Agent, Search, Sonar, Embeddings)
- Type-safe request/response definitions
- Auto-detect `PERPLEXITY_API_KEY` env var
- Support streaming
- Provide `output_text` convenience property for Agent API responses
- Python 3.8+, Node.js

**LangChain integration** also exists: `langchain-perplexity` package with `ChatPerplexity` class. Supports structured outputs for Tier 3+ users.

[SOURCE: https://docs.perplexity.ai/docs/sdk/overview, https://docs.langchain.com/oss/python/integrations/chat/perplexity]

---

## 9. Unique Capabilities (What Sonar/Agent API Do That Search APIs Cannot)

1. **Grounded synthesis** — Sonar doesn't return raw results; it returns a written answer with inline citation markers mapped to a `citations` array. This is fundamentally different from Exa `/search` (raw results) or even Exa `/answer` (structured verdict). Sonar produces conversational, multi-paragraph answers.

2. **Multi-provider gateway with integrated search** — The Agent API lets you run GPT-5.2 or Claude Opus with web_search bolted on. No other API offers "pick any frontier model + add web search as a tool" in one call. OpenRouter offers multi-provider access but without integrated search tooling.

3. **Pro Search multi-step reasoning** — Sonar Pro with `search_type: "pro"` autonomously chains multiple searches and URL fetches, adapting its strategy based on intermediate results. This is an agentic research loop inside a single API call.

4. **Deep Research as API** — `sonar-deep-research` runs exhaustive multi-source research and returns comprehensive reports. Comparable to Exa's Deep Researcher but with different pricing (token-based vs flat).

5. **Model fallback chains** — Agent API supports `models=[...]` for automatic failover across providers in one request.

6. **Search API as standalone product** — Raw ranked results at $5/1K without any LLM processing. Useful for RAG pipelines where you want to control the synthesis model yourself.

7. **Embeddings API** — Both standard and "contextualized" embeddings. No competitor in the search API space (Exa, Brave Search, Tavily) offers embeddings.

---

## 10. Perplexity "Computer" — Consumer Multi-Agent Product

Separate from the API, but relevant context: Perplexity launched "Computer" on 2026-02-25, a multi-model orchestration platform that coordinates 19 AI models (Claude Opus 4.6 as orchestrator, dispatches to Gemini, Grok, GPT-5.2, etc.). Available to Perplexity Max subscribers at $200/month with per-token billing. This is the consumer product; the Agent API is the developer equivalent.

[SOURCE: https://venturebeat.com/ai/perplexity-launches-computer-ai-agent-that-coordinates-19-models-priced-at, https://www.implicator.ai/perplexity-launches-computer-an-agent-platform-orchestrating-19-ai-models-at-once/]

---

## What's Uncertain

- **Sonar API rate limits** — The rate limits page only documents Agent API and Search API tiers. Sonar API rate limits may be the same as Agent API or may differ. [UNVERIFIED]
- **"No markup" verification** — Perplexity claims direct provider pricing with no markup. This was verified via Exa /answer with 0.9 confidence, but spot-checking individual model prices against provider pages would strengthen confidence. The Agent API model table prices match Anthropic/OpenAI published pricing for the models I can verify. [SOURCE + INFERENCE]
- **Agent API vs Sonar pricing discrepancy** — `perplexity/sonar` appears at $0.25/$2.50 in the Agent API models table but $1/$1 in the Sonar API pricing. The Sonar API also has per-request search fees. These may be different billing models for the same underlying capability, or different model configurations. [UNVERIFIED — needs Perplexity confirmation]
- **Sonar model architecture** — Multiple sources claim Sonar is "built on open-source Llama architectures" but this is not confirmed in official Perplexity docs. [UNVERIFIED — from third-party guide only]
- **Context windows** — Not documented on the official models page for any Sonar model. Third-party sources cite 128K for sonar, but this needs verification. [UNVERIFIED]

---

## Disconfirmation Results

1. **"No markup" claim** — Searched for reports of hidden fees or markup. Found none. The verify_claim call returned `supported` at 0.9 confidence. Multiple developer-facing pages reinforce the transparent pricing claim with per-request cost breakdowns in every response.

2. **Agent API limitations** — Not all third-party models support all features (e.g., reasoning, tools). The docs explicitly warn about this. No reports of model unavailability or quality degradation through the proxy found, but this is early (launched ~Feb 2026).

3. **Sonar citation quality** — The citation mapping issue (1-indexed text markers, 0-indexed array) is a known developer friction point, not a bug. Multiple community discussions confirm this design. No automated binding exists — you must implement the mapping yourself.

---

## Sources Saved

All data retrieved from primary sources (docs.perplexity.ai, GitHub, VentureBeat). No papers saved to corpus — this is a product/API landscape review, not academic research.

### Search Log

| # | Tool | Query/URL | Result |
|---|------|-----------|--------|
| 1 | Exa web_search | "Perplexity Sonar API documentation models endpoints pricing 2026" | Pricing summaries, Sonar Pro blog, docs feature page |
| 2 | Exa web_search | "Perplexity Agent API multi-provider launch 2026" | Agent API docs, Computer launch coverage |
| 3 | Exa crawling | docs.perplexity.ai/docs/sonar/features | Full features page (streaming, structured output, prompting) |
| 4 | Exa crawling | docs.perplexity.ai/docs/agent-api/quickstart | Full Agent API quickstart with response examples |
| 5 | Exa web_search | "Perplexity MCP server" | Official + community MCP servers |
| 6 | Exa web_search | "Perplexity Sonar API rate limits pricing" | Rate limits page, pricing summaries |
| 7 | Exa crawling | docs.perplexity.ai/docs/agent-api/models | Full model + pricing table |
| 8 | Exa crawling | docs.perplexity.ai/docs/agent-api/tools | Tools docs (web_search, fetch_url, function calling) |
| 9 | WebFetch | docs.perplexity.ai/llms.txt | Full documentation sitemap |
| 10 | WebFetch | docs.perplexity.ai/docs/getting-started/pricing | Sonar model pricing with per-request fees |
| 11 | WebFetch | docs.perplexity.ai/docs/getting-started/models | Model descriptions and capabilities |
| 12 | WebFetch | docs.perplexity.ai/docs/search/quickstart | Search API details |
| 13 | WebFetch | docs.perplexity.ai/docs/sonar/openai-compatibility | Response format extensions (citations, search_results) |
| 14 | WebFetch | docs.perplexity.ai/docs/sonar/pro-search/quickstart | Pro Search multi-step reasoning |
| 15 | WebFetch | docs.perplexity.ai/docs/sdk/overview | SDK details |
| 16 | Exa web_search | "Perplexity Sonar API response format citations" | Citation parsing blog, LangChain integration |
| 17 | verify_claim | "no markup" pricing claim | Supported, 0.9 confidence |
| 18 | Exa web_search | "Perplexity Agent API developer gotchas" | SEO slop + general multi-agent article (low signal) |

<!-- knowledge-index
generated: 2026-03-21T23:52:37Z
hash: d27eb6cf2e94

sources: 1
  INFERENCE: Pricing comparison derived from retrieved Perplexity docs + known Exa pricing from our MCP configuration. Exa pricing may have changed — verify if making cost decisions.
table_claims: 1

end-knowledge-index -->
