claude-opus-5-5

**Verdict:** Five changes are worth acting on, ranked by impact on research quality:
1. **Get a free OpenAlex API key and put the content API in fetch_paper's chain.** OpenAlex now meters usage: keyless = $0.10/day (~100 searches), a free key = $1/day, and our openalex.py runs keyless, so the S2 fallback runs out quietly and then sleeps through retries on a budget 429. The same key unlocks `content.openalex.org` cached PDFs + Grobid TEI for 55M works, about 51% of OA articles published since 2026-06 (Frontiers 87%, Springer Nature 58%). That is the 2026 OA slice where fetch_paper went 0/8 in August. Cost: $0.01/PDF.
2. **Use S2 features we already pay for in rate limit:** pass `publicationDateOrYear` (S2 *does* filter by date; the MCP instruction saying otherwise is wrong) and expose `/snippet/search` for passage-level claim location.
3. **Fix the Exa publication drift:** `category:"publication"` hits now return `exa.ai/library/publication/<id>` card URLs with the DOI in `entities[].properties.doi`. Agents must cite the DOI or primary URL, not the card. Rename `research paper` → `publication` in DOMAINS.md, and stop relying on `category:github` (being deprecated).
4. **Run a 20-paper parser bake-off before touching Marker 2.** PaddleOCR-VL-1.6 (0.9B, 96.3) and MinerU2.5-Pro (1.2B, 95.8) lead OmniDocBench v1.7. Marker appears there only as the 1.8.2 pipeline (78.4), so the comparison with our Marker 2 balanced + surya-ocr-2 setup is unmeasured. Both leaders serve via vLLM, which fits the existing Modal L4 pattern.
5. **Retire or reroute `deep_research`.** It cannot run (GEMINI_API_KEY is deliberately absent). Claude Code now ships a native `/deep-research` with a verifier phase, and the official OpenAlex MCP (`https://mcp.openalex.org/mcp`) covers citation traversal and reference checking when S2 is throttled. Trial both before writing more code.
Nothing we call broke outright between April and October 2026. The silent degraders are OpenAlex metering (keyless), the OpenAlex `search` param matching full-text n-grams (lower precision), and Exa's publication-URL shape.

# Research tooling API refresh (2026-04 → 2026-10)

Scope: breaking/upcoming changes in APIs research-mcp calls (S2, OpenAlex, EuropePMC, NCBI, arXiv, Unpaywall, Exa, Gemini deep research); new full-text sources and PDF parsers; new scholarly search/answer APIs and MCP servers; native Claude Code / Codex / Cursor research features. Baseline read first: skills/research/references/{tool-routing,known-issues,tool-history}.md, research/search-tool-thinning-perplexity-exa-parallel-2026-06-06.md, 2026-10-13-recent-agent-search-policies.md, 2026-06-20-research-agent-orchestration-tooling.md, pdf-to-markdown-tooling-2026-05.md, research-mcp HEAD 5bde64f.

Stack facts read from code (2026-10-14): ~/.env exports only EXA, BRAVE, PERPLEXITY, GEMINI_API_KEY_CRITIQUE_ONLY among relevant keys — no S2_API_KEY, OPENALEX_API_KEY, NCBI_API_KEY, UNPAYWALL_EMAIL (defaults to markus@synthoria.bio in papers.py).

## Findings log

