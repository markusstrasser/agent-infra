---
title: "Adversarial Review: The 'Just Embed Everything' Orthodoxy"
date: 2026-04-07
status: complete
tags: [embedding, retrieval, RAG, adversarial, search, BM25, GraphRAG, agents]
summary: "Recent papers (Mar-Apr 2026) showing when embedding search fails, why, and what beats it. Single-vector embeddings have proven theoretical limits, BM25 wins on structured/numerical data, grep-based agents outperform RAG, and GraphRAG mostly doesn't help."
---

## Adversarial Review: The "Just Embed Everything" Orthodoxy

**Target claim:** Dense embedding retrieval (single-vector, cosine similarity) is the right default for search/retrieval systems. Vector databases are necessary infrastructure. Embed your corpus, query by similarity, and retrieval is solved.

**Prior belief:** Widely held since ~2023. MTEB leaderboard progress, ease of deployment (embed once, query forever), and vendor marketing (Pinecone, Weaviate, Chroma) cemented embeddings as the default retrieval layer. Hybrid search (BM25 + dense) acknowledged as better but embeddings are still the core.

**Date:** 2026-04-07
**Search window:** 2026-03-24 to 2026-04-07 (with key supporting papers from Jan-Mar 2026)

---

### The Case Against

#### 1. Single-Vector Embeddings Have Proven Theoretical Limits

**Weller et al. (2025, revised Mar 2026)** — "On the Theoretical Limitations of Embedding-Based Retrieval" (arXiv:2508.21038v2)

The number of distinct top-k subsets a single-vector embedding can return is bounded by the embedding dimension. This isn't a training problem — it's a mathematical ceiling. Even directly optimizing on the test set with free parameterized embeddings hits this wall. Created the LIMIT benchmark: SOTA models fail on extremely simple retrieval tasks because the required number of distinct rankings exceeds what the dimension can encode.

This is the strongest paper in the set. It's not "embeddings could be better." It's "embeddings *cannot* do this, provably."

**Archish et al. (Mar 31, 2026)** — "On Strengths and Limitations of Single-Vector Embeddings" (arXiv:2603.29519)

Follow-up to Weller. Key findings:
- Dimensionality alone doesn't explain failures (2k+1 dimensions suffice for top-k theoretically, but models fail anyway)
- **Domain shift and relevance misalignment** are the major contributors — the embedding's notion of "similar" diverges from the task's notion of "relevant"
- Finetuning helps but causes **catastrophic forgetting** (MSMARCO drops >40%)
- Multi-vector representations are markedly better — but nobody uses them in production because they're slow
- **"Drowning in documents" paradox:** as corpus grows, relevant documents are drowned out because embedding similarities behave like noisy statistical proxies. Single-vector is more susceptible than multi-vector.

[SOURCE: arXiv:2603.29519, abstract verified]

#### 2. BM25 Beats Dense Retrieval on Structured/Numerical Data

**Akarsu et al. (Apr 2, 2026)** — "From BM25 to Corrective RAG: Benchmarking Retrieval Strategies for Text-and-Table Documents" (arXiv:2604.01733)

10 retrieval strategies benchmarked on 23,088 financial QA queries over 7,318 mixed text-and-table documents:
- **BM25 outperforms SOTA dense retrieval on financial documents** — "challenging the common assumption that semantic search universally dominates"
- Best result: hybrid retrieval + neural reranking (Recall@5 = 0.816, MRR@3 = 0.605) — but the dense component alone loses to BM25
- Query expansion (HyDE, multi-query) provides **limited benefit for precise numerical queries**
- Contextual retrieval yields consistent gains

This directly mirrors our session experience: searching for "Broad Institute" (an entity name, not a concept) in a corpus of emails. BM25 would find the exact string. Dense retrieval returns "shipping notification" vibes.

[SOURCE: arXiv:2604.01733, abstract verified]

