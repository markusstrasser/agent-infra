# Firecrawl API Deep Dive

**Question:** Full API surface, structured extraction, pricing, MCP server, self-hosting, comparison to Exa, agent endpoint, rate limits
**Tier:** Deep | **Date:** 2026-03-02
**Ground truth:** No prior Firecrawl research in corpus

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | 7 core API endpoints: scrape, crawl, map, search, extract, agent, browser | Official API docs index page | HIGH | [SOURCE: docs.firecrawl.dev/api-reference] | VERIFIED |
| 2 | AGPL-3.0 license on main repo | GitHub API + Exa /answer verification | HIGH | [SOURCE: github.com/firecrawl/firecrawl] | VERIFIED |
| 3 | MCP server package: `firecrawl-mcp` v3.9.0 on npm | npm registry page | HIGH | [SOURCE: npmjs.com/package/firecrawl-mcp] | VERIFIED |
| 4 | Free tier: 500 one-time credits, Hobby $16/mo for 3K | Pricing page | HIGH | [SOURCE: firecrawl.dev/pricing] | VERIFIED |
| 5 | Agent uses proprietary Spark-1 models (mini/pro) | Agent feature docs | HIGH | [SOURCE: docs.firecrawl.dev/features/agent] | VERIFIED |
| 6 | Self-hosted via Docker Compose, TypeScript + Redis + Playwright | Self-host docs | HIGH | [SOURCE: docs.firecrawl.dev/contributing/self-host] | VERIFIED |
| 7 | /agent and /browser NOT supported in self-hosted | Self-host docs capability table | HIGH | [SOURCE: docs.firecrawl.dev/contributing/self-host] | VERIFIED |
| 8 | MCP server exposes 14 tools including browser automation | npm README (full tools listing) | HIGH | [SOURCE: npmjs.com/package/firecrawl-mcp] | VERIFIED |

---

## 1. Full API Surface

Base URL: `https://api.firecrawl.dev/v2`
Auth: `Authorization: Bearer fc-YOUR-API-KEY`
SDKs: Python (`firecrawl-py`), Node (`@mendable/firecrawl-js`), CLI (`firecrawl`)

### Standard Endpoints

| Endpoint | Method | What it does | Credits |
|----------|--------|-------------|---------|
| `/scrape` | POST | Single URL to markdown/JSON/HTML/screenshot/branding. JS rendering, browser actions (click, scroll, type, wait, screenshot, execute JS, generate PDF). Supports `onlyMainContent`, tag include/exclude, location/proxy settings, caching (`maxAge`). | 1/page (5 with enhanced proxy, 4 extra for JSON mode) |
| `/crawl` | POST | Async recursive website crawl. Returns job ID, poll with GET `/crawl/{id}`. Supports `maxDepth`, `limit`, `allowExternalLinks`, `deduplicateSimilarURLs`. | 1/page |
| `/map` | POST | Fast URL discovery from sitemap + SERP + cached crawls. Returns list of URLs with optional titles/descriptions. Supports `search` param for relevance-ranked results. | 1/call (regardless of URL count) |
| `/search` | POST | Web search + optional content scraping in one call. Returns `web`, `images`, `news` source types. Categories: `pdf`, `research`, `github`. Time filtering via `tbs` param (Google-style: `qdr:d`, `qdr:w`, custom date ranges). Location-aware. | 2/10 results (+ scrape costs if `scrapeOptions` set) |

### Agentic Endpoints

| Endpoint | Method | What it does | Credits |
|----------|--------|-------------|---------|
| `/extract` | POST | LLM-powered structured extraction across URLs/wildcards. Pass JSON Schema + prompt. Supports `enableWebSearch`, `showSources`. Async (returns job ID). Can use FIRE-1 agent for complex navigation. Billing: 1 credit per 15 tokens. | Dynamic (token-based) |
| `/agent` | POST | Autonomous research agent. Only `prompt` required (no URLs needed). Uses Spark-1 models. Searches web, navigates, extracts structured data. Async (poll with GET `/agent/{id}`). | Dynamic (5 free daily runs, few hundred credits typical) |
| `/browser` | POST | Persistent cloud browser sessions. Create session, execute commands (bash `agent-browser` commands, Python Playwright, JS). Full interactive automation. | 2/browser-minute |

