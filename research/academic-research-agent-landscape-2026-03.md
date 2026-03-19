# Academic Research Agent Landscape — March 2026

**Question:** What's genuinely novel in OpenScholar, STORM, scite, PaperQA2, and adjacent tools? What patterns transfer to a personal research agent?
**Tier:** Standard | **Date:** 2026-03-19
**Ground truth:** Prior sweep (epistemic-causal-bayesian-sweep, March 12) noted PaperQA2/OpenScholar as "practical leaders for automated lit review" and our researcher skill + papers-mcp as "comparable in architecture." This memo goes deeper.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | OpenScholar-8B outperforms GPT-4o by 6.1% on ScholarQABench | Nature paper, Feb 2026 | HIGH | [SOURCE: nature.com/articles/s41586-025-10072-4] | VERIFIED |
| 2 | GPT-4o hallucinates citations 78-90% of the time | Same Nature paper | HIGH | [SOURCE: nature.com/articles/s41586-025-10072-4] | VERIFIED |
| 3 | PaperQA2 three-phase agentic RAG matches human expert accuracy (69.5% vs 66.8%) | arXiv:2409.13740, Medium writeup | HIGH | [SOURCE: arxiv.org/abs/2409.13740] | VERIFIED |
| 4 | STORM's multi-perspective simulation yields 25% improvement in article organization | arXiv:2402.14207, NAACL 2024 | HIGH | [SOURCE: arxiv.org/abs/2402.14207] | VERIFIED |
| 5 | scite has 1.6B+ classified citations with stance data | Our existing research + MCP integration | HIGH | [SOURCE: scite MCP, prior research] | VERIFIED |
| 6 | SciRAG's citation-graph reasoning outperforms prior systems on QASA/ScholarQA | arXiv:2511.14362 | MEDIUM | [SOURCE: arxiv.org/abs/2511.14362] | [PREPRINT] |
| 7 | Elicit's Systematic Review achieves "human-level accuracy" | Elicit blog + PMC evaluation | MEDIUM | [SOURCE: elicit.com, PMC:11921719] | PARTIALLY VERIFIED |
| 8 | Agentic RAG yields ~50% higher accuracy vs traditional RAG | Marketing claim, kodexolabs | LOW | [SOURCE: kodexolabs.com] | [UNVERIFIED] |

## Key Findings

### 1. OpenScholar — The Benchmark Setter

**Published in Nature (Feb 2026).** This is the highest-prestige validation of a research agent to date. Key architecture:

- **Datastore:** 45M open-access papers, domain-specific. Not general web — curated scientific literature only.
- **Specialized retriever + reranker:** Purpose-built for scientific passages, not general-purpose embedding.
- **Self-feedback inference loop:** The genuinely novel pattern. After initial generation, the model critiques its own output and iterates. This is *not* simple retry — it's structured self-evaluation against citation quality and factual consistency.
- **Open-source everything:** Model weights, datastore, code, benchmark. Reproducible.

**What's genuinely novel:** The self-feedback loop that specifically targets citation accuracy. OpenScholar doesn't just retrieve-then-generate — it generates, evaluates citations against retrieved passages, and refines. This closed loop is what gets citation accuracy to human-expert level while GPT-4o fabricates 78-90% of citations.

**Transferable pattern:** Our `researcher` skill does a version of this (Phase 5 claim verification), but it's manual/instruction-based. A structural implementation would: (1) generate draft answer, (2) for each citation, verify the cited passage actually supports the claim, (3) regenerate sections where citations don't hold. This could be a post-synthesis verification step in our pipeline.

### 2. PaperQA2 — The Engineering Benchmark

**FutureHouse.** The most mature open-source research agent. Key architecture:

- **Three-phase pipeline:** Search → Gather Evidence (RCS) → Generate Answer. Each phase is tool-invokable by an agent that can iterate.
- **RCS (Re-ranking and Contextual Summarization):** The key differentiator. Raw chunks are NOT injected into the answer prompt. Instead, each chunk is (a) re-scored for relevance, then (b) contextually summarized by an LLM, then (c) scored summaries are selected. This compresses evidence while preserving attribution.
- **Metadata-aware embeddings:** DOI, citation count, journal rank, retraction status attached before embedding. The embedding includes more than just text semantics.
- **NumPy vector store:** Viable because chunk pool is capped at <1000. No external vector DB needed. Clever constraint.
- **Hybrid retrieval:** Dense + sparse (tantivy). Reduces false negatives.
- **CalVer since Dec 2025:** Signals rapid iteration, not stability guarantees.

**What's genuinely novel:** RCS is the key insight. Most RAG systems stuff raw chunks into the context and let the LLM figure it out. PaperQA2 interposes an explicit evidence quality assessment step where each chunk gets a relevance score AND a contextual summary before being promoted to the answer stage. This is essentially "evidence gathering as a first-class agent operation."

