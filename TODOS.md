# Meta Project Backlog

## Alpha Features to Evaluate

### Gemini 2.5 Computer Use Model (Preview)
- [ ] Evaluate for browser automation vs existing Playwright skills
- [ ] Test on SEC/EDGAR navigation automation
- [ ] Compare latency/cost vs scripted Playwright approach
- [ ] Reference: https://ai.google.dev/gemini-api/docs/models/gemini-2.5-computer-use-preview

### Gemini 3.1 Flash-Lite Preview
- [ ] Update model strings in intel/tools/llm_check.py
- [ ] Benchmark cost/quality vs gemini-3-flash-preview
- [ ] Update model-guide skill with new model info
- [ ] Released March 3, 2026

### Gemini thinking_level Parameter (Gemini 3+)
- [ ] Add thinking_level control to claim_extraction.py (use "low" for structured extraction)
- [ ] Add thinking_level control to daily_synthesis.py (use "high" for analysis)
- [ ] Requires migrating Gemini calls from llmx subprocess to direct SDK
- [ ] Cost optimization: ~30% savings on low-thinking tasks

## In Progress

### Google Trends API (Alpha)
- [x] Create download_google_trends_api.py with official API support
- [x] Add OAuth2 authentication flow
- [x] Implement fallback to scraping when API unavailable
- [x] Add to pyproject.toml dependencies
- [ ] Apply for alpha access at https://developers.google.com/search/apis/trends
- [ ] Download client.json to intel/config/
- [ ] Test end-to-end with real API credentials
- [ ] Compare data consistency with scraped data

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

### Monitor
- [ ] RLM "Learned Context Folding" replication status
- [ ] MCP protocol Tasks spec (SEP-1686) draft status
- [ ] Agent SDK v0.2.x stability (currently v0.1.x, 27 releases in 2 months)