#### 3. Negation Causes "Semantic Collapse" in Vector Space

**Sahoo et al. (Mar 18, 2026)** — "Negation is Not Semantic: Diagnosing Dense Retrieval Failure Modes" (arXiv:2603.17580)

The most damning finding with a great name. On TREC 2025 BioGen (biomedical contradiction detection):
- Adversarial dense retrieval for contradiction detection: **MRR 0.023** (catastrophic)
- Cause: **Semantic Collapse** — "negation signals become indistinguishable in vector space"
- "Drug X treats condition Y" and "Drug X does NOT treat condition Y" map to nearly identical embeddings
- Their fix: abandon dense retrieval entirely for contradictions, use **decoupled BM25 backbone** (Weighted MRR 0.790)
- Ranked 2nd on TREC Task A, 3rd/50 on Task B — with BM25, not embeddings

This is particularly relevant for biomedical/health search (our domain). Searching for evidence AGAINST a claim with embeddings retrieves evidence FOR it.

[SOURCE: arXiv:2603.17580, abstract verified]

#### 4. Grep-Based Agents Outperform Embedding Retrieval

**Cao et al. (Mar 20, 2026)** — "Coding Agents are Effective Long-Context Processors" (arXiv:2603.20432)

Agents using ripgrep over raw files outperform embedding-based retrieval on BrowseComp-Plus benchmark at 100K+ documents, up to 3T tokens. The agent writes grep commands, reads results, and iterates. No embeddings, no vector DB, no index.

Already documented in meta `search-retrieval-architecture.md`. This session's own experience confirms: 4 failed embedding searches for "Broad Institute email" — would have been found instantly with `grep -i "broadinstitute\|ewalker" indexed/gmail_parsed.json`.

**Wang et al. (Jan 30, 2026)** — "GrepRAG: An Empirical Study and Optimization of Grep-Like Retrieval for Code Completion" (arXiv:2601.23254)

Systematic study. LLMs autonomously generate ripgrep commands to retrieve context. Results:
- Naive grep-RAG **matches sophisticated graph-based baselines** on CrossCodeEval
- Effectiveness comes from "lexically precise code fragments spatially closer to the completion site"
- Limitations: noisy matches from high-frequency keywords, context fragmentation from rigid truncation
- GrepRAG (grep + lightweight post-processing): **7-15% relative improvement over SOTA** on code exact match

The pattern: grep finds the exact thing; embeddings find things that are sort-of-like the thing.

[SOURCE: arXiv:2601.23254, abstract verified]

#### 5. GraphRAG Mostly Doesn't Help (And Costs 10-100x More)

**Tuora et al. (Feb 6, 2026)** — "UnWeaving the knots of GraphRAG — turns out VectorRAG is almost enough" (arXiv:2603.29875)

Title says it all. Key arguments:
- GraphRAG has "orders of magnitude increased componential complexity" for index creation
- Graph retrieval relies on heuristics
- Their alternative (UnWeaver): entity-based decomposition into standard vector retrieval recovers most of GraphRAG's benefits without the graph
- Conclusion: the problem isn't that vectors can't represent the information — it's that chunks mix too many concepts into one vector. Disentangle chunks into entities → vector search works again.

**Xiang et al. (Jun 2025, revised Feb 22, 2026)** — "When to use Graphs in RAG" (arXiv:2506.05690v3)

Benchmark (GraphRAG-Bench) finding that **GraphRAG frequently underperforms vanilla RAG on many real-world tasks.** Benefits are limited to hierarchical knowledge retrieval and multi-hop reasoning — exactly the cases benchmarks like HotPotQA test. For simple factual retrieval (the majority of queries in practice), the graph adds cost without benefit.

[SOURCE: arXiv:2506.05690v3, arXiv:2603.29875, abstracts verified]

#### 6. Scaling Embedding Dimension Has Diminishing — and Sometimes Negative — Returns

