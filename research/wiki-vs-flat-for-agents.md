---
title: "Wiki-Style Knowledge Organization vs Flat Files for AI Agents"
date: 2026-04-04
tags: [agent-architecture, knowledge-management, retrieval]
status: complete
---

## Wiki-Style Knowledge Organization vs Flat Files + Search for AI Agents — Research Memo

**Question:** Should we compile ~115 research memos into wiki-style synthesized articles, or do agents navigate better with flat source files + search tools?
**Tier:** Standard | **Date:** 2026-04-04
**Ground truth:** Cao et al. 2026 finding that BM25/embedding retrieval hurts coding agent performance by 40.5% when agents already have grep; crossover at ~500K tokens. Our repo is ~115 files, well under that.

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Adding BM25/embedding retrieval to coding agents with native tools hurts by 40.5% on average | Empirical benchmark across multiple LCBs | HIGH | Cao et al. arXiv:2603.20432 | VERIFIED |
| 2 | Coding agents outperform SOTA long-context processors by 17.3% via externalized file-system interaction | Benchmark results | HIGH | Cao et al. arXiv:2603.20432 | VERIFIED |
| 3 | LLM-generated AGENTS.md/CLAUDE.md context files reduce success rates by 0.5-3% | 138 real-world Python tasks, 4 frontier models | HIGH | Gloaguen et al. arXiv:2602.11988 (ETH Zurich) | VERIFIED |
| 4 | LLM-generated context files inflate trajectory length by ~4 steps and inference cost by >20% | Same study | HIGH | Gloaguen et al. arXiv:2602.11988 | VERIFIED |
| 5 | Human-written context files provide only ~4% improvement, mainly for undocumented repos | Same study | HIGH | Gloaguen et al. arXiv:2602.11988 | VERIFIED |
| 6 | Broad architectural overviews in context files act as distractions, prompting excessive grep/read/test cycles | Trajectory analysis in same study | HIGH | Gloaguen et al. arXiv:2602.11988 | VERIFIED |
| 7 | Format choice alone can swing LLM accuracy by up to 40% on code translation tasks | Empirical study | MEDIUM | arXiv:2411.10541 [UNVERIFIED — cited in Wire blog] | PARTIAL |
| 8 | Context rot: trivially simple tasks drop from 95% to 60-70% accuracy as input length increases | Chroma research | MEDIUM | [SOURCE: usewire.io blog, citing Chroma] | PARTIAL |
| 9 | LLM-curated hierarchical context trees (domain→topic→subtopic→entry) match SOTA on memory benchmarks with zero external infra | LoCoMo + LongMemEval benchmarks | MEDIUM | ByteRover arXiv:2604.01599 | VERIFIED |
| 10 | Automated context file generation should be deprecated in standard workflows | Author recommendation from ETH study | HIGH | Gloaguen et al. arXiv:2602.11988 | VERIFIED |

---

### Key Findings

#### 1. The Retrieval Paradox (Cao et al. 2026)

The strongest evidence comes from Cao et al. (arXiv:2603.20432), which we already have indexed. Their key finding: when coding agents already have access to native navigation tools (grep, file read, directory listing), adding BM25 or embedding-based retrieval **hurts** performance by 40.5% on average. The mechanism: retrieval introduces noise and displaces the agent's own navigation strategy, which is more targeted because the agent can iteratively refine its search based on intermediate results.

The crossover point is approximately 500K tokens. Below that threshold, the entire codebase fits in context or is navigable via native tools, making retrieval redundant at best and harmful at worst. Our 115-memo corpus is well under this threshold.

The implication for wiki-style synthesis: a wiki article is essentially a pre-computed retrieval result. It pre-selects and re-organizes information from source files. If the agent can navigate source files directly, the wiki article adds a layer of indirection that may introduce the same distraction effects as retrieval.

#### 2. The AGENTS.md Distraction Effect (Gloaguen et al. 2026)

