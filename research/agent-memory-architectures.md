# Memory and State Management

*Split from `frontier-agentic-models.md` on 2026-03-01. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*Date: 2026-02-27. Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*

---

### What's PROVEN

All prior findings hold. Additionally:

**NEW — "Anatomy of Agentic Memory" (arXiv:2602.19320, Feb 2026):** Taxonomy and empirical analysis of 5 memory architectures (LOCOMO, AMem, MemoryOS, Nemori, MAGMA) across multiple backbone models. Key findings: **benchmarks are underscaled, evaluation metrics are misaligned with semantic utility, performance varies significantly across backbone models, and system-level costs are frequently overlooked.** Explains why agentic memory systems "often underperform their theoretical promise." [SOURCE: arXiv:2602.19320] [PREPRINT]

**NEW — A-MEM "Agentic Memory" (arXiv:2502.12110, ICLR 2026):** Zettelkasten-inspired dynamic memory. When new memory added, generates structured attributes (descriptions, keywords, tags), identifies connections to historical memories, enables memory evolution. Superior to SOTA baselines across 6 foundation models. [SOURCE: arXiv:2502.12110, OpenReview] [PUBLISHED ICLR 2026]

**NEW — "Memory in the Age of AI Agents" survey (arXiv:2512.13564, Dec 2025):** Comprehensive survey covering the fragmented landscape. Open challenges: catastrophic forgetting, retrieval efficiency, memory structure choices (structured vs unstructured, symbolic vs neural, graph vs vector). [SOURCE: arXiv:2512.13564]

**NEW — ICLR 2026 MemAgents Workshop:** Dedicated workshop on memory for LLM-based agentic systems. Key themes: long-horizon competence, standardized memory metrics, distinguishing true memory use from shortcut exploitation. Indicates the field considers this an unsolved problem. [SOURCE: iclr.cc/virtual/2026/workshop]

### What's CLAIMED → PARTIALLY RESOLVED

- ~~Whether self-managing memory (Letta) or externally-managed (Claude Code files+git) works better.~~ → **Still no controlled comparison**, but the Anatomy paper shows that ALL memory approaches have significant evaluation gaps. The question may be premature — we don't have good metrics to compare them.
- ~~Whether graph-based memory meaningfully outperforms flat.~~ → **Incremental gains at best** (Mem0: +2%). A-MEM's Zettelkasten approach shows promise but evaluation is on conversational tasks, not our use case (entity tracking, investigation state).

### Engineering implications for us

Our files+git approach remains defensible. The Anatomy paper shows that fancier memory architectures "often underperform their theoretical promise" due to evaluation gaps and cost overhead. Files+git has the advantage of **auditability** (git log), **simplicity**, and **zero infrastructure**. The A-MEM Zettelkasten pattern (structured connections between memories) is conceptually interesting but adds complexity we don't need yet.

<!-- knowledge-index
generated: 2026-03-21T23:52:34Z
hash: 0fa3264ebfba


end-knowledge-index -->
