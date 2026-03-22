# Cognee (topoteretes/cognee) — Technical Assessment

**Question:** Is Cognee a viable dependency for an agent infrastructure system that currently uses SQLite knowledge substrate with manual claim/assertion registration and provenance tracking?
**Tier:** Deep | **Date:** 2026-03-19
**Ground truth:** Current system uses SQLite + manual `add_assertion()`/`add_evidence()` with provenance tracking via knowledge substrate (`substrate/`). Works but requires explicit registration. Question is whether automated graph construction produces better results.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Cognee has 14.3K GitHub stars, Apache 2.0 license | GitHub API data | HIGH | [SOURCE: GitHub API] | VERIFIED |
| 2 | Created Aug 2023, v0.5.5 as of March 2026 (pre-1.0 beta) | GitHub API + PyPI | HIGH | [SOURCE: GitHub API, PyPI] | VERIFIED |
| 3 | $7.5M seed round (Feb 2026) led by Pebblebed | Multiple press sources | HIGH | [SOURCE: eu-startups.com, trendingtopics.eu] | VERIFIED |
| 4 | 15 contributors, dominated by 4 core team members (Vasilije 1847, dexters1 1273, hajdul88 691, boris 577) | GitHub API | HIGH | [SOURCE: GitHub API] | VERIFIED |
| 5 | Claims 70+ enterprise users including Bayer | Company website (self-reported) | MEDIUM | [D2: company claims, not independently verified] | UNVERIFIED |
| 6 | Entity extraction uses LLM (via LiteLLM + Instructor) — no dedicated NER model | DeepWiki + docs | HIGH | [SOURCE: deepwiki, cognee docs] | VERIFIED |
| 7 | Graph backends: Kuzu (default/embedded), Neo4j, NetworkX | DeepWiki architecture docs | HIGH | [SOURCE: deepwiki] | VERIFIED |
| 8 | "Memify" is post-hoc graph refinement (prune stale, strengthen frequent, reweight edges) — NOT a separate pipeline stage in the codebase | DeepWiki shows no memify step; blog describes it as optimization | MEDIUM | [SOURCE: deepwiki, cognee blog] | VERIFIED |
| 9 | HotPotQA benchmark: 0.93 correctness, 0.84 F1 (vs 0.4 base RAG) | Cognee's own benchmark (not independent) | LOW | [D3: self-reported, no independent replication] | UNVERIFIED |
| 10 | "Cognee works best with manually curated, focused ontologies" — their own admission | Cognee blog post | HIGH | [SOURCE: cognee.ai/blog/deep-dives/grounding-ai-memory] | VERIFIED |
| 11 | Ontology support via RDF/OWL files + fuzzy matching (difflib, cutoff 0.80) | Cognee blog technical deep-dive | HIGH | [SOURCE: cognee.ai/blog] | VERIFIED |
| 12 | 335 test files in the repository | GitHub API tree enumeration | HIGH | [SOURCE: GitHub API] | VERIFIED |
| 13 | Breaking changes in v0.5.5 (memify triplet embeddings, DLT write disposition, param rename) | GitHub releases page | HIGH | [SOURCE: GitHub releases] | VERIFIED |
| 14 | 40+ core dependencies including litellm, instructor, lancedb, kuzu, onnxruntime, fastembed, rdflib, fastapi | pyproject.toml from GitHub | HIGH | [SOURCE: GitHub pyproject.toml] | VERIFIED |

## Key Findings

### 1. Maturity — Pre-1.0 Beta, Well-Funded Startup

- **Created:** August 2023 (2.5 years old)
- **Current version:** v0.5.5 (Development Status: Beta)
- **Funding:** $7.5M seed (Feb 2026, Pebblebed + 42CAP). Berlin-based startup (Topoteretes UG).
- **Contributors:** 15 total, but heavily concentrated — top 4 account for ~85% of commits. Bus factor concern.
- **Stars:** 14.3K (healthy but inflated by the AI/memory hype cycle — compare to actual production adoption).
- **Release cadence:** Very active — multiple releases per week including dev/rc tags. Sign of active development but also instability risk.
- **License:** Apache 2.0 — fully permissive, no concerns.

**Assessment:** Active project with real investment behind it, but pre-1.0 with frequent breaking changes. Not yet mature for a dependency you don't want to babysit.

### 2. Architecture — The `add → cognify → search` Pipeline

