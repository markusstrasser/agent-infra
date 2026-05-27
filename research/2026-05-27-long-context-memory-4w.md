# Long-Context & Agent Memory — 4-Week Scan (2026-04-29 → 2026-05-27)

**Standard-tier pass.** Scope: 1M+ context behavior, tool attention at scale,
retrieval vs long-context, episodic memory, KV cache, agentic memory ecosystem.
**Primary trigger:** open question from `frontier-delta-2026-05-08` —
"Does Opus 4.7's 1M context preserve tool-attention quality past ~70%?"

## TL;DR

1. **The open question now has empirical evidence (arXiv:2605.02173).** Opus 4.7
   and Gemini 3.1 Pro hold **>80% multi-hop accuracy at 512K, modest degradation
   at 1M**. GPT-5.5 and Qwen3.6-plus cliff sharply between 512K→1M. DeepSeek V4
   Pro declines smoothly across the range. Single-needle is solved at 1M; multi-hop
   is the real differentiator.
2. **Agent memory ecosystem matured this window.** Mem0 2026 hits 93.4% on
   LongMemEval / 91.6% LoCoMo at <7K tokens/retrieval — a real production
   tradeoff curve, not vapor (preuve.ai stats, May).
3. **Group/multi-party memory is unsolved.** GroupMemBench (2605.14498):
   strongest memory system only 46.0% average; **BM25 matches or beats** most
   "agent memory" systems. Hard evidence that ingestion-time entity-flattening
   destroys the information group memory needs.
4. **KV cache is being made lossless.** VeriCache (2605.17613) drafts with
   compressed KV, verifies against full KV — **identical outputs to full-KV
   inference, up to 4× throughput**. The "lossy KV ≠ acceptable in production"
   debate is being closed by speculative-decoding-style architecture.
5. **Skill-bank work continues post-COS-PLAY.** SkillRAE (2605.10114) — skill
   graph + rescue-aware compilation — +11.7% over SOTA. Pattern is congruent
   with our skill bank; the novelty is *compilation*, not retrieval.

## The headline answer: Opus 4.7 at 1M tokens

**arXiv:2605.02173 "Retrieval and Multi-Hop Reasoning in 1M-Token Context
Windows: Evaluating LLMs on Classical Chinese Text"** (2026-05-04).

Tested 5 models at 256K / 512K / 1M tokens on (a) single-needle retrieval and
(b) three-hop chain reasoning:

| Model | Single-needle @1M | Multi-hop @1M | Degradation regime |
|---|---|---|---|
| Gemini 3.1 Pro | 100% | >80% at 512K, modest drop | **Stable** |
| Claude Opus 4.7 | 100% | >80% at 512K, modest drop | **Stable** |
| GPT-5.5 | 100% | sharp collapse 512K→1M | **Late-cliff** |
| Qwen3.6-plus | not perfect | sharp collapse 512K→1M | **Late-cliff** |
| DeepSeek V4 Pro | not perfect | gradual decline across range | **Smooth-decline** |

Key paper claim, verbatim from abstract: *"nominal context-window length is a
poor proxy for usable long-context multi-hop capability"*; the 512K→1M
transition is the sharpest differentiator among current frontier models.

**Implication for our infrastructure:**
- Opus 4.7's 1M context **does preserve usable quality past 70%** for
  retrieval-shaped tasks (the closest analogue to tool selection from a large
  schema bag). The earlier worry (from Tool Attention 2604.21816 simulations) is
  partially disconfirmed for Opus and Gemini Pro; **still confirmed** for
  GPT-5.5.
- We can stop hedging on Opus 4.7 1M for large-context analysis tasks where
  multi-hop reasoning is required. For GPT-5.5 the prior advice (keep <512K,
  externalize via RAG) stands.
- The probe I considered ("eager vs lazy schema at 800K on Opus") would now
  cost less than expected — paper's own results suggest the ceiling holds.
  Still worth doing if we ship a >300-tool MCP fleet, but not the priority.

**Confidence:** Single paper, single language (classical Chinese), specific
task shape. Treat as the strongest signal we have, not as a closed question.
Want a second paper in the same direction before fully updating priors.

## Tool-attention auxiliary evidence

- **channel.tel "Past 50 tools, function-calling accuracy falls off a cliff"
  (2026-05-03)** — practitioner measurement, not arxiv: function-calling decay
  curve becomes severe past 50 tools regardless of context length. Argues for
  **per-turn toolset scoping**. Aligns with our existing skill-bank design
  (lazy tool injection beats eager).
- **ofox.ai "Long-Context LLM Benchmarks 2026" (2026-05-21)** — secondary
  aggregator over RULER / MRCR v2 / NoLiMa @ 200K. Mainly framing material;
  no new measurements.
