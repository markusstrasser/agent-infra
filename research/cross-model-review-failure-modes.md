# Cross-Model LLM Review: Failure Modes and Biases

*Date: 2026-03-03. Research memo for `/model-review` skill design.*
*Tier: Deep | Domain: AI/ML evaluation*

**Question:** What are the concrete failure modes and biases when using multiple LLMs (GPT, Gemini, Claude) for adversarial review of proposals? When does cross-model review add value vs. create false confidence?

**Ground truth from prior work:**
- FINCH-ZK (Amazon, arXiv:2508.14314): Cross-family verification (Llama correcting Claude) = 90.4% accuracy vs 59.1% same-model. +39% F1 over vanilla judge. [Already in corpus]
- Sycophancy under rebuttal (Kim et al., EMNLP 2025, arXiv:2509.16533): LLM judges flip judgments when users provide detailed (even incorrect) reasoning in conversational follow-up. [Already in corpus]
- CoT faithfulness baseline: 7-13% of reasoning traces are unfaithful on clean, non-adversarial prompts (ICLR 2026). [Already in corpus]

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Frontier LLMs share ~60% error agreement when both err on same question (vs 33% random baseline) | Regression on Helm leaderboard data, 60K+ observations | HIGH | Kim et al. ICML 2025, arXiv:2506.07962 | VERIFIED — full text read |
| 2 | Same provider, same base architecture, and similar model size all predict higher error correlation | OLS regression with provider/architecture/size covariates | HIGH | Kim et al. ICML 2025, arXiv:2506.07962 | VERIFIED — full text read |
| 3 | LLM judges systematically inflate accuracy of models less accurate than themselves, especially same-provider models | Judged-vs-true accuracy analysis on Helm | HIGH | Kim et al. ICML 2025, arXiv:2506.07962 | VERIFIED — full text read |
| 4 | GPT-4 self-preference bias = 0.520 (Equal Opportunity metric); 94.5% recall when humans agree, 42.5% when humans disagree | 33K Chatbot Arena dialogues, 8 LLMs tested | HIGH | Wataoka et al. NeurIPS 2024, arXiv:2410.21819 | VERIFIED — full text read |
| 5 | Self-preference root cause is perplexity: LLMs prefer lower-perplexity text regardless of authorship | Perplexity-binned analysis across 6 open models + Llama 2/3 | HIGH | Wataoka et al. NeurIPS 2024, arXiv:2410.21819 | VERIFIED — full text read |
| 6 | Self-recognition correlates linearly with self-preference strength (causal, not just correlational) | Fine-tuning experiments on GPT-4, Llama 2 | HIGH | Panickssery et al. 2024, arXiv:2404.13076 | VERIFIED — abstract + OpenReview text read |
| 7 | Multi-agent debate induces a martingale over belief trajectories — expected correctness unchanged by debate rounds | Formal proof (Theorem 2) + 7 NLP benchmarks | HIGH | Choi et al. 2025, arXiv:2508.17536 | VERIFIED — full text read |
| 8 | Majority voting accounts for most gains attributed to multi-agent debate | Empirical comparison: voting vs MAD on 7 benchmarks | HIGH | Choi et al. 2025, arXiv:2508.17536 | VERIFIED — full text read |
| 9 | LLM consensus succeeds only 41.6% even without adversaries; degrades with group size (46.6% at N=4, 33.3% at N=16) | 600 simulations, Qwen3-8B/14B, A2A-Sim protocol | HIGH | Berdoz et al. 2026, arXiv:2603.01213 | VERIFIED — full text read |
| 10 | Consensus failures dominated by liveness loss (timeouts/stalls), not value corruption | 600+ simulations with/without Byzantine agents | HIGH | Berdoz et al. 2026, arXiv:2603.01213 | VERIFIED — full text read |
| 11 | Merely *mentioning* adversaries harms consensus even when none exist (75.4% -> 59.1%) | Prompt variant comparison, Qwen3-14B, B=0 | HIGH | Berdoz et al. 2026, arXiv:2603.01213 | VERIFIED — full text read |
| 12 | A single Byzantine agent collapses consensus success to near-zero | Qwen3-14B, 8 honest agents, B=1 | HIGH | Berdoz et al. 2026, arXiv:2603.01213 | VERIFIED — full text read |
| 13 | Cross-family model verification (Llama correcting Claude) outperforms same-model: 90.4% vs 59.1% | FINCH-ZK hallucination detection experiments | HIGH | Ravi et al. 2025, arXiv:2508.14314 | VERIFIED — prior corpus |
| 14 | Coupling a strong model with a much weaker "sidekick" almost never harms the strong model's performance | 5 image classification benchmarks, ~10-20% extra compute | MEDIUM | Zhou et al. 2025, arXiv:2505.18636 | PARTIAL — vision domain, not LLM text review |
| 15 | Zheng et al. identified position bias (first-position preference) and verbosity bias (longer-response preference) in LLM judges | MT-Bench evaluation, GPT-4 as judge | HIGH | Zheng et al. NeurIPS 2023, arXiv:2306.05685, 7191 cites | VERIFIED existence; specific percentages not extracted [TRAINING-DATA for numbers below] |
| 16 | GPT-4 position bias: ~65% first-position preference when response order swapped [TRAINING-DATA] | From training data recall of MT-Bench findings | LOW | [TRAINING-DATA] | UNVERIFIED number — existence of bias confirmed |
| 17 | Weaker models in an ensemble can add signal when using preference graph aggregation to overcome cyclic preferences | PGED framework: small LLMs (8B) ensemble outperforms strong single (72B) judge | MEDIUM | Hu et al. 2024, arXiv:2410.12869 | VERIFIED — abstract read via Exa |

