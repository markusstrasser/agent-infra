# Search & Retrieval Architecture

Research conducted 2026-02-28. Evaluated CAG (Cache-Augmented Generation) vs embedding-based retrieval for our tooling.

## Current Setup

### EMB Pipeline (`~/Projects/emb`)
- **Model:** `gte-modernbert-base` (768d, 149M params, 8K context)
- **Search:** Dense + BM25 hybrid (RRF fusion), cross-encoder reranking (`Qwen3-Reranker-0.6B`), freshness decay
- **Chunking:** Sentence-aware, multi-scale (200/500 word) with parent dedup
- **Contextual retrieval:** LLM-generated context prepended per Anthropic's method
- **Speed:** ~50ms per query. Embedding: 50-200 entries/s on M3 Max
- **Used by:** selve (personal knowledge), research-mcp (research corpus)

### CAG Implementation (`research-mcp/src/research_mcp/cag.py`)
- Stuffs full paper texts into Gemini's 1M context window
- Auto-tiers: `gemini-3-flash-preview` for broad sweeps (>30 papers), `gemini-3-flash-preview` for focused analysis
- ~930K usable tokens after reserving for prompt + output
- Called via `mcp__research__ask_papers` in researcher skill

## Decision Framework: When to Use What

```
Query arrives
    │
    ├─ Corpus ≤ 200K tokens? ──→ CAG directly (skip embeddings entirely)
    │                             Use Gemini Flash-Lite for simple lookups
    │
    ├─ Text corpus as files + agent has shell? ──→ Agent shell navigation
    │   grep/rg/sed/Python, no index needed       Best above ~500K tokens
    │   Don't add retrieval alongside              $0.11-0.83/query
    │
    ├─ Simple factual / keyword? ──→ EMB hybrid search (BM25 + dense)
    │   "What is X's revenue?"        Fast, cheap, high precision
    │   "Find papers about Y"
    │
    ├─ Moderate complexity? ──→ EMB search + reranking
    │   "Papers about X in context Y"  Cross-encoder catches semantic nuance
    │   Phrase-level semantic match     that BM25 + dense miss
    │
    ├─ Complex / multi-hop? ──→ Gemini 2.5 Flash (CAG)
    │   "Which papers disagree about X?"    Full context, cross-referencing
    │   "What mechanism explains A and B?"  ~$0.01/query, ~$0.001 cached
    │
    └─ Very complex / synthesis? ──→ Gemini 2.5 Flash (thinking) or Flash Preview
        "Synthesize across 15 papers"       Higher quality reasoning
        "Find contradictions in corpus"     Worth the extra cost
```

## Model Comparison for CAG

### Gemini (current provider — keep)

| Model | Context | Input $/1M | Cached $/1M | Cache Discount | Notes |
|---|---|---|---|---|---|
| 2.5 Flash-Lite | 1M | $0.075 | $0.01 | 90% | Good for simple lookups in large context |
| 2.5 Flash | 1M | $0.15 | $0.03 | 90% | Best for multi-hop retrieval |
| Flash Preview | 1M | varies | varies | 90% | Highest quality, use for complex synthesis |

**Why Gemini wins for CAG:**
- 1M context window (largest available)
- 90% cache discount (vs 50% on Groq)
- Explicit cache management (create/delete/TTL) vs Groq's automatic-only
- MRCR v2 benchmark (8-needle at 128K): Flash = 52.4%, Flash-Lite = 30.6%
- Flash-Lite non-thinking drops to 16.6% on MRCR — **bad for multi-needle retrieval**

### Kimi K2.5 (not worth adding)

- 256K context, $0.60/M input (4x Flash price, 75% smaller window)
- Retrieval accuracy: 92-94% at 100K, drops to 75-80% at 256K
- No context caching API. Available on Groq but only Kimi K2 (not K2.5) has caching there
- Open-source weights on HuggingFace if local inference ever needed

### Groq (see note below)

| Model | Context | Input $/1M | Speed | Cache | Quality |
|---|---|---|---|---|---|
| gpt-oss-20b | 128K | $0.075 | 1,000 TPS | 50% off | No MRCR data |
| gpt-oss-120b | 128K | $0.15 | 500 TPS | 50% off | No MRCR data |
| Llama 4 Scout | 128K | $0.11 | 750 TPS | None | Degrades past ~64K |
| Llama 3.1 8B | 128K | $0.05 | 840 TPS | None | Too small for extraction |
| Kimi K2 | 256K | $1.00 | 200 TPS | 50% off | Preview only |

## Groq Assessment

