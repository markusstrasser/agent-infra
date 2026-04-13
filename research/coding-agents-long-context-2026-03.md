---
title: "Coding Agents as Long-Context Processors"
date: 2026-03-30
tags: [agent-architecture, long-context, retrieval, benchmarks]
status: complete
---

## Coding Agents as Long-Context Processors — Research Memo

**Question:** How does treating huge corpora as directory trees navigated by coding agents compare to RAG/embedding retrieval and long-context LLMs?
**Tier:** Standard | **Date:** 2026-03-30
**Ground truth:** We already use coding agents (Claude Code) for codebase navigation via grep/read/glob. This paper formalizes the insight and benchmarks it against alternatives.

### Paper Identity

- **Title:** Coding Agents are Effective Long-Context Processors
- **Authors:** Weili Cao, Xunjian Yin, Bhuwan Dhingra, Shuyan Zhou
- **arXiv:** [2603.20432](https://arxiv.org/abs/2603.20432) (submitted 2026-03-20)
- **S2 ID:** 4745e39bc1fcce9fadad5f6757c6543a9aae747f (saved to corpus)
- **Highlighted by:** @dair_ai [SOURCE: Brave search; specific tweet URL not recovered]

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | 88.5% on BrowseComp-Plus (750M tokens) vs 80% prior SOTA | Table in paper, 100-example eval subset scores 89% (folder) | HIGH | arXiv:2603.20432 Table 1 | VERIFIED |
| 2 | 17.3% average improvement over SOTA across benchmarks | Averaged across 5 benchmarks | HIGH | arXiv:2603.20432 abstract | VERIFIED |
| 3 | Scales to 3T tokens (Natural Questions full corpus) | 56% accuracy at 3T scale | HIGH | arXiv:2603.20432 Table 1 | VERIFIED |
| 4 | Adding BM25/embedding retrieval HURTS performance | Native search drops 40.5% when retrievers available | HIGH | arXiv:2603.20432 Table 4 | VERIFIED |
| 5 | Folder-based organization outperforms single-file by 6% | 89.0% vs 83.0% no-retriever setting | HIGH | arXiv:2603.20432 Table 2 | VERIFIED |
| 6 | Cost $0.11-0.83 per query (10-100x more than RAG) | Table 5 cost breakdown | HIGH | arXiv:2603.20432 Table 5 | VERIFIED |
| 7 | No task-specific training or prompting required | Generic "answer question by iterating files" prompt | HIGH | arXiv:2603.20432 Section 3 | VERIFIED |

### Core Technique: Corpus as Directory Tree

**The insight:** Instead of stuffing documents into a context window (attention-based) or building embedding indexes (retrieval-based), organize the corpus as a filesystem and let a coding agent navigate it with shell commands and Python.

**Corpus construction:**
- Each document becomes an individual `.txt` file in a directory
- Document IDs serve as filenames (e.g., `81813.txt`, `23043.txt`)
- For BrowseComp-Plus: ~100K documents in a folder hierarchy
- For Natural Questions (3T tokens): single JSONL file due to corpus size constraints
- No preprocessing, no embeddings, no index construction

**Agent instructions (minimal):**
> "Answer the following question by iterating through files under folder {context_location}: Question: {question}"

That is the entirety of the task-specific prompt. No few-shot examples, no search strategy hints.

**Agents tested:**
- OpenAI Codex v0.46.0 (GPT-5 backbone)
- Claude Code (Sonnet 4.5 backbone)

### Navigation Patterns (Emergent, Not Instructed)

The agents autonomously develop three distinct strategies depending on task type:

**1. Iterative Query Refinement (multi-hop retrieval tasks)**
- Agent starts with `rg 'Brandon Beck.*wife'` across corpus
- Reads matched files with `sed -n '1,200p'`
- Extracts new entities, formulates refined queries
- Chains 6+ hops: "Riot Games -> Brandon Beck -> Natasha Beck -> Pepperdine -> Valorant -> Demon1 -> Max Mazanov"
- No explicit chain-of-thought prompting — the agent discovers the strategy

**2. Programmatic Aggregation (analytical tasks)**
- Agent writes ~300 lines of Python with regex patterns
- Classifies and counts information across documents
- Handles negations ("no", "not", "never") and quantity mismatches
- Zero retrieval tool usage — pure programmatic processing
- This is the mode that has no RAG equivalent

**3. Direct Inference (mixed/short tasks)**
- Minimal tool invocation
- Relies on LLM's inherent reasoning after brief file reads
- Used on LongBench where documents fit in working memory

**Coordinate-based reading (key technique):**
- `nl` (number lines) to create line-indexed versions of files
- `sed -n 'START,ENDp'` to extract specific ranges
- `sed` usage increases 634% in folder mode vs single-file mode
- Agents build a mental coordinate system: discover with grep, locate with nl, extract with sed

### The Retrieval Tool Paradox (Most Surprising Finding)

Adding standard IR tools to coding agents **hurts** performance:

| Configuration | Native Search Commands | BrowseComp-Plus |
|---|---|---|
| No retriever | 14.92 | 89.0% |
| + BM25 retriever | 9.84 | 82.0% |
| + Gemini embeddings | 8.33 | 86.0%-90.0% |

**Mechanism:** When retriever tools are available, agents default to them and reduce native exploration (grep/ripgrep). But retriever ranking is imperfect — agents trust the top-k results and miss context that native exploration would have found. The retriever becomes a crutch that narrows the search space.

This is the "retrieval tool displacement" effect: native commands drop 40.5% when retrievers are present.

**Exception:** Embedding retrieval helps on the 100-example BrowseComp-Plus subset (90.0% vs 89.0%), but hurts on Oolong benchmarks. BM25 is consistently worse.

### Head-to-Head Comparisons

**vs. Full-context LLMs:**

| Method | BrowseComp-Plus (750M) |
|---|---|
| GPT-5 full context | 20.0% |
| Coding agent (Codex) | 88.5% |

Full-context LLMs catastrophically fail at 750M tokens. Attention mechanisms cannot effectively process this scale even with models that technically accept the input.

**vs. RAG:**

| Method | BrowseComp-Plus | Oolong-Real |
|---|---|---|
| RAG | 65.0% | 13.38% |
| Coding agent | 88.5% | 37.46% |

RAG is cheap ($0.006-0.111/query) but accuracy is much lower. The gap widens on harder tasks (Oolong-Real: 180% relative improvement).

**vs. ReAct search agents:**

| Method | BrowseComp-Plus |
|---|---|
| ReAct agent | 72.5% |
| Coding agent | 88.5% |

ReAct uses search-observe-think loops but lacks the filesystem navigation and code generation capabilities.

**One exception:** On LongBench (188K tokens), coding agents score 62.5% vs prior SOTA 63.3% — slight underperformance. At shorter contexts, the overhead of tool invocation provides no benefit over direct context processing.

### Cost Analysis

| Method | $/query range | Best accuracy |
|---|---|---|
| RAG | $0.006-0.111 | 65.0% |
| Coding agent (no retriever) | $0.111-0.703 | 88.5% |
| Coding agent + BM25 | $0.094-0.828 | 82.0% |
| GPT-5 full context | $0.129-1.421 | 20.0% |

Coding agents are 10-100x more expensive than RAG per query but deliver dramatically better accuracy. They are cost-competitive with full-context approaches while being vastly more accurate.

### Practical Implications

**For codebases of 50-100 files (our use case):**
- This paper validates what we already do. Claude Code navigating via Read/Grep/Glob IS the technique described here, just at smaller scale.
- At 50-100 files (~500K-2M tokens), the advantage over RAG is probably smaller. The paper shows coding agents slightly underperform on LongBench (188K tokens). The sweet spot is >500K tokens where attention mechanisms degrade.
- The "no retriever is better" finding is directly actionable: don't add embedding search to coding agent workflows. Let the agent use native grep/ripgrep. This matches our experience — the agent-infra MCP (section-search) was retired because grep was faster.
- The programmatic aggregation strategy (writing Python scripts to process files) is something we already do via agent subagent delegation. The paper shows this emerges naturally.

**For massive corpora (>100M tokens):**
- The directory-tree approach is a genuine alternative to building embedding pipelines.
- Setup cost is near zero: just dump documents as text files. No chunking, no embedding, no vector DB.
- Query cost is higher ($0.11-0.83) but accuracy is dramatically better than RAG ($0.006-0.111 but 65% accuracy).
- The 3T token result (Natural Questions, 56% accuracy) shows the approach works at truly massive scale, though accuracy does degrade.

**Transferable patterns for our infrastructure:**
1. **Folder structure matters.** Organizing documents as individual files in directories outperforms single-file concatenation by 6%. We already do this (each project is a directory, each file is individually addressable).
2. **Don't add retrieval tools to agents that have native search.** The retrieval tool paradox is the key insight. When agents have grep/ripgrep, adding BM25 or embedding search makes them lazier and less accurate.
3. **The coordinate-based reading pattern** (nl + sed, or in our case Read with offset/limit) is the high-value technique. Agents that can index into files precisely outperform those that read entire files.
4. **Programmatic aggregation is a distinct strategy.** For analytical questions over many documents, the agent should write a script — not search-and-read. This argues for keeping Python execution capability in agent toolkits.

### What's Uncertain

- **Reproducibility.** Paper uses Codex v0.46.0 and Claude Code with Sonnet 4.5 — specific versions that may not be available for reproduction. Zero citations so far (too recent).
- **BrowseComp-Plus representativeness.** 830 queries from OpenAI's BrowseComp, not independently constructed. Selection bias toward web-search-style questions.
- **Cost trajectory.** At $0.11-0.83/query, this is viable for high-value questions but not for high-volume retrieval. Cost depends entirely on model pricing which changes monthly.
- **LongBench underperformance.** At shorter contexts (<200K tokens), coding agents add overhead without benefit. The crossover point where coding agents beat direct context isn't characterized.
- **Folder structure for code.** The paper tests on document corpora. Code has richer structure (imports, function calls, types) that grep/ripgrep can exploit better than plain text search. The advantage may be larger for code than the paper measures.

### Comparison to Our Search/Retrieval Architecture

Our `search-retrieval-architecture.md` memo documents the CAG vs embedding retrieval tradeoffs. This paper provides strong evidence for the "CAG + native tools" approach we already use:

| Dimension | Our approach | Paper's approach | Alignment |
|---|---|---|---|
| File organization | Per-project directories, individual files | Per-document txt files in folders | Same |
| Search | grep/ripgrep via agent tools | grep/ripgrep via shell | Same |
| Retrieval augmentation | Retired (agent-infra MCP, zero usage) | Shown to hurt performance | Validated |
| Programmatic processing | Subagent delegation for analysis | Agent writes Python scripts | Same |
| Scale | 50-100 files per project | 100K+ documents, up to 3T tokens | Different scale |

The paper essentially validates our architecture at massive scale and provides the first rigorous benchmark evidence that native search tools outperform embedding retrieval for agent-based information processing.

---

**References:**

Cao, W., Yin, X., Dhingra, B., & Zhou, S. (2026). Coding Agents are Effective Long-Context Processors. arXiv:2603.20432. https://arxiv.org/abs/2603.20432

BrowseComp-Plus benchmark: https://github.com/texttron/BrowseComp-Plus

<!-- knowledge-index
generated: 2026-03-31T03:05:16Z
hash: 865d3f0f938d

title: Coding Agents as Long-Context Processors
status: complete
tags: agent-architecture, long-context, retrieval, benchmarks
table_claims: 7

end-knowledge-index -->