- **usewire "Long context tripled hallucinations in 35 open models"
  (2026-05-07)** — references a March 2026 study over 172B tokens, 35 open
  weights. Hallucinations triple as context grows. **Open-weight only**, so
  doesn't speak directly to Opus 4.7 / GPT-5.5 / Gemini 3.1 Pro. Useful as
  context-rot evidence at the lower tier.

## Agent memory benchmark wave

**LongMemEval-V2 (arXiv:2605.12493, 2026-05-12).** 451 manually curated
questions across 5 memory abilities for web agents (static recall, dynamic
state tracking, workflow knowledge, environment gotchas, premise awareness).
History trajectories up to **500 trajectories / 115M tokens**. Two proprietary
methods proposed: AgentRunbook-R (RAG) and AgentRunbook-C (trajectory-coded
sandbox). AgentRunbook-C **72.5%** vs strongest RAG baseline **48.5%** vs
off-the-shelf coding agent **69.3%**. Interpretation: the coding-agent +
trajectory storage pattern beats RAG for web-agent memory.
**Relevance:** validates our "executable substrate over passive retrieval"
intuition. Phenome / intel both shaped like this task class.

**GroupMemBench (arXiv:2605.14498, 2026-05-14).** Multi-party conversation
memory — speakers, audiences, theory-of-mind. Six adversarial categories
(multi-hop, knowledge-update, term-ambiguity, user-implicit, temporal,
abstention). **Strongest agent memory system: 46.0% average.** Knowledge
update 27.1%, term ambiguity 37.7%. **BM25 matches or beats most agent memory
systems.** Failure mode: current memory ingestion erases structural and
lexical features that group memory depends on.
**Relevance:** *if we ever build multi-user/shared-agent memory* (we don't
currently — all memory is per-user-per-project), this is the eval. Also: the
"BM25 beats X" pattern is a recurring red flag for over-engineered retrieval
stacks. Apply to our own knowledge-index hook.

**MNEMA (Zenodo 20010220, TUM, 2026-05-03).** Three-tier architecture:
LLM (substrate) + episodic memory (time-indexed) + semantic memory (typed
knowledge graph). Inter-session **consolidation** (episodic→semantic
distillation) and **self-inspection** (graph review + structurally-triggered
external acquisition). No benchmark numbers in the public abstract — would
need to read the PDF. Architecturally the closest match to what we already
do across `daily-logs/` (episodic) → `MEMORY.md` / improvement-log (semantic).
**Relevance:** validates our split (daily logs ≠ MEMORY.md is the right
boundary). Not adopting code; pattern-confirming reference.

**Mem0 2026 (preuve.ai stats, mem0.ai blog, May).** Token-efficient
algorithm. Numbers:

| System | LongMemEval | LoCoMo | Tokens/retrieval | p95 latency |
|---|---|---|---|---|
| Mem0 2026 | 93.4% | 91.6% | <7K | 1.44s |
| Full-context | 72.9% | n/a | ~26K | 9.87s (17.12s p95) |
| Zep | ~80% | n/a | n/a | n/a |
| MemPalace | 96.6% Recall@5 | n/a | retrieval-only | n/a |
| Oracle GPT-4o | 92% (ideal) → ~58% interactive | n/a | n/a | n/a |

40% token-cost reductions reported in real deployments. Mem0 episodic memory
blog (May 11) explicitly grounds the model in Tulving 1972 — semantic vs
episodic. Implementation: timestamp + scope (user/agent/run) + surrounding
context + metadata tags; auto-consolidation of repeated episodic → semantic.
**Relevance:** if we ever shop external memory infra (currently we don't —
git + filesystem + sqlite is our substrate), Mem0 is the leading candidate
on numbers. Letta/Zep/MemGPT are visibly behind on the same evals.

## KV cache — new compression regime

**VeriCache (arXiv:2605.17613, 2026-05-17).** Lossy KV cache → lossless LLM
inference. Method: use compressed KV to **draft** tokens, then **verify**
against full KV (speculative-decoding-style architecture, applied to KV
compression). Parallelizes compressed decoding (HBM-bound) with full-KV
retrieval (PCIe/network-bound). Amortizes drafting overhead. **Up to 4× higher
throughput than full-KV with identical outputs.** Compatible with
token-dropping and quantization compression families.
**Relevance:** infrastructure-level, not direct to us. But the
"speculative-decoding-pattern for KV" is architecturally significant — it
closes the lossy-KV debate for production. Expect inference providers to ship
this in 2026 H2; we benefit transparently.

**Conf-KV (arXiv:2605.24786, 2026-05-24).** Confidence-aware KV eviction +
mixed-precision storage for long-horizon inference.
**Minimal-Intervention KV Retention (arXiv:2605.14292, 2026-05-14).** Design-
space study + diversity-penalty survivor — small-budget regime.
Both are research-stage; neither has frontier-model evals at the scale we'd
need before adopting. Tracking, not adopting.

## Skill-bank update