The actual pipeline during `cognify`:

1. **classify_documents** — Route by document type
2. **extract_chunks_from_documents** — Chunk text (configurable, defaults to `min(embedding_max_tokens, llm_max_tokens // 2)`)
3. **extract_graph_from_data** — **LLM-powered entity/relationship extraction** via `get_llm_client()` using Instructor for structured output. Produces `KnowledgeGraph` Pydantic model with typed nodes and edges.
4. **summarize_text** — Hierarchical summaries
5. **add_data_points** — Embed via `get_embedding_engine()`, store across triple-database architecture

**Entity extraction:** There is NO dedicated NER model. Cognee uses the configured LLM (via LiteLLM → any provider including Claude/Anthropic) with Instructor for structured Pydantic output. The `KnowledgeGraph` model defines entity types (name, type, properties dict) and relationships (source, target, type). Users can pass `graph_model=CustomGraph` to define domain-specific schemas.

**Graph DB backends:**
- **Kuzu** (default) — embedded, file-based, zero-config. Like SQLite for graphs.
- **Neo4j** — server-based, optional extra
- **NetworkX** — in-memory only, development use
- FalkorDB and Amazon Neptune mentioned in some docs

**Triple-database architecture:**
- Relational (SQLite/PostgreSQL) — metadata, users, datasets, pipeline state
- Vector (LanceDB default, or ChromaDB/PGVector) — embeddings
- Graph (Kuzu default) — entity-relationship graph

### 3. Self-Hostable? — Yes, With Caveats

**Fully local storage:** All default backends (SQLite + LanceDB + Kuzu) are file-based, embedded, zero-external-dependency. No Neo4j server needed.

**LLM dependency is unavoidable.** Entity extraction and summarization require an LLM. You can use:
- Local models via Ollama/llama-cpp (supported as extras)
- Any API provider via LiteLLM (OpenAI, Anthropic, etc.)

**Bottom line:** Self-hostable for storage, but the core pipeline is LLM-dependent. You can run it against a local LLM, but extraction quality will degrade with smaller models. Claude via LiteLLM is explicitly supported.

### 4. Knowledge Graph Quality — The Ontology Problem

**This is the critical question, and Cognee's own team is honest about the answer:**

> "Cognee works best with manually curated, focused ontologies tailored to your dataset."
> — cognee.ai/blog/deep-dives/grounding-ai-memory

> "Automatic ontology generation sounds great until you realize how domain-specific the problem is."
> — cognee.ai/blog/fundamentals/ai-memory-in-five-scenes

**Without an ontology:** The LLM extracts whatever entities it sees. For investment research, this means:
- "AAPL" and "Apple Inc" and "Apple" become three separate nodes
- Relationships are whatever the LLM hallucinates from context
- No enforcement of domain-specific entity types (Company, Filing, Metric)
- No validation that relationships are meaningful

**With a custom ontology (OWL/RDF):** Cognee adds a fuzzy matching step (difflib, cutoff 0.80) that maps extracted entities to ontology classes. This helps with entity resolution but:
- Requires you to build the ontology yourself
- Fuzzy matching at 0.80 cutoff will produce false matches in domains with similar terms
- No active learning or feedback loop from user corrections in the open-source version

**For investment research and genomics specifically:**
- **Investment:** You'd need a FIBO subset + custom entity types. LLM extraction of financial relationships from unstructured text is notoriously unreliable (earnings calls, SEC filings have specific structures that generic extraction misses).
- **Genomics:** Gene names are extremely ambiguous (MARCH1 vs march, SEPT7). Without a purpose-built ontology from HGNC/UniProt, auto-extraction would produce garbage. Even with one, the fuzzy matching would create false positives (SLC6A4 matching SLC6A3).

**Verdict on graph quality:** For general-purpose "agent memory" (conversation history, user preferences, simple facts), auto-extraction is adequate. For specialized domains with precise ontologies, it adds complexity without adding reliability over manual curation.

### 5. The "Memify" Step — Partially Real, Partially Marketing

**What the documentation says:** Memify "prunes stale nodes, strengthens frequent connections, reweights edges based on usage signals, and adds derived facts."

**What the codebase shows:** The DeepWiki architecture documentation does NOT include memify as a pipeline stage. The actual pipeline is `add → cognify → search`. The v0.5.5 release notes mention "Memify pipeline now uses triplet embeddings instead of coding rules" — suggesting it exists but was recently reworked.