### F1 OpenAlex — usage-metered API, keyless budget is $0.10/day, content API (50M+ PDFs + Grobid TEI) needs a key  [VERIFIED live 2026-10-14]
Probe: `curl -D- "https://api.openalex.org/works?search=spaced%20repetition&per_page=1"` → 200, headers `x-ratelimit-limit: 1000`, `x-ratelimit-limit-usd: 0.1`, `x-ratelimit-cost-usd: 0.001`, `meta.cost_usd: 0.001`. Same headers with `mailto=` (polite pool no longer raises anything). Singleton `GET /works/doi:…` costs 0.
Docs (help.openalex.org/access/example-costs.md, /api/authentication.md, read 2026-10-14): search = 10 credits ($0.001), list+filter = 1 credit, `rerank=true` +10, `search.semantic` = 10 credits and 1 req/s, content download $0.01/file; "Every account gets **$1 of usage per day** for free … Without a key you get $0.10/day"; budget exhaustion returns 429 (refusal is free). Per-second limit 10 (no key) / 30 (free key).
Content API: `has_content.pdf:true` count = 55,295,273 works; 693,665 of them published ≥2026-08-01. Work objects carry `content_urls: {pdf: https://content.openalex.org/works/W….pdf, grobid_xml: ….grobid-xml}`. Keyless probe → `401 {"error":"API key required","message":"Content downloads require an API key. Get one free at https://openalex.org/users"}`.
Other changes: `corpus=core|expansion|all` (Aug 2026) replaces `include_xpac`; default is core (320M), expansion ~190M mostly datasets/repo records. `search` OQL echo is "get works where full text has (…)" (1.15M hits for "spaced repetition") vs `filter=title_and_abstract.search:` (28k) — keyword `search` matches full-text n-grams, so precision for topical queries is lower than our code assumes. `search.semantic=` (paragraph-length queries) live: probe returned 49 hits, top = SAM spacing paper.
Impact on our code: openalex.py runs keyless (no OPENALEX_API_KEY in ~/.env; mailto is ignored) → ~100 searches/day before 429; `_raise_with_backoff` + tenacity then sleep/retry 4× on a budget 429 that will not clear until UTC reset (header `x-ratelimit-reset`, seconds) — a silent latency sink on exactly the S2-fallback path. papers.py does not use OpenAlex content at all.

### F2 Semantic Scholar — date filter and snippet search exist; our code uses neither  [VERIFIED live 2026-10-14, keyed]
Probes (x-api-key = $S2_API_KEY from shell env; ~2.5 s spacing):
- `GET /graph/v1/paper/search?query=spaced%20repetition&publicationDateOrYear=2026-08-01:&limit=2&fields=title,publicationDate` → 200, top hits dated 2026-08-18 and 2026-09-14. The MCP server instruction "S2 has no date/recency filtering. Use search_preprints" is wrong; discovery.py never passes `publicationDateOrYear`.
- `GET /graph/v1/paper/search/bulk?…&publicationDateOrYear=2026-08-01:` → 200, total 226, but bulk is boolean-match, unranked (first hit off-topic) — use relevance search for topical queries.
- `GET /graph/v1/snippet/search?query=spacing%20effect%20retention&limit=1` → 200, `{data:[{score, paper:{corpusId,title,authors,openAccessInfo:{license,status,disclaimer:"…extracted from the open access paper or abstract available at https://pmc…"}}, snippet:{text,…}}]}` — passage-level retrieval over S2's OA full text. Not wired anywhere in research-mcp (rg: 0 hits).
- `GET /recommendations/v1/papers/forpaper/arXiv:1706.03762` → 200 `{"recommendedPapers": []}` (empty for a landmark paper; not useful as a traversal fallback).
- `GET /datasets/v1/release/latest` → release_id 2026-10-06 (weekly bulk releases still flowing).
- Keyless `GET /graph/v1/paper/arXiv:1706.03762` → 429 immediately; keyless snippet/bulk → 429 "apply for a key". The shared unauthenticated pool is effectively unusable; our key works.

### F3 OpenAlex content coverage where our fetch chain fails  [VERIFIED live 2026-10-14, keyless group_by]
`/works?filter=<f>&group_by=primary_location.source.host_organization_lineage`:
| subset | OA articles | with cached PDF | ratio |
|---|---:|---:|---:|
| published ≥2026-06-01 | 2,094,995 | 1,062,418 | 51% |
| publication_year 2024 | 4,657,257 | 2,904,094 | 62% |
Per publisher, ≥2026-06-01: Springer Nature 78k/134k (58%), Frontiers 39k/45k (87%), Elsevier 57k/180k (32%), MDPI 22k/98k (23%). This is the exact slice where the 2026-08-24 incident logged fetch_paper 0/8 (Sci-Hub has no 2026 content; publisher HTML cookie-walls). Content is served from content.openalex.org, so publisher Cloudflare is not in the path. Cost with a free key: $0.01/PDF, i.e. ~100 PDFs/day inside the free $1 (minus searches).

