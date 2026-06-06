---
title: Search Tool Thinning — Perplexity vs Exa vs Parallel
date: 2026-06-06
status: active
tags: [mcp, search, exa, perplexity, parallel, benchmarks, routing]
---

# Search Tool Thinning — Perplexity vs Exa vs Parallel

## Question

Should we keep Perplexity, Exa, and Parallel globally available in Codex, or thin/scope them by project?

## Short Verdict

Thin by role, not by benchmark winner.

- Keep **Exa** as the default source-finding and retrieval tool.
- Keep **Parallel** for hard multi-hop/background research, but it does not need to be a first-line search tool in every session.
- Demote **Perplexity** from global always-on unless we actively rely on its `ask`/`reason` behavior in that project. It overlaps most with normal model+search workflows and has weaker local probe results than Exa for source discovery.

Best near-term config: **global Exa, project-scoped Parallel and Perplexity** for research-heavy repos. If global convenience matters more than startup thinning, keep Parallel global and demote only Perplexity.

## Evidence

### Independent-ish search API benchmark

AIMultiple's May 25, 2026 benchmark is the closest current third-party comparison found, but it is still a trade-press benchmark with an LLM judge. It tested 8 APIs on 100 AI/LLM-domain queries, 5 results each, about 4,000 results total.

Results:

| API | Agent Score | Latency |
|---|---:|---:|
| Brave | 14.89 | 669 ms |
| Firecrawl | 14.58 | 1,335 ms |
| Exa | 14.39 | about 1.2 s |
| Parallel Search Pro | 14.21 | 13.6 s |
| Tavily | 13.67 | 998 ms |
| Parallel Search Base | 13.5 | about 2.9 s |
| Perplexity | 12.96 | 11 s+ |

Interpretation: Exa and Parallel Pro are in the top statistical tier; Perplexity was weaker in this raw-search-style comparison. Do not over-weight exact scores: the domain is AI/LLM queries, the judge is GPT-5.2, and latency is from a single environment.

Source: https://aimultiple.com/agentic-search

### Exa current pricing and claims

Current Exa pricing says:

- Search: $7/1k requests, contents/highlights for up to 10 results included.
- Deep Search: $12-$15/1k requests.
- Contents: $1/1k pages.
- Answer: $5/1k requests.
- Agent: $0.025-$2.00/run fixed effort.

Exa's own evals claim strong SimpleQA and MSMARCO retrieval performance, but these are vendor evals. More useful for us: Exa has a clear differentiated product shape: semantic/source discovery, code/docs search, people/company search, contents, and URL crawling.

Sources:
- https://exa.ai/pricing
- https://exa.ai/docs/changelog/pricing-update
- https://exa.ai/blog/api-evals
- https://exa.ai/blog/people-search-benchmark

### Perplexity current pricing and claims

Current Perplexity pricing says:

- Search API: $5/1k requests, raw web results, no token cost.
- Agent API `web_search`: $0.005/invocation; `fetch_url`: $0.0005/invocation.
- Sonar: token costs plus request fee. Low context request fees are $5/1k for Sonar and $6/1k for Sonar Pro/Reasoning Pro; medium/high cost more.
- Sonar Deep Research adds citation tokens, search query fees, and reasoning token fees.

Perplexity's research post claims a large index, hybrid retrieval/ranking, p50 Search API latency of 358 ms, and better quality than Exa/Brave/SERP-based APIs on SimpleQA, FRAMES, BrowseComp, and HLE. This is a vendor eval, but it is at least accompanied by an open `search_evals` harness.

For our stack, Perplexity's differentiated value is not raw retrieval. It is quick synthesized answers and reason/search in one call. That is useful, but less essential now that Codex/Gemini/Claude can pair strong models with Exa/Brave/Parallel.

Sources:
- https://docs.perplexity.ai/docs/getting-started/pricing
- https://docs.perplexity.ai/docs/sonar/quickstart
- https://research.perplexity.ai/articles/architecting-and-evaluating-an-ai-first-search-api

### Parallel current pricing and claims

Current Parallel pricing says:

- Search API: $0.005/request for 10 results.
- Extract API: $0.001/request.
- Chat API: $0.005/request.
- Task API: $0.005-$2.40/request, depending on processor.
- Task processors range from Lite $5/1k to Ultra8x $2,400/1k.