**Assessment:** Memify appears to be a real but evolving feature for post-ingestion graph optimization. The concept (prune/reweight based on usage) is sound. But "derived facts" and "self-improvement" language is marketing. The core mechanism is likely frequency-based edge weighting and node deduplication — useful but not magic.

### 6. Search Quality — Graph vs Plain RAG

**Seven search modes:**
1. `GRAPH_COMPLETION` — vector search → find relevant graph triplets → graph traversal → structured context → LLM answer
2. `RAG_COMPLETION` — standard vector retrieval + LLM synthesis
3. `CHUNKS` — pure vector similarity (baseline)
4. `SUMMARIES` — hierarchical summary retrieval
5. `TEMPORAL` — time-aware search
6. `CODE` — code-specific retrieval
7. `CYPHER` — direct graph queries

**Self-reported benchmark (HotPotQA):**
- Cognee GRAPH_COMPLETION: 0.93 correctness
- Base RAG: 0.40 correctness
- DeepEval F1: 0.84 (+314% improvement)

**Critique of benchmark:** This is Cognee's own benchmark on HotPotQA, which is designed for multi-hop reasoning where graph structure obviously helps. No independent replication. HotPotQA tests whether the system can combine information from multiple paragraphs — this is the exact use case graph-augmented retrieval excels at. Performance on single-document factual queries (more common in practice) is not reported.