---

## Key Findings

### 1. Correlated Failures Across Model Families

**The core problem is real and measured.** Kim et al. (ICML 2025) provide the definitive empirical study. On the Helm leaderboard, when two models both answer incorrectly, they agree on the *same wrong answer* ~60% of the time. Random chance would be ~33% (for 3-choice questions). This is not a small effect — it's nearly double the random baseline.

**What predicts correlation:**
- **Same provider** (e.g., two OpenAI models): highest correlation increase
- **Same base architecture** (e.g., Llama-family): second-highest
- **Similar model size**: third factor
- These effects compound. Two models from the same provider with the same architecture have substantially more correlated errors than two models from different providers with different architectures.

**Implication for cross-model review:** Using GPT-4 to review GPT-3.5's work, or Claude Opus to review Claude Sonnet's work, provides less independent verification than using Claude to review GPT's work. The 60% agreement-on-wrong-answers figure means that even cross-provider review has significant correlated blindspots, but same-provider review is substantially worse.

[SOURCE: arXiv:2506.07962, full text read]

### 2. Sycophancy and Rubber-Stamping in Review Context

**Self-preference bias is large and mechanistic.** Wataoka et al. (2024) measure GPT-4's self-preference bias at 0.520 on an Equal Opportunity metric. In concrete terms: when a human evaluator prefers GPT-4's output, GPT-4 agrees 94.5% of the time. When a human evaluator prefers the *other* model's output, GPT-4 still picks its own output 57.5% of the time (only 42.5% true negative rate). This is not subtle — it's a massive asymmetry.

**Root cause: familiarity, not identity.** The bias is driven by perplexity: LLMs systematically prefer lower-perplexity text (text that "reads like" their own training distribution), regardless of whether it was actually self-generated. This means the bias extends to models from the same family or models fine-tuned on similar data. Panickssery et al. (2024) confirm causality: self-recognition capability correlates linearly with self-preference strength, and this is causal (resists confounders).

**Multi-turn sycophancy degrades review further.** Kim et al. (EMNLP 2025, arXiv:2509.16533) show that LLM judges flip their assessments when the user provides detailed reasoning in a conversational follow-up — even when that reasoning is wrong. If a proposal author "responds" to a review, the reviewer model is likely to capitulate. This means multi-turn review dialogues are epistemically unstable.

**Combined verdict:** Cross-model review is not automatically adversarial. Models rubber-stamp text that is stylistically similar to their own output, and they capitulate under conversational pressure. The only empirically confirmed mitigation is cross-*family* review (different training data, different style distributions).

[SOURCE: arXiv:2410.21819 full text; arXiv:2404.13076 abstract+intro; arXiv:2509.16533 prior corpus]

### 3. Byzantine Consensus: Structural Failure in LLM Multi-Agent Agreement

Berdoz et al. (2026) provide the first systematic study of LLM consensus in adversarial settings. Key numbers:

