# Epistemic Quality Evaluation for LLM Agent Systems

*Date: 2026-03-02. Models in scope: Opus 4.6, Gemini 3.1 Pro, GPT-5.2. CLI agent (Claude Code) context.*
*Part of the [agentic research synthesis](agentic-research-synthesis.md).*

---

## What's PROVEN

### 1. Existing Benchmarks for Epistemic Quality

**SeekBench (Shao et al., ICLR 2026, arXiv:2509.22391)** — First process-level benchmark specifically for agent epistemic competence. 190 expert-annotated traces, 1,800+ steps. Three dimensions:

- **Groundedness**: does the agent's reasoning cite the actual retrieved evidence vs. generate independent of it?
- **Recovery**: does the agent reformulate searches when results are low-quality?
- **Calibration**: does the agent correctly assess when evidence is sufficient to answer?

LLM-as-judge pipeline included. Applied to RL-trained search agents; found critical gaps between final answer accuracy and underlying epistemic quality. Most systems look good on accuracy, fail on process. [SOURCE: arXiv:2509.22391] [PUBLISHED ICLR 2026]

**FActScore (Min et al., EMNLP 2023, arXiv:2305.14251, 1,091 citations)** — Decomposes text into atomic facts, checks each against a knowledge source (Wikipedia by default). Metric = % atomic facts supported. Key findings:
- ChatGPT scores **58%** on biography generation (42% of atomic claims unsupported)
- Automated version vs. human: <2% error rate
- Open source, pip-installable
- Limitation: knowledge source must be pre-specified; doesn't handle arbitrary factual domains

[SOURCE: arXiv:2305.14251] [PUBLISHED EMNLP 2023]

**SAFE + LongFact (Wei et al., NeurIPS 2024, arXiv:2403.18802, 122 citations)** — Google DeepMind. Extends FActScore to arbitrary domains using Google Search as the knowledge source. Pipeline:
1. Decompose response into individual facts
2. For each fact, generate search queries → issue to Google Search
3. Reason over search results: supported / not supported / irrelevant
4. Aggregate using F1@K (factual precision × recall relative to preferred response length)

Key numbers:
- Agrees with crowd-sourced human annotators **72%** of the time
- Wins **76%** of disagreements (i.e., SAFE is more accurate than humans)
- Costs **$0.19/response** vs $4.00/response for humans — **20x cheaper**
- 16,000 facts verified across 13 models
- Open source: github.com/google-deepmind/long-form-factuality

[SOURCE: arXiv:2403.18802] [PUBLISHED NeurIPS 2024]

**VeriScore (Song et al., 2024, arXiv:2406.19276, 79 citations)** — Addresses FActScore/SAFE limitation: both assume every claim is verifiable. VeriScore handles mixed verifiable/unverifiable content, making it better for multi-turn dialogue, opinions, and creative outputs. Human evaluation confirms its extracted claims are "more sensible than competing methods across eight different long-form tasks." [SOURCE: arXiv:2406.19276] [PREPRINT]

**Calibration benchmarking (arXiv:2602.00279, 2025)** — 20 LLMs on 7 scientific QA datasets. Key findings:
- **Answer frequency (consistency across multiple samples) yields the most reliable calibration signal** — not verbalized confidence, not token probabilities
- Verbalized approaches ("I'm 80% confident") are **systematically biased and poorly correlated with correctness**
- Instruction tuning causes **probability mass polarization** — token-level confidence scores become unreliable
- Standard ECE (Expected Calibration Error) is insufficient as the sole calibration metric; use AUROC + AUPRC + Brier Score together
- RLHF/instruction tuning models should be calibrated by sampling, not by reading logprobs

[SOURCE: arXiv:2602.00279] [PREPRINT — 2025, multiple models]

**CoT faithfulness baseline (ICLR 2026 submission, existing corpus)** — 7-13% of reasoning traces are unfaithful on CLEAN, non-adversarial prompts. GPT-4o-mini: 13%, Haiku 3.5: 7%. The reasoning trace is not a reliable window into the model's actual decision process. [SOURCE: OpenReview ICLR 2026] [EXISTING CORPUS]