### Output Formats (for `/scrape`)

- `markdown` (default) -- clean markdown, main content only
- `html` -- cleaned HTML (scripts/styles removed, relative URLs resolved)
- `rawHtml` -- unmodified HTML as received
- `links` -- list of links on page
- `images` -- list of images
- `screenshot` -- full-page or viewport screenshot (expires 24h)
- `summary` -- LLM-generated summary
- `json` -- structured extraction with JSON Schema + prompt
- `changeTracking` -- git-diff or JSON comparison against previous scrape
- `branding` -- comprehensive brand identity (colors, fonts, typography, spacing, components, personality)

### Browser Actions (for `/scrape`)

Before scraping, you can chain: `wait` (duration or element), `click`, `write`, `press`, `scroll`, `screenshot`, `scrape`, `executeJavascript`, `pdf`.

### Notable Features

- **Change Tracking**: Compare current page to previous scrape. Git-diff or structured JSON comparison. Tag-based branching for separate change histories.
- **Branding extraction**: Full design system extraction (colors, fonts, typography, spacing, button styles, personality traits).
- **PDF parsing**: 3 modes (fast/auto/OCR). 1 credit/page for parsing, flat 1 credit for base64 raw.
- **Location/proxy**: Auto-select proxy by country. Basic (free), enhanced (5x cost, anti-bot), auto (try basic first).
- **Caching**: `maxAge` param, default 2 days. "500% speed improvement" when fresh data not needed.

[SOURCE: docs.firecrawl.dev/api-reference/endpoint/scrape, /crawl, /map, /search, /extract, /agent]

---

## 2. Structured Extraction

Two pathways to structured JSON output:

### a. JSON format on `/scrape`

Pass `formats: [{ type: "json", schema: {...}, prompt: "..." }]` to `/scrape`. The schema is standard JSON Schema. The LLM extracts from the scraped page content. Costs 4 additional credits per page.

### b. `/extract` endpoint

Dedicated extraction across multiple URLs or wildcards:
```python
from firecrawl import Firecrawl
firecrawl = Firecrawl(api_key="fc-KEY")

res = firecrawl.extract(
    urls=["https://example.com/*"],
    prompt="Extract product details",
    schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "price": {"type": "number"}
        },
        "required": ["name", "price"]
    }
)
```

### c. `/agent` endpoint (Pydantic/Zod support)

Python SDK accepts Pydantic models directly:
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class Founder(BaseModel):
    name: str = Field(description="Full name")
    role: Optional[str] = None

class FoundersSchema(BaseModel):
    founders: List[Founder]

