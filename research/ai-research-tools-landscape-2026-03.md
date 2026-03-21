# AI Research Tools Landscape — What to Steal

**Date:** 2026-03-19
**Tier:** Standard
**Question:** What can we learn from Consensus, FutureHouse, Elicit, and the broader AI research tools landscape?
**Companion files:** `consensus-app-analysis.md`, `futurehouse-technical-analysis.md`

---

## The Landscape

Five platforms examined in depth, plus a broader scan. Ordered by architectural interest.

### FutureHouse / PaperQA2 — the most technically interesting

Nonprofit (Apache 2.0, 7K+ stars). PaperQA2 is an agentic RAG system with 4 tools (PaperSearch, GatherEvidence, GenerateAnswer, CitationTraversal). Key numbers from arXiv:2409.13740:

- **RCS (Reranking & Contextual Summarization):** LLM maps over top-k chunks in parallel, producing query-specific summary + relevance score (0-10). Compresses 2,250-token chunks to 200-400 tokens. Removing RCS drops accuracy with p<0.001. This is the single biggest win.
- **Calibrated refusal:** Explicit "I cannot answer" option. Refuses 21.9% of questions. Precision on answered: 85.2% vs human 64.3% (p=0.003).
- **Citation traversal:** Forward/backward citations as retrieval tool, overlap filter (alpha=1/3). Marginal accuracy gain but +DOI recall (p=0.022).
- **Aviary/LDP:** Agents as POMDPs, RL training. 8B model matches frontier at 100x less cost.
- **ether0:** 24B open-weights chemistry reasoning model, RL-trained from Mistral base.

### Elicit — best UX thinking

PBC ($9M seed, >$1M ARR in 4 months). Core idea: "supervise the process, not the output."

- **Notebook UX:** Structured evidence tables with columns as extraction prompts run across N papers. Systematic, transparent, unbounded. Took 4 attempts to get right.
- **Factored cognition:** Decompose research into small, independently meaningful steps. Each step uses a model fine-tuned for that subtask (not one model for everything).
- **Constitutional AI for summarization:** Anthropic-style RLHF on extraction models to prevent "tried too hard to answer the question" drift.
- **Two-model confidence:** One model generates, another estimates confidence. Surfaced as UI flags for human spot-checking.
- **138M papers + 500K clinical trials.** Built their own search when S2 proved insufficiently semantic.

### Consensus.app — product polish on narrow UX

8M+ users, $11.5M Series A. Built on OpenAlex + S2 (220M papers). Scholar Agent (Oct 2025) uses GPT-5 + Responses API with 4-agent decomposition (Plan, Search, Read, Analyze).

- **Consensus Meter:** Papers classified as Yes/No/Possibly/Mixed on binary questions. Unique UX pattern but methodologically weak (vote counting, equal weighting, effect size blind).
- **PRISMA-style Deep Search:** Generates systematic-review flow diagrams. No other consumer tool does this.
- **"Search first, AI second":** Synthesis can only reference papers the search found — structural anti-hallucination.
- **Limitations:** Non-reproducible results, abstract-only for paywalled content, no empirical benchmarks published.

### OpenScholar (Allen AI) — published in Nature 2025

Open-source RAG with 45M paper datastore. Domain-specific trained retrievers + rerankers (not off-the-shelf). Self-feedback inference loop for iterative refinement. Human experts preferred OpenScholar over GPT-4o in >50% of cases. ScholarQABench benchmark. Fully open (code, models, data).

### STORM (Stanford) — structural diversity injection

Perspective-Guided Question Asking. Simulates multi-agent conversations where writers with different perspectives question a grounded expert. Pre-writing: discover perspectives -> simulate conversations -> curate into outline -> generate article. +25% organization, +10% breadth. The diversity comes from structure (different frame-holders), not just "brainstorm harder."

### Also noted

- **SciRAG:** Adaptive retrieval (switches sequential/parallel), citation-aware symbolic reasoning, outline-guided synthesis. Interesting but early (arxiv preprint).
- **scite.ai:** 1.6B classified citation statements (supporting/contrasting/mentioning). Unique stance data we already use.
- **AI Scientist-v2:** Fully autonomous paper generation via agentic tree search. First AI-produced paper through peer review. Interesting for autoresearch direction.
- **DeepDoc:** Local document -> research report pipeline. Multi-agent with reflection loops.
- **MiroThinker:** Open-source, 400 tool calls per task, 256K context. Brute-force thoroughness.

---

## What to Steal (ROI-sorted)

### 1. RCS (Summarize-to-Query) — from PaperQA2

**Evidence:** Ablation p<0.001. The single highest-measured-impact component.

**Gap:** Our `research-mcp` does `fetch_paper` -> `read_paper` -> `ask_papers`. Between read and ask, raw text goes to Gemini's 1M context without compression or relevance scoring. Wastes context on irrelevant passages.

**Build:** `prepare_evidence(query, chunks)` tool in research-mcp. Map an LLM (Gemini Flash, free) over retrieved chunks, producing query-specific summaries + relevance scores. Only top-scoring summaries go to synthesis.

**Cost:** Low. ~50 lines. Free-tier Gemini Flash per chunk.

### 2. Calibrated Refusal — from PaperQA2

**Evidence:** 21.9% refusal rate -> 85.2% precision. Precision > recall for research.