**Sycophancy under rebuttal (Kim et al., EMNLP 2025 Findings, arXiv:2509.16533)** — LLMs deployed as evaluators are more likely to endorse a user's counterargument when:
- Framed as conversational follow-up (vs. simultaneous presentation)
- The user provides detailed (even incorrect) reasoning
- The user uses casual phrasing (even without justification)

Implication for agents: when an agent serves as evaluator in multi-turn or review loops, its judgments are epistemically unstable under pressure. This is a measurement problem — the eval signal degrades when the agent being evaluated can influence the evaluator. [SOURCE: arXiv:2509.16533] [PUBLISHED EMNLP 2025 Findings]

---

### 2. Lightweight Eval Approaches

**SAFE-style pipeline (practical version)**

Can be implemented without Google Search API (use Exa or your existing search MCPs):
1. Sample N outputs from the agent (N=3-5 sufficient; more for high-stakes)
2. Decompose each output into atomic claims using Claude
3. For each claim, query Exa to find corroborating/contradicting sources
4. Score: supported / contradicted / unverifiable
5. Aggregate: factual precision rate over verifiable claims

Cost at Exa's rates: ~$0.05-0.10/response at 5 claims/response. Runnable as a periodic sample (not every output).

**Sampling-based calibration check**

For any claim the agent made confidently:
1. Run the same query N=10 times with temperature > 0
2. Measure consistency (fraction agreeing on the same answer)
3. Compare consistency rate to correctness rate on a held-out ground-truth set
4. If consistency != accuracy (e.g., 90% consistent but 60% accurate), the agent is overconfident

This doesn't require ground truth for production monitoring — consistency is the proxy.

**Cross-model verification as eval signal**

Key constraint from Debate-or-Vote (arXiv:2508.17536, ACL 2025): multi-agent debate is a martingale — debate doesn't improve expected correctness, voting does. But cross-model disagreement IS a useful signal for identifying uncertain claims. Pattern:
- Run same agent task with Claude and Gemini independently
- Where they agree: higher confidence (but not guaranteed correct)
- Where they disagree: flag for human review or deeper sourcing
- This is adversarial pressure, not voting — the goal is finding the failure mode, not majority truth

**Hook-based epistemic monitoring (applicable to this system)**

The researcher skill already has a PostToolUse prompt hook for source citations. This is the architectural pattern. Extensions:
- PostToolUse hook on research output writes: count citations, flag paragraphs without provenance tags
- Stop hook on research sessions: verify claim-to-source ratio meets threshold before allowing completion
- Periodic FActScore sample: cron job that takes 10 random research outputs from the last month, runs SAFE-lite on them, logs precision rate to a metrics file

---

### 3. Agentic-Specific Causes of Bad Epistemics

**Context length degrades reasoning quality, not just retrieval**

The key result (Du et al., EMNLP 2025, arXiv:2510.05381, existing corpus): even when models PERFECTLY retrieve relevant information, performance degrades 13.9–85% as input length increases. The problem is not "lost in the middle" (retrieval failure) — it's processing capacity. Longer context = worse reasoning over that context.

Implication: agents that accumulate tool outputs in a growing context window are not just subject to retrieval degradation — their reasoning quality drops even when the relevant information is right there. This is architectural. The "recitation strategy" (+4% accuracy: prompt model to restate evidence before reasoning) helps but doesn't eliminate the issue.

Topically-related distractors (relevant-but-wrong content) cause worst hallucination amplification. [SOURCE: Chroma Research 2026, arXiv:2510.05381]

**Error propagation across agent steps**

Multi-step agents compound errors. A small misread of retrieved content in step 3 can propagate through steps 4-10 uncorrected. SWE-EVO found a 3x drop in performance (65% → 21%) going from single-issue to long-horizon tasks. FeatureBench found 11% vs 74% on SWE-bench. The bottleneck is sequential error accumulation, not any single step failure. [SOURCE: arXiv:2512.18470, arXiv:2602.10975]

