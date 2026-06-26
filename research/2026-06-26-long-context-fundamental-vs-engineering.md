---
title: "Long-Context Degradation: What's Information-Theoretically Fundamental vs an Engineering Artifact"
date: 2026-06-26
tier: Deep
question: "Is long-context performance degradation in transformer LLMs fundamental or solvable? Separate the floor we can't beat from the artifacts we can innovate out of."
---

# Long-Context Degradation — Fundamental vs Engineering

**Question:** When vendors claim 100M-token context, is the performance decay at length a law of nature or an engineering problem? Separate the information-theoretic floor from contingent training/architecture artifacts.

**Tier:** Deep | **Date:** 2026-06-26
**Ground truth:** Builds on local memos `research/context-rot-evidence.md` (2026-03-21) and `research/2026-05-27-long-context-memory-4w.md`. This memo reframes their evidence around the fundamental/contingent axis and adds the architecture-side primaries (SSMax, SSM-recall, attention sinks, Magic LTM-2).

---

## TL;DR — the one-paragraph answer

There are **three** separable phenomena, and they sit at different depths:

1. **Cost** (O(n²) compute / O(n) KV cache) — an **engineering** problem with a hard tradeoff attached. You can go sub-quadratic, but only by giving up lossless all-pairs recall. *Innovate-able, but the escape has a price.*
2. **Softmax dilution** — **fundamental in vanilla form** (the max of a softmax over n items provably → 0 as n grows), but **engineerable** with logit scaling (SSMax). *Half-fundamental, half-fixed.*
3. **Reasoning-capacity decay** — even with *perfect retrieval and forced attention*, a fixed-width model still degrades. This is the **information-bottleneck floor** and it is the genuinely fundamental one. *Not innovate-able without growing the model or offloading state.*

The "100M context" marketing conflates **capacity** (can the window hold 100M tokens? — yes, engineerable) with **utility** (can the model reason over all 100M uniformly well? — no, floored). The honest frontier is **hierarchical memory + retrieval**, not dense 100M attention, because most of a 100M context is irrelevant to any query and spending all-pairs compute to rediscover that every forward pass is waste.

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Dense self-attention is O(n²) compute; FlashAttention makes *memory* O(n) (online softmax) but compute stays quadratic | Architecture fact; n² pairwise relationships (10K tok = 100M pairs) | HIGH | local `context-rot-evidence.md` [SOURCE: Anthropic context-engineering blog] | VERIFIED |
| 2 | Softmax's max element → 0 as input size n grows → attention distribution flattens at long context, hurting retrieval & length-generalization | Mathematical property + LM experiments | HIGH | [SOURCE: arXiv:2501.19399 SSMax] | VERIFIED |
| 3 | Replacing softmax with Scalable-Softmax (logit scale ∝ log n) restores sharp attention at long context; retrofittable mid-pretraining | Pretraining + retrieval experiments | HIGH | [SOURCE: arXiv:2501.19399] | VERIFIED |
| 4 | Even with *perfect retrieval* and even when *forced to attend only to relevant tokens*, models still degrade 13.9%–85% as raw input length grows | Controlled ablation (irrelevant tokens → whitespace, still degrades) | HIGH | [SOURCE: arXiv:2510.05381 Du et al., EMNLP 2025] | VERIFIED |
| 5 | The degradation in #4 is a *processing-capacity* limit, not a retrieval limit — the strongest evidence the floor is real | Same paper; recitation mitigates only +4% on RULER | HIGH | [SOURCE: arXiv:2510.05381] | VERIFIED |
| 6 | Sub-quadratic recurrent models (SSMs/Mamba) compress history into fixed-size state → provably lossy on associative recall vs transformers | AR benchmark; transformers≠SSMs on in-context recall | HIGH | [SOURCE: arXiv:2508.19029 "When recalling in-context, Transformers are not SSMs"] | VERIFIED |
| 7 | Window attention fails past cache size; keeping a few initial "attention sink" tokens recovers it → enables streaming to "infinite" length but does NOT extend the *effective context* | StreamingLLM | HIGH | [SOURCE: arXiv:2309.17453] | VERIFIED |
| 8 | Advertised context window ≫ effective usable window; top models degrade severely far below their max (some by ~1K tokens on hard tasks) | MECW measurement across frontier models | MED | [SOURCE: arXiv:2509.21361 Paulsen] [PREPRINT] | VERIFIED |
| 9 | Degradation curve is *flattening* for frontier models on retrieval: Opus 4.6 76% on 8-needle @1M (vs Sonnet 4.5 18.5%); Opus 4.7/Gemini 3.1 Pro hold >80% multi-hop @512K | Vendor + independent benchmarks | MED | local memos [SOURCE: anthropic.com; arXiv:2605.02173] | VERIFIED |
| 10 | Retrieval at length is NOT uniform across vendors: Gemini 3 Pro 77%@128K → 26.3%@1M (50-pt cliff); GPT-5.5 cliffs 512K→1M | MRCR / multi-hop benchmarks | MED | local memos [BENCHMARK] | VERIFIED |
| 11 | Magic claims a 100M-token LTM model; explicitly argues needle-in-haystack is too easy (semantically odd needle is cheatable) and uses a harder eval | Vendor research blog | MED | [SOURCE: magic.dev/blog/100m-token-context-windows, 2024-08] [VENDOR] | VERIFIED |
| 12 | Attention dilution in fixed-capacity transformers is the theoretical attribution for personalization/privacy decay at length | Theory + 29K-instance benchmark | MED | local memo [SOURCE: arXiv:2602.15028 PAPerBench] [PREPRINT] | VERIFIED |
| 13 | KV cache can be made effectively lossless+cheap: speculative-decoding-style verify against full KV → identical outputs, up to 4× throughput | VeriCache | MED | local memo [SOURCE: arXiv:2605.17613] [PREPRINT] | VERIFIED |

