# Practical Calibration Measurement for AI Agents

*Date: 2026-03-02. Deep tier research.*
*Part of [epistemic-quality-evals](epistemic-quality-evals.md). Updates that memo's "What's Uncertain" on calibration.*

---

## RQ1: Minimum Viable Sample for Calibration Measurement

### What the evidence says

**The gold standard is 15 samples per query.** Savage et al. (Stanford, medRxiv 2024, full text read) tested Sample Consistency across 4 LLMs and 3 medical QA datasets. They used 15 forward passes per question because "Manakul et al. demonstrated a plateau in Sample Consistency performance beyond a sample size of 15" (citing the SelfCheckGPT paper). [SOURCE: medRxiv 10.1101/2024.06.06.24308399, full text read]

**The Muller et al. benchmark (arXiv:2602.00279, 2026) used 685,000 long-form responses across 20 LLMs and 7 datasets.** They confirm answer frequency (consistency across samples) yields the most reliable calibration. But they don't specify a minimum N per query — their scale was designed for benchmark-level analysis, not production monitoring. [SOURCE: arXiv:2602.00279, abstract only]

### Is N=10 runs on 20 canary queries enough?

**Short answer: probably, with caveats.**

**Statistical power analysis** [INFERENCE]:
- With 20 canary queries at N=10 each, you get 200 total observations per calibration check.
- For detecting a 10 percentage-point miscalibration (e.g., agent claims 80% confidence but is correct 70% of the time), a one-proportion z-test at alpha=0.05 with N=200 gives power ~0.80. That's sufficient for a monthly check.
- For detecting a 5pp miscalibration, you need ~750 observations (75 queries at N=10, or 50 queries at N=15).
- Assumption: canary queries have known ground truth. If they don't, you're measuring consistency, not calibration. Consistency is still useful but measures different things.

**The Savage plateau at 15 samples** is for per-query uncertainty estimation. If your goal is aggregate calibration across a test set (not per-query uncertainty), you can trade per-query samples for more queries: 20 queries x 10 samples = 200 data points, which is comparable to 13 queries x 15 samples = 195 data points.

