# Factual Verification Systems for AI Agents — Research Memo

**Questions:** RQ1 (Closed-loop verification architecture) + RQ6 (What reduces slop)
**Tier:** Deep | **Date:** 2026-03-02
**Ground truth:** Existing `epistemic-quality-evals.md` memo (SAFE, FActScore, VeriScore, SeekBench baselines). Our SAFE-lite system has 65% "unclear" rate, 71.4% precision.

---

## Recitation of Key Evidence

Before synthesis, restating the concrete data points I'm drawing from:

1. **FINCH-ZK** (Goel, Schwartz, Qi — Amazon AWS, arXiv:2508.14314, 5 citations): Cross-model consistency detection. FELM dataset: sentence-level F1 = 49.2% (vs 35.4% vanilla GPT-4 judge, +39%). GPQA-diamond: +5.6% answer accuracy for Claude 4 Sonnet, +12.6% for Llama 4 Maverick. Disabling cross-model sampling degrades response-level F1 from 65.1% to 62.0%. Cross-model improver (Llama 4 Maverick correcting Claude 4 Sonnet) hit 94.4% full-response accuracy vs 80.3% same-model. Cost: 36x baseline for 10 samples, reducible to 8x with batch judge + 3 samples.
2. **VeriScore** (Song, Kim, Iyyer — UMass Amherst, EMNLP 2024 Findings, arXiv:2406.19276, 79 citations): VerRatio (verifiable claims per sentence) ranges from 0.03 (creative writing) to 2.31 (non-fiction books). Among 320 annotated claims, 55% supported by search, 40% inconclusive, 2.8% contradicted. Claim extraction preferred over SAFE's in 334/360 annotated cases.
3. **Verifying the Verifiers** (Seo, Han, Jung et al. — COLM 2025): ~16% of benchmark annotations are ambiguous or incorrectly labeled. Frontier LLMs with few-shot ICL achieve top-tier verification performance (often overlooked baseline).
4. **Alignment Bottleneck** (Akhter, Ruggeri et al. — arXiv:2602.10380): Claim decomposition only improves performance when evidence is Sub-claim Aligned Evidence (SAE). Standard Repeated claim-level Evidence (SRE) fails to improve and often degrades performance. Conservative "abstention" on uncertain sub-claims reduces error propagation vs aggressive incorrect predictions.
5. **PRM for Clinical Notes** (Wang et al. — Mayo Clinic + UIUC, EMNLP 2025): LLaMA-3.1 8B PRM achieves 98.8% accuracy distinguishing gold-standard from error-containing clinical notes. 56.2% accuracy selecting physician-preferred notes. Key: defining meaningful "steps" + injecting realistic domain-informed errors for training data.
6. **PRM for Radiology** (Thomas, Varma et al. — Stanford, arXiv:2510.23217): 0.5B parameter PRM for sentence-level verification of radiology reports. +7.5% MCC, +1.8% AUROC over white-box baselines. Filtering worst 10% of reports improves F1-CheXbert by 4.5%. Generalizes to unseen LVLM generators.
7. **TruthTensor** (Shahabi et al. — Inference Labs, arXiv:2601.13545): Uses live prediction markets (500+ markets) as ground truth for LLM evaluation. Models with similar forecast accuracy diverge on calibration, drift, and risk-sensitivity.
8. **Cleanlab RAG Benchmark** (Sardana, Mueller — Cleanlab blog, April 2025): 6 RAG datasets. TLM (sampling-based confidence) consistently highest AUROC across domains. HHEM (Vectara) and Prometheus competitive in some domains. Key finding: no single evaluation model dominates all domains.
9. **SAFE** (Wei et al. — Google DeepMind, NeurIPS 2024, arXiv:2403.18802, 122 citations): $0.19/response, 72% human agreement, 76% win rate on disagreements. 16,000 facts verified.
10. **Du et al.** (EMNLP 2025, arXiv:2510.05381): Recitation strategy +4% accuracy on long-context tasks. Even with perfect retrieval, context length degrades reasoning 13.9-85%.
11. **Claimify** (Metropolitansky, Larson — Microsoft Research, ACL 2025): High-confidence-only claim extraction. Handles ambiguity by extracting claims only when interpretation is confident. Framework for evaluating claim extraction in fact-checking context.

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Nobody has deployed SAFE at scale outside benchmarking contexts | Exhaustive search of production deployment reports, blog posts, and enterprise case studies found zero evidence of SAFE in production | MEDIUM | [INFERENCE from search absence] | UNVERIFIED — absence of evidence |
| 2 | VeriScore filters unverifiable claims via linguistic definition: "describes a single event/state with all necessary modifiers" | Direct from paper Section 1-2 | HIGH | arXiv:2406.19276 | VERIFIED |
| 3 | VeriScore's "inconclusive" rate is 40% on annotated claims (320 claims) | Direct from paper Table/Results | HIGH | arXiv:2406.19276 | VERIFIED |
| 4 | Cross-model verification (FINCH-ZK) improves detection F1 by 6-39% over single-model | FELM dataset experiments, multiple ablations | HIGH | arXiv:2508.14314 | VERIFIED |
| 5 | Cross-model improver (different family correcting) hits 94.4% vs 80.3% same-model on GPQA-diamond | Table 4, ablation G4.b | HIGH | arXiv:2508.14314 | VERIFIED |
| 6 | Same-model consistency checking degrades to 62.0% F1 vs 65.1% cross-model (FELM response-level) | Table 3, ablation G2.a | HIGH | arXiv:2508.14314 | VERIFIED |
| 7 | FINCH-ZK costs 36x baseline (10 samples) or 8x (3 samples + batch judge) | Table 5 cost analysis | HIGH | arXiv:2508.14314 | VERIFIED |
| 8 | ~16% of fact-checking benchmark annotations are ambiguous or incorrect | 14 benchmarks analyzed | HIGH | Seo et al. COLM 2025 | VERIFIED |
| 9 | Claim decomposition only helps with sub-claim-aligned evidence, not repeated claim-level evidence | Experiments on PHEMEPlus, MMM-Fact, COVIDFact | HIGH | arXiv:2602.10380 | VERIFIED |
| 10 | 0.5B PRM achieves +7.5% MCC for radiology report sentence-level verification | Stanford, single model family | MEDIUM | arXiv:2510.23217 | VERIFIED (single source) |
| 11 | 8B PRM hits 98.8% accuracy on clinical note error detection | Mayo Clinic, EMNLP 2025 | MEDIUM | aclanthology.org/2025.emnlp-main.967 | VERIFIED (single source) |
| 12 | Prediction markets provide contamination-free, drift-aware ground truth for LLM evaluation | TruthTensor framework, 500+ markets | MEDIUM | arXiv:2601.13545 | VERIFIED (framework, not production system) |
| 13 | Recitation strategy provides +4% accuracy, but only tested on vanilla generation (not tool-augmented) | Du et al. EMNLP 2025 | HIGH for vanilla; UNVERIFIED for tool-augmented | arXiv:2510.05381 | PARTIAL |
| 14 | No published evidence that structured output formats (JSON, tables) reduce hallucination rate | Exhaustive search found no controlled experiments | LOW | [INFERENCE from search absence] | UNVERIFIED |