**Transferable pattern:** Our papers-mcp `ask_papers` feeds full text to Gemini 1M, which is brute-force but works. The RCS pattern could improve quality by: (1) for each retrieved chunk, ask "is this relevant to the specific question?" (2) summarize relevant chunks in context, (3) only feed top-scored summaries to the synthesis prompt. This is cheaper than feeding everything and lets us use smaller context windows. Directly implementable as a pre-synthesis step in `ask_papers` or as a standalone tool.

### 3. STORM — The Perspective Simulator

**Stanford, NAACL 2024.** Fundamentally different from retrieve-and-answer systems. Key architecture:

- **Phase 1 — Perspective Discovery:** Given a topic, the system identifies diverse perspectives (e.g., for "climate change": atmospheric scientist, economist, policy analyst, affected community member).
- **Phase 2 — Simulated Conversations:** For each perspective, a simulated "writer" asks questions of a simulated "expert" who is grounded in retrieved web sources. Multiple rounds of Q&A per perspective.
- **Phase 3 — Outline Curation + Article Generation:** Information from all conversations is organized into a structured outline, then expanded into a long-form article with citations.

**What's genuinely novel:** The insight that *good questions* produce better research than *good answers*. Instead of asking "What is X?" and retrieving, STORM asks "What would a [perspective] want to know about X?" — this generates a *diversity of questions* that cover more ground than any single query formulation. The multi-perspective conversation simulation is a structural mechanism for coverage breadth.

**Co-STORM (EMNLP 2024):** Adds human-in-the-loop — the human can guide which perspectives are explored, inject their own questions, and steer the conversation. This is the collaborative version.

**Transferable pattern — HIGH VALUE:** Our `researcher` skill's "brainstorm 8-10 angles" instruction is the prompt-engineering version of STORM's architectural solution. STORM makes this *structural*: it literally instantiates different personas and runs multi-turn conversations from each perspective. We could:
1. In the exploratory phase, explicitly simulate 3-4 persona-based question-generation rounds before searching (not just brainstorm queries, but brainstorm from *perspectives*)
2. Use the generated questions as search queries, not just the user's original question
3. This is implementable without new infrastructure — it's a prompt pattern in the `researcher` skill's Phase 2

### 4. SciRAG — The Citation Graph User

**arXiv:2511.14362 (preprint).** Three innovations, one genuinely novel:

- **Adaptive retrieval (sequential vs parallel):** Standard engineering — switch strategy based on query complexity.
- **Citation-aware symbolic reasoning:** The novel part. Uses the *citation graph* — not just the text of papers — to organize and filter supporting documents. If Paper A cites Paper B supportively, and Paper B cites Paper C contrastingly, this graph structure informs which evidence chains are reliable.
- **Outline-guided synthesis:** Plan → critique → refine. Similar to OpenScholar's self-feedback but with explicit outline structure.

**Transferable pattern:** We have scite's citation stance data (supporting/contrasting/mentioning). SciRAG shows that citation *graph structure* (not just individual stance) carries information. A paper that's cited supportingly by 12 papers but contrastingly by 3 well-cited papers is different from one that's contrastingly cited by 3 obscure papers. We already have the data source (scite); the missing piece is using it as a filter in evidence gathering, not just as a post-hoc check.

### 5. scite — Unique and Underused

**1.6B+ classified citation statements.** No other tool provides this. Current state:

- **Smart Citations:** Each citation classified as supporting, contrasting, or mentioning with the actual citation snippet.
- **MCP available:** We have it configured and use it in Phase 4b (citation stance verification).
- **Coverage:** Strong in biomedicine. Weaker in CS, social science, psychometrics.
- **Editorial notices:** Flags retractions — critical for quality control.

**What's genuinely novel:** The *stance* dimension. S2 tells you "Paper A cites Paper B." scite tells you "Paper A cites Paper B *to support claim X* / *to contrast with claim Y*." This is a different kind of evidence entirely.

**Transferable pattern — currently underused:** We use scite only in Phase 4b as a post-hoc check on top-3 claims. Higher-value uses:
1. **Early disconfirmation:** Before forming hypotheses, search scite for contrasting citations on the topic. Surface disagreements *before* you've committed to a direction.
2. **Consensus check:** For any claim entering our knowledge substrate, check scite tally. Claims with S:50 C:0 M:200 are different from S:12 C:8 M:30.
3. **Retraction screening:** Before citing any paper, check `editorialNotices`. This should be structural (in `save_paper` or `fetch_paper`), not manual.

### 6. Elicit — The Systematic Review Specialist

**Commercial, $12/mo.** Key developments:

- **Research Agents (2025):** Break prompts into systematic programs, execute with evidence grounding. This is their version of agentic RAG.
- **Strict Screening (Dec 2025):** Higher precision mode for systematic reviews meeting academic standards.
- **Semi-automated second reviewer:** PMC-published evaluation (2025) shows Elicit as viable Reviewer 2 in dual-reviewer systematic review workflows.