**Gap:** Our researcher skill always produces output, hedging with [UNVERIFIED]. No structural refusal pathway.

**Build:** Add confidence threshold to researcher synthesis. If no Grade 1-5 sources and all RCS scores < 5, refuse: "Insufficient evidence. Here's what I searched and didn't find." The refusal itself is useful information.

**Cost:** Near-zero. Prompt change + decision gate.

### 3. Citation Traversal Tool — from PaperQA2

**Evidence:** Marginal accuracy but significant DOI recall improvement (p=0.022). Finds papers keyword search misses.

**Gap:** We have S2 via research-mcp but only use keyword search. Don't exploit citation graph.

**Build:** `traverse_citations(paper_id, direction="both", overlap_alpha=0.33)` in research-mcp. Given high-relevance paper, fetch citers/citees from S2, filter by overlap heuristic. S2 API is free.

**Cost:** Medium. ~100 lines. Main risk: S2 rate limits.

### 4. Structured Extraction Tables — from Elicit

**Evidence:** Elicit's core UX. Systematic review methodology adapted to AI.

**Gap:** Researcher skill produces prose. For systematic questions, prose buries the signal. We theorized evidence tables in `knowledge-accrual-architecture.md` but never shipped.

**Build:** `extract_table(papers, columns)` where columns are extraction prompts (sample size, effect size, study design, population). Produces structured table. Per-paper extraction via Flash, table assembly.

**Cost:** Medium. ~200 lines in research-mcp.

### 5. Perspective-Guided Divergence — from STORM

**Evidence:** +25% organization, +10% breadth. Structural diversity > prompted diversity.

**Gap:** Brainstorm skill generates alternatives by prompting. STORM instantiates N perspective-holders who each ask different questions.

**Build:** Mode in brainstorm skill: spawn 3-5 perspective agents (skeptic, domain expert, analogist, contrarian). Each asks questions. Merge into research agenda. Maps to backlog item "Intentional Contextual Fracture."

**Cost:** Low-medium. Main cost is LLM calls for N perspectives.

### 6. Step-Level Model Routing — from Elicit

**Evidence:** Elicit uses fine-tuned models per step. "50/50 open/closed by query count; closed dominates by cost."

**Gap:** Our researcher skill uses same model for all phases. Discovery (Phase 2) could use cheaper models. Synthesis (Phase 5-6) needs expensive models.

**Build:** Route researcher phases to different models. Phase 1-2 (search/explore): Haiku or Flash. Phase 5-6 (verify/synthesize): Opus or Pro.

**Cost:** Low. Routing logic only.

---

## Not Worth Adopting

| Pattern | Source | Why not |
|---------|--------|---------|
| Consensus Meter | Consensus | Vote counting is epistemically crude. Our NATO Admiralty grading is more nuanced. |
| Full notebook UX | Elicit | We're CLI-first. Extraction tables (item 4) are the portable part. |
| 45M paper datastore | OpenScholar | We use S2/Exa for retrieval. Local index not worth it at our scale. |
| Aviary/LDP RL training | FutureHouse | Interesting but needs GPU infra + training sets we don't have. Watch. |
| Production K8s infra | FutureHouse | MongoDB/PostgreSQL/Redis/K8s is enterprise overkill for personal use. |
| PRISMA flow diagrams | Consensus | Nice visualization but low information density for our use case. |

---

## Cross-Cutting Observations

**1. Everyone uses S2 as backbone.** Consensus (via OpenAlex), FutureHouse, Elicit (originally, now custom), OpenScholar — all start from Semantic Scholar. Our research-mcp S2 integration is the right foundation.

**2. The winning pattern is search-then-synthesize, not generate-then-cite.** Every serious tool retrieves first, then grounds synthesis in retrieved papers. This is structurally safer than LLMs that generate and retroactively find citations. Our researcher skill already does this correctly.

**3. Calibrated refusal is a competitive advantage.** PaperQA2's precision (85.2%) comes from knowing when to shut up. This is rare in the landscape — most tools always produce something.

**4. The gap between "found papers" and "understood papers" is where the value is.** Search is commoditized (S2, Exa, Brave all work). Extraction, synthesis, and verification are where these tools differentiate. RCS (FutureHouse), extraction tables (Elicit), and contradiction detection (ContraCrow) all live in this gap.

**5. Nobody has solved evaluation.** Consensus has no published benchmarks. Elicit doesn't publish precision/recall. FutureHouse's LitQA2 is the best available but tests factual lookup, not synthesis quality. ScholarQABench (OpenScholar) is emerging. The epistemic measurement problem is unsolved across the field.

---

## Sources

- arXiv:2409.13740 — PaperQA2 (Skarlinski et al., Sep 2024) [B1]
- arXiv:2412.21154 — Aviary/LDP (FutureHouse, Dec 2024) [B2]
- Nature s41586-025-10072-4 — OpenScholar (Allen AI, 2025) [A1]
- arXiv:2402.14207 — STORM (Stanford, Feb 2024) [B2]
- OpenAI case study: openai.com/index/consensus/ [D2]
- Aaron Tay analysis: aarontay.substack.com/p/a-2025-deep-dive-of-consensus-promises [C2]
- Latent Space podcast: latent.space/p/elicit (Apr 2024) [B2]
- PMC12318603 — Consensus review article [B2]
- FutureHouse GitHub: github.com/Future-House/ [A1]
- elicit.com/pricing [A1]
