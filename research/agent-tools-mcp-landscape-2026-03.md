# Agent Tools & MCP Landscape Beyond Search — March 2026

**Date:** 2026-03-19
**Tier:** Standard
**Ground truth:** We use Exa, Brave, Perplexity, Firecrawl, scite, Semantic Scholar (research-mcp), context7. All configured as user-scope MCPs. Firecrawl intel-only. See `search-api-integration-landscape.md` and `agentic-search-api-comparison.md` for existing search API coverage.

---

## Question

What tools and MCP servers exist beyond our current search-heavy stack that provide genuinely different capabilities for AI agents?

## Search Axes

1. **MCP registries/directories** — what's been published in the ecosystem
2. **Agent-native APIs** — tools built for LLM consumption (not just search)
3. **Niche data APIs** — unique data moats (knowledge graphs, citation stance, entity resolution)
4. **Browser/compute/memory** — non-search agent infrastructure
5. **Domain-specific MCPs** — scientific, financial, geospatial, security

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Diffbot has a trillion-fact real-time knowledge graph with entity extraction from any URL | VentureBeat article + API docs + LangChain integration | HIGH | [SOURCE: venturebeat.com, diffbot docs] | VERIFIED |
| 2 | E2B provides isolated cloud sandboxes for agent code execution, MCP server available | GitHub repo (383 stars), multiple registry listings | HIGH | [SOURCE: github.com/e2b-dev/mcp-server] | VERIFIED |
| 3 | Browserbase/Stagehand offers cloud AI browser with act/extract/observe APIs, MCP runs server-side | Browserbase changelog (Mar 14 2026), Stagehand V3, Ruby SDK | HIGH | [SOURCE: browserbase.com/changelog] | VERIFIED |
| 4 | Linkup has dual-mode search (fast + deep intelligence) with company enrichment, raised $10M | Company blog, multiple comparison articles | MEDIUM | [SOURCE: linkup.so] | VERIFIED |
| 5 | Jina Reader converts any URL to clean LLM-friendly markdown for free | Jina docs, Docfork listing | HIGH | [SOURCE: jina.ai, docfork.com] | VERIFIED |
| 6 | BioContextAI connects 14+ biomedical databases behind one MCP (Ensembl, KEGG, Reactome, STRING, AlphaFold, UniProt, OpenTargets) | GitHub repo (20 stars), Nature Biotech 2025 publication | MEDIUM | [SOURCE: github.com/biocontext-ai/knowledgebase-mcp] | VERIFIED |
| 7 | MCP.science has 12 servers but mostly general-purpose or physics-niche | GitHub repo (120 stars), README analysis | HIGH | [SOURCE: github.com/pathintegral-institute/mcp.science] | VERIFIED |
| 8 | Composio offers 400+ pre-built integrations with OAuth handling as MCP tools | Multiple listings, ecosystem presence | MEDIUM | [SOURCE: search results] | NOT FULLY VERIFIED |
| 9 | Apify has 3,000+ pre-built scrapers ("Actors") with MCP integration | Apify ecosystem listings | MEDIUM | [SOURCE: apify.com] | TRAINING-DATA + search |
| 10 | ATTOM MCP server provides comprehensive property data (valuations, tax, hazard) | ATTOM website | MEDIUM | [SOURCE: attomdata.com] | VERIFIED |

---

## Tier 1 — Genuinely Different Capabilities

### Diffbot Knowledge Graph
- **What:** Trillion-fact knowledge graph built from crawling the entire web. Entity extraction from any URL → structured JSON (people, companies, products, articles). Real-time.
- **Unique:** Only real-time knowledge graph API at scale. Agent asks "what is this company?" and gets structured data with officers, revenue, competitors, funding — not search results.
- **Integration:** LangChain graph loader, direct API.
- **Pricing:** Enterprise. Expensive but irreplaceable for structured entity data.
- **For us:** Would be killer for intel entity research. Worth testing if company enrichment queries become frequent.

### E2B Cloud Sandboxes
- **What:** Isolated cloud execution environments for running agent-generated code. MCP server: `@e2b/mcp-server`.
- **Unique:** Agent can run arbitrary Python/JS/any-runtime code without touching local machine. Automatic cleanup, resource limits, network isolation.
- **Install:** `npx @smithery/cli install e2b --client claude` or `npx -y @e2b/mcp-server`
- **Pricing:** Free tier available, API key from e2b.dev.
- **For us:** Fills a real gap for autoresearch (evolutionary code search needs sandboxed execution) and code-review-scout (run code to verify fixes). Also useful for safe evaluation of untrusted scripts.