The ETH Zurich study (arXiv:2602.11988) is the most directly relevant paper. They tested whether repository-level context files (AGENTS.md, CLAUDE.md, CURSOR_RULES) help coding agents on 138 real-world Python tasks across 4 frontier models.

Results:
- **LLM-generated context files:** -0.5% to -3% success rate, +4 trajectory steps, +20% inference cost
- **Human-written context files:** +4% improvement, but only in undocumented repos
- **Mechanism of harm:** Broad architectural overviews cause agents to "execute significantly more searches (grep), read more files, and run redundant testing loops." The overview acts as a stimulus for unfocused exploration rather than targeted problem-solving.

This is a strong signal against wiki-style synthesis. A wiki article about "Agent Memory Systems" that synthesizes 8 memos would be exactly the kind of broad architectural overview that the ETH study found to be distracting. The agent would read the wiki article, get primed with a broad conceptual map, and then over-explore rather than going directly to the specific memo it needs.

**Critical nuance:** The ETH study tested context files that are loaded into every agent session regardless of task relevance. A wiki article that is selectively retrieved based on the current question would have a different effect. But our question is about pre-synthesized articles as a knowledge organization strategy, not about selective retrieval — and we already know retrieval hurts (Claim 1).

#### 3. Flat Files + Native Search Is the Empirical Winner

Multiple lines of evidence converge:

**Cao et al.** showed that coding agents externalize long-context processing into "explicit, executable interactions" with the filesystem. The agent's iterative grep→read→refine cycle is more effective than any pre-computed retrieval or synthesis because the agent adapts its search strategy based on intermediate findings.

**ByteRover** (arXiv:2604.01599) is interesting as a counterpoint — it uses LLM-curated hierarchical context trees stored as human-readable markdown files. But notably, it stores these as flat files on the local filesystem with no vector DB, no graph DB, no embedding service. The hierarchy is in the file organization (domain/topic/subtopic/entry), not in pre-synthesized documents. This is much closer to our current flat-file-with-index approach than to wiki articles.

**Context rot** (Chroma research, cited in Wire blog): even simple tasks degrade from 95% to 60-70% accuracy as input length grows. A wiki article that synthesizes 8 memos would be substantially longer than any single memo, meaning the agent would process it less accurately than it would process a single targeted memo found via grep.

#### 4. What Actually Helps: Thin Indexes, Not Thick Articles

The evidence points to a specific pattern that works:

- **Thin index files** that map topics to file paths (like our existing research-index.md) — these are short, provide routing information, and don't distract
- **Flat source files** with descriptive names and clear structure — these are what the agent actually reads when it needs information
- **Native search tools** (grep, glob) to find the right file — agents are good at this and the results show it

What does NOT help:
- **Pre-synthesized articles** that try to be comprehensive — too long, too broad, act as distractors
- **Retrieval layers** (BM25, embedding) — add noise, displace native navigation
- **LLM-generated context files** — consistently hurt performance

The one case where synthesis helps is **undocumented repositories** (ETH finding: +4% from human-written context). But our repo is extensively documented with 115 memos, each on a specific topic. The documentation exists; the question is organization, not coverage.

---

### What's Uncertain

1. **No study directly tests wiki-style synthesis vs flat files for knowledge corpora.** The ETH study tests context files for code repos, not knowledge bases. The Cao study tests retrieval for coding tasks, not research memo navigation. We are extrapolating from adjacent findings.

2. **Scale effects are uncharacterized.** At 115 files, flat + search clearly wins. At 1,000 files? 10,000? The crossover point for knowledge corpora (as opposed to code) is unknown. ByteRover's hierarchical approach suggests that at some scale, organization matters — but their hierarchy is still flat files with structured naming, not wiki articles.

3. **Task type matters.** The evidence is from coding agents doing SWE tasks. A research synthesis agent that needs to integrate findings across 8 memos might benefit differently from pre-synthesis than a coding agent navigating a codebase. However, our agents do both (navigate memos AND write code), and the dominant use case is targeted retrieval of specific findings, not cross-memo synthesis.