**Practical design:**
- 20 canary queries with known ground truth (mix of easy/hard)
- N=10 samples per query at temperature 0.5-1.0 (Savage found no difference between 0.5 and 1.0)
- Monthly cadence is fine for trend detection; weekly if you're changing prompts/skills
- Cost: 200 API calls/month. At Claude Opus pricing (~$0.50/response for a moderate query), ~$100/month. Cheaper with Haiku/Sonnet for the repeated samples.
- Score using Brier score over the aggregate, not ECE alone (Muller et al.'s key methodological finding)

**Nobody has published a "monthly calibration check" system for production agents.** This is a gap in the literature. The closest is the SAFE-lite periodic sampling pattern (Wei et al., NeurIPS 2024), but that measures factual precision, not calibration. [INFERENCE from absence of search results across S2, Exa, and WebSearch]

### Key caveat

Canary queries measure calibration on **known-answer questions**. Agent research outputs involve open-ended claims where ground truth is expensive to establish. Calibration on canary queries is a necessary but not sufficient proxy for calibration on actual work product.

---

## RQ2: Hedging Language vs Accuracy

### The evidence is clear: hedging is orthogonal to accuracy

**Yona et al. (EMNLP 2024, arXiv:2405.16908, full text read via HTML)** formalized this precisely:

- **Metric:** "faithful response uncertainty" = match between linguistic decisiveness and intrinsic confidence (measured by sampling consistency)
- **Vanilla prompting:** cMFG scores of 0.52-0.54 across all models tested (Gemini Nano/Pro/Ultra, GPT-3.5, GPT-4). Random baseline = 0.50. Models answer with **decisiveness = 1.0** (maximally confident language) regardless of actual uncertainty.
- **With uncertainty prompting:** hedges appear but are not aligned with actual uncertainty. Best result: Gemini Ultra cMFG = 0.70 on PopQA. GPT-4: 0.57-0.63. The correlation between expressed decisiveness and intrinsic confidence is "weak" even in the best case.
- **Punting rates:** Vanilla 1%, Uncertainty prompt 10%. Models that hedge more also refuse more, but the hedges themselves don't track confidence.

[SOURCE: arXiv:2405.16908, read via HTML rendering]

**Tang et al. (npj Complexity, Feb 2026, peer-reviewed)** studied words of estimative probability (WEPs) — "maybe," "probably not," etc. Found that LLMs and humans interpret these words differently in probability terms. The mapping from hedging language to probability is unstable across models and contexts. [SOURCE: nature.com/articles/s44260-026-00070-6, abstract]

**Tao et al. (arXiv:2509.24202, 2025)** created the first large-scale dataset of hedging expressions with human-annotated confidence scores. Their finding: "while most LLMs underperform in expressing reliable [linguistic confidence], carefully designed prompting achieves competitive calibration." But this requires a specific mapper trained on human annotations — the raw hedging language of an unprompted model carries almost no calibration signal. [SOURCE: arXiv:2509.24202, abstract + intro]

### Practical implication

**Do not use hedging language as a calibration proxy.** An agent that says "likely" or "approximately" is not better calibrated than one that states things flatly. The hedging is a linguistic style preference imposed by RLHF, not a reflection of epistemic state. If you want calibrated uncertainty expression, you need either:

1. **Sampling consistency** (run N times, measure agreement) — proven effective
2. **ConfTuner-style fine-tuning** (Li et al., NeurIPS 2025) — uses tokenized Brier score as loss function, but requires fine-tuning access
3. **Forced verbalized confidence** with post-hoc calibration — the model states "I am X% confident," but you recalibrate X against observed accuracy on a held-out set

Option 1 is the only one that works for black-box API models without fine-tuning. Option 3 works but requires the held-out reference set that Option 1 also needs.

---

## RQ3: Cross-Model Agreement as Calibration Proxy

### Agreement correlates with correctness, but the margin isn't huge

**ChainPoll (Friel & Sanyal, Galileo 2023):** Multi-call voting with chain-of-thought achieved 0.781 AUROC for hallucination detection — 11% better than next best method, 23% better than standard metrics. [SOURCE: platilus.com/blog/cross-model-verification, which cites the original paper]

| Method | AUROC |
|--------|-------|
| ChainPoll (CoT voting) | 0.781 |
| SelfCheck-BertScore | 0.673 |
| SelfCheck-NGram | 0.644 |
| G-Eval | 0.570 |

**Xue et al. (Educ. Psychol. Meas., Feb 2026):** Studied inter-LLM consistency across 5 models (Claude, DeepSeek, Gemini, GPT, Qwen). Key finding: intra-LLM consistency (same model, multiple runs) was "almost perfect" regardless of temperature. Inter-LLM consistency was "moderate, with higher agreement observed for items that were easier to score." [SOURCE: PMC12909151]

**Debate-or-Vote (arXiv:2508.17536, ACL 2025, from prior corpus):** Multi-agent debate is a martingale — debate does not improve expected correctness. But disagreement IS a useful signal for identifying uncertain claims. This is an adversarial identification pattern, not a consensus-truth pattern. [SOURCE: prior corpus, arXiv:2508.17536]

### Practical implication

Cross-model agreement is a **decent but imperfect** proxy for correctness:
- When models agree: ~78% AUROC for detecting correct answers (not 95%+)
- When models disagree: useful signal for human review escalation
- The value is in **disagreement detection** (identifying where to look harder), not in agreement-as-truth (treating consensus as correct)

**Design pattern for our system:**
1. Run critical claims through Claude + Gemini independently
2. Where they agree: mark as higher confidence (but still verify key claims)
3. Where they disagree: flag for human review or deeper sourcing
4. This is NOT voting — it's adversarial uncertainty identification
5. Cost: 2x per critical claim. Worth it for high-stakes outputs, not for every query.

### Quantification gap

Nobody has published the specific number I want: "When Claude and Gemini agree on a factual claim, what percentage of the time is it actually true?" ChainPoll is same-model multi-call, not cross-model. The Xue et al. paper measures consistency, not accuracy-conditioned-on-agreement. This specific conditional probability is an open question. [INFERENCE from absence of results]

---

## RQ4: Proper Scoring Rules for Text Outputs

### The core problem: text outputs don't have probability distributions

Brier score requires: a probability forecast p and a binary outcome y. Brier = (p - y)^2. Simple for weather forecasts ("30% chance of rain" + did it rain?). Not simple for "the company's revenue growth was driven by cloud services."

### Three approaches found

**Approach 1: Force verbalized probabilities, then score them**

ConfTuner (Li et al., NeurIPS 2025) introduces the "tokenized Brier score" — a proper scoring rule adapted for LLM fine-tuning. The model outputs "I am X% confident that..." and the tokenized Brier loss is:

> tokenized_Brier = sum over confidence tokens of (token_probability - correctness)^2

This is theoretically proven to be a proper scoring rule (i.e., the optimal strategy for the model is to report its true probability of being correct). Results: improves calibration across diverse reasoning tasks, generalizes to black-box models via prompting (not just fine-tuning). [SOURCE: openreview.net/pdf?id=VZQ04Ojhu5, abstract + intro read; full metrics not extractable from PDF]

**Practical for us:** We can prompt the agent to append "Confidence: X%" to factual claims, then score those probabilities against verified outcomes using Brier score. This requires:
- A verification step (SAFE-lite or human review) to establish ground truth
- Enough claims to calculate meaningful Brier scores (50+ claim-outcome pairs minimum for a useful reliability diagram)
- The agent must be prompted to give confidence; unprompted confidence is poorly calibrated (Muller et al., Yona et al.)

**Approach 2: Decompose text into scorable claims**

Combine FActScore/SAFE decomposition with scoring:
1. Decompose research output into atomic claims
2. For each claim, determine if it's verifiable
3. For verifiable claims, establish ground truth (search-based verification)
4. Score: supported=1, contradicted=0, unclear=skip
5. Factual precision = sum(supported) / sum(verifiable)

This gives a precision rate, not a Brier score — but it's the practical equivalent for text outputs. SAFE achieves this at $0.19/response. Our SAFE-lite implementation using Exa costs ~$0.05-0.10/response. [SOURCE: arXiv:2403.18802, prior corpus]

**Approach 3: Prophet Arena / forecasting tournaments**

Prophet Arena (Yang et al., arXiv:2510.17638) uses Brier score to rank LLMs on their probabilistic predictions about real-world events. This works because they force models to output probability forecasts on well-defined questions with eventual ground truth (sports outcomes, election results, market movements).

**Practical for us:** Frame calibration checks as prediction markets. Instead of "research company X," ask "What is the probability that company X will report revenue above $Y in Q3?" — a question with eventual ground truth. Then Brier-score the agent's probability forecast. This only works for claims with resolvable outcomes, but investment research produces many such claims. [INFERENCE: applicable to intel project specifically]

### CRPS (Continuous Ranked Probability Score)

CRPS is the generalization of Brier score to continuous distributions. It's used in weather forecasting and was referenced in the RQ. For LLM agent outputs, CRPS would apply if the agent produces prediction intervals ("revenue will be $2-3B"). The CRPS of a prediction interval [a,b] against an outcome x is tractable to compute. **No papers found applying CRPS to LLM agent outputs.** This is an open research direction. [INFERENCE from absence of results]

---

## RQ5: Statistical Process Control for Agent Metrics

### SPC has been applied to ML monitoring, but not agent epistemic quality

**Zamzmi et al. (arXiv:2402.08088, FDA/CDRH, 2024)** proposed an SPC framework for OOD detection and data drift monitoring in ML-enabled medical devices. They use:
- **Shewhart control charts** (X-bar, R charts) for detecting abrupt shifts
- **CUSUM** (Cumulative Sum) for detecting gradual drifts
- Applied to radiological image classification features, not text/agent outputs

[SOURCE: arXiv:2402.08088, abstract]

**The practitioner literature on ML drift detection** (Deepchecks, Encord, OneUpTime) uses:
- Population Stability Index (PSI) for feature distribution shifts
- Kolmogorov-Smirnov tests for distribution comparison
- CUSUM and EWMA for sequential monitoring

None of these are applied to agent epistemic quality specifically. [SOURCE: deepchecks.com, encord.com, oneuptime.com/blog]

### Practical SPC design for agent metrics [INFERENCE]

We already have time-series data from our hooks:
- `~/.claude/epistemic-metrics.jsonl` — pushback index, lint scores, SAFE-lite precision
- `~/.claude/session-receipts.jsonl` — per-session metadata
- `~/.claude/subagent-log.jsonl` — researcher source citation rates

**Proposed SPC charts:**

1. **X-bar chart for SAFE-lite precision:** Run SAFE-lite on 5-10 research outputs per week. Plot weekly mean factual precision. Set UCL/LCL at mean +/- 3 sigma from 8-week baseline. Signal: precision dropping below LCL indicates systematic degradation.

2. **CUSUM for pushback index:** Pushback index (% of responses that push back vs agree) should stay in a range. Monotonic decline = sycophancy drift. CUSUM detects this faster than Shewhart charts because it accumulates small deviations.

3. **R-chart for consistency:** Run the 20 canary queries monthly. Plot the range (max-min) of consistency scores. Increasing variability signals model instability or prompt sensitivity.

4. **p-chart for unsourced claim rate:** Weekly count of unsourced claims / total claims in research outputs (from epistemic-lint.py). Proportional control chart with binomial limits.

**Implementation cost:** Most of the data collection infrastructure already exists. The SPC logic is ~50 lines of Python per chart type. The hard part is establishing the baseline (need 8-12 data points = 2-3 months of weekly measurement before control limits are meaningful).

**Statistical requirement:** SPC charts assume approximate normality or at least stable variance. Agent metrics likely violate this — they're bounded (0-100%), may have bimodal distributions, and have small samples. Use the p-chart (binomial-based) for rate metrics and nonparametric variants (rank-based CUSUM) for others.

---

## RQ6: Cromwell's Rule in Practice

### The principle

Cromwell's rule (attributed to statistician Dennis Lindley, named after Oliver Cromwell's 1650 letter to the Church of Scotland): never assign prior probability 0 or 1 to any event unless it is logically certain or impossible. Because once P(A)=0 or P(A)=1, no amount of evidence can update it via Bayes' theorem. [TRAINING-DATA — this is textbook probability theory]