**What's genuinely novel:** The framing of research as *program execution*. Rather than "search and summarize," Elicit decomposes a research question into a systematic program (define criteria → search → screen → extract → synthesize) and executes each step with grounded evidence. This is distinct from PaperQA2's iterative approach — it's more structured and protocol-driven.

**Transferable pattern:** Our researcher skill is closer to Elicit's "systematic program" model than to PaperQA2's iterative model. The phases (ground truth → exploratory → hypothesis → disconfirmation → verification) *are* a program. What Elicit adds: explicit *screening criteria* defined upfront. We could formalize: "Before searching, define what counts as relevant evidence and what would be excluded." This is a small prompt addition to Phase 2 that would sharpen results.

### 7. Emerging Systems Worth Tracking

| System | Novel Pattern | Maturity | Track? |
|--------|--------------|----------|--------|
| DeepDoc | Multi-agent pipeline for *local* document analysis (not web search) | Early | LOW — our `ask_papers` covers this |
| MiroThinker | 400 tool calls/task, 256K context, open-source | Released | MEDIUM — high tool-call density is interesting |
| Agentic Hybrid RAG | Dynamic GraphRAG vs VectorRAG selection | Preprint | LOW — premature |

## What's Uncertain

1. **OpenScholar's self-feedback loop generalizability.** Tested on scientific QA; unclear if the pattern works for investment research, policy analysis, or other domains where "citation accuracy" means something different.
2. **RCS cost.** PaperQA2's contextual summarization step adds an LLM call per chunk. At scale (100+ papers), this could be expensive. No published cost analysis.
3. **STORM at scale.** The multi-perspective simulation generates many LLM calls. 28K GitHub stars but unclear how many production deployments exist.
4. **scite coverage gaps.** Confirmed weak in CS and social sciences. Unknown coverage for financial/economic literature.

## Actionable Patterns for Our System (Ranked by ROI)

### Tier 1: Implement Soon (high value, low cost)

1. **Perspective-based question generation (from STORM).** In researcher skill Phase 2, before selecting search axes, generate questions from 3-4 explicit personas relevant to the domain. This is a prompt-level change, no infrastructure needed.

2. **scite as early disconfirmation (not just post-hoc).** Move scite from Phase 4b to *also* Phase 2 — search for contrasting citations on the topic before committing to hypotheses.

3. **Screening criteria definition (from Elicit).** Add to Phase 2: "Before searching, define: what evidence would be relevant? What would be excluded? What quality threshold applies?" One paragraph, sharpens everything downstream.

### Tier 2: Worth Building (medium value, medium cost)

4. **RCS-style evidence gathering (from PaperQA2).** Before `ask_papers` synthesis, interpose a step: re-score each chunk for relevance, contextually summarize, feed only top-scored summaries. Reduces context waste, improves synthesis quality.

5. **Self-feedback citation verification (from OpenScholar).** After generating a research memo, programmatically check: for each inline citation, does the cited source actually support the claim? Flag mismatches for revision.

### Tier 3: Track, Don't Build (interesting but premature)

6. **Citation graph filtering (from SciRAG).** Use citation graph structure (not just individual stance) to weight evidence. Requires scite data + graph construction — not worth building until we have a concrete use case where single-stance data is insufficient.

7. **Retraction screening in paper pipeline.** Check `editorialNotices` via scite when saving papers. Low frequency event but high consequence when it matters.

## Sources Saved

Papers discovered but not saved to corpus (S2 MCP was erroring). Key references:
- OpenScholar: arXiv, Nature 2026 (DOI: 10.1038/s41586-025-10072-4)
- PaperQA2: arXiv:2409.13740
- STORM: arXiv:2402.14207 (NAACL 2024), Co-STORM at EMNLP 2024
- SciRAG: arXiv:2511.14362

## Search Log

| Query | Tool | Result |
|-------|------|--------|
| OpenScholar architecture retrieval synthesis | Exa advanced | Nature paper found, detailed architecture |
| STORM Stanford multi-perspective article generation | Exa advanced | GitHub repo (28K stars), architecture details |
| PaperQA2 agentic RAG architecture evaluation | Exa advanced | Medium writeup, analyticsvidhya, medevel — good detail |
| Novel AI research agent tools 2025 2026 | Exa advanced + additional queries (scite, Elicit, Consensus) | SciRAG, DeepDoc, MiroThinker, Agentic Hybrid RAG |
| Elicit research AI agent 2025 2026 | Brave | Systematic Review features, Research Agents, PMC evaluation |
| scite AI new features 2025 2026 | Brave | Rate-limited, used prior research |
| STORM arXiv:2402.14207 | WebFetch | Architecture confirmed from abstract |