### F4 Unpaywall, EuropePMC, NCBI, arXiv export, CORE — all alive, no breaking change observed  [VERIFIED live 2026-10-14]
- Unpaywall `GET api.unpaywall.org/v2/10.1038/nature14539?email=…` → 200 (Heroku), keys unchanged incl. `oa_locations_embargoed`, `updated: 2026-08-26`. best location = HAL repository, `url_for_pdf: null` (same shape memory already records).
- EuropePMC `search?query=…%20AND%20FIRST_PDATE:[2026-09-01%20TO%202026-10-14]&format=json` → 200, `version: "6.9"`, hitCount 112. (curl needs `-g` for the brackets.)
- NCBI ESearch keyless → 200 with `x-ratelimit-limit: 3` (unchanged 3 rps keyless; NCBI_API_KEY not set).
- arXiv `export.arxiv.org/api/query?search_query=ti:spaced%20AND%20ti:repetition&sortBy=submittedDate` → 200 Atom, top = 2026-09-14 paper.
- CORE v3 keyless `GET https://api.core.ac.uk/v3/search/works/?q=…&limit=1` (trailing slash; no-slash form 301s to an HTML meta-refresh page) → 200, totalHits 245,742, `x-ratelimit-limit: 10`; records carry `dataProviders`, `outputs`, `downloadUrl`/`fullText` fields. CORE is not in our stack; its value is repository (green OA) copies — the IRIS/DSpace blind spot the 2026-07-04 ladder works around by hand.

### F5 Exa — publication index rebuilt (Jul 2026); results are now Exa library pages, not primary URLs  [VERIFIED live + changelog 2026-10-14]
Changelog (exa.ai/docs/changelog.md, read 2026-10-14): 2026-04-01 `/research` endpoint retired (→ `/search type:"deep-reasoning"`), `resolvedSearchType`/`highlightScores` removed 2026-05-01, `startCrawlDate`/`endCrawlDate` silently ignored; 2026-06-16 Exa Agent API (`effort`, `outputSchema`, `input.data`); 2026-07-01 `agent_run` in hosted MCP (`https://mcp.exa.ai/mcp?tools=agent_run`); 2026-07-23 "Publication research": 350M-publication index, "`category: "publication"` … replaces the `research paper` category", "the `pdf`, `github`, and `tweet` search categories are being deprecated"; 2026-08-28 Dynamic Highlights beta (`dynamic: true` + header `Exa-Beta: dynamic-highlights-2026-08-28`, vendor-claimed ~30% fewer agent-trajectory tokens); 2026-09-24 Agent Ultra (`effort:"ultra"`, default $20 cap, `budget.maxDurationSeconds`).
Probe `POST api.exa.ai/search {"query":"interpretable memory models for spaced repetition","category":"publication","startPublishedDate":"2026-08-01","contents":{"text":{"maxCharacters":1500}}}` → $0.007; result `url` = `https://exa.ai/library/publication/fwlmhlpwzmz` (an Exa-rendered card: venue, abstract, author h-index, topics), `entities[0].properties` = {title, year, date, type:"preprint", citationCount, referenceCount, doi:"10.5281/zenodo.22727106", abstract, authors}. The hit was the Zenodo deposit dated 09-12, not the arXiv version (published 2026-09-14 per arXiv API). `category:"research paper"` still accepted and returns identical results (alias). `category:"github"` still returns results. Date filter held on this sample (both hits ≥ 2026-08-01) — the 2026-08-17 leakage gotcha may be fixed post-rebuild; one probe, not a test.
Impact: exa_verify.py uses `/answer` (still documented) and no deprecated params — no break. Agent-side: anyone citing an Exa publication hit must resolve `entities[].properties.doi`, not the `exa.ai/library` URL. skills/research/DOMAINS.md:14 still names `research paper` (works via alias; rename to `publication`). Memory/routing notes leaning on `category:github` are on a deprecated category.

### F6 Gemini Deep Research — unchanged IDs, still preview; our tool is unrunnable anyway  [VERIFIED doc 2026-10-14]
ai.google.dev/gemini-api/docs/deep-research.md.txt: agents still `deep-research-preview-04-2026` / `deep-research-max-preview-04-2026` (matches deep_research.py), "currently in preview", Interactions API only; added tools `mcp_server` and `file_search` (uploaded corpora), `collaborative_planning`, est. $1–3 / $3–7 per task. No deprecation date published. deep_research.py still needs GEMINI_API_KEY, which ~/.env deliberately does not export (only GEMINI_API_KEY_CRITIQUE_ONLY) — the tool fails for every caller (known-issues 2026-09-25). google-genai pinned 2.25.0.