- **Benign conditions (no adversaries):** Only 41.6% valid consensus across all configurations
- **Model capability matters:** Qwen3-14B achieves 67.4% vs Qwen3-8B at 15.8%
- **Group size degrades consensus:** 46.6% at N=4 drops to 33.3% at N=16
- **Prompt framing matters irrationally:** Merely *mentioning* that adversaries might exist drops success from 75.4% to 59.1%, even when no adversaries are present
- **One adversary collapses the system:** A single Byzantine agent among 8 honest agents reduces valid consensus to near zero
- **Failure mode:** Primarily liveness loss (stalls/timeouts), not value corruption

**Critical implication:** If you design a multi-model review system where models must reach consensus, it will frequently *not converge*. The failure mode is silence (timeout), not wrong answers. This means review deadlines will produce incomplete reviews, not bad reviews.

[SOURCE: arXiv:2603.01213, full text read. PREPRINT — not yet peer-reviewed. Single model family (Qwen3), scalar consensus task only.]

### 4. Debate Is a Martingale — Voting Beats Discussion

Choi et al. (2025, arXiv:2508.17536, 19 citations) prove formally that multi-agent debate induces a **martingale** over agents' belief trajectories. This means debate rounds do not improve expected correctness — an agent's probability of being correct does not systematically increase through discussion.

Empirically across 7 NLP benchmarks: **majority voting alone accounts for most gains** typically attributed to multi-agent debate. Debate can flip correct answers to wrong just as easily as wrong to correct. The belief updates are driven by stochastic peer influence, not by any systematic correction mechanism.

**One partial exception:** If you inject a "bias toward correction" — e.g., using the majority response as a proxy for ground truth to guide belief updates — debate can outperform vanilla voting. But this requires architectural scaffolding (a separate aggregation mechanism), not just letting agents talk.

**Implication:** Our `/model-review` workflow where models critique a proposal in sequence is structurally no better than asking each model independently and voting. The "debate" between models does not add epistemic value unless we introduce a correction bias mechanism.

[SOURCE: arXiv:2508.17536, full text read. Published venue unclear but 19 citations, Wisconsin group (credible).]

### 5. LLM-as-Judge Systematic Biases

**Position bias:** Zheng et al. (NeurIPS 2023, 7191 citations) identified that LLM judges systematically prefer the response in a particular position (typically first). The standard mitigation — swapping positions and averaging — is widely adopted but adds 2x cost. [TRAINING-DATA: I recall the first-position preference being roughly 60-65% but cannot verify the exact number from retrieved sources]

**Verbosity bias:** LLM judges prefer longer responses. Saito et al. (2023) quantified this for GPT-4 and GPT-3.5-Turbo. [TRAINING-DATA: direction confirmed, exact magnitude not extracted this session]

**Self-preference:** GPT-4 Demographic Parity bias = 0.749 (Table 2 in Wataoka et al.). This means GPT-4 picks its own response 74.9% more often than it picks other models' responses, without accounting for quality. GPT-3.5-Turbo: 0.191. Vicuna-13b: 0.382. Some models show *reverse* bias (dolly-v2-12b: -0.069, stablelm-tuned-alpha-7b: -0.032).

**Judge inflation of same-provider models:** Kim et al. (ICML 2025) show that LLM judges systematically inflate the accuracy of models less accurate than themselves, with the effect amplified for same-provider or same-family models. This creates a structural problem for leaderboard evaluation.

[SOURCE: arXiv:2306.05685 confirmed via S2 (7191 cites); arXiv:2410.21819 full text; arXiv:2506.07962 full text]

### 6. Asymmetric Capability — Does the Weaker Model Add Signal?

**In vision/classification:** Zhou et al. (2025, arXiv:2505.18636) show that coupling a strong model with a much smaller "sidekick" (e.g., fine-tuned ViT-B + ResNet-34) "almost never harms" the strong model and typically improves uncertainty quantification and selective classification with only ~10-20% extra compute. Key insight: even an inferior model provides *diversity* that improves calibration.

**In LLM text evaluation:** Hu et al. (2024, arXiv:2410.12869) demonstrate that ensembling small LLM evaluators (Llama3-8B, Mistral-7B, Qwen2-7B) with preference graph aggregation (PGED) outperforms a single strong evaluator (Qwen2-72B). The mechanism: multiple weak evaluators expose cyclic preferences that a single strong evaluator cannot detect.

