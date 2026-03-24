---
title: Research Tooling Field Report — 2026-03-24
date: 2026-03-24
type: operational
---

# Research Tooling Field Report — 2026-03-24

Session debrief from a multi-tool research workflow (ARC-AGI investigation).

## What Worked

- **`exec_command` (Bash)** — backbone for local state, direct HTML fetches, lightweight verification. Faster and less brittle than research MCPs for known URLs.
- **`multi_tool_use.parallel`** — high value for local reads and independent shell checks. Worth using aggressively for non-web calls.
- **`perplexity_search`** — good for finding official docs/pages quickly. Not a general-purpose search tool, but fast for targeted lookups.
- **`web_search_exa`** — useful for semantic paper discovery when adjacent literature needed, not exact URLs.
- **`search_literature` (scite)** — useful as stance check and metadata sanity, even when it only returns mentioning citations.

## What Broke or Was Noisy

| Tool | Issue | Severity |
|------|-------|----------|
| `search_papers` (S2) | Repeated 403 errors | High — had to manually switch to `backend:"openalex"` |
| `read_arxiv_paper` | Returns empty string for valid IDs | High — tool appears broken (note: paper-search MCP removed 2026-03-20, may be stale tooling) |
| `brave_web_search` | 429 rate limits on parallel use | Medium — fine for serial, bad for bursty |
| `firecrawl_scrape` | Credits exhausted | Blocking — no fallback |
| `verify_claim` | Citation set noisy — junk alongside real sources | Low — usable but not sole provenance |
| Heavy JS docs sites | Scraping MCPs struggle with Mintlify/Next.js | Medium — `curl \| perl \| rg` was more reliable |

## Recommended Research Sequence

Validated ordering — each step is cheaper/more reliable than the next:

1. `rg` / `grep` local repo state
2. Official docs / primary pages (direct fetch)
3. Semantic discovery with Exa or OpenAlex
4. Direct fetch of the primary source
5. scite / verification pass
6. Synthesize

**Key lesson:** parallel web MCP calls usually hurt (rate limits). Parallel local reads always help.

## Tooling Changes Wanted

1. `search_papers` should auto-fallback from S2 to OpenAlex on 403
2. `read_arxiv_paper` should fail loudly, not return ""
3. `verify_claim` should rank citations by directness and suppress irrelevant sources
4. Rate-limit / credit state should be queryable before using Brave or Firecrawl
5. A docs fetcher tuned for Mintlify/Next.js pages would eliminate shell fallback work

## Revisions

(none yet)

<!-- knowledge-index
generated: 2026-03-24T18:03:11Z
hash: 13e3ef1303da

title: Research Tooling Field Report — 2026-03-24

end-knowledge-index -->