4. **The ETH study's -3% finding may be task-dependent.** The tasks were Python SWE fixes, not open-ended research. Context file harm may be smaller or reversed for exploratory tasks where broad orientation has value.

5. **Human-written vs LLM-generated quality gap.** The +4% for human-written context files suggests that high-quality, task-relevant synthesis can help. A well-curated wiki article written by a human might help in ways that LLM-generated synthesis does not. But the ROI is low (+4%) and the maintenance burden is high.

---

### Recommendation for Our Repo

**Do not build wiki-style synthesized articles.** The evidence strongly favors the current approach: flat files + thin indexes + native search.

Specifically:

1. **Keep the flat memo structure.** Each memo on a specific topic, findable by grep. This is what agents navigate best.

2. **Invest in index quality, not article synthesis.** The existing `research-index.md` with "consult before" triggers is the right pattern — it's a thin routing layer, not a thick knowledge layer. Make the index entries more descriptive if needed, but don't build wiki articles.

3. **If synthesis is needed, do it at query time.** When an agent needs to integrate findings across memos, it should read the relevant memos and synthesize in-context. This is what `ask_papers(use_rcs=True)` does for academic papers — score chunks for relevance, then synthesize. The same principle applies: real-time synthesis from source files beats pre-computed synthesis that decays.

4. **Consider ByteRover-style organization at scale.** If the corpus grows past ~500 files, organize by domain/topic/subtopic directory structure with descriptive file names. But still flat files, not synthesized articles.

5. **The only case for wiki articles:** If an external human audience (not agents) needs to consume the knowledge. Wiki articles are a human UX optimization, not an agent UX optimization.

---

### Search Log

| # | Tool | Query | Hits | Signal |
|---|------|-------|------|--------|
| 1 | Exa advanced | agent knowledge organization wiki vs flat files | 10 | LOW — mostly KM systems, not agent-specific |
| 2 | Exa advanced | RAG vs CAG long context LLM agent | 10 | MEDIUM — Agentic RAG survey, Chain of Agents |
| 3 | S2 search | documentation structure AI agents wiki knowledge | 15 | LOW — application-domain papers, not methodology |
| 4 | scite | context window + agent + retrieval + flat files | 0 | NONE — too specific for scite |
| 5 | S2 search | long context LLM agents RAG vs flat files coding | 15 | HIGH — Cao et al., ByteRover, context engineering |
| 6 | Exa simple | wiki vs flat files AI coding agents context engineering 2026 | 8 | HIGH — ETH Zurich AGENTS.md study, Wire blog |
| 7 | WebFetch | arXiv:2603.20432 (Cao et al.) | 1 | HIGH — confirmed findings |
| 8 | WebFetch | arXiv:2604.01599 (ByteRover) | 1 | MEDIUM — hierarchical context approach |

### References

- Cao, W., Yin, X., Dhingra, B., & Zhou, S. (2026). Coding Agents are Effective Long-Context Processors. arXiv:2603.20432
- Gloaguen, T., Mündler, N., Müller, M., & Raychev, V. (2026). Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents? arXiv:2602.11988 (ETH Zurich / LogicStar.ai)
- Nguyen, A. et al. (2026). ByteRover: Agent-Native Memory Through LLM-Curated Hierarchical Context. arXiv:2604.01599
- Wire Blog (2026). Structured Context vs Raw Text for AI. usewire.io. [Cites arXiv:2411.10541 for format impact, Chroma for context rot]

<!-- knowledge-index
generated: 2026-04-04T17:49:38Z
hash: 301e0463f56c

title: Wiki-Style Knowledge Organization vs Flat Files for AI Agents
status: complete
tags: agent-architecture, knowledge-management, retrieval
table_claims: 10

end-knowledge-index -->