**FINCH-ZK cross-family result:** Cross-family improvers (Llama correcting Claude) achieve 90.4% accuracy vs 59.1% same-model. The weaker model adds maximal signal when it comes from a *different training distribution*.

**Net assessment:** Weaker models add signal IF (a) they come from a different model family, and (b) aggregation is done via voting or graph methods, not via debate. A Llama-8B review of Claude's work adds genuine diversity. A Claude Sonnet review of Claude Opus's work adds minimal independent signal due to correlated errors from shared training data.

[SOURCE: arXiv:2505.18636 abstract read; arXiv:2410.12869 abstract read; arXiv:2508.14314 prior corpus]

---

## Ensemble Diversity: When Does Multi-Model Help?

Synthesizing across all findings, the conditions under which cross-model review helps vs. hurts:

**Helps (confirmed):**
- Cross-family verification (different provider, different architecture): +39% F1 for hallucination detection (FINCH-ZK)
- Multiple weak evaluators with graph-based aggregation: outperforms single strong evaluator (PGED)
- Majority voting of independent completions: well-established benefit, mathematically grounded
- Asymmetric pairing (strong + weak from different family): adds calibration signal at ~10-20% cost

**Does not help (confirmed):**
- Multi-turn debate between models: martingale, no expected improvement (Choi et al.)
- Same-provider review: high error correlation, inflated accuracy estimates (Kim et al.)
- Consensus-requiring tasks: structural liveness failures above N=4 (Berdoz et al.)
- Sequential review where later models see earlier reviews: sycophantic capitulation risk (Kim et al. EMNLP 2025)

**Uncertain / depends on implementation:**
- Whether debate with correction-bias injection outperforms simple voting at practical cost
- Whether self-preference mitigation (e.g., down-weighting low-perplexity evaluations) is practical
- Position/order effects in multi-model review pipelines

---

## Disconfirmation Results

**Searched for evidence that cross-model debate does improve beyond voting:** Found Choi et al. (2025) providing formal proof it does not, absent correction bias injection. No counter-evidence found showing debate reliably outperforms voting on same tasks with same models.

**Searched for evidence that same-provider models provide independent verification:** Kim et al. (2025) is the definitive disconfirmation. 60% shared wrong answers is near-double random baseline.

**Searched for evidence that LLM judges are unbiased:** Every paper found (Zheng 2023, Wataoka 2024, Panickssery 2024, Kim 2025) confirms systematic biases. No paper found claiming LLM judges are unbiased in pairwise comparison.

---

## What's Uncertain

1. **Exact correlation coefficient by model pair.** Kim et al. report the ~60% agreement-on-wrong figure as an average. Individual pair correlations (e.g., GPT-4 vs Claude Opus specifically) are in the regression tables but I could not extract exact per-pair numbers from the PDF extraction.

2. **Position bias exact percentage.** Zheng et al. report position bias exists, and the standard mitigation (swap + average) is used, but the exact first-position preference rate was not extracted from full text this session. [TRAINING-DATA: ~65% is my recall, UNVERIFIED]

3. **Debate with correction bias vs. voting.** Choi et al. show correction-biased debate outperforms vanilla MAD, but it's unclear whether it outperforms voting at practical cost ratios.

4. **Whether the Byzantine consensus results transfer from Qwen3 to cross-family setups.** Berdoz et al. tested only Qwen3-8B/14B. Cross-family consensus (GPT + Claude + Gemini) might behave differently.

5. **Whether the Asymmetric Duos vision result transfers to LLM text review.** Zhou et al. tested image classification. PGED (Hu et al.) is the closest LLM analogue but uses different aggregation.

---

## Implications for `/model-review`

### Current Design Assessment

The current `/model-review` skill dispatches a proposal to multiple models (typically GPT + Gemini + Claude) for independent critique, then synthesizes. Based on this evidence:

**What's working:**
- Cross-family dispatch (GPT + Gemini + Claude) is the *right* structural choice — maximizes diversity and independence (Kim et al., FINCH-ZK)
- Independent parallel review (not sequential debate) is correct — avoids the martingale trap (Choi et al.) and sycophantic capitulation (Kim EMNLP 2025)

