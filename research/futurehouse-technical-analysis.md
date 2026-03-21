# FutureHouse Technical Analysis

**Date:** 2026-03-19
**Tier:** Deep
**Question:** Technical architecture, products, open source, and transferable patterns from FutureHouse's AI-for-science agent platform

## Company Overview

FutureHouse is a philanthropically-funded nonprofit (founded 2023, ~23 employees, San Francisco) building AI agents for scientific research. CEO Sam Rodriques (TIME100 AI 2025). 10-year mission: build semi-autonomous AIs for scientific research.

Key products: PaperQA2 (literature RAG agent), WikiCrow (Wikipedia-style article generation), ContraCrow (contradiction detection), Robin (multi-agent scientific discovery), Aviary/LDP (agent training framework), ether0 (24B chemistry reasoning model), FutureHouse Platform (hosted agent service with Crow/Falcon/Owl/Phoenix/Finch agents).

## PaperQA2 Architecture

### The 7-Stage Retrieval Pipeline

1. **Paper Discovery** — Agent generates keyword queries with optional year ranges. Semantic Scholar returns ~12 candidates. Papers parsed via GROBID (section-aware) or PyMuPDF.
2. **Chunking** — ~750-token chunks with 750-char overlap. GROBID enables semantic section-level chunking.
3. **Hybrid Embedding** — Dense vectors (text-embedding-3-small default) concatenated with sparse keyword encodings (256 dimensions via tiktoken modulus-encoding).
4. **Initial Ranking** — Cosine similarity, top-k=30 chunks.
5. **RCS (Reranking & Contextual Summarization)** — LLM maps over top-k chunks in parallel, producing JSON with query-specific summary + 0-10 relevance score. Compresses 2,250-token chunks to 200-400 tokens. THE key innovation.
6. **Citation Traversal** (optional) — Forward/backward citations via S2/Crossref when RCS score >= 8. Overlap filter (alpha=1/3) prevents explosion.
7. **Answer Generation** — Top 5-15 summaries into final prompt. Wikipedia-style with inline citations. Can refuse via "I cannot answer."

### Agent Design

4 tools: PaperSearch, GatherEvidence, GenerateAnswer, CitationTraversal. Invoked in any order, iteratively. Agentic > fixed pipeline (p=0.015). High-performing runs: 1.26 searches, 0.46 citation traversals per question.

Metadata enrichment: Semantic Scholar (citations, publication), Crossref (DOI, retraction check), Unpaywall (open access).

Default models: gpt-4o-2024-11-20 (answer), text-embedding-3-small (embedding). All LiteLLM-compatible.

### Benchmarks

- LitQA2 (248 questions): Precision 85.2% vs human 64.3% (p=0.0029). Accuracy 66.0% vs human 63.1% (NS).
- RAG-QA Arena science benchmark: #1 (March 2025).
- WikiCrow: 86.1% citation precision vs Wikipedia 71.2% (p=0.0013).
- ContraCrow: ROC AUC 0.842, found ~1.64 validated contradictions per paper.

## What's Genuinely Novel

1. **RCS** — Simultaneous summarization + reranking via LLM. Compresses context 5x while improving relevance. Ablation: removing it drops accuracy with p<0.001.
2. **Calibrated refusal** — 21.9% refusal rate produces 85.2% precision. Structural "I cannot answer" option.
3. **Citation graph as retrieval tool** — With overlap-fraction filter for convergence.
4. **Aviary/LDP** — Formalizing agents as Language Decision Processes enables RL training. 8B models matching frontier at 100x less cost.
5. **ether0 emergent reasoning** — RL-trained model spontaneously invents terminology and reasoning patterns.

## Open Source

| Repo | What | License |
|------|------|---------|
| paper-qa | Core RAG agent (7K+ stars) | Apache 2.0 |
| aviary | Agent gym (5 environments) | Apache 2.0 |
| ldp | Language Decision Process framework | Apache 2.0 |
| robin | Multi-agent scientific discovery | Apache 2.0 |
| WikiCrow | Wikipedia article generation | Apache 2.0 |
| llm-client | Unified LLM interface | Apache 2.0 |
| ether0 | 24B chemistry model + rewards | Apache 2.0 |

OPEN: Algorithms, model weights, training code.
CLOSED: Production infrastructure (MongoDB/PostgreSQL/Redis/K8s), Crow/Falcon/Owl/Phoenix/Finch agent implementations (API-only).

## Transferable Patterns

1. **RCS over raw chunk injection** — Summarize-to-query before synthesis step. Our gap: research-mcp passes raw text to Gemini without compression/scoring.
2. **Calibrated refusal** — Explicit "insufficient information" option. Our gap: researcher skill hedges but always answers.
3. **Citation graph retrieval** — Add traverse_citations tool using S2 API with overlap filter.
4. **Agentic conditional branching** — Value is in conditional branching (search more if insufficient), not volume of actions.
5. **Hybrid dense+sparse embedding** — For any local paper index we build.

## Sources

- arXiv:2409.13740 — PaperQA2 paper (Skarlinski et al., Sep 2024)
- arXiv:2412.21154 — Aviary paper (Dec 2024)
- github.com/Future-House/ — All repos
- futurehouse.org — Announcements, platform details
- unite.ai — Platform launch coverage
- Exa company_research — Company data