### F7 PDF→markdown — open 1B-class VLM parsers now lead public benchmarks; no benchmark covers Marker 2  [VERIFIED README/blog 2026-10-14; head-to-head UNVERIFIED]
OmniDocBench README (raw.githubusercontent.com/opendatalab/OmniDocBench/main/README.md; v1.7 since 2026-04-30, rows added 2026-09-11), end-to-end Overall ↑ (text edit ↓, formula CDM, table TEDS):
| parser | size | Overall | TextEdit | FormulaCDM | TableTEDS |
|---|---|---:|---:|---:|---:|
| TeleOCR | 1.2B | 96.91 | 0.027 | 96.6 | 96.8 |
| PaddleOCR-VL-1.6 (arXiv 2606.03264) | 0.9B | 96.34 | 0.033 | 97.5 | 94.8 |
| MinerU2.5-Pro (2605) | 1.2B | 95.75 | 0.036 | 97.5 | 93.4 |
| GLM-OCR | 0.9B | 95.22 | 0.044 | 97.2 | 92.8 |
| dots.ocr | 3B | 90.77 | 0.048 | 90.0 | 87.2 |
| olmOCR | 7B | 85.74 | 0.139 | 88.1 | 83.0 |
| Mistral OCR (2503) | – | 85.66 | 0.097 | 89.9 | 76.8 |
| Marker **1.8.2** (pipeline) | – | 78.44 | 0.157 | 85.2 | 65.8 |
The Marker row is the 1.x pipeline, not our deployed marker-pdf 2.0 `--mode balanced` + `datalab-to/surya-ocr-2` on vLLM (skills/modal/references/marker-pdf-extraction.md). OmniDocBench is roughly half Chinese pages and many non-paper types, so the gap overstates what we would see on English papers. Datalab's own OmniParseBench (datalab.to/blog/omni-parse-bench, 2026-10-08; 16,288 tests, 2,937 pages, 92 languages; vendor benchmark) scores hosted "Datalab accurate" 92.7 / "balanced" 91.6 vs Gemini 3.8 Flash 92.9, Mistral OCR 89.5 — it omits PaddleOCR-VL and MinerU, so it cannot settle the question. Both leaders are open weights, ~1B, served through vLLM, so they fit the same Modal L4 container pattern Marker 2 uses.
Action: a 20-paper bake-off on our own corpus (equations + tables, English), Marker 2 balanced vs PaddleOCR-VL-1.6 vs MinerU2.5-Pro, scored with parse_health.py plus spot-checked tables; adopt only on a measured win.