**Killingback et al. (Feb 4, 2026)** — "Scaling Laws for Embedding Dimension in Information Retrieval" (arXiv:2602.05062)

Comprehensive analysis across two model families:
- Performance follows a power law with embedding dimension — diminishing returns
- For evaluation tasks aligned with training: improvement continues but flattens
- **For misaligned tasks: performance DEGRADES with larger embedding dimensions**

This means bigger embeddings don't uniformly help. If your query type doesn't match training distribution (entity lookup in a personal email corpus vs. semantic passage retrieval), more dimensions can make things worse.

[SOURCE: arXiv:2602.05062, abstract verified]

---

### Strength Assessment

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Evidence quality | **HIGH** | Theoretical proofs (Weller), TREC competition results (Sahoo), controlled benchmarks (Akarsu, Wang), multiple independent groups |
| Target was genuinely believed | **YES** | "Just use embeddings" is default advice in every RAG tutorial, vendor pitch, and LLM app framework |
| Structural, not anecdotal | **YES** | Mathematical ceiling (dimension bounds), systematic benchmarks, identified mechanism (semantic collapse, drowning paradox) |
| Critique is unanswered | **MOSTLY** | Multi-vector and late interaction models (ColBERT) partially address; adoption is low due to cost/complexity |
| Constructive null | **YES** | Multiple alternatives identified: BM25 for exact/structured, grep for agents, hybrid+rerank for general, entity decomposition for multi-concept chunks |

---

### What Survives

Single-vector embeddings are still the right tool for:

1. **Conceptual/semantic queries** — "what did I think about loneliness in my 30s?" — where the query IS a topic and you want vibes, not exact matches
2. **Cross-lingual retrieval** — BM25 can't match "Einsamkeit" to "loneliness"
3. **Image/multimodal search** — no lexical alternative exists for visual similarity
4. **First-stage candidate generation** in a multi-stage pipeline — fast ANN over millions of documents, then rerank. But the reranker does the real work.

The claim that survives: embeddings are useful as a cheap, fast recall layer. The claim that dies: embeddings are sufficient for retrieval, or that embedding similarity = relevance.

---

### Verdict: **WEAKENED**

Not demolished — embeddings still have valid uses. But the "embed everything, query by cosine similarity" orthodoxy is significantly weakened by converging evidence from theory (provable dimension bounds), practice (BM25 wins on structured data), production (semantic collapse on negation), and agent systems (grep outperforms).

**The emerging consensus (early 2026):**
- Hybrid (BM25 + dense) is minimum viable, not optional
- Reranking does the actual relevance work; first-stage retrieval is just candidate generation
- For agents: grep/ripgrep is better than embeddings for known-item retrieval
- For entity/metadata queries: structured filters beat semantic similarity
- For growing corpora: single-vector embeddings degrade ("drowning paradox")
- GraphRAG is mostly unnecessary complexity for non-multi-hop tasks

**What this means for selve:** The search pipeline already has `--hybrid --rerank`. The missing pieces are structured metadata filters (`--from`, `--participant`, `--type`) and a grep-first routing layer for entity queries. The embedding index isn't broken — it's being asked questions it can't answer.

---

### Sources & Search Log

**Papers cited (8):**

