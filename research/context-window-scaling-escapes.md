# Context Window Scaling: Bigger =/= Better — But Architectural Escapes Emerging

*Split from `frontier-agentic-models.md` on 2026-03-01. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*Date: 2026-02-27. Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*

---

### What's PROVEN

All prior findings confirmed. Additionally:

**NEW — Sparse attention explosion (2025-2026):** Every major lab now has a sparse attention project. This confirms the field accepts n² as the root cause.

| System | Lab | Key Innovation | Status |
|---|---|---|---|
| **NSA (Native Sparse Attention)** | DeepSeek | Dynamic hierarchical token selection, natively trainable | **Best Paper ACL 2025** [arXiv:2502.11089] |
| **MoBA** | Moonshot AI | MoE-style block attention routing | **NeurIPS 2025 Spotlight**, deployed in Kimi [arXiv:2502.13189] |
| **FlashMoBA** | MIT Han Lab | CUDA kernel for MoBA, 14.7x over FlashAttention-2 | [arXiv:2511.11571] [PREPRINT] |
| **DSA** | DeepSeek | O(Lk) selective attendance, k << L | Deployed in V3.2-Exp |
| **SQA** | — | Reduces query heads (not KV), 3x throughput at 32K-200K | [arXiv:2510.01817] [PREPRINT] |
| **SSA** | — | Stochastic full/sparse training, 50/50 | [arXiv:2511.20102] [PREPRINT] |

Two in production (MoBA in Kimi, DSA in DeepSeek). NSA won best paper at ACL 2025. Anthropic, OpenAI, and Google have NOT announced sparse attention in flagship models — open question whether they have better internal approaches.

**NEW — Alternatives to compaction:**

- **RLM (Recursive Language Models, arXiv:2512.24601):** Treats long prompts as external environment. LLM uses Python REPL to inspect/transform input, recursively calls sub-LLMs. **Never summarizes** — frames summarization (including compaction) as information-lossy. Handles inputs 2 orders of magnitude beyond context window. Outperforms base LLMs even on shorter prompts. Prime Intellect calls this "learned context folding." [SOURCE: arXiv:2512.24601, primeintellect.ai] [PREPRINT]

- **TTT-E2E (End-to-End Test-Time Training, arXiv:2512.23675):** Reformulates long-context as continual learning: sliding-window attention that continues learning at test time. For 3B models: **constant inference latency regardless of context length** — 2.7x faster than full attention at 128K. [SOURCE: arXiv:2512.23675] [PREPRINT]

- **LoongRL (ICLR 2026):** RL for long-context reasoning. **Models trained at 16K effectively solve 128K tasks.** +23.5% absolute gain. LoongRL-14B (74.2) rivals o3-mini (74.5). The model learns WHEN and HOW to search, not how to hold everything in attention. [SOURCE: openreview.net, ICLR 2026] [PUBLISHED]

- **qTTT (arXiv:2512.13898):** Identifies "score dilution" as the mechanism behind long-context failures. Cache-preserving gradient updates to query projections only. Provably overcomes static self-attention limitations. [SOURCE: arXiv:2512.13898] [PREPRINT]

- **Document Reconstruction RLVR (arXiv:2602.08237):** Unsupervised RL that trains models to reconstruct documents by identifying missing paragraphs. Captures global narrative coherence without human annotation. [SOURCE: arXiv:2602.08237] [PREPRINT]

### New benchmarks beyond NIAH

| Benchmark | What it tests | Key finding |
|---|---|---|
| **NoLiMa** (ICML 2025) | Latent associative reasoning (minimal lexical overlap) | Performance degrades sharply when literal matching unavailable |
| **MECW** (arXiv:2509.21361) | Actual vs advertised effective context | >99% gap between advertised and effective for most models |
| **HELM Long Context** (Stanford, Sep 2025) | Standardized MRCR + RULER across 10 models | Prior evals used inconsistent benchmark versions |
| **LOCA-bench** (arXiv:2602.07962) | Language agents under controllable context growth | Advanced context management substantially improves success |
| **HELMET + LongProc** (Princeton) | Real RAG, citation, summarization; long output | Real-world task fidelity, not synthetic needles |

### Engineering implications for us

**RLM's "never summarize, delegate instead" is architecturally the same as our subagent pattern taken to its logical conclusion.** This validates our direction. But it challenges compaction — if compaction is information-lossy, maybe delegation to a sub-task is always better than summarizing the conversation.

**LoongRL's result** (16K trains solve 128K) suggests that the model's ability to **search its own context strategically** may matter more than raw window size. This supports our JIT retrieval pattern over our dump-everything-in-context anti-pattern.

<!-- knowledge-index
generated: 2026-03-21T23:52:35Z
hash: d525eff92127


end-knowledge-index -->
