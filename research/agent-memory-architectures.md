---
title: Memory and State Management
date: 2026-03-24
---

# Memory and State Management

*Split from `frontier-agentic-models.md` on 2026-03-01. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*Date: 2026-02-27, updated 2026-03-24. Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Agentic memory benchmarks are underscaled and metrics misaligned with semantic utility | 5 architectures tested across backbone models | HIGH | [arXiv:2602.19320] | VERIFIED |
| 2 | A-MEM Zettelkasten-style connections outperform baselines across 6 models | ICLR 2026 accepted paper | HIGH | [arXiv:2502.12110] | VERIFIED |
| 3 | MemOS beats mem0, LangMem, Zep, OpenAI-Memory on LOCOMO benchmark | Self-reported benchmark (not independent) | MEDIUM | [arXiv:2505.22101, GitHub] | VERIFIED-SELF-REPORTED |
| 4 | Structurally lossless trimming reduces tokens 20-86% while preserving all user/assistant messages | 76 real coding sessions, single user | MEDIUM | [arXiv:2602.22402] | VERIFIED-SINGLE-USER |
| 5 | Dual-process memory (fast vector + full deliberation fallback) improves complex query accuracy | D-Mem paper | MEDIUM | [arXiv:2603.18631] | VERIFIED-ABSTRACT-ONLY |
| 6 | Dopamine-gated RPE routing fixes A-MEM's O(N²) evolution bottleneck | D-MEM paper (different from #5) | MEDIUM | [arXiv:2603.14597] | VERIFIED-ABSTRACT-ONLY |
| 7 | Episodic memory is the missing piece for long-term agents (position paper, 29 citations) | Theoretical argument + cognitive science analogy | MEDIUM | [arXiv:2502.06975] | POSITION-PAPER |
| 8 | Agent-autonomous compression achieves 22.7% token reduction while maintaining accuracy on SWE-bench | N=5 instances, Claude Haiku 4.5, small sample | LOW | [arXiv:2601.07190] | VERIFIED-SMALL-N |
| 9 | File-based memory hits context rot, multi-hop, and temporal query limitations in production | Practitioner report (sells competing product) | MEDIUM | [buttondown.com/nicoloboschi] | SOURCE-BIASED |
| 10 | Multi-agent memory coordination breaks down at 10+ agents working in parallel | Practitioner analysis | MEDIUM | [thegradient.ink] | UNVERIFIED |
| 11 | Three-layer memory (sensory/episodic/semantic) is the convergent architecture | Multiple independent sources | HIGH | [multiple] | PATTERN |
| 12 | AriadneMem threads disconnected evidence across time for multi-hop answers | Lifelong dialogue benchmark | MEDIUM | [arXiv:2603.03290] | VERIFIED-ABSTRACT-ONLY |
| 13 | LifelongAgentBench shows current agents fail at knowledge accumulation/transfer | New benchmark, 11 citations | HIGH | [arXiv:2505.11942] | VERIFIED |

## Prior Findings (still holding)

**"Anatomy of Agentic Memory" (arXiv:2602.19320, Feb 2026):** Taxonomy of 5 memory architectures. Benchmarks are underscaled, evaluation metrics misaligned, system-level costs overlooked. Memory systems "often underperform their theoretical promise." [SOURCE: arXiv:2602.19320] [PREPRINT]

**A-MEM (arXiv:2502.12110, ICLR 2026):** Zettelkasten-inspired dynamic memory with structured attributes, historical connections, memory evolution. [SOURCE: arXiv:2502.12110] [PUBLISHED ICLR 2026]

**"Memory in the Age of AI Agents" survey (arXiv:2512.13564, Dec 2025):** Comprehensive survey. Open challenges: catastrophic forgetting, retrieval efficiency, memory structure choices. [SOURCE: arXiv:2512.13564]

**ICLR 2026 MemAgents Workshop:** Field considers agent memory unsolved. Key themes: long-horizon competence, standardized metrics, distinguishing real memory from shortcut exploitation. [SOURCE: iclr.cc/virtual/2026/workshop]

## New Findings (March 2026 update)

### Papers

**CMV — Contextual Memory Virtualisation (arXiv:2602.22402, Feb 2026):** Treats accumulated LLM understanding as version-controlled state. DAG with snapshot, branch, and trim primitives. Three-pass structurally lossless trimming: strips tool outputs, base64, metadata while preserving user/assistant messages verbatim. **20-86% token reduction** (mean 20%, mixed tool-use sessions average 39%). Break-even within 10 turns. Evaluated on 76 real coding sessions. **Directly relevant to our compaction problem.** [SOURCE: arXiv:2602.22402] [PREPRINT]

**D-Mem — Dual-Process Memory (arXiv:2603.18631, March 2026):** Kahneman System 1/System 2 inspired. Fast vector retrieval for routine queries + "Full Deliberation" module as high-fidelity fallback for complex queries. Learns to route queries to the right path. Addresses the fundamental tension between retrieval speed and accuracy. [SOURCE: arXiv:2603.18631] [PREPRINT]