---

## The framework: three phenomena at three depths

### Phenomenon 1 — Cost (engineering, with a priced escape)

Dense attention computes every query·key pair: **O(n²) compute**. FlashAttention removed the O(n²) *memory* via online softmax (tiling, never materialize the full matrix) but the **compute is still quadratic** [Claim 1]. The KV cache grows **O(n)** per token, which is the practical memory wall at inference.

You can go sub-quadratic. Every route trades the same thing — **all-pairs interaction**:

| Approach | Mechanism | What it gives up |
|---|---|---|
| **SSMs / Mamba** | Compress history into fixed-size recurrent state | Exact associative recall — provably lossy [Claim 6] |
| **Linear attention** | Kernel feature map, O(n) | Sharp selective recall (same fixed-state problem) |
| **Sliding window + attention sinks (StreamingLLM)** | Cache recent K/V + a few initial "sink" tokens | Anything outside the window — enables *infinite streaming*, NOT a larger *effective* context [Claim 7] |
| **Sparse / hierarchical attention** | Attend to a subset / pooled summaries | Resolution on the dropped pairs |

This is the **genuine no-free-lunch and it IS fundamental**: a model with a **fixed-size state** (any RNN/SSM/linear-attention) cannot losslessly answer arbitrary recall queries over unbounded history — there is not enough state to store it. Transformers escape this by keeping *all* KV (the cache *is* unbounded lossless memory), which is exactly why they cost O(n²). So: **cheap long context and lossless arbitrary recall are in fundamental tension.** You pick. The current frontier mostly keeps full attention (pays the cost) and attacks the cost with kernels/hardware, not by going lossy — because the lossy methods bleed on exactly the recall-heavy tasks people want long context for [Claim 6, Claim 11 — Magic's own argument].

> Key subtlety [Claim 7]: "infinite-length streaming" (StreamingLLM) is routinely mis-sold as "infinite context." It is not. It keeps generating fluently forever by *forgetting* the middle. The effective context is still the window. Don't confuse "doesn't crash at length" with "uses length."

### Phenomenon 2 — Softmax dilution (fundamental form, engineerable)

Softmax over n logits is a normalized competition. As n→∞, the **maximum attainable attention weight → 0** unless logits grow — so the distribution flattens and the model can't sharply prioritize the one key token among millions [Claim 2]. This is a real mathematical property, not a bug, and it's the rigorous version of your "isn't attention finite?" intuition. It's also *partly* the mechanism behind context-rot's attention-dilution attribution [Claim 12].

**But it's fixable.** Nakanishi's **Scalable-Softmax (SSMax)** rescales logits by a factor proportional to **log n** (the context length) so the sharpest-attention capability is preserved as the window grows. It's a drop-in replacement, improves long-context retrieval and length-generalization, and can even be retrofitted partway into pretraining [Claim 3]. So this phenomenon is **fundamental in the vanilla architecture but engineered away** — it belongs in the "contingent" bucket the moment you adopt the fix.

### Phenomenon 3 — Reasoning-capacity decay (the real floor)

This is the one you can't innovate out of within the fixed-model paradigm. **Du et al. (EMNLP 2025)** is the cleanest demonstration: they hand the model **perfect retrieval** — the relevant tokens are guaranteed present and identified — and even **force attention onto only those tokens**, replacing all irrelevant content with whitespace. Performance *still* degrades **13.9%–85%** as the raw input length grows [Claim 4, Claim 5]. Retrieval is not the bottleneck; **processing capacity** is.

The mechanism: a transformer has a **fixed width** (residual stream dimension), a **fixed number of heads**, and **fixed depth**. That is finite capacity to integrate and reason over information, regardless of how much you cram in or how well you point at it. PAPerBench attributes its length-decay to exactly this — **attention dilution in fixed-capacity transformers** [Claim 12]. This is the information-bottleneck argument, and it is **fundamental**: you beat it only by (a) growing the model, (b) spending more test-time compute per token, or (c) **not putting everything in the window** (offload to external state).

The lone cheap mitigation — **recitation** (prompt the model to re-state the retrieved evidence before answering) — buys only **+4% on RULER** [Claim 5]. A patch, not a cure. (Worth noting: it's already in our `context-rot-evidence.md` as a free technique for skills.)

---

## Fundamental vs contingent — the verdict table

| Source of degradation | Verdict | Why | Escape |
|---|---|---|---|
| O(n²) compute / O(n) KV | **Engineering** | Hardware + kernels (FlashAttention) + lossy alternatives | Sub-quadratic, *but* see tradeoff below |
| Lossless recall vs cheap cost | **Fundamental tradeoff** | Fixed-state models can't store unbounded history [Claim 6] | Pick one; or hybrid (some full-attention layers) |
| Softmax dilution | **Fundamental form, fixed** | max-softmax→0 is math [Claim 2]; SSMax restores it [Claim 3] | Adopt SSMax / logit scaling |
| Lost-in-the-middle / positional bias | **Contingent** | Position-encoding + training artifact | RoPE → YaRN → NoPE; better long-context curricula |
| Distractors worse than filler / context-rot | **Mostly contingent** | Training/eval artifact; shuffled haystacks *improve* scores | Better long-context training data + reranking |
| Long-context training-data scarcity | **Contingent** | Models see far fewer 100K-token examples than 4K | Synthetic long-context data, curriculum |
| KV-cache cost/loss | **Contingent** | Being made lossless+cheap (VeriCache 4×) [Claim 13] | Speculative-KV verification |
| Reasoning-capacity decay at length | **FUNDAMENTAL FLOOR** | Fixed width = finite capacity; degrades with perfect retrieval [Claim 4] | Bigger model, more test-time compute, or external memory |

**The clean split:** everything *positional and retrieval-shaped* is being innovated away (and the curve is measurably flattening — Opus 4.6 went 18.5%→76% on 8-needle @1M [Claim 9]). The two things that **stay**: (1) the **cost-vs-lossless-recall tradeoff**, and (2) the **fixed-capacity reasoning floor**.

---

## The "100M context" reality check

- **Magic's LTM-2** literally claims 100M-token context [Claim 11]. Notably, *Magic itself* says needle-in-haystack is a cheat eval — a semantically-odd needle in a whale novel is trivially findable and "reduces the required storage capacity to less than a real task," which is also why RAG looks deceptively good. They built a harder eval (HashHop) precisely because the easy one hides the floor. That's a vendor *admitting* the capacity≠utility gap.
- **MECW** [Claim 8]: across frontier models, advertised window ≫ effective window — severe degradation far below the max, sometimes within ~1K tokens on hard tasks. "1M" / "100M" is a capacity spec, not a utility guarantee.
- **Vendor spread** [Claim 10]: at 1M, Gemini 3 Pro drops to 26% (a 50-point cliff) while Opus 4.7 / Gemini 3.1 Pro hold >80% multi-hop at 512K. "1M context" means radically different things per model. Single-needle @1M is essentially solved; **multi-hop is the differentiator**.

**So is 100M feasible?** As an *engineering capacity number* — yes, you can build a model whose window holds 100M tokens (sub-quadratic + enough hardware). As a *uniformly-usable reasoning surface* — no, the fixed-capacity floor [Phenomenon 3] guarantees decay, and the cost of dense all-pairs over 100M is absurd when ~all of it is irrelevant to any query.

**Which is why the real frontier is hierarchical memory + retrieval, not dense attention.** Attending to everything equally is the *wrong objective*; relevance routing is the point. Mem0-class systems hit 93.4% on LongMemEval at **<7K tokens/retrieval** (local memo) — i.e., a good memory tier beats stuffing the window, at a fraction of the cost. The endgame architecture looks like: cheap long *capacity* (streaming / SSM layers / big KV) for the substrate, full attention reserved for a *retrieved working set*, and an external memory hierarchy doing the routing.

---

## Disconfirmation / what could flip this

- **Could the "fundamental floor" be just more bad training data?** Du et al. is the firewall: perfect retrieval + forced attention + whitespace-padding still degrades. If a future result shows a fixed-width model holding flat accuracy to arbitrary length with controlled retrieval, the floor claim weakens. Not seen as of 2026-06.
- **Could SSMs close the recall gap?** "Transformers are not SSMs" [Claim 6] shows learning-rate sensitivity confounds some prior SSM-vs-transformer comparisons, so *measured* SSM recall may be understated. But the *fixed-state* argument is structural, not empirical — a hybrid (a few full-attention layers in an SSM stack, e.g. Jamba-style) is the actual production answer, conceding the point.
- **Vendor benchmarks are self-reported.** Claim 9's Opus numbers are vendor MRCR; the independent multi-hop paper (2605.02173) corroborates the *direction* but on a single language/task. Treat "curve flattening" as strong signal, not closed.
- **Recency:** post-cutoff primaries (2602.15028, 2605.02173, 2605.17613) are carried from project ground-truth memos, not re-fetched here; the architecture primaries (2501.19399, 2508.19029, 2309.17453) are independently retrieved this session.

---

## Sources & search log

**Retrieved this session (Exa, research-paper category):**
- arXiv:2501.19399 — Nakanishi, *Scalable-Softmax Is Superior for Attention* (softmax dilution + log-n logit scaling fix)
- arXiv:2508.19029 — Okpekpe & Orvieto, *When recalling in-context, Transformers are not SSMs* (SSM associative-recall weakness)
- arXiv:2309.17453 — Xiao et al., *Efficient Streaming Language Models with Attention Sinks* (StreamingLLM) [ICLR 2024]
- magic.dev/blog/100m-token-context-windows (2024-08) — LTM-2 100M claim + needle-eval critique

**Carried from local ground-truth memos (`context-rot-evidence.md`, `2026-05-27-long-context-memory-4w.md`):**
- arXiv:2510.05381 — Du et al., *Context Length Alone Hurts* (EMNLP 2025) — the fixed-capacity floor
- arXiv:2509.21361 — Paulsen, *MECW* — advertised ≫ effective window
- arXiv:2602.15028 — PAPerBench — attention-dilution-in-fixed-capacity attribution
- arXiv:2605.02173 — 1M multi-hop reasoning eval — curve-flattening + vendor spread
- arXiv:2605.17613 — VeriCache — lossless KV cache
- Liu et al. 2024 (TACL) — Lost-in-the-Middle; Chroma Research 2026 — context rot across 18 models

**Search axes used:** (mechanism) softmax dilution + scaling fix; (architecture/adjacent) SSM vs transformer recall tradeoff; (practitioner/vendor) 100M-token feasibility claims; (mechanism) streaming/sink attention. Local ground truth supplied the quality-degradation and benchmark axes — not re-searched (diminishing returns).