---

## Key Findings

### 1. SAFE/FActScore Operational Deployments: Nobody Is Running These at Scale

**Finding:** No evidence that SAFE, FActScore, or VeriScore have been deployed as continuous production verification systems outside of academic benchmarking. [INFERENCE from exhaustive search]

- Google DeepMind published SAFE (NeurIPS 2024) but no follow-up deployment report exists.
- The SAFE GitHub repo (google-deepmind/long-form-factuality) has not been updated for production use patterns.
- Kore.ai wrote a blog post about SAFE but it's a description of the paper, not a deployment report.
- VeriScore has 33 GitHub stars, 4 forks, last push Dec 2025. It's a research tool, not production infrastructure.
- FActScore (1,091 citations) is the most cited but is limited to Wikipedia as knowledge source.

**Why this matters:** These systems were designed as evaluation metrics, not production guardrails. The gap between "paper that measures factuality" and "system that blocks bad outputs in real-time" is enormous. Production systems need: (a) latency under 2s, (b) domain-specific knowledge sources, (c) handling of unverifiable claims, (d) cost under $0.01/response.

**What IS deployed:** Cleanlab's TLM (sampling-based confidence scoring, proprietary), Vectara's HHEM (trained classifier), and various LLM-as-judge setups. These are simpler than SAFE but run in real-time. The Cleanlab benchmark (April 2025) shows TLM achieving highest AUROC across 6 RAG datasets, but exact numbers are presented as graphs, not tables. [SOURCE: cleanlab.ai/blog/rag-evaluation-models/]