**D-MEM — Dopamine-Gated Agentic Memory (arXiv:2603.14597, March 2026):** Different paper from above. Biologically-inspired Reward Prediction Error (RPE) gating from VTA dopamine system. Decouples short-term interaction from long-term cognitive restructuring. Only processes memories that are "surprising" (high prediction error) through the expensive evolution pipeline. Fixes A-MEM's O(N²) bottleneck. [SOURCE: arXiv:2603.14597] [PREPRINT]

**AriadneMem (arXiv:2603.03290, March 2026):** Addresses two failure modes: (i) disconnected evidence requiring linking facts distributed across time, (ii) multi-hop answers needing temporal threading. Lifelong memory with evidence threading. [SOURCE: arXiv:2603.03290] [PREPRINT]

**Focus — Autonomous Compression (arXiv:2601.07190, Jan 2026):** Agent autonomously decides when to consolidate key learnings into persistent "Knowledge" block and prune raw history. Inspired by slime mold (Physarum polycephalum) exploration strategies. 22.7% token reduction on SWE-bench Lite (N=5, Haiku 4.5). Small sample but the mechanism is interesting. [SOURCE: arXiv:2601.07190] [PREPRINT]

**Episodic Memory position paper (arXiv:2502.06975, Feb 2025):** 29 citations. Argues episodic memory (context-rich, temporally-located experiences) is fundamentally different from semantic memory (distilled facts) and agents need both. Current systems collapse all memory into semantic. [SOURCE: arXiv:2502.06975] [PREPRINT]

**Memory for Autonomous LLM Agents survey (arXiv:2603.07670, March 2026):** Most comprehensive recent survey (2022-early 2026). Formalizes agent memory as write-manage-read loop. Three-dimensional taxonomy: temporal scope × representational substrate × control policy. Five mechanism families: context-resident compression, retrieval-augmented stores, reflective self-improvement, hierarchical virtual context, policy-learned management. [SOURCE: arXiv:2603.07670] [PREPRINT]

**Collaborative Memory (arXiv:2505.18279, May 2025):** Multi-user memory sharing with dynamic access control for agent ensembles. 18 citations. Relevant when 3+ agents need shared state. [SOURCE: arXiv:2505.18279] [PREPRINT]

**ForgetAgent (2026):** Verifiable deletion in multi-layer memory architectures. Privacy/compliance angle — guarantees deleted memories are unrecoverable. [SOURCE: DOI:10.22214/ijraset.2026.78270]

**LifelongAgentBench (arXiv:2505.11942, May 2025):** 11 citations. Shows current agents are stateless and unable to accumulate/transfer knowledge over time. New benchmark for lifelong learning evaluation. [SOURCE: arXiv:2505.11942] [PREPRINT]

**Aeon (arXiv:2601.15311, Jan 2026):** Neuro-symbolic memory management. Hybrid approach combining neural retrieval with symbolic graph structures. Addresses "Lost in the Middle" and quadratic attention cost. [SOURCE: arXiv:2601.15311] [PREPRINT]

### GitHub Repos (traction-filtered, 2025-2026)

| Repo | Stars | Key Idea | Language | Relevance |
|------|-------|----------|----------|-----------|
| **MemTensor/MemOS** | 7.7K | Memory OS with skill memory, cross-task reuse. Beats baselines on LOCOMO. | Python/TS | High concept, heavy deps |
| **agentscope-ai/ReMe** | 2.4K | Memory management kit (Alibaba). File-based + vector. v0.3.1. | Python | Worth watching |
| **foramoment/engram-ai-memory** | ~1K | Cognitive memory: Ebbinghaus forgetting, knowledge graph, semantic search. Zero API cost. Claude/Cursor compatible. | Go | **Most relevant to us** |
| **agentralabs/agentic-memory** | ~500 | Belief revision, cognitive architecture, binary format. | Python | Interesting concepts |
| **mnemon-dev/mnemon** | ~300 | Go-based, LLM-supervised persistent memory. Claude Code compatible. | Go | Niche |
| **smysle/agent-memory** | ~200 | Lifecycle management (creation→consolidation→decay→archival). | Python | Good lifecycle model |

### Practitioner Consensus

Multiple independent practitioners converging on the same conclusions:

1. **Three-layer memory is the convergent architecture:** sensory (in-context) → episodic (session history) → semantic (distilled knowledge). [SOURCE: multiple Medium articles, DEV Community, The Gradient, Feb-March 2026]

2. **File-based works for single-agent, breaks at scale:** Context rot, multi-hop failures, temporal query limitations. The "file is all you need" claim benchmarks well on small examples but hits walls in production. [SOURCE: buttondown.com/nicoloboschi] — NOTE: author sells competing product, but the specific failure modes ring true.

3. **HOT/COLD architecture for production:** Bounded low-latency HOT path during generation, async COLD path for consolidation/indexing. [SOURCE: Medium/@betanu701, March 2026]