### How it applies to LLM calibration

LLMs exhibit the opposite of Cromwell's rule — they over-assert certainty:

- **Verbalized confidence:** Models rarely say "0% confident" or "100% confident" explicitly, but they express certainty through decisive language (decisiveness=1.0 by default per Yona et al.). The practical violation isn't numeric — it's linguistic.
- **Probability mass polarization:** Instruction-tuned models push token-level probabilities toward 0 and 1 (Muller et al.). This means the model's internal probability distribution is overconfident at the extremes. Even when you can read logprobs, they're unreliable as calibrated probabilities.

### Practical mechanisms to cap confidence

**1. Hard floor/ceiling on verbalized confidence:**
Prompt: "When stating your confidence, never assign below 5% or above 95% unless the claim is logically necessary or impossible."
Effectiveness: low. This is an instruction, and instructions alone don't produce reliability. Models will state "95% confident" instead of "100% confident" — same overconfidence, different number. [INFERENCE]

**2. Platt scaling / temperature calibration:**
Post-hoc recalibration of logits or verbalized probabilities. Compress extreme probabilities toward the center:
- p_calibrated = sigmoid(a * logit(p_raw) + b)
- where a < 1 compresses and b shifts. Fit on a held-out calibration set.
This is the standard approach in ML calibration (Platt 1999). It implicitly enforces Cromwell's rule by pulling extremes toward center. [TRAINING-DATA]