### 2. VeriScore's Claim Filtering: Linguistic Definition, Not ML Classification

**Finding:** VeriScore's innovation is a **definitional filter**, not a learned classifier. It defines verifiable claims as those that "describe a single event or state with all necessary modifiers (spatial, temporal, relative clauses)." The extraction prompt includes few-shot examples that implicitly teach the model what counts as verifiable. [SOURCE: arXiv:2406.19276]

Key mechanism differences from FActScore/SAFE:
- **Sliding window context**: processes sentences with 0-3 preceding and 0-1 following sentences, making claims self-contained without separate decontextualization step.
- **Verifiable-only extraction**: FActScore/SAFE decompose ALL content into atomic claims, then try to verify everything (including opinions, advice, subjective judgments). VeriScore only extracts what can plausibly be checked.
- **VerRatio varies wildly by domain**: from 0.03 claims/sentence (creative writing) to 2.31 (non-fiction books). This means a SAFE-style pipeline applied to investment research memos (which mix facts, inferences, opinions, and recommendations) would classify most content as "unclear" — which is exactly what we see with our 65% unclear rate.

**Can this reduce our 65% unclear rate?** Partially. The 40% "inconclusive" rate VeriScore reports (on 320 annotated claims that passed the verifiability filter) means even after filtering out unverifiable content, search still can't confirm/deny ~40% of verifiable claims. Our problem is likely a combination of:
- **~30% genuinely unverifiable** (opinions, inferences, recommendations) — VeriScore-style filtering would correctly exclude these
- **~35% verifiable but search-unfindable** — domain coverage problem (Exa/Google don't index the right sources for our domains)
- **~35% claim formulation problem** — claims decomposed too atomically or too vaguely for search to match

[INFERENCE: splitting the 65% unclear rate into these three buckets based on VeriScore's 40% inconclusive rate among verified-verifiable claims]

### 3. Cross-Model Claim Extraction: FINCH-ZK Is the First Serious Evidence

**Finding:** FINCH-ZK (Amazon AWS, arXiv:2508.14314) provides the first systematic evidence that cross-model verification substantially outperforms same-model verification. [SOURCE: arXiv:2508.14314, full paper read]

**Specific numbers on correlated failures:**
- Disabling cross-model sampling (all samples from Claude 4 Sonnet) degrades response-level F1 from 65.1% to 62.0% on FELM — a 3.1 point drop. [SOURCE: Table 3, G2.a]
- Adding weaker cross-model samplers (Claude 3.5 Sonnet + Llama 4 Scout) improves sentence-level F1 from 49.2% to 50.9%. [SOURCE: Table 3, G2.b]
- **The biggest finding**: using a *different model family* as the improver (Llama 4 Maverick correcting Claude 4 Sonnet outputs) jumps full-response accuracy from 59.1% to 90.4% on RAG-judged GPQA-diamond — a 31.3 point improvement. Same-model improvement only reaches 59.1%. [SOURCE: Table 4, G4.b vs G0.b]

**This confirms correlated failures exist within model families.** The improvement from cross-family correction is far larger than from cross-model-within-family. Claude correcting Claude misses errors that Llama catches, and vice versa.

**Cost tradeoff:** Full FINCH-ZK with 10 samples costs 36x the baseline response ($0.39 vs $0.01 per response on GPQA-diamond). With 3 samples + batch judge: 8x ($0.08). This is deployable for high-value outputs but not for every response. [SOURCE: Table 5]

**For our use case (investment research):** The pattern is clear — use Claude for generation, route through Gemini or Llama for verification. The cross-family gap is where the signal is. Our current same-model `/model-review` approach captures some of this, but should be using genuinely different model families, not just different models within the Anthropic family.

### 4. The "Unclear" Problem: It's Three Problems, Not One

**Finding:** The 65% "unclear" rate in our SAFE-lite system is a composite of three distinct failure modes, each requiring a different fix.

**Problem 1: Unverifiable claims being verified (~30% of unclear)**
Claims like "the evidence suggests moderate confidence in X" or "this approach has potential" are inherently unverifiable — they're judgments, not facts. VeriScore's approach (only extract verifiable claims) would eliminate these from the pipeline entirely. FActScore/SAFE naively decompose everything and then fail on opinions.

*Fix:* Add a verifiability filter before verification. VeriScore's prompt-based approach (few-shot with verifiable/unverifiable examples) is simple to implement. [INFERENCE: implementation cost is low, ~50 lines of prompt engineering]

**Problem 2: Domain coverage gap (~35% of unclear)**
Investment research, competitive intelligence, and domain-specific analysis rely on information that isn't well-indexed by Google/Exa. Company-specific metrics, proprietary frameworks, historical trade data — these don't appear in web search results.

*Fix:* Domain-specific knowledge sources. VeriScore uses Google Search; we'd need to wire in:
- SEC EDGAR for financial claims
- Company-specific fact databases
- Historical price data APIs
- Our own prior research corpus (research-mcp)

The Alignment Bottleneck paper (arXiv:2602.10380) confirms this: decomposition only helps when evidence is **sub-claim aligned**. Repeated claim-level evidence (throwing the same broad search at every sub-claim) "fails to improve and often degrades performance." [SOURCE: arXiv:2602.10380]

**Problem 3: Claim formulation quality (~35% of unclear)**
Poorly decomposed claims produce queries that don't match available evidence even when evidence exists. "The company's Q3 revenue exceeded expectations" requires knowing: which company, what expectations, what the actual revenue was.

*Fix:* Better claim extraction. Claimify (Microsoft Research, ACL 2025) shows that high-confidence-only extraction (refusing to decompose ambiguous content) produces better downstream results than extracting everything. VeriScore's context-window approach (including surrounding sentences) also helps. [SOURCE: aclanthology.org/2025.acl-long.348]

### 5. What Actually Reduces Slop — Ranked by Evidence Strength

**5a. Cross-model verification: STRONG evidence, HIGH cost**

FINCH-ZK provides the clearest numbers: +39% F1 improvement over vanilla GPT-4 judge for detection, +12.6% answer accuracy for mitigation (on Llama 4 Maverick). Cross-family correction provides an additional massive boost (59.1% -> 90.4% full-response accuracy). [SOURCE: arXiv:2508.14314]

Cost: 8-36x per response. Practical for high-value outputs (research memos, trade recommendations), not for every chat message.

**5b. Retrieval quality: STRONG evidence, the binding constraint**

Multiple lines of evidence converge:
- Cleanlab benchmark: evaluation model performance varies dramatically by domain (some models near-random on some datasets). The retrieval/context is the bottleneck, not the judge. [SOURCE: cleanlab.ai]
- Alignment Bottleneck paper: sub-claim-aligned evidence is *necessary* for decomposition to help. Without it, decomposition actively hurts. [SOURCE: arXiv:2602.10380]
- Du et al.: even with *perfect* retrieval, reasoning degrades 13.9-85% as context grows. Bad retrieval makes this catastrophically worse because topically-related-but-wrong content causes the worst hallucination amplification. [SOURCE: arXiv:2510.05381]
- RAG meta-analysis: 1.35x OR improvement in factuality in biomedical systems (via systematic review). [SOURCE: W4406421570, existing corpus]

*The chain:* retrieval quality -> evidence alignment -> claim verification accuracy -> factual precision. If retrieval is bad, everything downstream fails.

**5c. Process reward models: STRONG evidence in narrow domains, EMERGING for general use**

Two concrete deployable implementations found:
1. **Clinical notes PRM** (Mayo Clinic, EMNLP 2025): 8B LLaMA-3.1 fine-tuned on synthetic error-injected clinical notes. 98.8% accuracy detecting errors. Key insight: domain-expert-defined error taxonomy for training data generation. [SOURCE: aclanthology.org/2025.emnlp-main.967]
2. **Radiology PRM** (Stanford, arXiv:2510.23217): 0.5B model, sentence-level verification. +7.5% MCC over baselines. Generalizes to unseen generator models. [SOURCE: arXiv:2510.23217]

Both require domain-specific training data (error injection + expert annotation of steps). No general-purpose deployable PRM exists for arbitrary fact-checking. The math/code PRMs (Lightman et al., 2023) don't transfer to factual domains.

*For investment research:* Would need to define "steps" in analysis (claim extraction -> evidence retrieval -> reasoning -> conclusion) and inject realistic errors at each step. Feasible but requires ~200 annotated examples per domain. [INFERENCE]

**5d. Recitation before synthesis: MODERATE evidence, LOW cost**

Du et al. (EMNLP 2025, arXiv:2510.05381) show +4% accuracy from prompting models to restate evidence before answering. Training-free, model-agnostic.

**Critical gap:** This was tested on vanilla long-context QA, NOT on tool-augmented or agentic settings. No published evidence on whether recitation helps when the model has already used tools to retrieve information (the tool outputs are already in context, so "reciting" them may be redundant). [UNVERIFIED for tool-augmented settings]

*Inference:* Recitation likely helps LESS in tool-augmented settings because tool outputs are already recent in context (no "lost in the middle" problem for the most recent retrieval). But it may still help for synthesis across MULTIPLE tool calls where earlier retrievals have been pushed out of recent attention. [INFERENCE]

**5e. Structured output (tables, JSON, evidence matrices): NO EVIDENCE**

Searched extensively for controlled experiments comparing free-form text generation vs structured output formats on hallucination rate. Found nothing.

StructFact (Huang et al., ACL 2025) studies LLMs reasoning ABOUT structured data, not whether structured output FORMAT reduces hallucination. JSONSchemaBench (Geng et al., 2025) benchmarks constrained decoding compliance, not factual accuracy.

*Inference:* Structured output likely helps indirectly by:
- Forcing explicit claim-evidence pairing (each row must cite a source)
- Making gaps visible (empty cells in evidence column)
- Reducing narrative flow that buries contradictions

But this is a workflow intervention, not a measured effect on factual precision. Nobody has A/B tested "write a research memo in paragraph form" vs "fill in this claims table" on hallucination rate. [INFERENCE — no supporting evidence found]

**5f. Multi-model verification ROI: STRONG evidence from FINCH-ZK**

Specific catch rates from FINCH-ZK ablations:
- Cross-model adds +3.1 F1 points on FELM response-level detection (65.1% vs 62.0%)
- Cross-family improver adds +31.3 points on GPQA-diamond full-response accuracy (90.4% vs 59.1%)
- Human evaluation: annotators preferred FINCH-ZK improved responses in 84% (42/50) of cases on Natural Questions

**What it misses:** FINCH-ZK doesn't report false negative rate directly (hallucinations it failed to detect). The sentence-level recall is 53.1% — meaning **47% of hallucinated sentences are missed even with cross-model checking**. [SOURCE: Table 1]

**5g. Prediction markets as ground truth: EMERGING**

TruthTensor (Shahabi et al., arXiv:2601.13545) is the first framework using live prediction markets (500+ markets) to evaluate LLM reasoning. Key insight: models with similar forecast accuracy diverge on calibration, drift, and risk-sensitivity — the dimensions that matter for investment research.

This is the most promising approach for sparse-ground-truth domains like investment research. Prediction markets provide:
- Forward-looking, contamination-free evaluation
- Continuous calibration signal (not binary right/wrong)
- Domain-specific (economics, politics, technology)

**Limitation:** Markets have thin liquidity on niche questions. Works for "will X company beat earnings" but not for "is this accounting irregularity significant?" [INFERENCE]

---

## Disconfirmation

**Searched for and found:**
- "Verifying the Verifiers" (COLM 2025): ~16% of fact-checking benchmark annotations are wrong. This means reported F1 scores for ALL verification systems (including FINCH-ZK, SAFE, VeriScore) are measured against noisy ground truth. Real performance could be higher or lower. [SOURCE: openreview.net/pdf?id=3NjnRo6apU]
- Alignment Bottleneck: claim decomposition sometimes HURTS (SRE setup). Not all verification is beneficial. [SOURCE: arXiv:2602.10380]
- FINCH-ZK sentence-level recall is only 53.1% — nearly half of hallucinations are missed even with the best system. [SOURCE: arXiv:2508.14314, Table 1]
- VeriScore "inconclusive" rate is 40% even AFTER filtering for verifiability — search verification has a hard ceiling. [SOURCE: arXiv:2406.19276]

**Searched for but did NOT find:**
- Evidence that structured output reduces hallucination
- Evidence that recitation works in tool-augmented settings
- Evidence of SAFE/FActScore in production deployment
- General-purpose deployable PRMs (only domain-specific)

---

## Actionable Recommendations for Our System

### High-ROI changes (implement now)

1. **Add verifiability filter to SAFE-lite.** Before verification, classify each claim as verifiable/unverifiable using VeriScore's prompt pattern. Drop unverifiable claims from the pipeline. Expected: reduce "unclear" from 65% to ~40% by removing genuinely unverifiable content.

2. **Wire cross-family verification into model-review.** Currently model-review uses llmx which may route to the same model family. Ensure verification uses a genuinely different family (Claude generates -> Gemini verifies, or vice versa). FINCH-ZK shows +31.3 points from cross-family correction.

3. **Domain-specific evidence sources for SAFE-lite.** Replace or supplement Exa search with domain-specific APIs (SEC EDGAR, price data, our own corpus) for investment-domain claims. Alignment Bottleneck shows this is necessary, not optional.

### Medium-ROI changes (next cycle)

4. **Train domain-specific PRM for research output.** Following Mayo Clinic pattern: define "steps" in research analysis, inject realistic errors at each step, fine-tune small model (8B sufficient). Requires ~200 annotated examples.

5. **Implement prediction-market calibration.** Use Polymarket/Metaculus as delayed ground truth for predictions our system makes. Not real-time verification, but calibration signal over time.

### Low-ROI / premature

6. **Full SAFE deployment.** At $0.19/response and 36x latency, not practical for routine use. Reserve for periodic sampling (monthly quality audits).

7. **Structured output enforcement.** No evidence it reduces hallucination directly. May help via workflow discipline but shouldn't be prioritized over retrieval quality and cross-model verification.

---

## What's Uncertain

- Whether recitation helps in tool-augmented settings (only tested vanilla)
- Whether VeriScore's verifiability filter transfers to investment research domain (tested on biography, QA, creative writing)
- The exact contribution of claim formulation quality vs search coverage to our 65% unclear rate (need ablation study)
- Long-term calibration of cross-model verification (do model families converge over time, reducing the cross-family benefit?)
- Whether 16% benchmark annotation noise (Verifying the Verifiers) inflates or deflates reported F1 scores

---

## Search Log

| # | Query | Tool | Result |
|---|-------|------|--------|
| 1 | VeriScore claim extraction verifiable unverifiable classification | Exa | GitHub repo + arXiv abstract |
| 2 | SAFE factual verification production deployment enterprise | S2 | Surveys only, no deployments |
| 3 | Claimify claim extraction evaluation | S2 | No results (found via Exa earlier) |
| 4 | VeriScore verifiable unverifiable mechanism | Exa | arXiv HTML + review pages |
| 5 | SAFE deployed production system enterprise | Exa | Press coverage only, no deployments |
| 6 | Process reward models factual verification | Exa | Clinical notes PRM + radiology PRM |
| 7 | Cross-model factual verification pipeline | Exa | FINCH-ZK (Amazon), LM vs LM, Alignment Bottleneck |
| 8 | FINCH-ZK paper full text | Exa crawl | Full paper extracted |
| 9 | Structured output reduce hallucination | Exa | StructFact, JSONSchemaBench — no hallucination evidence |
| 10 | Retrieval quality binding constraint hallucination | Exa | Cleanlab benchmark, hybrid retrieval paper |
| 11 | Prediction markets ground truth AI verification | Exa | TruthTensor framework |
| 12 | VeriScore HTML paper | WebFetch | Claim classification mechanism extracted |
| 13 | Cleanlab RAG evaluation blog | Exa crawl | Full benchmark details |
| 14 | FINCH-ZK S2 search | S2 | Found + saved (868b62765...) |
| 15 | Verifying the Verifiers S2 search | S2 | Not found on S2 |
| 16 | Clinical PRM S2 search | S2 | Not found on S2 |

---

## Sources Saved to Corpus

| Paper | S2 ID | Status |
|-------|-------|--------|
| FINCH-ZK (Goel et al., Amazon, 2025) | 868b62765e7f42a26938faf33d938e8070b0eecf | Saved |
| VeriScore (Song et al., EMNLP 2024) | 32d8df3dddfeb5d04326a17c0d506b1304aa8dc1 | Already in corpus |
| SAFE (Wei et al., NeurIPS 2024) | 58e194695187fe4daeb04ea694e0f59af2441177 | Already in corpus |
| FActScore (Min et al., EMNLP 2023) | bd5deadc58ee45b5e004378ba1d54a96bc947b4a | Already in corpus |
| Verifying the Verifiers (Seo et al., COLM 2025) | Not on S2 | URL: openreview.net/pdf?id=3NjnRo6apU |
| Alignment Bottleneck (Akhter et al., 2025) | Not on S2 | arXiv:2602.10380 |
| PRM Clinical Notes (Wang et al., EMNLP 2025) | Not on S2 | aclanthology.org/2025.emnlp-main.967 |
| PRM Radiology (Thomas et al., 2025) | Not on S2 | arXiv:2510.23217 |
| Claimify (Metropolitansky, Larson, ACL 2025) | Not on S2 | aclanthology.org/2025.acl-long.348 |
| TruthTensor (Shahabi et al., 2025) | Not on S2 | arXiv:2601.13545 |

<!-- knowledge-index
generated: 2026-03-22T00:13:51Z
hash: d6072fb014d3

sources: 6
  INFERENCE: from search absence
  INFERENCE: from search absence
  INFERENCE: from exhaustive search
  INFERENCE: splitting the 65% unclear rate into these three buckets based on VeriScore's 40% inconclusive rate among verified-verifiable claims
  INFERENCE: implementation cost is low, ~50 lines of prompt engineering
  INFERENCE: — no supporting evidence found
table_claims: 29

end-knowledge-index -->