4. **Multi-agent memory coordination is the actual bottleneck:** At 10+ parallel agents, the problem isn't individual agent memory but shared state coordination. [SOURCE: thegradient.ink, 2026]

5. **"100-tick distillation" pattern:** After every N interactions, consolidate session memory into a SOUL.md or equivalent persistent file. Decay older entries. [SOURCE: clawcity.app]

## What's CLAIMED → PARTIALLY RESOLVED

- ~~Whether self-managing memory or externally-managed works better.~~ → **Still no controlled comparison.** The Anatomy paper's finding that all approaches have evaluation gaps still holds.
- ~~Whether graph-based memory meaningfully outperforms flat.~~ → **Incremental at best.** MemOS claims strong LOCOMO results but self-reported. A-MEM's Zettelkasten is validated (ICLR) but on conversational tasks.
- **NEW: Whether lossless trimming beats lossy compaction.** → CMV paper says yes (20-86% reduction, preserves all messages). But single-user study. Needs replication.
- **NEW: Whether surprise-gating improves memory efficiency.** → D-MEM's RPE routing is theoretically sound (avoids processing conversational noise) but no independent evaluation yet.

## Engineering Implications for Us

### What we already have (implicitly)
We already implement the three-layer architecture without naming it:
- **Sensory:** context window (in-session state)
- **Episodic:** session JSONL transcripts, searchable via `sessions.py` FTS5
- **Semantic:** MEMORY.md, research memos, improvement-log, substrate

### Actionable gaps (ordered by expected value)

**1. Structurally lossless trimming (CMV paper) — HIGH value, LOW complexity**
Strip tool outputs, base64, raw metadata from session transcripts before/during compaction while preserving user/assistant messages verbatim. Our compaction-canary already detects information loss. CMV's three-pass algorithm could be a concrete improvement: (a) identify mechanical bloat, (b) extract and externalize, (c) rewrite with references. 39% reduction in mixed tool-use sessions matches our typical sessions. Could implement as a pre-compaction hook or a `sessions.py` enhancement.

**2. Memory decay/staleness scoring — MEDIUM value, LOW complexity**
Engram's Ebbinghaus forgetting curves applied to MEMORY.md entries. Score entries by `last_accessed × access_count`. Auto-flag entries unread in N sessions for review/pruning. We do ad-hoc review but have no systematic decay. Substrate already has staleness tracking — extend to MEMORY.md. Simple: add `last_referenced` dates to memory files, sweep weekly.

**3. Surprise-gated writing — MEDIUM value, MEDIUM complexity**
D-MEM's RPE concept applied to improvement-log: before writing a finding, check if it's actually surprising (diverges from existing rules/findings). We have the 2+ recurrence gate but that's recurrence-gated, not novelty-gated. A finding that matches 5 existing rules is noise even if it recurs. Could add a dedup/similarity check against existing findings before appending.

**4. Autonomous consolidation trigger — LOW value (we partially have this)**
Focus-style: detect when working memory is 70%+ full and autonomously consolidate to checkpoint.md. We have the checkpoint mechanism but the trigger is ad-hoc (instruction-driven). Claude Code's compaction already handles this somewhat. Marginal improvement.

**5. Episodic retrieval upgrade — LOW value now, HIGHER at scale**
AriadneMem-style temporal threading across sessions. Our `sessions.py` FTS5 is keyword-based — adding timestamped causal edges (session A's finding led to session B's fix) would help connect findings. Not urgent at current scale. Would matter more with 100+ daily sessions.

### What we should NOT build
- **MemOS/Cognee-scale infrastructure** — massive dep surface, our repos are 20-50 files. Files+git+SQLite remains the right tier.
- **Vector DB layer** — FTS5 + file reads work for our scale. Vector adds infra cost for marginal retrieval improvement.
- **Multi-agent shared memory** — only 4 concurrent agents, mostly independent. Not hitting the coordination bottleneck yet.
- **Skill memory / cross-task reuse tracking** — MemOS's concept is interesting but premature for us. Skills are human-authored and rarely change.

### Assessment: files+git still wins for us

The disconfirmation search found legitimate criticisms of file-based memory (context rot, multi-hop, temporal queries), but the critic (Boschi) sells competing products, and the specific failure modes require scale we don't have (100+ agent sessions/day, 10+ concurrent agents). Our system's advantages — auditability (git log), simplicity, zero infrastructure, compaction survival (CLAUDE.md/rules auto-load) — remain load-bearing.

The one technique with clear ROI is **structurally lossless trimming** from the CMV paper. Everything else is either premature or already partially implemented.

## Revisions

- **2026-03-24:** Major update. Added 11 new papers, 6 GitHub repos, practitioner consensus findings. Upgraded from snapshot to full claims table. Added actionable gaps section with priority ordering. Prior conclusion (files+git defensible) still holds but with sharper understanding of where it breaks.

<!-- knowledge-index
generated: 2026-03-24T14:38:55Z
hash: 685d7b1b718b

title: Memory and State Management
table_claims: 13

end-knowledge-index -->