**Instruction-following pressure distorts epistemic output**

RLHF/instruction tuning optimizes for user approval. This creates a structural tension:
- Calibration gets worse (probability mass polarization; verbalized confidence unreliable)
- Sycophancy gets worse (model yields to user pressure in multi-turn)
- Source attribution gets weaker (users reward fluent confident answers, not hedged sourced ones)

The calibration paper (arXiv:2602.00279) confirms this: "instruction tuning causes strong probability mass polarization, reducing the reliability of token-level confidences." The sycophancy paper (arXiv:2509.16533) confirms the multi-turn version: evaluators flip under casual pressure.

This is the instruction-following vs. epistemic quality tradeoff: models trained to be helpful are biased toward giving answers rather than "I don't know" or "insufficient evidence."

**Tool use: reduces and amplifies hallucination depending on quality**

RAG reduces hallucination vs. closed-book generation (1.35x OR improvement in biomedical meta-analysis, W4406421570). SAFE itself is an example — a tool-using agent is more accurate than humans at fact-checking.

But: RETRIEVAL QUALITY is the constraint. Poor retrieval (wrong documents, topically-related but incorrect content) AMPLIFIES hallucination by providing authoritative-looking but wrong context. The agent grounds its claims on bad sources and gains false confidence.

Agentic hallucination taxonomy (arXiv:2510.24476): knowledge-based errors (wrong facts retrieved or remembered) + logic-based errors (correct facts, wrong inference) compound in multi-step systems. These interact: logic errors on bad retrieved facts are doubly undetectable.

**Multi-turn reliability degradation**

Princeton reliability study (arXiv:2602.16666, existing corpus): r=0.02 correlation between capability improvements and reliability improvements over 18 months. Outcome consistency universally low. CLEAR framework shows 60% pass@1 drops to 25% over 8 consecutive runs.

Agents in production loops accumulate variance: small inconsistencies in earlier turns create divergent states in later turns, and the variance compounds.

---

## What's UNCERTAIN

**Process-level benchmarks for code agents**: SeekBench applies to search/QA agents. No direct equivalent for code/task agents measuring the epistemic quality of plans, assumptions, and uncertainty expressions during multi-step execution.

**Ground truth for agentic research tasks**: SAFE works when Google Search can verify claims. For investment research, competitive intelligence, or domain-specific analysis, ground truth for verification is sparse or contested. FActScore-style pipelines become unreliable when the topic is not well-indexed.

**Whether calibration by sampling works in production**: The sampling-based calibration approach requires N independent runs of the same task. For tasks with external effects (web browsing, API calls), this may be impractical. **UPDATE (2026-03-02):** Deep dive completed. Sample Consistency plateaus at 15 samples (Manakul/SelfCheckGPT). N=10 on 20 canary queries (~200 observations) has ~80% power to detect 10pp miscalibration. Monthly cadence feasible at ~$100/month. Full analysis: [calibration-measurement-practical.md](calibration-measurement-practical.md).

**Adversarial robustness of cross-model review**: The Debate-or-Vote finding (debate is a martingale) was on reasoning tasks. It's unclear whether it generalizes to factual disagreements between models that have different training data and knowledge cutoffs. **UPDATE (2026-03-02):** ChainPoll achieves 0.781 AUROC for hallucination detection via multi-call voting. Cross-model agreement is a decent but imperfect proxy. P(correct | models agree) has NOT been measured cross-model specifically. See [calibration-measurement-practical.md](calibration-measurement-practical.md).

---

## Disconfirmation

- Tool use does NOT uniformly increase hallucination. RAG reduces hallucination 1.35x on average in biomedical systems. The failure mode is bad retrieval, not retrieval per se.
- Sampling-based calibration DOES work. Answer consistency is the most reliable calibration signal available, even if imperfect. It's not hopeless.
- Cross-model disagreement IS a useful signal for uncertainty even though debate doesn't improve correctness. The goal is identification of uncertain claims (adversarial), not consensus truth (voting).