**3. Beta-calibrated confidence:**
Map raw probabilities through a Beta distribution CDF with parameters fit to calibration data. This naturally caps at (epsilon, 1-epsilon) and handles non-linear miscalibration better than Platt scaling. [TRAINING-DATA]

**4. The practical approach: treat any claim at >95% or <5% as suspect**
In production, flag claims the agent asserts with certainty for additional verification. The base rate of 7-13% CoT unfaithfulness (ICLR 2026) means even the model's most confident claims have a non-trivial error rate. The practical Cromwell's rule for agent systems: **never trust a claim at face value just because the agent expressed certainty.** [INFERENCE from ICLR 2026 CoT faithfulness data + Cromwell's principle]

**5. ConfTuner's approach (NeurIPS 2025):**
The tokenized Brier score is a proper scoring rule, which means it automatically penalizes extreme probabilities that aren't warranted. A model fine-tuned with ConfTuner will naturally avoid 0% and 100% confidence when the evidence doesn't support it, because the Brier loss is maximized when overconfident predictions are wrong. This is the most principled solution but requires fine-tuning access. [SOURCE: NeurIPS 2025, openreview.net]

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Sample Consistency plateaus at 15 forward passes per query | Manakul et al. (SelfCheckGPT), cited by Savage et al. | HIGH | medRxiv, full text read | VERIFIED (via Savage) |
| 2 | SC by Sentence Embedding achieves ROC AUC 0.68-0.79 for discrimination | 4 models, 3 datasets | HIGH | medRxiv, full text read | VERIFIED |
| 3 | SC by GPT Annotation achieves ROC AUC 0.66-0.74 with accurate raw calibration | Same study | HIGH | medRxiv, full text read | VERIFIED |
| 4 | N=10 samples on 20 queries (200 observations) has ~80% power to detect 10pp miscalibration | Statistical calculation | MEDIUM | INFERENCE (one-proportion z-test) | CALCULATED |
| 5 | Vanilla LLM hedging: cMFG 0.52-0.54 (random=0.50) — hedging is near-random | EMNLP 2024, 5 models, multiple datasets | HIGH | arXiv:2405.16908, full HTML read | VERIFIED |
| 6 | Best prompted hedging: Gemini Ultra cMFG=0.70 on PopQA | Same study | HIGH | arXiv:2405.16908 | VERIFIED |
| 7 | ChainPoll achieves 0.781 AUROC for hallucination detection via multi-call voting | Galileo Technologies, 4 benchmark datasets | MEDIUM | platilus.com (secondary) | VERIFIED via secondary |
| 8 | Inter-LLM consistency is moderate; higher for easier items | 5 models (Claude, DeepSeek, Gemini, GPT, Qwen) | MEDIUM | PMC12909151 | VERIFIED |
| 9 | No published "monthly calibration check" system for production agents exists | Extensive search across S2, Exa, WebSearch | MEDIUM | Absence of evidence | UNVERIFIED (absence) |
| 10 | Tokenized Brier score is a theoretically proven proper scoring rule for LLM confidence | NeurIPS 2025 peer review | HIGH | openreview.net, abstract read | VERIFIED |
| 11 | SPC (Shewhart, CUSUM) applied to ML drift detection in medical devices | FDA/CDRH researchers | MEDIUM | arXiv:2402.08088 | VERIFIED |
| 12 | No SPC system applied to agent epistemic quality specifically | Search across S2, Exa | LOW | Absence of evidence | UNVERIFIED (absence) |
| 13 | Instruction-tuned models exhibit probability mass polarization | 20 models, 685K responses | MEDIUM (preprint) | arXiv:2602.00279 | PREPRINT |
| 14 | Confidence Elicitation universally overconfident in medical QA | 4 models, 3 medical datasets | HIGH | medRxiv, full text read | VERIFIED |

---

## Disconfirmation Results

1. **"Hedging = better calibration" — DISCONFIRMED.** Yona et al. (EMNLP 2024) directly measures this and finds hedging is near-random relative to actual confidence. The intuition that cautious language indicates epistemic humility is wrong for LLMs. The hedging is a style artifact of RLHF, not a calibration signal.

2. **"Cross-model agreement is reliable truth signal" — PARTIALLY CONFIRMED, PARTIALLY DISCONFIRMED.** Agreement helps (0.781 AUROC with ChainPoll) but is far from decisive. The specific conditional probability (P(correct | models agree)) has not been measured cross-model. The signal is better for identifying DISAGREEMENTS (where at least one model is wrong) than for confirming AGREEMENTS (where both could be wrong in the same way due to shared training data).

3. **"ECE is sufficient for calibration measurement" — DISCONFIRMED.** Muller et al. (2026) explicitly warns against relying exclusively on ECE. Need AUROC + AUPRC + Brier Score together. ECE is sensitive to binning and can be gamed.

4. **"Token-level probabilities are useful for calibration" — DISCONFIRMED for instruction-tuned models.** Probability mass polarization (Muller et al.) makes logprobs unreliable after RLHF. Reasoning-process models partially mitigate this, but the effect varies by provider.

---

## What's Uncertain

1. **Exact minimum N for per-query calibration:** The 15-sample plateau (Manakul) is the only empirical data point. Whether 10 is "good enough" depends on the use case. Nobody has done the power analysis for agent calibration specifically.

2. **Cross-model conditional accuracy:** P(claim is true | Claude and Gemini agree on it) has not been measured. ChainPoll measures same-model multi-call, not cross-model.

3. **CRPS for agent prediction intervals:** No work found. This is entirely unexplored for text-output agents.

4. **SPC applicability to non-normal, bounded agent metrics:** The statistical validity of Shewhart charts on SAFE-lite precision scores (bounded 0-1, potentially bimodal) is uncertain. p-charts and nonparametric alternatives are more appropriate but less standard.

5. **Whether ConfTuner-style training transfers to agentic settings:** ConfTuner was tested on QA tasks. Whether calibrated verbalized confidence survives multi-step agent workflows (where the agent's confidence compounds across steps) is unknown.

---

## Actionable Recommendations

### Minimum Viable Calibration System (build first)

1. **20 canary queries** with known ground truth, spanning easy/hard and multiple domains relevant to the agent's work
2. **Run each query 10 times** at temperature 0.5 with seed variation
3. **Measure consistency** (fraction of runs agreeing on the same answer)
4. **Compare consistency to correctness** on the held-out ground truth
5. **Score with Brier** (not just ECE): Brier = mean((consistency - correctness)^2)
6. **Monthly cadence**, logged to `~/.claude/epistemic-metrics.jsonl`
7. **Implementation cost:** ~$100/month in API calls, ~200 lines of Python

### Enhanced System (build second)

1. **Weekly SAFE-lite** on 5 random research outputs → factual precision tracking
2. **SPC p-chart** on unsourced claim rate from epistemic-lint.py
3. **CUSUM on pushback index** to detect sycophancy drift
4. **Cross-model disagreement flagging** on high-stakes claims (2x cost but better than nothing)
5. **Forced confidence elicitation** + Platt scaling for investment research predictions with eventual ground truth

### What NOT to build

- **Hedging language detector** as calibration proxy — evidence says this doesn't work
- **Token-level probability extraction** — unreliable after instruction tuning
- **Full cross-model ensemble** for every output — 2x cost for moderate signal; reserve for critical claims

---

## Search Log

| # | Tool | Query | Result |
|---|------|-------|--------|
| 1 | list_corpus | (check existing) | Found prior epistemic-quality-evals.md with calibration paper references |
| 2 | S2 search | "calibration LLM confidence" | Found Muller 2026, Xiong 2023, medical calibration papers |
| 3 | Exa | "linguistic hedging LLM accuracy calibration" | Found Tao 2025, Yona EMNLP 2024, Tang npj 2026 |
| 4 | Exa crawl | arXiv:2602.00279 HTML | Abstract only — full paper not accessible via crawling |
| 5 | WebFetch | arXiv:2405.16908 HTML | Full paper content extracted — key numerical results |
| 6 | S2 search | "proper scoring rules text generation Brier score" | Found Shao ICML 2024 |
| 7 | Exa | "Brier score proper scoring rules LLM text outputs" | Found ConfTuner NeurIPS 2025, Prophet Arena |
| 8 | Exa | "SPC charts monitoring AI model performance" | Found Zamzmi 2024 FDA, practitioner blogs |
| 9 | Exa | "Cromwell's rule probability capping LLM calibration" | General articles, no specific implementations |
| 10 | Exa | "cross-model agreement accuracy factual correctness" | Found Platilus blog (ChainPoll), Xue 2026, Council of AI |
| 11 | fetch_paper | Savage medical calibration | Full text read — 12K tokens, comprehensive methodology |
| 12 | save_paper | ConfTuner, Savage, Shao ICML | Saved to corpus |

## Sources Saved to Corpus

| Paper | S2 ID | Status |
|-------|-------|--------|
| ConfTuner (Li et al., NeurIPS 2025) | f1f48068bfb3368f62e61fb6a97aa25fb10c8aa6 | Saved |
| Language Generation with Strictly Proper Scoring Rules (Shao, ICML 2024) | 590088c7bc699fe26507cb1e9f70aac531d1f069 | Saved |
| LLM Uncertainty Measurement and Calibration for Medical Diagnosis (Savage et al.) | 2285c7d0c84eb08b184e2d4ebab1f2f46647c28f | Saved, fetched, read in full |
| RL for Better Verbalized Confidence in Long-Form Generation | fe13d660dbad9cd52d753f360424745e11d4844f | Saved |

<!-- knowledge-index
generated: 2026-03-21T23:52:35Z
hash: b53185c48100

sources: 6
  INFERENCE: from absence of search results across S2, Exa, and WebSearch
  INFERENCE: from absence of results
  INFERENCE: applicable to intel project specifically
  INFERENCE: from absence of results
  TRAINING-DATA: — this is textbook probability theory
  INFERENCE: from ICLR 2026 CoT faithfulness data + Cromwell's principle
table_claims: 14

end-knowledge-index -->
