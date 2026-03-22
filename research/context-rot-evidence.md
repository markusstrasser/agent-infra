# Context Rot: Universal and Architectural — But the Curve Is Flattening

*Split from `frontier-agentic-models.md` on 2026-03-01. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*Date: 2026-02-27. Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*

---

### What's PROVEN

**Chroma Research (2026)** tested 18 frontier models including Claude Opus 4, Sonnet 4, Sonnet 3.7, Haiku 3.5, o3, GPT-4.1, Gemini 2.5 Pro/Flash, Qwen3. All 18 models degraded with context length. [SOURCE: research.trychroma.com/context-rot]

Key empirical findings:
- **Lost-in-the-Middle (Liu et al., Stanford/TACL 2024):** ~75% accuracy at position 1 (start), ~55% at position 10 (middle), ~72% at position 20 (end). U-shaped curve. 30%+ performance drop for middle-positioned information. [SOURCE: Liu et al. 2024]
- **Distractors compound:** Even a single distractor reduces performance vs. needle-only. Four distractors show compound degradation. Individual distractors have non-uniform impact (distractor 3 consistently worse than others in tested configs). [SOURCE: Chroma]
- **Shuffled haystacks IMPROVE performance:** Counterintuitively, sentence-level randomization of haystack content consistently improved performance across all 18 models. Logical flow of ideas makes context rot worse. [SOURCE: Chroma]
- **n-squared attention budget:** Transformer architecture creates n^2 pairwise token relationships. 10K tokens = 100M relationships. 100K = 10B. This is architectural, not a bug. [SOURCE: Anthropic context engineering blog, Sep 2025]

**NEW — Du et al. "Context Length Alone Hurts" (EMNLP 2025):** Even when models **perfectly retrieve** all relevant information, performance still degrades 13.9%–85% as input length increases within claimed context windows. Degradation persists even when irrelevant tokens are replaced with whitespace, and even when models are **forced to attend only to relevant tokens**. This is the strongest evidence yet: the problem is processing capacity, not retrieval failure. Simple mitigation: prompt model to recite retrieved evidence before solving ("recitation strategy") — +4% on RULER for GPT-4o. [SOURCE: arXiv:2510.05381, EMNLP 2025]

**NEW — MECW "Maximum Effective Context Window" (Paulsen, arXiv:2509.21361):** Measured gap between advertised maximum context window and actually usable effective context. Top models failed with as few as **100 tokens in context** on harder tasks. Most experienced severe degradation by 1K tokens. All fell >99% short of their advertised MCW. [SOURCE: arXiv:2509.21361] [PREPRINT]

**NEW — PAPerBench (arXiv:2602.15028):** ~29,000 instances, 1K to 256K tokens, 377K evaluation questions. Both personalization quality and privacy awareness degrade with context length. Theoretical analysis attributes this to **attention dilution** in soft attention with fixed-capacity Transformers. [SOURCE: arXiv:2602.15028] [PREPRINT]

### What's CLAIMED (degradation curve flattening)

**NEW — Opus 4.6 MRCR v2:** 76% on 8-needle retrieval at 1M tokens, up from Sonnet 4.5's 18.5% — a **4x improvement**. This partially resolves our prior unknown about whether Opus 4.6 has different degradation curves. The curve IS flatter for this model on multi-needle retrieval. [SOURCE: anthropic.com/news/claude-opus-4-6] [VENDOR BENCHMARK]

**NEW — Gemini 3 Pro MRCR cliff:** 77% at 128K tokens, drops to **26.3% at 1M tokens** — a 50-point cliff. 1M context is NOT equally reliable across providers. [SOURCE: llm-stats.com] [BENCHMARK]

**NEW — GPT-5.2 MRCR:** Near-100% (98%) on 4-needle variant out to 256K tokens. Smaller window (400K) but apparently much higher reliability within range. May indicate a deliberate quality-over-quantity architecture trade. [SOURCE: awesomeagents.ai] [BENCHMARK]

**NEW — Context Discipline (arXiv:2601.11564):** Llama-3.1-70B accuracy declined only from 98.5% to 98% at 15K words. BUT inference time showed "marked, non-linear increase." For simple retrieval, context rot may be less severe than assumed. The real tax may be computational (prefill time, memory bandwidth) rather than cognitive for easy tasks — but cognitive degradation dominates on hard tasks. [SOURCE: arXiv:2601.11564] [PREPRINT]

### What's SPECULATED → PARTIALLY RESOLVED

- ~~Whether Opus 4.6 specifically has different degradation curves~~ → YES, substantially flatter. 76% MRCR at 1M is a genuine step change. But this is vendor-reported on a single benchmark — independent evaluation needed.
- ~~Whether 1M context is a marketing number~~ → DEPENDS ON MODEL. Opus 4.6 appears genuinely more usable at 1M than predecessors. Gemini 3 Pro shows a 50-point cliff — effectively unusable past 128K.
- The auto-compact hypothesis (performance from reserving free context for reasoning) remains unresolved and plausible.

### Engineering implications for us

Context rot remains universal and architectural. **Every token in CLAUDE.md, rules, and skill descriptions degrades reasoning.** The progressive disclosure architecture (CLAUDE.md → rules → skills) remains correct.

**NEW nuance:** The degradation curve IS getting flatter for frontier models on retrieval tasks. But the Du et al. EMNLP result shows that even with perfect retrieval and forced attention, reasoning quality still degrades. **Don't conflate better retrieval with better reasoning over context.** Our subagent pattern remains the right architecture.

**NEW technique worth adopting:** Recitation strategy (prompt model to repeat relevant evidence before answering). Training-free, model-agnostic, +4% on RULER. Low cost, easy to add to skills.

<!-- knowledge-index
generated: 2026-03-22T00:13:51Z
hash: 77d70ff4a520


end-knowledge-index -->