**Not useful for CAG in our setup.** Smaller context (128K vs 1M), weaker caching (50% vs 90%), no explicit cache control (2hr volatile TTL, automatic prefix matching only), no retrieval quality benchmarks.

**Where Groq might fit (unresolved):**
- Fast cheap classification/extraction on small documents ($0.05-0.075/M at 800-1000 TPS)
- Tool routing / intent classification where latency matters more than depth
- Bulk processing tasks where you need high throughput on simple prompts
- We haven't found a concrete use case in our current tooling that isn't already covered by Gemini Flash-Lite or local models

**API key available:** `GROQ_API_KEY` in env. Models accessible via OpenAI-compatible API at `https://api.groq.com/openai/v1`.

## Key Research Findings

### Agent Shell Navigation (Cao et al. 2026)

**Third path:** For text corpora navigable as files, coding agents with shell commands (grep, rg, sed, Python scripts) outperform both CAG and embedding retrieval above ~500K tokens.

- **Paper:** Cao, Yin, Dhingra & Zhou (arXiv:2603.20432). Tested Codex v0.46.0 (GPT-5) and Claude Code (Sonnet 4.5).
- **Key result:** 88.5% on BrowseComp-Plus (750M tokens) vs 80% prior SOTA. Scales to 3T tokens.
- **Retrieval tool paradox:** Adding BM25 or embedding retrieval to agents that already have grep **reduces native search usage by 40.5%** and hurts overall accuracy. Agents default to the retriever and miss things grep would have found.
- **Applicability condition:** Only applies when the corpus is navigable as text files via shell tools. Does NOT apply to: numpy embeddings, structured databases, cross-source personal data (e.g., selve's 74K embedded entries).
- **Scale crossover:** Below ~500K tokens, direct context window is competitive. Above 750M, agent navigation dominates.
- **Cost:** $0.11-0.83/query (10-100x more than RAG). Only justified for multi-hop over very large corpora.
- **Implication for us:** Validates retiring meta-knowledge MCP (zero usage) and repo-tools MCP (zero usage). Don't add retrieval layers when native file navigation covers the same corpus.

### CAG vs Embedding Retrieval (Chan et al., arXiv:2412.15605)
- CAG: 40x faster than naive RAG pipeline, +3% recall on HotPotQA/SQuAD
- But that 40x is vs a slow pipeline. Our EMB search is ~50ms. CAG is ~2-5s. EMB is faster for us.
- CAG's real advantage: **cross-document reasoning**, not speed

### Lost in the Middle (Stanford)
- Models fail to find information in the middle of long contexts
- 30%+ accuracy drop when relevant info is in middle vs start/end
- Failure is abrupt, not gradual — unreliable at max context
- Implication: for CAG, put highest-priority documents at start and end of context

### MRCR v2 (Google, multi-needle retrieval at 128K)
- Gemini 2.5 Flash: 52.4% on 8-needle — best available for CAG retrieval
- Flash-Lite: 30.6% (thinking), 16.6% (non-thinking) — dramatic drop
- **Flash-Lite is only suitable for single-fact lookups, not multi-hop**
- No other provider publishes MRCR-equivalent benchmarks

### Anthropic Contextual Retrieval (2024)
- Contextual embeddings + BM25 reduce failed retrievals by 49%
- With reranking: 67% reduction
- For knowledge bases under 200K tokens: skip RAG, stuff full context
- We already implement contextual retrieval in EMB (`emb contextualize`)

### Sharded Fan-Out (for corpora > 1M tokens)
- LLMxMapReduce (arXiv:2410.09342): split corpus into N chunks, parallel LLM calls, aggregate
- No turnkey product exists. Closest: LlamaIndex SubQuestionQueryEngine
- For us: shard into N Gemini Flash calls, each with cached context, fan-out in parallel
- 6 shards x 1M = 6M token corpus. At cached rates: ~$0.02/query
- Not needed yet — our corpora fit in 1M. Worth building if/when they don't.

### Cost Reality
- EMB query: ~$0.0001
- CAG query (Gemini Flash cached): ~$0.001
- CAG query (uncached): ~$0.01
- Sharded fan-out (6 shards, cached): ~$0.02
- **EMB is 10-100x cheaper per query.** CAG justifies its cost only for complex/multi-hop queries.

## Actionable Next Steps

1. **Improve routing in research-mcp:** Auto-select EMB vs CAG based on query complexity and corpus size (the decision framework above)
2. **Use Flash Preview for complex synthesis tasks** in `ask_papers` — add as a third tier above Flash
3. **Document ordering in CAG:** Put highest-relevance papers at start and end of context (mitigate lost-in-middle)
4. **Watch for:** Groq adding larger-context models with better caching; Gemini further reducing cached token costs