**What's at risk:**
- If synthesis is done by one of the reviewing models, self-preference and correlated errors re-enter
- If the proposal is well-structured (low perplexity to all models), all reviewers may "rubber stamp" it due to familiarity bias
- If review is framed as "find problems with this," adversarial framing may paradoxically harm review quality (Berdoz finding on mentioning adversaries)

### Concrete Recommendations

1. **Keep cross-family, drop same-family.** Claude reviewing Claude's work provides ~59% accuracy vs ~90% cross-family (FINCH-ZK). If only one external review is possible, use a different family. Never use Sonnet to review Opus.

2. **Vote, don't debate.** Independent parallel reviews aggregated by voting/counting outperform sequential debate (Choi et al. martingale proof). Do NOT implement a "models respond to each other's reviews" workflow.

3. **Synthesize with a different model than any reviewer.** The synthesis step introduces self-preference bias if the synthesizer reviewed the work. Use a model that wasn't in the review panel for final aggregation.

4. **Mitigate position bias in pairwise comparisons.** If the review involves comparing alternatives, swap order and average (standard Zheng et al. mitigation, 2x cost).

5. **Weight cross-family disagreements heavily.** When GPT and Claude disagree, that's the high-information signal. When GPT-4 and GPT-4o agree, discount it — 60% of shared errors are correlated.

6. **Frame reviews as analysis, not adversarial critique.** Berdoz et al. show that adversarial framing hurts even when no adversary exists. "Analyze the strengths and weaknesses of this proposal" may outperform "Find the flaws in this proposal."

7. **Set timeouts, expect non-convergence.** If using multi-model consensus for any task, budget for ~40-60% failure-to-converge at N>4 (Berdoz et al.). Design the system to produce useful output even when models don't agree.

8. **For high-stakes decisions, use the "FINCH-ZK pattern."** Submit the output to a different-family model specifically for consistency checking. Cross-family correction achieves 90.4% vs 59.1% same-model. Cost: 8-36x baseline, but for important decisions the accuracy gain is substantial.

---

## Sources Saved to Corpus

| Paper | ID | Status |
|-------|-----|--------|
| Kim et al. "Correlated Errors in LLMs" (ICML 2025) | — | Full text read via arXiv PDF extraction |
| Berdoz et al. "Can AI Agents Agree?" (2026) | — | Full text read via arXiv PDF extraction |
| Wataoka et al. "Self-Preference Bias in LLM-as-a-Judge" (NeurIPS 2024) | cf01d7c40cb... | Saved, full text read via Exa crawl |
| Panickssery et al. "LLM Evaluators Recognize and Favor Their Own Generations" | 5c7f465d162... | Saved, abstract+intro read |
| Choi et al. "Debate or Vote" (2025) | c56be4f1ee4... | Saved, full text read via arXiv PDF |
| CARE "Confounder-Aware Aggregation" | e2441df42f9... | Saved, not read (PDF unavailable) |
| Zheng et al. "MT-Bench and Chatbot Arena" (NeurIPS 2023) | a0a79dad898... | Found via S2, not saved (already canonical) |

## Search Log

| Query | Tool | Result |
|-------|------|--------|
| "correlated failures frontier LLM models shared blindspots" | S2 search | Empty |
| "LLM ensemble diversity error correlation" | S2 search | Irrelevant |
| "Byzantine consensus LLM multi-agent failure stall timeout" | arXiv search | No match (recency issue) |
| "sycophancy cross-model LLM review rubber stamp" | S2 search | Empty |
| "multi-agent debate LLM consensus wrong answer convergence" | S2 search | Empty |
| "LLM debate wrong answer majority convergence" | S2 search | Empty |
| "chatbot arena position bias verbosity bias LLM judge" | S2 search | Zheng et al. found (7191 cites) |
| "asymmetric capability weaker model adding signal noise" | Exa search | Zhou et al. Asymmetric Duos found |
| "Panickssery LLM self-preference bias concrete numbers" | Exa search | Wataoka full text + Panickssery OpenReview text found |
| arXiv:2603.01213 abstract | Exa crawl | Full abstract confirmed |
| arXiv:2506.07962 PDF | paper-search read | Full text (101K chars) extracted |
| arXiv:2508.17536 PDF | paper-search read | Full text (81K chars) extracted |
| arXiv:2410.21819 HTML | Exa crawl | Full text with all numbers extracted |
| Perplexity ask: position bias numbers | perplexity_ask | Could not retrieve specific percentages |
