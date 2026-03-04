# Exa's Recommended Skill vs Our Setup (2026-03-04)

**Context:** Exa published a "Research Paper Search Agent Skill" — single MCP tool (`web_search_advanced_exa` with `category: "research paper"`) + Claude skill for paper search. Comparison against our multi-source architecture.

---

## Their approach

- Single-tool MCP: `web_search_advanced_exa` only
- Skill locks to `category: "research paper"`
- Token isolation via subagent instruction in the skill
- Filter documentation hardcoded in skill text

## Our approach

- 7-tool Exa MCP (web_search, advanced, crawling, company, people, deep_researcher)
- papers-mcp for academic search (S2, PubMed, arXiv, bioRxiv, Google Scholar)
- Brave + Perplexity as independent triangulation
- Researcher skill orchestrates across all sources
- Subagent delegation enforced architecturally (global CLAUDE.md)

## Verdict: ours is better

| Dimension | Exa skill | Our setup |
|-----------|-----------|-----------|
| Academic paper quality | Websearch with category hint | Dedicated APIs (S2/PubMed) — 80/100, zero hallucinations in our benchmark |
| Hallucination rate | Websearch: 3 hallucinations per benchmark run | Academic tools: 0 per run |
| Tool coverage | 1 tool | 7 Exa + 5 academic + Brave + Perplexity |
| Entity enrichment | Not possible | company_research, people_search, deep search |
| Triangulation | Single index | 3 independent indexes (Exa, Brave, Perplexity) |
| Token isolation | Skill instruction (unreliable per tool-use research) | Architecture (global rules + subagent patterns) |
| Structured extraction | Not used | deep search `outputSchema` with per-field grounding |

## What was worth adopting

Not the skill — the new API capabilities behind it:

1. **`type: "deep"`** on `/search` — query expansion + parallel sub-searches + per-result summaries. Synchronous, 2-5s. $0.015/req (3x neural).
2. **`outputSchema` + `output.grounding`** — structured JSON extraction with per-field citations and confidence (low/medium/high). Replaces post-hoc LLM extraction for entity enrichment.
3. **`additionalQueries`** — supply domain-specific query variations instead of relying on Exa's auto-expansion.
4. **Research API usage-based pricing** — ~$0.13/task typical (was flat $5/operation).

All already accessible through our existing MCP tools. Documented in `agentic-search-api-comparison.md` §11 with routing table.

## Sources

- Exa Search API docs: https://exa.ai/docs/reference/search
- Exa Research API docs: https://exa.ai/docs/reference/exa-research
- Exa Deep changelog: https://exa.ai/docs/changelog/new-deep-search-type
- Our benchmark: `benchmarks/comparison-report.md` (EBF3 query, §10 of search comparison)