| # | Paper | arXiv | Date | Key finding |
|---|-------|-------|------|-------------|
| 1 | Weller et al., "Theoretical Limitations of Embedding-Based Retrieval" | 2508.21038v2 | Aug 2025 (rev. Mar 12, 2026) | Mathematical ceiling on single-vector retrieval capacity |
| 2 | Archish et al., "Strengths and Limitations of Single-Vector Embeddings" | 2603.29519 | Mar 31, 2026 | Drowning paradox, catastrophic forgetting on finetuning, multi-vector gap |
| 3 | Akarsu et al., "From BM25 to Corrective RAG" | 2604.01733 | Apr 2, 2026 | BM25 beats dense on financial/tabular data |
| 4 | Sahoo et al., "Negation is Not Semantic" | 2603.17580 | Mar 18, 2026 | Semantic collapse: MRR 0.023 for contradiction detection, BM25 fix |
| 5 | Cao et al., "Coding Agents are Effective Long-Context Processors" | 2603.20432 | Mar 20, 2026 | Agents with grep outperform embedding retrieval at 100K+ docs |
| 6 | Wang et al., "GrepRAG" | 2601.23254 | Jan 30, 2026 | Grep-based retrieval matches graph baselines, +7-15% with post-processing |
| 7 | Tuora et al., "UnWeaving GraphRAG — VectorRAG is almost enough" | 2603.29875 | Feb 6, 2026 | GraphRAG complexity unjustified; entity decomposition + vectors suffices |
| 8 | Killingback et al., "Scaling Laws for Embedding Dimension" | 2602.05062 | Feb 4, 2026 | Larger dimensions can degrade performance on misaligned tasks |

**Supporting (not directly cited):**

| Paper | arXiv | Relevance |
|-------|-------|-----------|
| Xiang et al., "When to use Graphs in RAG" | 2506.05690v3 (rev. Feb 2026) | GraphRAG underperforms vanilla RAG on many tasks |
| Randl et al., "RAG-E: Retriever-Generator Failure Modes" | 2601.21803 | End-to-end explainability framework for RAG failures |
| Xu et al., "Dense Retrievers Can Fail on Simple Queries" | 2506.08592 (EMNLP 2025) | Granularity dilemma in embeddings |
| Madhu et al., "HypRAG: Hyperbolic Dense Retrieval" | 2602.07739 | Alternative geometry for hierarchical data |

**Blog posts (practitioner signal):**

| Post | Date | Signal |
|------|------|--------|
| "Is RAG Dead? Long Context, Grep, and the End of the Mandatory Vector DB" (AkitaOnRails) | Apr 6, 2026 | Practitioner synthesis of Cao et al. |
| "Why Coding Agents Still Use grep as Their Search Backbone" (grapeot) | Mar 27, 2026 | Survey of grep vs. semantic in coding agents |
| "Is grep really better than a vector DB?" (Sara Zan) | Mar 15, 2026 | Nuanced analysis of when each wins |

**Search log:**

| # | Tool | Query | Hits | Signal |
|---|------|-------|------|--------|
| 1 | Exa | "arxiv dense embedding retrieval fails BM25 negative results" | 10 | HIGH — 5 directly relevant papers |
| 2 | Exa | "arxiv RAG retrieval failure modes production" | 10 | MED — mix of papers and blog posts |
| 3 | S2 | "embedding retrieval failure modes limitations" | 15 | MED — some relevant, some tangential |
| 4 | Exa | "arxiv 2026 coding agents outperform RAG grep" | 8 | HIGH — Cao et al. + GrepRAG + blog synthesis |
| 5 | Exa | "arxiv 2026 GraphRAG limitations critique" | 8 | HIGH — UnWeaver + GraphRAG-Bench + "When to use Graphs" |
| 6 | Exa crawl | 5 arxiv abstracts | 5 | Verified all claims |
| 7 | Exa crawl | 3 arxiv abstracts | 3 | Verified remaining claims |
| 8 | meta-knowledge | "embedding search quality" + "search retrieval accuracy" | 30 | Confirmed prior findings (Cao, Anthropic contextual retrieval) |

**Total tool calls:** 11 (within Standard budget of 10-20). No paper pipeline needed — all claims are from abstracts of retrieved papers, which are primary sources for the claims being made (the papers' own findings).

<!-- knowledge-index
generated: 2026-04-07T23:01:41Z
hash: 1507dda2b2f1

title: Adversarial Review: The 'Just Embed Everything' Orthodoxy
status: complete
tags: embedding, retrieval, RAG, adversarial, search, BM25, GraphRAG, agents

end-knowledge-index -->