**SkillRAE (arXiv:2605.10114, 2026-05-11).** Two-stage: offline builds a
multi-level skill graph (skill communities → skills → reusable subunits);
online does skill-ranked retrieval with **rescue-aware compact compilation**.
+11.7% over SOTA on SkillsBench (two public benchmarks total).
**Relevance:** congruent with our skill bank (`~/Projects/skills/`). Novel
contribution is **compilation** — not just "retrieve the skill" but "compile
retrieved skills into a compact, grounded, immediately-usable context." We
currently don't do this — our skills are loaded as-is by Claude Code skill
routing. Worth tracking; not adopting (our skill volume is too small to need
graph-based retrieval).

## Pertinent negatives

- **No new evidence on RAG-vs-long-context at frontier with proper controls
  in this window.** The biomedical RAG paper (2605.02520) doesn't bridge to
  Opus 4.7 / GPT-5.5 / Gemini 3.1 Pro tier.
- **No new tool-attention measurements specifically with >300 tools at >500K
  context** on frontier models. The closest is channel.tel's practitioner
  curve.
- **No frontier-tier memory architecture paper from a major lab** (Anthropic,
  OpenAI, DeepMind, Meta). Memory remains a research-and-startup space.
- **No new attention-degradation curves** that supersede the Chroma
  context-rot work cited in earlier memos. The aifounders.cz piece restates
  the Chroma findings, doesn't extend them.

## Open questions for next pass

1. **Single-paper limitation on the Opus-4.7-at-1M result.** Want a second
   empirical study (different language, different task shape) before fully
   closing the "tool attention at frontier" question.
2. **Does the GroupMemBench BM25-beats-memory pattern apply to our own
   knowledge-index hook?** Half-day probe: run a few representative agent
   questions against BM25-over-research/ vs current hook output.
3. **MNEMA PDF read.** Numbers absent from public abstract; the architecture
   is close enough to ours that benchmark numbers would either validate or
   challenge our daily-logs / MEMORY.md split.
4. **Mem0 2026 algorithm internals.** 93.4% LongMemEval at <7K tokens is
   striking. Worth reading the underlying technical post to see if the
   selection algorithm has transferable patterns even though we won't adopt
   their stack.

## Sources (graded)

| Grade | Source | Date | Notes |
|---|---|---|---|
| A | arXiv:2605.02173 1M-Token Multi-Hop | 2026-05-04 | Frontier-tested (Opus 4.7, Gemini 3.1 Pro, GPT-5.5, Qwen3.6, DeepSeek V4) |
| B | arXiv:2605.12493 LongMemEval-V2 | 2026-05-12 | 451 curated questions, proprietary methods |
| B | arXiv:2605.14498 GroupMemBench | 2026-05-14 | Multi-party adversarial; BM25-beats-memory finding |
| B | arXiv:2605.10114 SkillRAE | 2026-05-11 | Skill graph + compilation, +11.7% SOTA |
| B | arXiv:2605.17613 VeriCache | 2026-05-17 | Lossless KV via verify-against-full, 4× throughput |
| C | arXiv:2605.24786 Conf-KV | 2026-05-24 | Research-stage, no frontier eval |
| C | arXiv:2605.14292 Minimal-Intervention KV | 2026-05-14 | Small-budget design space |
| C | Zenodo 20010220 MNEMA | 2026-05-03 | TUM architecture; no public benchmark numbers |
| C | preuve.ai memory stats | 2026-05-04 | Aggregator, but numbers cross-reference Mem0 publications |
| C | mem0.ai episodic memory blog | 2026-05-11 | Vendor blog, framing-only |
| C | channel.tel function-calling decay | 2026-05-03 | Practitioner blog, useful pattern |
| C | aifounders.cz context-rot summary | 2026-05-04 | Restates Chroma March 2026 work |
| C | usewire long-context hallucinations | 2026-05-07 | Open-weight only, doesn't reach frontier |
| C | ofox.ai long-context benchmarks | 2026-05-21 | Aggregator over RULER/MRCR/NoLiMa |

Pre-frontier downweighted: the open-weight hallucination study and the
small-budget KV cache papers.

## Bottom line for this repo

- **Update prior on Opus 4.7 1M.** It works for multi-hop at >80% to 512K
  and degrades modestly at 1M for retrieval-shaped tasks. Stop hedging.
- **Keep skill-bank design.** SkillRAE confirms direction; their compilation
  step is a future-extension if our skill volume grows past ~50.
- **Watch GroupMemBench failure mode in our own knowledge-index hook.**
  BM25-beats-fancy-memory is a recurring pattern. Empirically check next time
  we touch the hook.
- **Don't adopt external memory infra.** Mem0 numbers are good, but git +
  filesystem + sqlite + skills is currently sufficient; the bar to switch
  would be a measured gap, not a vendor blog.
- **VeriCache is transparent infrastructure.** No action; we benefit when
  inference providers ship it.

<!-- knowledge-index
generated: 2026-05-27T09:17:50Z
hash: a4a64ae73916


end-knowledge-index -->