### Browserbase / Stagehand
- **What:** Cloud-hosted AI browser automation. Three core APIs: `act` (do something), `extract` (get data), `observe` (find elements). Built on Playwright, self-healing selectors.
- **Unique:** Natural language browser control. MCP server runs on their infrastructure (announced Mar 14, 2026). `stagehand.agent` integrates CUA models.
- **Stagehand V3 current:** Streaming support, Ruby/Python/JS SDKs.
- **Pricing:** Free plan (3 concurrent sessions). Paid plans scale up.
- **For us:** We already have claude-in-chrome for browser automation. Browserbase would be useful for headless/cloud scenarios where we need browser without a local Chrome instance (e.g., orchestrator tasks).

### Jina AI Reader + Embeddings
- **What:** `r.jina.ai/{url}` converts any URL to clean LLM-friendly markdown. No API key needed for basic usage. Also: embeddings-v4 (3.8B multimodal, text+images+PDFs) and reranker-v3 (listwise).
- **Unique:** Cleanest URL→text conversion available. Handles JS rendering. Free tier.
- **For us:** Could replace some WebFetch calls where we just need clean text extraction. Embeddings/reranker relevant if we build RAG pipelines.

### Composio
- **What:** 400+ pre-built tool integrations (GitHub, Slack, Jira, Salesforce, Gmail, etc.) exposed as MCP tools. Handles OAuth flows.
- **Unique:** One-stop auth + action layer. Agent doesn't need per-service API keys.
- **For us:** We already manage our own integrations and prefer direct control. Lower priority unless we need many new integrations quickly.

### Mem0 / Zep (Agent Memory)
- **What:** Persistent memory layers for AI agents. Graph-based memory, cross-session context, semantic recall. Mem0 has MCP server.
- **Unique:** Drop-in agent memory without building infrastructure.
- **For us:** We have our own memory system (MEMORY.md + knowledge substrate) that's better integrated with our workflow. Not needed.

---

## Tier 2 — Search API Alternatives

| Tool | What's Different | Pricing | Worth It? |
|------|-----------------|---------|-----------|
| **Linkup** | Deep intelligence mode (multi-step retrieval), company enrichment, GDPR/CCPA. Raised $10M. | €5/1K standard, €50/1K deep | **Benchmark for intel** — deep mode does things Exa can't |
| **Tavily** | Hallucination-reduction focus, source credibility scoring, generous free tier | $0.008/credit, 1K free/mo | We know this. Exa faster, better for our use. |
| **Bright Data SERP** | Multi-engine (Google/Yahoo/DuckDuckGo/Yandex/Baidu/Naver), 150M proxies, pay-per-success | $1.5/1K | Unique for geoblocked/multi-engine. Niche. |
| **YOU.com API** | Citation-tracked, compliance-focused | Custom | Too niche for us. |
| **WebSearchAPI.ai** | Google-powered, pre-extracted clean content for RAG | $30/mo 5K queries | Redundant with Exa+Brave. |
| **Serpex** | Claims better structured extraction | Variable | Too new. |

---

## Tier 3 — Domain-Specific MCPs

### Evaluated in Detail

**BioContextAI** (`biocontext-ai/knowledgebase-mcp`)
- **Databases:** Ensembl, KEGG, Reactome, STRING, InterPro, AlphaFold DB, Protein Atlas, UniProt, OpenTargets, PanglaoDB, PRIDE, EuropePMC, Google Scholar, Antibody Registry
- **Quality:** Published in Nature Biotechnology 2025. CI/CD, code coverage. Python/FastMCP.
- **Architecture:** Local via `uvx`, Docker, or remote test server. No API keys for BioContextAI itself (individual sources may rate-limit).
- **Stars:** 20. Last push: 2026-01-12. Maintenance risk.
- **Verdict:** **Useful for genomics project.** We don't have direct MCP access to Ensembl, KEGG, Reactome, STRING, AlphaFold, or OpenTargets. Currently we'd WebFetch these or use training data. The unified access layer is the value — agent can cross-query 14 databases without custom integration per source.
- **Risk:** Low maintenance (3 months since last push), low stars. But it's wrapping stable APIs, so drift is slow.

**MCP.science** (`pathintegral-institute/mcp.science`)
- **Servers:** 12 total. Materials Project, GPAW (quantum chemistry), NEMAD (neuroscience), Mathematica, Jupyter, Python execution, SSH, web fetch, TinyDB, TXYZ search, timer, example.
- **Quality:** 120 stars, v0.2.0 (early). MIT license.
- **Verdict:** **Not useful for us.** General-purpose servers (SSH, web fetch, TinyDB) duplicate what we have. Science-specific ones (Materials Project, GPAW, NEMAD) aren't in our domains (genomics, finance). Skip.

### Other Notable Domain MCPs (from search, not evaluated in detail)

