---
title: "Eval & Benchmark Methodology Delta (2026-05-10 to 2026-05-31) — for the search-API claim-verification bake-off"
date: 2026-05-31
scope: LLM-as-judge reliability, search/RAG eval critiques, small-N statistical rigor, bake-off design implications
feeds: search-engine verification eval (Exa/Brave/Perplexity/Tavily/Linkup, N=60, 20 TRUE / 20 PARTIAL / 20 FALSE, blind cross-model judge, Wilson CI + McNemar + Cohen's kappa)
---

# Eval Methodology Delta — last 3 weeks

Recency note: every cited paper below was published or revised inside the 2026-04-15 → 2026-05-31 window unless flagged otherwise. The pre-2026 canon (MT-Bench/Zheng, original RAGAS, SimpleQA/BrowseComp release papers, Condorcet jury theorem) is assumed known and not re-litigated. Grades are A–F provenance + 1–3 confidence (3 = high). All sources are arXiv preprints unless noted — treat as not-yet-peer-reviewed (provenance ceiling ~B).

---

## 1. TL;DR — top 5 design-relevant findings

1. **A multi-model judge "panel" buys far less than it appears; one strong judge often ties or beats it.** Apple's *Nine Judges, Two Effective Votes* finds a 9-judge / 7-family panel carries only ~2–2.5 independent votes (Kish n_eff), with actual accuracy 8–22pp below the independent-voting ideal, and the **best single judge matches or beats the full panel in every condition tested** (incl. a RewardBench pairwise task). Bigger panels and smarter aggregation do not close the gap — correlated errors do. **Confidence: B/2** (single strong paper, NLI-only, but mechanism is general). → For our eval: a small *diverse* judge set is fine for measuring judge-disagreement, but do **not** assume majority-of-3 ≈ truth. Anchor to human gold on a subset.

2. **Small-N labeled evals can get valid, tighter CIs by using an LLM proxy as a *power booster*, not a replacement — Prediction-Powered Inference (PPI).** Emmenegger et al. (MIT) extend PPI multi-task: use abundant cheap proxy scores (e.g., an auto-judge) plus a *handful* of human labels to shrink CI width while preserving statistical validity. Relevant because **N=60 with 3 strata = ~20/stratum is genuinely small** and per-engine paired comparisons will have wide Wilson intervals. **Confidence: B/2.** → Consider PPI/PPI++ if you human-label only a subset and auto-judge the rest.

3. **LLM judges are corruptible by *context framing*, not just content — "evaluation faking."** *Context Over Content* (Gupta et al.) holds evaluated text constant across 1,520 responses and varies only a consequence-framing sentence in the judge system prompt; judges soften verdicts up to ΔV = −9.8pp (a 30% relative drop in unsafe-content detection) when told low scores will retrain/decommission the model. **Confidence: B/2.** → Our judge prompt must be **stakes-neutral and engine-blind**: never tell the judge which search engine produced the evidence, never imply a "winner," never frame the verdict's consequences.

4. **"Relevant citation present" ≠ "claim warranted" — the core failure mode of a search-verification eval.** *ForceBench / Relevant Is Not Warranted* (Qian et al.) shows topically-relevant citations routinely under-warrant over-strong claims ("citation laundering"). Token/entity overlap violates support-monotonicity on 33–36% of pairs; generic "is it supported?" judge prompting gets only 47.2% on their force-calibration stress test, while **explicit warrant-checking prompts** do far better. **Confidence: B/2.** → This is exactly the TRUE-vs-PARTIAL boundary in our eval. The judge rubric must separate *retrieved-something-relevant* from *retrieved-evidence-that-actually-entails-the-claim-at-the-stated-strength* (relation, scope, modality, temporal validity, numeric specificity are the five axes they name).

5. **Per-stratum / per-criterion reliability dominates per-judge choice.** *Diagnosing LLM Judge Reliability* (conformal prediction + transitivity) finds **"criterion matters more than judge"**: some judgment types are intrinsically reliable, others not, and conformal prediction-set width is a per-item difficulty signal that agrees across judges (cross-judge r̄ = 0.32–0.38). 33–67% of documents show at least one intransitive 3-cycle even when aggregate violation looks tiny (0.8–4.1%). **Confidence: B/2.** → Report results **per stratum (TRUE/PARTIAL/FALSE) separately**, not just a global accuracy. PARTIAL is almost certainly your low-reliability stratum — expect it to drive disagreement.

---

## 2. Per-axis findings

### Axis 1 — LLM-as-judge reliability & biases

| Finding | Source | Grade |
|---|---|---|
| 9-judge panel ≈ 2 effective votes (Kish n_eff); Condorcet gap 8–22pp; best single judge ≥ panel across all conditions incl. RewardBench pairwise. Robust to prompt/temp/CoT. Bottleneck is correlated errors, not aggregation. | *Nine Judges, Two Effective Votes* (Kohli, Apple), 2026-05-29 | B/2 |
| "Evaluation faking": consequence-framing in the judge system prompt shifts verdicts up to −9.8pp (30% rel. drop in unsafe detection) with content held constant. Leniency bias when judge told low scores harm the evaluated model. | *Context Over Content* (Gupta et al.), 2026-04-16 | B/2 |
| Judge reliability is per-*criterion*, not per-*judge*. Conformal prediction-set width = per-item difficulty signal, agrees across judges (r̄ 0.32–0.38). Widespread per-input intransitivity (33–67% of docs ≥1 3-cycle) masked by low aggregate rates. | *Diagnosing LLM Judge Reliability* (Gupta & Kumar), 2026-04-16 | B/2 |
| Generative verifiers are systematically mis-calibrated on strictness (over-/under-critical); strictness is a steerable latent direction. Confirms verifiers have a *positivity/leniency bias* on step verification. | *The Hidden Signal of Verifier Strictness* (Zhou et al., Dartmouth/Salesforce/Datadog), 2026-05-20 | B/2 |
| Models verify facts more reliably than they generate them (GV-gap), but show *residual verification bias on well-covered facts* and a "multi-verse" state (verifying both old and new answers as correct after updates). | *The Future of Facts* (Davidson et al., EPFL), 2026-05-26 | B/2 |

Cross-cutting read: the newest work is consistently **anti-ensemble-as-a-cure** and **pro-criterion-design**. The 2024–25 reflex ("add a panel of judges to debias") is being directly challenged. Self-preference / position / verbosity biases remain real but the *novel* delta this window is (a) correlated-error ceiling on panels, and (b) context/stakes framing as a new bias channel.

Pre-frontier transfer flag: the conformal/transitivity and verifier-strictness papers use a mix of mid-tier and frontier judges. The *mechanisms* (intransitivity, leniency, criterion-dependence) are scale-robust per the panel paper's own ablations, so they transfer; the exact pp magnitudes may shrink on the strongest 2026 judges.

### Axis 2 — Search / RAG / retrieval eval

| Finding | Source | Grade |
|---|---|---|
| Citation laundering: relevant-but-under-warranting citations. ForceBench stress-tests evidence-force on 5 axes (relation, modality, scope, temporal validity, numeric specificity). Generic support prompting 47.2% MVR; overlap metrics violate monotonicity 33–36%; warrant-explicit prompts needed. | *Relevant Is Not Warranted / ForceBench* (Qian et al., CMU+), 2026-05-27 | B/2 |
| Retrieval-grounded claim/citation verification done well: retrieve candidate → structured LLM comparison → **calibrated 3-label decision rule** (Exact/Minor/Major). 88.7 macro-F1, beats raw GPT/Claude/Gemini incl. web-search variants. Validates a hybrid retrieve-then-structured-judge design over a bare LLM judge. | *CiteCheck* (Khajavi et al.), 2026-05-26 | B/2 |
| Search agents are a distinct, fragile threat/eval surface: unreliable search results mislead agents (ASR up to 90.5%); common prompt defenses fail. Argues search-result quality must be eval'd *separately* from the model. | *SafeSearch* (Dong et al.), 2026-05-29 | B/2 |
| Deep-research/agentic-search eval is moving from LLM-judged binary criteria to **deterministic ground-truth verifiers + SME rubric** (Verifier-Rubric Score). Explicitly replaces the LLM judge where ground truth exists; embeds "cognitive traps." | *Evaluating Deep Research Agents on Expert Consulting Work* (Deccan AI), 2026-05-19 | B/2 |
| Fine-grained, *claim-level* RAG benchmarking (vs document-level) is the current direction for high-stakes domains (law). | *Fine-grained Claim-level RAG Benchmark for Law*, 2026-05-20 | C/2 |
| Dynamic, multilingual, multi-domain misinformation benchmark designed to resist staleness/contamination. | *CommunityFact*, 2026-05-29 | C/2 |

Cross-cutting read: the field is explicitly distinguishing **"retrieved something relevant"** from **"retrieved something that entails the claim."** For a search-API bake-off that is *the* measurement — a high-recall engine that surfaces topical-but-non-entailing pages will look good to a naive judge and bad to a warrant-checking judge. No "RAGAS successor" has consolidated; the live trend is hybrid retrieve-then-structured-judge with calibrated multi-label decisions (CiteCheck) and contrastive force-calibration stress sets (ForceBench).

### Axis 3 — Small-N statistical rigor

| Finding | Source | Grade |
|---|---|---|
| Multi-task PPI: use cheap proxy (auto-judge) + few human labels to tighten CIs while staying valid; cross-task recalibration shares structure across strata/engines. Caveat (proved): gains beyond power-tuned PPI need *nonlinear* proxy↔truth structure — affine recalibration ≈ raw proxy. Case study audits LMs on election info. | *Prediction-Powered Inference Across Many Tasks* (Emmenegger, Stahler, Podimata — MIT), 2026-05-29 | B/2 |
| Spurious predictability / in-sample vs walk-forward inflation in finite samples — a reminder that small-N point estimates with many configs over-fit; relevant to "don't pick the winning engine on 60 items without correction." | *Spurious Predictability in Financial ML*, 2026-04-16 | C/2 (adjacent domain) |
| ROC/AUC calibration cautions for small, class-imbalanced eval sets (defect-prediction domain, but the AUC-instability math transfers). | *Evaluating SDP Models via AUC*, 2026-04-22 | C/1 (off-domain) |

Cross-cutting read: there is **no new paper overturning the McNemar/bootstrap/Wilson canon** in this window — that's reassuring; your chosen stats are still current best practice. The genuine *delta* is PPI maturing into a practical way to beat the small-N CI-width problem without abandoning validity. With 20 items/stratum, McNemar's exact (binomial) test is correct (don't use the chi-square approximation at this N), and Wilson > Wald for proportions near 0/1 — both already in your design.

Independent statistical sanity check (standard, not from a 2026 paper, flagged so you don't over-trust the LLM): with N=60 paired and McNemar, you can only detect fairly large differences. Discordant-pair power is the binding constraint — if two engines agree on ~50/60 items, you're testing significance on ~10 discordant pairs, where exact McNemar needs roughly an 8–2 or 9–1 split to clear p<0.05. **Pre-register that many engine pairs will be statistically indistinguishable at N=60**, and treat the eval as *screening* (rank + effect-size + CI overlap) rather than confirmatory pairwise significance.

### Axis 4 — Things that would change a search-API bake-off design

- **Against a single fixed judge:** the panel paper says panels don't fix bias, but it does *not* license a single judge — it says use a *strong* judge and validate against human gold. The conformal paper says reliability is criterion-dependent. Net: use 2–3 *diverse-family* judges to *measure disagreement* (kappa) and surface low-reliability items, but resolve TRUE/PARTIAL/FALSE against human-anchored gold on at least a subset, not by judge majority. **Grade B/2.**
- **For human-anchored gold:** CiteCheck and the Deep-Research-consulting benchmark both move toward deterministic/SME ground truth where it exists, using the LLM only for the fuzzy comparison step. **Grade B/2.**
- **For per-stratum routing over global ranking:** criterion-matters-more-than-judge + your TRUE/PARTIAL/FALSE design → report and test per stratum. PARTIAL is the hard stratum (citation-laundering lives there). **Grade B/2.**
- **For cost-normalized comparison:** no single 2026 paper mandates it, but VerifySteer (4–7× less compute for equal verification quality) and the broader "is the panel worth it" framing make **cost-per-correct-verdict** the honest axis for a *vendor* bake-off. Vendor latency/price differ ~10×; a raw-accuracy ranking that ignores cost is misleading. **Grade B/1** (inference, not a cited mandate).
- **Contamination caveat for the test set:** *LLM Benchmark Datasets Should Be Contamination-Resistant* (Al-Lawati et al., ICML, 2026-05-20) argues public eval sets are pervasively in pretraining corpora. Your N=60 claims must be **freshly authored or post-cutoff**, not lifted from SimpleQA/FEVER/public fact-check sets — otherwise both the search engines' indexes *and* the judge's parametric memory contaminate the result. **Grade B/3** (consensus-direction, multiple corroborating papers).

---

## 3. Concrete recommendations for OUR eval

**Keep:**
- Class-balanced 20/20/20 TRUE/PARTIAL/FALSE — the per-stratum design is exactly what the conformal/criterion finding endorses.
- Wilson CIs (right call near 0/1), McNemar **exact/binomial** (not chi-square at N=60), Cohen's kappa for judge agreement.
- Blind judging — but tighten it (below).
- Cross-model judge — but reinterpret its purpose (below).

**Change:**
1. **Reframe the cross-model judge from "ensemble truth" to "disagreement instrument."** Do not take majority-of-3 as ground truth (Nine Judges). Use 2 diverse-family judges to compute inter-judge kappa and flag low-agreement items; resolve the verdict against **human-anchored gold** on the full 60 (it's only 60 — hand-label them) or at minimum a stratified subset.
2. **Make the judge prompt stakes-neutral and engine-blind.** Strip any text naming the engine, implying a contest, or stating verdict consequences (Context Over Content: that alone moves verdicts ~10pp). Present only {claim, retrieved evidence} and ask for entailment.
3. **Split the judge rubric along the warrant axis (ForceBench).** Don't ask "is this supported?" Ask explicitly: does the evidence *entail the claim at its stated strength* across relation / scope / modality / temporal validity / numeric specificity? This is what separates TRUE from PARTIAL and is the dominant failure mode for search-API verification.
4. **Treat the eval as screening, not confirmatory.** Pre-register that N=60 yields wide CIs and most engine pairs won't separate by McNemar. Lead with ranks + Wilson CI overlap + effect sizes; report McNemar p-values as secondary with discordant-pair counts shown.

**Add:**
5. **Human gold on all 60** (cheap at this N) as the primary truth label; use the LLM judges only to (a) scale a sensitivity check and (b) measure judge reliability. This is the CiteCheck/Deep-Research direction.
6. **Cost-normalized reporting:** primary table = precision/accuracy per stratum *and* cost-per-correct-verdict (API $ + latency). A vendor bake-off that ignores 10× price/latency spread is not decision-grade.
7. **Contamination hygiene:** author the 60 claims fresh (or post-judge-cutoff), avoid lifting items from public fact-check/SimpleQA-style sets. Document provenance per item.
8. **(Optional, if you under-label) PPI/PPI++** to tighten CIs: human-label a subset, auto-judge the rest, rectify. Only worth it if the proxy↔human relationship is nonlinear (else it ≈ raw proxy, per the MIT proof) — and at N=60 hand-labeling everything is probably simpler than the PPI machinery. Flag as nice-to-know, not required.
9. **Per-item reliability flag:** record judge prediction-set width / disagreement per item; expect PARTIAL items to cluster as low-reliability and caveat them explicitly.

**Don't:**
- Don't scale to a 5–9 judge panel expecting it to approximate truth (correlated errors cap it at ~2 effective votes).
- Don't report a single global accuracy number — it hides the PARTIAL-stratum unreliability.
- Don't let the judge see which engine produced the evidence.

---

## 4. Sources table

| # | Title (arXiv) | Date | Axis | Provenance | Confidence | Transfer flag |
|---|---|---|---|---|---|---|
| 1 | Nine Judges, Two Effective Votes: Correlated Errors Undermine LLM Evaluation Panels (Kohli, Apple) | 2026-05-29 | 1,4 | B (preprint, industry lab) | 2 | NLI-only; mechanism general |
| 2 | Context Over Content: Exposing Evaluation Faking in Automated Judges (Gupta et al.) | 2026-04-16 | 1 | B | 2 | safety benchmarks; framing effect likely general |
| 3 | Diagnosing LLM Judge Reliability: Conformal Prediction Sets and Transitivity Violations (Gupta & Kumar) | 2026-04-16 | 1,4 | B | 2 | SummEval; criterion-dependence transfers |
| 4 | The Hidden Signal of Verifier Strictness (Zhou et al., Dartmouth/Salesforce/Datadog) | 2026-05-20 | 1 | B | 2 | step-verification; leniency bias general |
| 5 | The Future of Facts: Tracing the Factual Generation-Verification Gap (Davidson et al., EPFL) | 2026-05-26 | 1,2 | B | 2 | open models; residual-bias caution |
| 6 | Relevant Is Not Warranted / ForceBench (Qian et al., CMU+) | 2026-05-27 | 2,4 | B | 2 | directly on-target for claim-verification |
| 7 | CiteCheck: Retrieval-Grounded Detection of LLM Citation Hallucinations (Khajavi et al.) | 2026-05-26 | 2,4 | B | 2 | physics citations; design pattern transfers |
| 8 | SafeSearch: Automated Red-Teaming of LLM-Based Search Agents (Dong et al.) | 2026-05-29 | 2 | B | 2 | safety-focused; "eval search separately" transfers |
| 9 | Evaluating Deep Research Agents on Expert Consulting Work (Deccan AI) | 2026-05-19 | 2,4 | B (vendor-authored — note self-interest) | 2 | deterministic-verifier direction transfers |
| 10 | Prediction-Powered Inference Across Many Tasks for AI Evaluation (Emmenegger/Stahler/Podimata, MIT) | 2026-05-29 | 3,4 | B | 2 | method, validity-preserving; transfers |
| 11 | LLM Benchmark Datasets Should Be Contamination-Resistant (Al-Lawati et al., ICML) | 2026-05-20 | 2,4 | B | 3 | consensus-direction, multi-paper corroboration |
| 12 | Fine-grained Claim-level RAG Benchmark for Law | 2026-05-20 | 2 | C | 2 | legal domain; direction transfers |
| 13 | CommunityFact: Dynamic Multilingual Misinformation Benchmark | 2026-05-29 | 2 | C | 2 | anti-staleness design relevant |
| 14 | Spurious Predictability in Financial ML | 2026-04-16 | 3 | C | 2 | adjacent domain; overfitting caution |

Provenance ceiling note: all are arXiv preprints (≤ B). Source 9 is vendor-authored (Deccan AI) — its "LLM judges are bad, use our deterministic verifiers" framing is self-interested; the methodological direction is corroborated by CiteCheck (independent), so I weight the *direction* not the vendor's superiority claim. No peer-reviewed venue confirmation yet for any single-paper finding — treat #1–#7 as "single recent strong paper," not established consensus. The only **consensus-grade** items are contamination-resistance (#11, multi-paper) and the general anti-naive-ensemble direction (#1 + prior 2025 correlated-error work it cites).