result = app.agent(
    prompt="Find the founders of Firecrawl",
    schema=FoundersSchema,
    model="spark-1-mini"
)
```

Node SDK accepts Zod schemas:
```js
const result = await firecrawl.agent({
  prompt: "Find the founders of Firecrawl",
  schema: z.object({
    founders: z.array(z.object({
      name: z.string(),
      role: z.string().optional()
    }))
  })
});
```

### Reliability Assessment

- **Known limitations** (per docs): "Results might differ across runs, particularly for very large or dynamic sites." Extract is still labeled Beta.
- Complex logical queries ("find every post from 2025") acknowledged as unreliable.
- Agent is labeled "Research Preview" -- expect rough edges.
- Schema adherence is LLM-dependent -- no formal guarantees of 100% schema compliance, but JSON Schema validation is applied server-side.

[SOURCE: docs.firecrawl.dev/features/extract, docs.firecrawl.dev/features/agent]

---

## 3. Pricing

### Plans (billed yearly, prices shown are monthly equivalent)

| Plan | Credits/mo | Price/mo (yearly) | Concurrent browsers | Overage |
|------|-----------|-------------------|---------------------|---------|
| Free | 500 one-time | $0 | 2 | None |
| Hobby | 3,000 | $16 | 5 | $9/1K credits |
| Standard | 100,000 | $83 | 50 | $47/35K credits |
| Growth | 500,000 | $333 | 100 | $177/175K credits |
| Scale | 1,000,000 | $599 | 150 | Custom |
| Enterprise | Custom | Custom | Custom | Custom |

### Credit Costs Per Operation

| Operation | Credits |
|-----------|---------|
| Scrape | 1/page |
| Crawl | 1/page |
| Map | 1/call |
| Search | 2/10 results |
| Browser | 2/browser-minute |
| Extract | Token-based (1 credit = 15 tokens) |
| Agent | Dynamic (5 free daily runs, typical: few hundred credits) |
| Enhanced proxy | 5 credits/page |
| JSON extraction on scrape | 4 extra credits/page |
| PDF parsing | 1 credit/PDF page |

### Key Billing Details

- Credits do NOT roll over (except auto-recharge credits and custom annual plans).
- Failed requests: NOT charged (exception: FIRE-1 agent requests are always billed).
- Agent `maxCredits` param: caps spending per request (default 2,500).
- No pay-per-use plan exists -- subscription only.
- Auto-recharge packs available for burst usage.

[SOURCE: firecrawl.dev/pricing, docs.firecrawl.dev/features/agent, docs.firecrawl.dev/features/search]

---

## 4. MCP Server

### Package: `firecrawl-mcp`

- **npm package**: `firecrawl-mcp` (v3.9.0 as of 2026-02-17)
- **GitHub repo**: `github.com/firecrawl/firecrawl-mcp-server`
- **License**: MIT (separate from main repo's AGPL-3.0)
- **Weekly downloads**: ~30.6K
- **Transport**: stdio (default) or Streamable HTTP (`HTTP_STREAMABLE_SERVER=true`)

### Installation

```bash
# One-liner
env FIRECRAWL_API_KEY=fc-KEY npx -y firecrawl-mcp