| MCP | Domain | Data | Notes |
|-----|--------|------|-------|
| **ATTOM** | Real estate | Property valuations, ownership, tax, hazard risk | Commercial. Useful if we ever do real estate research. |
| **Kinetica** | Geospatial | Real-time geospatial SQL queries | Interesting for location-based analysis. Commercial. |
| **Earthdata** | Earth science | NASA Earth observation data | Niche. |
| **Verilex** | Gov/business/crypto | 20+ datasets: prediction markets, SEC, crypto | Could be interesting for intel. Needs evaluation. |
| **mcp-swiss** | Swiss open data | Zero-config gov/transport/weather data | Novel pattern (no API key), not relevant to us. |
| **NDepend** | .NET code analysis | Deep .NET static analysis | Not relevant (we don't do .NET). |
| **CodeQL MCP** | Security | GitHub CodeQL integration | Interesting for code-review-scout. Needs evaluation. |
| **SonarSense** | Code quality | SonarQube insights via MCP | Interesting if we set up SonarQube. |
| **SqlAugur** | Database | Safe read-only SQL Server with query parsing | Novel safety pattern. |
| **Tenzir** | Security data | TQL pipeline execution for security analysis | Niche. |

---

## Registries to Monitor

- **`github.com/punkpeye/awesome-mcp-servers`** — largest curated list, has web directory
- **`github.com/modelcontextprotocol/servers`** — official Anthropic repo
- **`github.com/wong2/awesome-mcp-servers`** — second largest
- **`smithery.ai`** — MCP server installer/registry

---

## Recommendations — What to Add to Our Stack

**High ROI (fill gaps we actually have):**

1. **E2B sandbox MCP** — We can't safely run generated code in isolation. Trivial to add. Fills gap for autoresearch and code-review-scout.
2. **Jina Reader** — `r.jina.ai/{url}` is cleaner than WebFetch for URL→markdown. Free, no key. Quick win.
3. **BioContextAI** (genomics only) — Direct MCP access to Ensembl/KEGG/Reactome/STRING/AlphaFold/OpenTargets. Currently we WebFetch these databases manually.

**Worth benchmarking:**

4. **Linkup deep search** — Test against Exa for intel company research. The deep intelligence mode (multi-step retrieval + enrichment) may outperform Exa for entity profiling.
5. **Diffbot Knowledge Graph** — If structured entity data (company officers, financials, competitor graphs) becomes a frequent need in intel. Expensive, evaluate on specific queries first.

**Not worth adding:**
- Tavily (Exa is better for us)
- YOU.com, WebSearchAPI.ai, Serpex (redundant)
- Composio (we manage our own integrations)
- Mem0/Zep (our memory system is better integrated)
- MCP.science (wrong domains)

---

## Search Log

| Query | Tool | Results | Signal |
|-------|------|---------|--------|
| "best MCP servers for AI agents 2025 2026" | Exa neural | 14 results | Nimble, Ultimate MCP, Nexus, Bauplan, Crawl4AI, Sinequa — mostly enterprise wrappers |
| "APIs purpose-built for LLM agents" | Exa neural | 11 results | Cognee, Timbr GraphRAG, neo4j agent-memory, LandingAI doc extraction |
| "niche data APIs with unique capabilities for AI" | Exa neural | 9 results | Bibcit, Dimensions Author Check, OpenAlex, WordLift Fact-Check, CrossRef |
| "awesome MCP servers list github" | Brave | 10 results | punkpeye (largest), wong2, appcypher, modelcontextprotocol/servers |
| "Tavily vs Exa vs SerpAPI vs Linkup" | Brave | 10 results | Multiple comparison articles, Linkup raised $10M |
| "Diffbot knowledge graph API" | Exa neural | 8 results | VentureBeat, LangChain integration, sentiment analysis use case |
| "Browserbase Stagehand E2B Composio" | Exa neural | 5 results | Stagehand V3, AI SDK, Ruby SDK, MCP on infra |
| "Jina Reader Mem0 Zep" | Exa neural | 5 results | jina-embeddings-v4, reranker-v3, Reader API |
| "novel unique MCP servers geospatial scientific financial" | Exa neural | 8 results | mcp-swiss, Verilex, ATTOM, Kinetica, MCP.science, Earthdata, BioContextAI |
| "code analysis security MCP servers" | Exa neural (github) | 10 results | NDepend, CodeQL, SonarSense, SqlAugur, Tenzir, agent-security-scanner |
| BioContextAI README | WebFetch | Full analysis | 14 databases, Nature Biotech pub, FastMCP |
| MCP.science README | WebFetch | Full analysis | 12 servers, early stage, mostly general-purpose |
| "Beyond Tavily" comparison article | WebFetch | 5 tools analyzed | WebSearchAPI.ai, Exa, YOU.com, Bing, Felo |
| "Exa alternatives" comparison article | WebFetch | 6 tools analyzed | Bright Data, Tavily, Firecrawl, Sonar, Linkup, Exa |