---

## Sources Saved to Corpus

| Paper | S2 ID | Status |
|-------|-------|--------|
| SeekBench (Shao et al., ICLR 2026) | f1b661db4328037cdab4e0d2fb2605a6452d72d1 | Saved |
| FActScore (Min et al., EMNLP 2023) | bd5deadc58ee45b5e004378ba1d54a96bc947b4a | Saved |
| SAFE + LongFact (Wei et al., NeurIPS 2024) | 58e194695187fe4daeb04ea694e0f59af2441177 | Saved |
| VeriScore (Song et al., 2024) | 32d8df3dddfeb5d04326a17c0d506b1304aa8dc1 | Saved |
| Sycophancy under rebuttal (EMNLP 2025) | — | Not in S2; arXiv:2509.16533 |
| Calibration benchmark (2025) | — | Not in S2; arXiv:2602.00279 |

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | ChatGPT has 58% factual precision on biography generation (42% claims unsupported) | FActScore benchmark, 2023 | HIGH (1,091 citations) | arXiv:2305.14251 | VERIFIED |
| 2 | SAFE costs $0.19/response vs $4.00 human; wins 76% of disagreements | Direct measurement, NeurIPS 2024 | HIGH (122 citations) | arXiv:2403.18802 | VERIFIED |
| 3 | Answer frequency (sampling consistency) is the most reliable calibration proxy | 20 models, 7 datasets | MEDIUM (preprint) | arXiv:2602.00279 | PREPRINT |
| 4 | Verbalized confidence claims are systematically biased and poorly correlated with correctness | Same dataset | MEDIUM | arXiv:2602.00279 | PREPRINT |
| 5 | Instruction tuning causes probability mass polarization; token-level confidence unreliable | Same dataset | MEDIUM | arXiv:2602.00279 | PREPRINT |
| 6 | 7-13% CoT reasoning traces unfaithful on clean non-adversarial prompts | ICLR 2026 submission | MEDIUM | ICLR 2026, existing corpus | VERIFIED |
| 7 | LLM evaluators flip judgments under casual user rebuttal with incorrect reasoning | EMNLP 2025 Findings | MEDIUM | arXiv:2509.16533 | VERIFIED |
| 8 | Context length degrades reasoning quality even when retrieval is perfect (13.9-85%) | EMNLP 2025, arXiv:2510.05381 | HIGH | Existing corpus | VERIFIED |
| 9 | Topically-related distractors cause worst hallucination amplification | Chroma 2026, 18 models | HIGH | research.trychroma.com | VERIFIED |
| 10 | 60% pass@1 drops to 25% over 8 consecutive agent runs | CLEAR framework | MEDIUM | arXiv:2511.14136, existing corpus | VERIFIED |
| 11 | RAG improves factuality 1.35x OR in biomedical meta-analysis | Systematic review, JAMIA 2025 | MEDIUM | W4406421570 | VERIFIED |
| 12 | SeekBench is the first process-level benchmark for agent epistemic competence | ICLR 2026 | MEDIUM | arXiv:2509.22391 | VERIFIED — paper claims "first" but not independently confirmed |
| 13 | INTRA: internal representations (esp. middle layers) outperform logit-based approaches for fact-checking without retrieval | 9 datasets, 18 methods, 3 models | MEDIUM | arXiv:2603.05471 | PREPRINT — March 2026. Requires model internals, not usable via API |
| 14 | Epistemic AI agents need 3 properties: demonstrable competence, falsifiability, epistemically virtuous behavior | Normative framework (Google DeepMind) | MEDIUM | arXiv:2603.02960 | PREPRINT — normative, not empirical. Framework aligns with our constitution |
| 15 | Performative CoT is difficulty-dependent: 80% tokens theater on easy tasks, genuine on hard | Attention probes on DeepSeek-R1 671B, GPT-OSS 120B | HIGH | arXiv:2603.05488 | PREPRINT — see cot-faithfulness-evidence.md |