# Or install globally
npm install -g firecrawl-mcp
```

### Claude Code / Desktop config

```json
{
  "mcpServers": {
    "firecrawl-mcp": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": {
        "FIRECRAWL_API_KEY": "fc-YOUR_KEY"
      }
    }
  }
}
```

### 14 Exposed Tools

| Tool | Purpose |
|------|---------|
| `firecrawl_scrape` | Single URL scrape (markdown/JSON/branding) |
| `firecrawl_batch_scrape` | Multiple known URLs in parallel |
| `firecrawl_check_batch_status` | Poll batch operation |
| `firecrawl_map` | Discover URLs on a site |
| `firecrawl_search` | Web search + optional content scraping |
| `firecrawl_crawl` | Async multi-page crawl |
| `firecrawl_check_crawl_status` | Poll crawl job |
| `firecrawl_extract` | LLM-powered structured extraction |
| `firecrawl_agent` | Autonomous research agent |
| `firecrawl_agent_status` | Poll agent job |
| `firecrawl_browser_create` | Create persistent browser session |
| `firecrawl_browser_execute` | Execute code in browser (bash/Python/JS) |
| `firecrawl_browser_list` | List browser sessions |
| `firecrawl_browser_delete` | Destroy browser session |

### Configuration Env Vars

- `FIRECRAWL_API_KEY` (required for cloud)
- `FIRECRAWL_API_URL` (for self-hosted)
- `FIRECRAWL_RETRY_MAX_ATTEMPTS` (default 3)
- `FIRECRAWL_RETRY_INITIAL_DELAY` (default 1000ms)
- `FIRECRAWL_RETRY_MAX_DELAY` (default 10000ms)
- `FIRECRAWL_RETRY_BACKOFF_FACTOR` (default 2)
- `FIRECRAWL_CREDIT_WARNING_THRESHOLD` (default 1000)
- `FIRECRAWL_CREDIT_CRITICAL_THRESHOLD` (default 100)

[SOURCE: npmjs.com/package/firecrawl-mcp]

---

## 5. Self-Hosting

### Stack

- **Language**: TypeScript (main API + worker)
- **Browser engine**: Playwright (microservice, Docker container)
- **Queue**: Redis + Bull (job queue with admin panel)
- **Database**: Supabase (optional, for auth/logging -- not required)
- **Container**: Docker Compose (API + worker + Redis + Playwright)

### Setup

```bash
# Clone repo, copy .env from apps/api/.env.example
docker compose build
docker compose up
# API available at http://localhost:3002
# Bull Queue admin: http://localhost:3002/admin/{BULL_AUTH_KEY}/queues
```

### Self-hosted vs Cloud Capability Gap

| Feature | Cloud | Self-hosted |
|---------|-------|-------------|
| /scrape, /crawl, /map, /search | Yes | Yes |
| /extract (with LLM) | Yes | Yes (requires OPENAI_API_KEY or Ollama) |
| /agent | Yes | **NO** |
| /browser | Yes | **NO** |
| Fire-engine (advanced anti-bot) | Yes | **NO** |
| Screenshot | Yes | Yes (with Playwright running) |
| Local LLMs (Ollama) | No | Yes (experimental) |
| PDF parsing (LlamaParse) | Yes | Yes (with LLAMAPARSE_API_KEY) |
| Kubernetes deploy | N/A | Yes (example manifests provided) |

### Open-Source Assessment

**Open-core model.** The main repo is AGPL-3.0, meaning you can self-host and modify freely but must share modifications. However:

- `/agent` and `/browser` endpoints are **cloud-only** (not in the open-source codebase)
- "Fire-engine" (advanced proxy/anti-bot infrastructure) is proprietary
- The Spark-1 models (mini/pro) used by `/agent` are proprietary
- AI features require an LLM API key (OpenAI, Ollama, or compatible)

So: self-hosted Firecrawl gives you scrape + crawl + map + search + extract. The agentic features (agent, browser, FIRE-1) are cloud-locked.

[SOURCE: docs.firecrawl.dev/contributing/self-host, github.com/firecrawl/firecrawl (AGPL-3.0)]

---

## 6. Comparison to Exa

| Dimension | Firecrawl | Exa |
|-----------|-----------|-----|
| **Primary function** | Web scraping/crawling API (URL -> content) | Semantic web search API (query -> content) |
| **Search** | Google-based web search with time filtering | Neural/semantic search (finds conceptually similar pages) |
| **Scraping depth** | Full: JS rendering, browser actions, anti-bot proxies, screenshots | Basic: fetches and cleans page content, no browser automation |
| **Structured extraction** | Built-in LLM extraction (JSON Schema, Pydantic/Zod) | No built-in extraction. Returns text/highlights/summaries. Exa /answer for single-claim verification. |
| **Agent/research** | `/agent` endpoint (autonomous browsing + extraction) | `deep_researcher` (autonomous research report generation) |
| **Self-hosting** | Yes (Docker, AGPL-3.0) | No |
| **MCP server** | Official `firecrawl-mcp` (14 tools, 30K weekly downloads) | Official `@anthropics/exa-mcp` (available in our config) |
| **Browser automation** | Full: persistent sessions, click/type/navigate, Playwright | None |
| **Change tracking** | Built-in (git-diff, JSON comparison) | None |
| **Caching** | Server-side, configurable `maxAge` | 15-min client cache |
| **Content filtering** | Category filters (pdf, research, github), location, time | Category filters (company, research paper, news, etc.), domain filters, date ranges |
| **Pricing model** | Credit-based subscription ($16-$599/mo) | Credit-based subscription |
| **Free tier** | 500 one-time credits | 1000 searches/month |

### Where Firecrawl Wins

1. **Scraping capability**: JS rendering, browser actions, anti-bot proxies, screenshots, PDF OCR. Exa just fetches and cleans pages.
2. **Structured extraction**: Native LLM-powered JSON extraction with schema validation. Exa returns text you'd need to parse yourself.
3. **Full website crawling**: Recursive crawl with depth/limit controls. Exa has no equivalent.
4. **URL discovery**: `/map` for fast sitemap + SERP URL enumeration.
5. **Browser automation**: Persistent sessions with click/type/navigate. Nothing comparable in Exa.
6. **Self-hosting**: Docker deployment option. Exa is cloud-only.
7. **Change tracking**: Monitor page changes over time with diffs.

### Where Exa Wins

1. **Semantic search quality**: Neural search finds conceptually related content, not just keyword matches. Firecrawl's `/search` is Google-based (keyword/ranking).
2. **Content highlights**: Exa can return relevance-ranked sentence highlights from pages. Firecrawl returns full page content or nothing.
3. **Deep research**: Exa's `deep_researcher` produces synthesized research reports. Firecrawl's `/agent` extracts structured data but doesn't synthesize.
4. **Domain/date filtering in search**: Exa has `includeDomains`, `excludeDomains`, `startPublishedDate`, `endPublishedDate`. Firecrawl has `tbs` (Google time params) and `categories` but less granular domain control.
5. **People search**: Exa has a dedicated `people_search` endpoint.
6. **Company research**: Exa has a dedicated `company_research` endpoint.
7. **Claim verification**: Exa `/answer` provides structured factual verification with citations.

### Complementary Use Pattern

For agent infrastructure, they serve different roles:
- **Exa** for discovery (finding the right pages via semantic search) and verification (fact-checking)
- **Firecrawl** for extraction (scraping those pages for structured data) and monitoring (change tracking)

The overlap is narrow: both can search the web and return content, but Exa's search is semantic while Firecrawl's is Google-based. Both have "research agent" features but they're architecturally different -- Exa synthesizes, Firecrawl extracts.

[INFERENCE: Based on direct comparison of official documentation for both services. Not benchmarked head-to-head.]

---

## 7. Agent (/agent) Endpoint — Deep Dive

### Architecture

The `/agent` endpoint is an autonomous web research agent that:
1. Takes a natural language `prompt` (required, max 10K chars)
2. Optionally accepts `urls` to constrain scope and `schema` for structured output
3. Runs asynchronously -- returns job ID immediately
4. Uses proprietary **Spark-1** models (not GPT/Claude)
5. Autonomously searches web, navigates pages, extracts data
6. Returns structured JSON matching your schema (or freeform)

### Models

| Model | Cost | Best for |
|-------|------|----------|
| `spark-1-mini` (default) | 60% cheaper | Most tasks, high-volume extraction |
| `spark-1-pro` | Standard | Complex research, critical extraction |

### Workflow

```
POST /agent {prompt, schema?, urls?, maxCredits?, model?}
  -> {success: true, id: "uuid"}

