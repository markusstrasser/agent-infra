# Meta Project Backlog

## Alpha Features to Evaluate

### Gemini 2.5 Computer Use Model (Preview)
- [ ] Evaluate for browser automation vs existing Playwright skills
- [ ] Test on SEC/EDGAR navigation automation
- [ ] Compare latency/cost vs scripted Playwright approach
- [ ] Reference: https://ai.google.dev/gemini-api/docs/models/gemini-2.5-computer-use-preview

### Gemini 3.1 Flash-Lite Preview — DONE 2026-03-05
- [x] Update model strings in intel/tools/llm_check.py — Set as default for `verify` task ($0.25/$1.50 vs $2/$12)
- [x] Add FAST_MODELS dict for --fast flag option across all tasks
- [x] Update daily_synthesis.py default to Flash-Lite
- [x] Update model-guide skill with pricing, benchmarks, prompting tips
- **Benchmarks:** 34 intelligence (vs Flash 46, Pro 57), 389 tok/s (99th percentile), $0.25/$1.50/M
- **Verdict:** Use for high-volume simple tasks; Flash non-reasoning is strictly better for complex work

### Gemini thinking_level Parameter (Gemini 3+)
- [ ] Add thinking_level control to claim_extraction.py (use "low" for structured extraction)
- [ ] Add thinking_level control to daily_synthesis.py (use "high" for analysis)
- [ ] Requires migrating Gemini calls from llmx subprocess to direct SDK
- [ ] Cost optimization: ~30% savings on low-thinking tasks

## In Progress

### Google Trends API (Alpha) — BLOCKED
- [x] Create download_google_trends_api.py with official API support
- [x] Add OAuth2 authentication flow
- [x] Implement fallback to scraping when API unavailable
- [x] Add to pyproject.toml dependencies
- [ ] ~~Apply for alpha access~~ — **Requires organization/corporate account**, individual access not available
- [ ] ~~Download client.json~~ — Blocked pending alpha access
- **Fallback:** Old scraping method (`download_google_trends.py`) still works — verified 2026-03-05
- **Revisit:** If/when API opens to individuals or org access obtained

## Architecture Improvements

### Cost Optimization
- [ ] Add effort parameter tiers to orchestrator (Claude Sonnet 4.6)
- [ ] Set CLAUDE_CODE_EFFORT_LEVEL per task type
- [ ] Use Haiku for search-heavy subagents (CLAUDE_CODE_SUBAGENT_MODEL)

### Hook Telemetry
- [ ] Deploy PostToolUseFailure JSONL logger
- [ ] Measure false positive rates for all hooks
- [ ] Retire hooks with <1 trigger/week after 30 days

## Research

### Pending Papers (from maintenance-checklist.md)
- [ ] arXiv:2506.04018 — AgentMisalignment (capability-misalignment scaling)
- [ ] arXiv:2601.20103 — TRACE (reward hacking detection, 37% undetectable)
- [ ] arXiv:2509.25370 — AgentDebug (targeted correction +24% vs blind retry)
- [ ] arXiv:2602.16943 — Mind the GAP (check S2 index)

### paper-search MCP: No Date Filtering, Poor Relevance for Bio
- [ ] `search_biorxiv` / `search_arxiv` return irrelevant results for domain queries — no date filter, keyword matching picks up unrelated fields (neuroscience for "variant interpretation", computer vision for "genome foundation model")
- [ ] Evaluate fix options: (1) add `start_date`/`end_date` params to paper-search MCP, (2) replace with Exa `category: "research paper"` + date filter for weekly scans, (3) use bioRxiv API directly (`https://api.biorxiv.org/details/biorxiv/{start}/{end}`) which supports date ranges
- [ ] For weekly genomics surveillance, GitHub releases API was most reliable for tool versions; Exa with specific tool names for preprints. Broad sweep queries via paper-search are currently useless.
- **Evidence:** 2026-03-20 genomics weekly scan — 20 results from bioRxiv/arXiv, 0 relevant to WGS/genomics

### Monitor
- [ ] RLM "Learned Context Folding" replication status
- [ ] MCP protocol Tasks spec (SEP-1686) draft status
- [ ] Agent SDK v0.2.x stability (currently v0.1.x, 27 releases in 2 months)