Parallel's strongest public evidence is on deep-research style benchmarks, not simple retrieval. On DeepSearchQA it claims:

- April 2026: Ultra 70%, Ultra2x 77%, Ultra4x 81%, Ultra8x 82%; GPT-5.4 with code execution 63%, Gemini 3.1 Pro 62%, Opus 4-6 58%, Perplexity Sonar Pro 28%, Exa Search Deep Reasoning 18%.
- December 2025: Ultra2x 72.6% vs Gemini Deep Research 64.3%, GPT-5.2 Pro 61%, Exa 30%, Perplexity Deep Research 25%.

Parallel also has search benchmarks where it claims strong agent outcomes using a common GPT-5.4 harness, but these are Parallel-created benchmarks. The real takeaway is architectural: Parallel's Task API keeps intermediate data in a sandbox/code state instead of stuffing every search/extract result back into the model context. That is genuinely relevant for long multi-hop research.

Sources:
- https://parallel.ai/ai/pricing
- https://parallel.ai/blog/deep-research
- https://parallel.ai/blog/deepsearch-qa
- https://parallel.ai/blog/search-api-benchmark
- https://parallel.ai/benchmarks
- https://arxiv.org/abs/2601.20975

### Our local probe

The May 19 local 5-query probe compared Gemini search, Perplexity `_ask`, and Exa `web_search_exa`.

Net result:

- Exa: 4/5 effective; best at canonical source discovery, especially fresh paper discovery.
- Perplexity: 2/5 effective; good for a biomedical numeric lookup, but one hard refusal on a simple release-version query.
- Gemini: 3/5 effective, but biomedical safety-filter failure makes it unsafe as sole source for genomics/phenome.

Source: `research/gemini-3.5-flash-vs-exa-vs-perplexity-probe.md`

## Decision Matrix

| Job | Preferred tool | Why |
|---|---|---|
| Find the canonical page/paper/docs | Exa | Best local evidence and differentiated source discovery. |
| Crawl/read a known URL from search results | Exa or Parallel Extract | Exa is already enough for most; Parallel Extract is useful if we standardize around Parallel task flows. |
| Quick grounded answer | Perplexity Ask or model+Exa | Perplexity is convenient, but not unique enough to justify global startup by itself. |
| Multi-hop exhaustive research | Parallel Task | Public benchmarks and architecture fit this job better than raw search loops. |
| Benchmark/source triangulation | Exa + Brave, then optionally Parallel | Independent indexes matter more than one vendor score. |
| Biomedical exact lookup | Perplexity or domain MCPs | Local probe favors Perplexity over Gemini; domain MCPs should beat both when available. |

## Thinning Recommendation

1. **Global**
   - Keep `exa`.
   - Keep `brave-search` if we want an independent index baseline.
   - Keep `context7`, `node_repl`, and authenticated remote `scite` as they solve different problems.

2. **Project-scoped**
   - Move `perplexity` out of global and enable only in `agent-infra`, `intel`, `phenome`, and `genomics` if still desired.
   - Move `parallel` out of global unless we want its Task API available everywhere. It is valuable, but its best use is research-heavy work, not every coding session.

3. **Routing rule**
   - Default: Exa first.
   - Escalate to Parallel when the question needs multi-hop entity collation, exhaustive set building, or background research with structured output.
   - Use Perplexity when a synthesized answer is the deliverable and the citations are enough, or for biomedical exact-number lookups where Gemini/model search is unreliable.

## Why Not Delete Perplexity Entirely?

Do not delete it yet. It still has two live niches:

- Quick answer-with-citations workflow.
- Biomedical exact lookup fallback, based on the local probe.

But those are project/workflow-specific niches, not a strong case for global always-on MCP startup.

## Implementation Sketch

If we thin now:

1. Backup `~/.codex/config.toml`.
2. Remove global `[mcp_servers.perplexity]`.
3. Either keep global `[mcp_servers.parallel]` for one more week or remove it globally and add it to project `.mcp.json` / generated `.codex/config.toml` only for research-heavy repos.
4. Run:
   - `uv run python3 scripts/codex_parity_sync.py --check`
   - `uv run python3 scripts/codex_mcp_smoke.py --project agent-infra --timeout 25`
   - repeat smoke for `intel`, `genomics`, `phenome`

My call: remove Perplexity from global first; leave Parallel global unless startup logs show it is a meaningful contributor. If still too much MCP startup noise, demote Parallel next.