### F8 Scholarly MCP servers and APIs for our gaps  [connector doc VERIFIED 2026-10-14; servers not installed or probed]
- **Official OpenAlex MCP** (help.openalex.org/access/connector.md): `claude mcp add --transport http openalex https://mcp.openalex.org/mcp`; Streamable HTTP + OAuth sign-in, "Every query runs on your own API key and daily budget"; stateless; covers search, citing works ("Who cites this paper: 10.1038/…"), OQL systematic searches, reference checking ("Check whether these references are real and give me DOIs"). It fills the gap "citation traversal when S2 is rate-limited" (OpenAlex `filter=cites:W…` costs 1 credit) and does reference verification without our code. Tool list and output shape UNVERIFIED (needs OAuth). OpenAlex also offers search email alerts (`/api/alerts/`), a candidate replacement for hand-built recency sweeps (UNVERIFIED).
- **S2 snippet search** (F2) is the cheapest passage-level claim-locating route we are not using; it complements scite stance (scite gives cite-context stance, snippet gives the paper's own text).
- Community MCP servers found (smaniches/semantic-scholar-mcp 8★, Burton-David/ResearchAssistantMCP, bighean/paper-search-mcp 0★ fork, academix, Scholar-MCP 0★; Exa search 2026-10-14): all wrap the same APIs research-mcp already calls. Skip.
- Dataset/code search: Exa `category:"github"` is being deprecated (F5); OpenAlex expansion corpus (`corpus=expansion`, ~190M mostly DataCite/repository records) is the free dataset-search route (UNVERIFIED for quality).
- Not probed (UNVERIFIED): CORE full-text download rate on a sample, Europe PMC new endpoints beyond v6.9, alphaXiv overview/PDF endpoints beyond what alphaxiv.py already uses, Elicit/Consensus APIs.

### F9 Native CLI research features  [Claude Code CHANGELOG.md VERIFIED 2026-10-14; Codex/Cursor UNVERIFIED]
Claude Code (raw CHANGELOG.md, head = 2.1.296):
- A built-in `/deep-research` command exists (fixes from 2.1.196 onward: verifier reports `unverified` instead of "all claims refuted"; Fetch-phase agent chips; 2.1.218 "start only when invoked manually"; 2.1.281 reliability fix). It overlaps our Gemini `deep_research` tool, which cannot run anyway (F6). Its quality vs our /research skill is untested.
- WebFetch no longer silently truncates at 100,000 chars; it reports unread length and accepts `offset`. WebSearch budget now refills at 100 calls/hour (`CLAUDE_CODE_WEB_SEARCH_REFILLS_PER_HOUR`) instead of a hard stop at 200.
- MCP: URL-mode elicitation on 2026-07-28 protocol connections (OAuth/browser flows such as the OpenAlex connector); per-server `request_timeout_ms` now honored (long MCP calls such as fetch_paper no longer die at the 60 s default if configured); the tasks panel can stop long-running MCP calls.
- Read handles PDF page ranges natively, but list-form `pages` ("6,9,15") now errors.
- Codex and Cursor: not probed in this pass (UNVERIFIED). Prior memo cursor-builtins-and-review covers Cursor review features only.
None of these deletes research-mcp code outright: fetch_paper's value is the corpus plus the parse, not the fetch.

## Summary table

| item | what's new | evidence (date) | affects | action | effort |
|---|---|---|---|---|---|
| OpenAlex metering + key | keyless $0.10/day, free key $1/day; search $0.001, singleton free; mailto no longer helps; budget 429 until UTC reset | live headers `x-ratelimit-limit-usd: 0.1`; help.openalex.org/access/example-costs.md (2026-10-14) | research_mcp/openalex.py, server.py (OPENALEX_API_KEY), ~/.env | adopt: add key; on 429 read `x-ratelimit-reset`, fail fast instead of tenacity retries | S |
| OpenAlex content API | cached PDF + Grobid TEI for 55.3M works; 51% of OA articles since 2026-06 | live `has_content.pdf:true` counts; keyless download → 401 "API key required" (2026-10-14) | research_mcp/papers.py fetch chain (before Sci-Hub for post-2021 DOIs); TEI could skip Marker for text | adopt | M |
| OpenAlex `search` semantics | `search=` = full-text n-gram match (1.15M hits vs 28k title+abstract); `rerank=true` (+$0.001); `search.semantic=` (1 rps) | live `meta.x_query.oql` (2026-10-14) | openalex.py search() | adopt: use `title_and_abstract.search` or `rerank=true` for topical queries; offer semantic | S |
| OpenAlex `corpus=` | replaces `include_xpac` (Aug 2026); default core | help.openalex.org/api/deprecations.md | none today (we don't send include_xpac) | watch | – |
| S2 date filter | `publicationDateOrYear` works on relevance search | live probe, 2026-08+ hits (2026-10-14) | discovery.py search(); MCP server instructions text | adopt | S |
| S2 snippet search | passage-level retrieval over OA full text with license/source | live `/graph/v1/snippet/search` 200 (2026-10-14) | new tool in server.py / discovery.py | adopt | S |
| S2 recommendations | returns `[]` for a landmark paper | live (2026-10-14) | traverse_citations fallback ideas | skip | – |
| Exa publication category | 350M-pub index; card URLs + `entities.properties.doi`; `research paper` alias still works; `pdf/github/tweet` categories deprecated | changelog 2026-07-23; live probe $0.007 (2026-10-14) | skills/research/DOMAINS.md:14; researcher memory Exa gotchas | adopt (doc/routing edits) | S |
| Exa removed fields | `/research` retired 04-01; `resolvedSearchType`/`highlightScores` removed 05-01; crawl-date params ignored | changelog | exa_verify.py uses `/answer` only → unaffected | watch | – |
| Exa Agent / Ultra / Dynamic Highlights | agent API (06-16), MCP `agent_run` (07-01), Ultra ≤$20/run (09-24), `dynamic:true` beta (08-28) | changelog | possible deep_research replacement; not tested | watch | – |
| Gemini Deep Research | same preview IDs; adds `mcp_server`, `file_search`, collaborative planning | ai.google.dev deep-research doc (2026-10-14) | deep_research.py (unrunnable: no GEMINI_API_KEY) | skip / retire tool | S |
| Claude Code `/deep-research` | native multi-phase research with verifier | CC CHANGELOG 2.1.196–2.1.281 | could replace deep_research | watch: trial vs /research | S |
| CC WebFetch offset, WebSearch refill, MCP `request_timeout_ms`, URL elicitation | no 100k truncation; 100 searches/h refill; long MCP calls configurable | CC CHANGELOG (head 2.1.296) | .mcp.json for research-mcp (set timeout for fetch_paper); research skill notes | adopt (config) | S |
| Official OpenAlex MCP | hosted, OAuth, runs on own key; citing-works, OQL, reference checks | help.openalex.org/access/connector.md | complements traverse_citations / verify_citations | watch: trial (tool shapes UNVERIFIED) | S |
| CORE v3 | keyless search works (10/min); repository green-OA copies | live 200, totalHits 245,742 (2026-10-14) | papers.py fetch chain after OpenAlex content | watch (measure hit rate first) | M |
| PaddleOCR-VL-1.6 / MinerU2.5-Pro | lead OmniDocBench v1.7 (96.3 / 95.8) | OmniDocBench README (2026-10-14) | corpus/extract/pdf_marker_modal.py | watch: bake-off | M |
| Datalab OmniParseBench | new vendor bench; Datalab ≈ Gemini 3.8 Flash | datalab.to blog 2026-10-08 | none | skip | – |
| Unpaywall, EuropePMC 6.9, NCBI E-utils, arXiv export | no breaking change; NCBI keyless still 3 rps | live probes (2026-10-14) | papers.py, europepmc.py, pubmed.py, arxiv.py | none (optional NCBI_API_KEY for 10 rps) | – |
| NCBI announcements | rsync retired 2026-06-01; Taxonomy moved to Datasets (Oct 2026); PMC new search; E-utilities "remain available" | ncbiinsights posts 2026-03…08 | none | skip | – |
| Community scholarly MCP servers | wrappers over same APIs, ≤8★ | Exa search (2026-10-14) | – | skip | – |

## Breaking-change risks (silent degraders first)

- **OpenAlex keyless budget (live now).** Each search costs $0.001 of a $0.10 daily allowance. After ~100 searches/day `search_papers backend=openalex` returns 429 until UTC midnight, and openalex.py sleeps and retries four times first, which looks like a hang rather than an error. Any agent swarm using the S2 fallback hits this within one session.
- **OpenAlex `search` precision.** Keyword search matches full-text n-grams, so topical queries return very large, loosely relevant sets. Known-item lookups still work, but "S2 empty → OpenAlex" can return plausible-looking noise. Note this in the MCP instructions or switch to `title_and_abstract.search` / `rerank=true`.
- **Exa publication URLs.** Citations copied from `exa.ai/library/publication/...` are not primary sources. The hit can be a Zenodo or other secondary deposit instead of the arXiv or journal version (observed). verify_citations.py will not recognize these URLs as DOIs.
- **Exa deprecated categories.** `github` and `pdf` still return results today, but are flagged for removal. Routing memories that depend on `category:github` will break without notice.
- **MCP server instruction text is wrong** about S2 having no date filter. This steers agents to bioRxiv-only recency searches.
- **OpenAlex legacy controls.** A request mixing `corpus=` with `include_xpac` errors. Not used today; guard if added.
- **Gemini Deep Research** is still "preview" with April-2026 IDs. Expect a rename at GA, though the tool is already unrunnable here.
- **Claude Code Read** now errors on list-form PDF `pages` ("6,9,15"); it used to return only the first entry silently. Skills that pass lists need to change to per-range calls.
- **UNVERIFIED and unprobed:** Codex/Cursor native research features; CORE download success rate; OpenAlex MCP tool schemas; Europe PMC changes beyond version string 6.9; any S2 API changelog entry for 2026 (no public changelog found in this pass).

Context from coordinator (2026-10-14): research-mcp already has alphaXiv search, an arXiv-API save fallback, and bioRxiv pagination fixed (page size 30). These were not re-recommended.