**Honest assessment:** Graph-augmented retrieval IS genuinely better than plain RAG for multi-hop questions. This is well-established in the literature (Microsoft's GraphRAG paper, LightRAG, etc.). But the improvement depends on graph quality, which depends on extraction quality, which depends on the LLM and domain.

### 7. Integration Surface — Library, Server, or Both

**Library usage (recommended for our case):**
```python
import cognee
cognee.config.llm_api_key = "sk-..."
await cognee.add(data)
await cognee.cognify()
results = await cognee.search("query", search_type=SearchType.GRAPH_COMPLETION)
```

**Server modes available:**
- REST API (FastAPI + uvicorn, included in core deps)
- CLI interface
- MCP server for AI agents (newer addition)
- LangChain retriever integration
- LlamaIndex integration

**Claude/Anthropic support:** Explicitly supported via LiteLLM + `anthropic` extra. Set `LLM_API_KEY` and `LLM_PROVIDER=anthropic`.

### 8. Dependencies — Heavy

**40+ core dependencies** (not optional extras — these are mandatory):

| Category | Dependencies | Concern |
|----------|-------------|---------|
| LLM | litellm, instructor, openai, tiktoken | Core — unavoidable |
| Storage | sqlalchemy, aiosqlite, lancedb, kuzu, networkx | Multiple DB engines loaded regardless of use |
| Web framework | fastapi, uvicorn, gunicorn, websockets, python-multipart | Server framework in a library — unnecessary if using as library only |
| Data processing | rdflib, pypdf, nbformat, jinja2, numpy, onnxruntime, fastembed | Heavy ML deps |
| Misc | aiohttp, aiofiles, structlog, pympler, tenacity, fakeredis, diskcache, alembic, limits, aiolimiter, cbor2, langdetect, datamodel-code-generator | Kitchen sink |

**Red flags:**
- **FastAPI/uvicorn/gunicorn as core deps** — a library should not force a web framework on you. These should be optional extras.
- **onnxruntime + fastembed as core** — embedding engine loaded regardless of whether you use their embeddings. If you're using Claude's embeddings or no embeddings, this is dead weight.
- **fakeredis as core dep** — testing mock in production dependencies.
- **networkx always installed** even when using Kuzu/Neo4j.
- **Total install:** 14.7 MB source, but actual installed footprint with all transitive deps is likely 500MB+ (onnxruntime alone is ~200MB).

**Comparison to current substrate:** Our knowledge substrate is ~4 Python files, SQLite, no external deps beyond stdlib. Cognee would add 40+ transitive dependencies.

### 9. Red Flags

1. **Overcomplicated for targeted use cases.** If you need entity-relationship storage with provenance, SQLite + manual registration is simpler, more predictable, and zero-dependency. Cognee adds value only if you need automated graph construction from unstructured text AND can tolerate LLM extraction errors.

2. **Pre-1.0 with breaking changes.** v0.5.5 had 3 breaking changes. The API is still evolving. Pinning to a specific version is essential, but you'd be fighting upgrades.

3. **Dependency bloat.** 40+ core deps including web framework, ML runtime, and Redis mock. Not designed as a lightweight embeddable library.

4. **Contributor concentration.** 4 people write 85% of the code. If the startup pivots or the lead dev leaves, maintenance risk is real.

5. **Self-reported benchmarks only.** No independent benchmark validation. HotPotQA tests the best case for graph-augmented retrieval.

6. **Ontology quality is YOUR problem.** The system doesn't solve the hard problem (what entities and relationships matter in your domain) — it just provides plumbing to use your ontology for fuzzy matching during extraction.

7. **LLM-dependent extraction = nondeterministic.** Same document processed twice may produce different graphs. No deterministic reproducibility guarantee.

8. **"Memify" is evolving/unstable.** Recently changed from "coding rules" to "triplet embeddings" in v0.5.5 (breaking change). The memory refinement feature is not settled.

## What's Uncertain

- **Actual production quality at scale.** "70+ companies" claim is self-reported. No public case studies with measurable outcomes.
- **Performance overhead.** No published latency benchmarks for cognify or search operations.
- **Memory refinement effectiveness.** Memify claims are not empirically validated in any public benchmark.
- **Multi-tenant isolation.** Claims multi-tenant support but no security audit or isolation guarantees documented.

## Verdict: Not Recommended as a Dependency

**For your specific use case** (investment research + genomics with manual claim/assertion registration and provenance tracking):

1. **Your current substrate is better for specialized domains.** Manual registration with provenance tracking produces higher-quality knowledge graphs than LLM auto-extraction for domains where precision matters. You control exactly what goes in, with what evidence, at what confidence. Cognee's auto-extraction would add noise that you'd then need to filter.

2. **The value proposition doesn't match.** Cognee solves "I have lots of unstructured text and want a knowledge graph automatically." Your system solves "I have structured assertions with evidence chains and want provenance tracking." These are different problems.

3. **The dependency cost is too high.** 40+ dependencies, pre-1.0 API, breaking changes, 500MB+ installed footprint — for a feature (auto-extraction) that would produce worse results than manual curation in your domains.

4. **Selective adoption paths if you want graph-augmented retrieval:**
   - **Better option:** Add graph traversal to your existing substrate directly. Kuzu (Cognee's default graph DB) is an excellent embedded graph DB — use it standalone without Cognee's extraction pipeline. 1 dependency vs 40+.
   - **If you want auto-extraction later:** Build a thin LiteLLM + Instructor pipeline yourself (2 dependencies) that extracts into your existing substrate schema. You already have the schema; you just need the extraction step.
   - **If you want the full Cognee experience:** Use it as a separate service (Docker) for exploratory graph building on new data sources, then manually promote high-quality subgraphs into your substrate.

## Sources Saved

No papers saved — this was primarily a software engineering evaluation using GitHub API, web sources, and documentation.

## Search Log

| Tool | Query | Hits | Signal |
|------|-------|------|--------|
| Exa (advanced) | cognee architecture cognify pipeline | 10 | HIGH — architecture details |
| Brave | cognee topoteretes architecture review | 15 | HIGH — found DeepWiki, Reddit |
| GitHub API | repo metadata, contributors, releases, pyproject.toml | N/A | HIGH — primary source |
| WebFetch | DeepWiki architecture pages (x3) | 3 | HIGH — detailed pipeline docs |
| WebFetch | cognee.ai blog (ontology, memory) | 2 | HIGH — honest admissions about ontology |
| Brave | cognee funding | 10 | HIGH — confirmed $7.5M seed |
| Exa | cognee limitations, comparison | 8 | MEDIUM — mostly marketing, some useful GraphRAG critique |
| verify_claim | production usage | 1 | MEDIUM — confirmed claims exist, not independently verified |
| verify_claim | LiteLLM + Instructor + Claude | 1 | HIGH — confirmed integration path |
| WebFetch | Graphlit vs Cognee comparison | 1 | MEDIUM — competitor perspective |
| WebFetch | PyPI metadata | 1 | HIGH — version timeline, first release March 2024 |

<!-- knowledge-index
generated: 2026-03-22T00:13:51Z
hash: 4195a447c2ff

sources: 2
  D2: company claims, not independently verified
  D3: self-reported, no independent replication
table_claims: 14

end-knowledge-index -->