GET /agent/{id}
  -> {status: "processing"} or
  -> {status: "completed", data: {...}, creditsUsed: 15}
```

SDK convenience: `app.agent(...)` blocks until complete. `app.start_agent(...)` returns immediately for async polling.

### Pricing

- 5 free daily runs (playground or API)
- Dynamic credit usage based on prompt complexity and data processed
- Default `maxCredits` = 2,500 (configurable)
- If maxCredits exceeded: job fails, credits consumed so far still charged
- "Parallel Agents" with Spark-1 Fast: fixed 10 credits per cell
- Typical run: "a few hundred credits" per the docs

### vs /extract

| Feature | /agent | /extract |
|---------|--------|---------|
| URLs required | No | Yes (or wildcards) |
| Speed | Faster | Standard |
| Web search | Built-in | Optional (`enableWebSearch`) |
| Model | Spark-1 (mini/pro) | Uses configured LLM |
| Self-hosted | No | Yes |
| Maturity | Research Preview | Beta |

Firecrawl explicitly positions `/agent` as the "successor to `/extract`" -- faster, more reliable, no URLs needed.

### Limitations

- Cloud-only (not available in self-hosted)
- Research Preview (expect rough edges)
- Dynamic pricing hard to predict
- `maxCredits` cap = job fails if exceeded, partial credits lost
- Not suitable for simple known-URL extraction (use `/scrape` with JSON format instead)
- Results expire after 24 hours via API (viewable in activity logs after)

[SOURCE: docs.firecrawl.dev/features/agent, docs.firecrawl.dev/api-reference/endpoint/agent]

---

## 8. Rate Limits and Concurrency

### API Rate Limits (requests per minute)

The rate limits page table columns appear to be: Plan | /scrape | /crawl | /extract,/agent | /search | /map | /batch_scrape | status endpoints

| Plan | /scrape | /crawl | /extract,/agent | /search | /map | /batch_scrape | status |
|------|---------|--------|----------------|---------|------|--------------|--------|
| Free | 10 | 10 | 1 | 5 | 10 | 1,500 | 500 |
| Hobby | 100 | 100 | 15 | 50 | 100 | 1,500 | 25,000 |
| Standard | 500 | 500 | 50 | 250 | 500 | 1,500 | 25,000 |
| Growth | 5,000 | 5,000 | 250 | 2,500 | 1,000 | 1,500 | 25,000 |
| Scale | 7,500 | 7,500 | 750 | 7,500 | 1,000 | 25,000 | 25,000 |

### Concurrent Browser Limits

| Plan | Concurrent browsers |
|------|-------------------|
| Free | 2 |
| Hobby | 5 |
| Standard | 50 |
| Growth | 100 |
| Scale/Enterprise | 150+ |

### FIRE-1 Agent Rate Limits (separate from main)

- /scrape with FIRE-1: 10 req/min
- /extract with FIRE-1: 10 req/min

### Key Details

- Rate limits are requests/minute, not credits
- Concurrent browsers = real bottleneck (pages processed simultaneously)
- Queue overflow: excess jobs wait; time in queue counts against `timeout` param
- Extract endpoints share limits with /agent
- Batch scrape endpoints share limits with /crawl
- 429 responses on rate limit exceeded
- Built-in retry with exponential backoff in SDKs and MCP server

[SOURCE: docs.firecrawl.dev/rate-limits]

---

## What's Uncertain

1. **Spark-1 model internals**: No documentation on what Spark-1 mini/pro actually are (fine-tuned open model? Custom architecture?). Opaque.
2. **Agent reliability at scale**: "Research Preview" with acknowledged rough edges. No public benchmarks on extraction accuracy.
3. **Extract token pricing granularity**: "1 credit = 15 tokens" but unclear if this counts input+output tokens, and which model's tokenizer.
4. **Self-hosted feature parity roadmap**: No public timeline for when/if agent+browser come to self-hosted.
5. **Rate limit table column headers**: The HTML rendering was garbled. I reconstructed from context (7 columns matching 7 endpoint groups) but column assignments for the last 3 could be off. [INFERENCE]

## Search Log

| # | Tool | Query | Result |
|---|------|-------|--------|
| 1 | Exa web_search | "Firecrawl API documentation endpoints..." | Blog posts, marketing pages (5 results) |
| 2 | Exa crawling | docs.firecrawl.dev/api-reference | API reference index (v2 overview) |
| 3 | Exa crawling | docs.firecrawl.dev/.../scrape | Full OpenAPI spec for /scrape |
| 4 | Exa crawling | docs.firecrawl.dev/.../extract | Full OpenAPI spec for /extract |
| 5 | Exa crawling | docs.firecrawl.dev/.../agent | Full OpenAPI spec for /agent |
| 6 | Exa crawling | firecrawl.dev/pricing | Pricing page with plans and credits |
| 7 | Exa crawling | docs.firecrawl.dev/features/agent | Agent feature docs (detailed) |
| 8 | Exa crawling | docs.firecrawl.dev/contributing/self-host | Self-hosting instructions |
| 9 | Exa web_search | "Firecrawl MCP server npm..." | MCP package discovery |
| 10 | Exa crawling | docs.firecrawl.dev/features/search | Search feature docs |
| 11 | Exa crawling | docs.firecrawl.dev/features/map | Map feature docs |
| 12 | Exa crawling | docs.firecrawl.dev/features/extract | Extract feature docs |
| 13 | Exa crawling | docs.firecrawl.dev/rate-limits | Rate limits page |
| 14 | Exa crawling | npmjs.com/package/firecrawl-mcp | Full MCP server README (14 tools) |
| 15 | gh api | repos/mendableai/firecrawl | Repo metadata (87.5K stars, AGPL-3.0) |
| 16 | verify_claim | "AGPL-3.0 license" | Confirmed |
