# Divergent Research: Beyond Causal DAGs — What Else Should We Build?

**Date:** 2026-03-06
**Tier:** Deep | **Axes:** 4 (causal discovery, reasoning verification, analogical/scientific, temporal/metacognitive)
**Method:** 4 parallel research agents → 30 papers saved → Gemini synthesis across corpus → manual integration
**Ground truth:** Extends `ai-reasoning-causal-abductive-deductive.md` (the causal scaffolding memo)

---

## Executive Summary

We built DAG validation + hook + skill scaffolding for causal reasoning. This memo explores what's **adjacent and unbuilt**. Five high-ROI opportunities emerged:

1. **Sensitivity analysis** (PySensemakr) — quantify DAG misspecification robustness. Ready now.
2. **LLM-augmented causal discovery** (causal-learn + LLM priors) — suggest DAGs from data. Usable with caveats.
3. **Generative PRMs** (ThinkPRM) — verify reasoning steps beyond math. Promising but not deployable yet.
4. **Metacognitive prompting** (Think²) — 3x improvement in self-correction. Cheap to try.
5. **Temporal gates** — LLMs fail hard on counterfactual temporal reasoning. Our existing DAG temporal ordering is more valuable than we thought.

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| C1 | PySensemakr implements Cinelli-Hazlett OVB framework in Python, works with statsmodels OLS | Library docs, pip-installable | HIGH | [pysensemakr.readthedocs.io] | VERIFIED |
| C2 | causal-learn (CMU) implements PC, FCI, GES, NOTEARS, LiNGAM in pure Python | arXiv:2307.16405, pip-installable | HIGH | [Zheng et al. 2023] | VERIFIED |
| C3 | Causal-Copilot integrates 20+ causal methods into LLM agent, automates discovery+inference pipeline | arXiv:2504.13263, live demo at causalcopilot.com | MEDIUM | [Wang et al. 2025, 7 cites] | VERIFIED-ABSTRACT |
| C4 | LLM-Driven Causal Discovery via Harmonized Prior: LLM priors on single-aspect causal questions (not pairwise) improve structure learning on real data | IEEE TKDE 2025 | MEDIUM | [Ban et al. 2025, 21 cites] | VERIFIED-ABSTRACT |
| C5 | "LLM Cannot Discover Causality" — LLMs should be restricted to non-decisional support in causal discovery | arXiv, 3 cites | MEDIUM | [ffd1939e, 2025] | VERIFIED-ABSTRACT |
| C6 | ThinkPRM: generative PRM using 1% of PRM800K labels outperforms discriminative PRMs; +8% on GPQA-Diamond, +4.5% on LiveCodeBench (out-of-domain) | arXiv:2504.16828, code released | HIGH | [Khalifa et al. 2025, 56 cites] | VERIFIED-ABSTRACT |
| C7 | CRV (Circuit-based Reasoning Verification): white-box method finds structural signatures of reasoning errors in attribution graphs; domain-specific error patterns | arXiv:2510.09312 | MEDIUM | [Zhao et al. 2025, 3 cites] | VERIFIED-ABSTRACT |
| C8 | Think² (grounded metacognition): Ann Brown's regulatory cycle as structured prompting → 3x increase in successful self-correction, 84% human preference for trustworthiness | arXiv:2602.18806 | MEDIUM | [Elenjical et al. 2026, 0 cites] | [PREPRINT] |
| C9 | GPT-4 analogical reasoning: 0.452 accuracy on letter-string analogies vs human 0.753; drops to ~0.1 on symbolic alphabets | Lewis & Mitchell 2024, 40 cites | HIGH | [b69ae70a] | VERIFIED-ABSTRACT |
| C10 | AI Scientist v2: 1/3 papers accepted at ICLR workshop (scores 6,7,6); but 57% train/test overlap, hallucinated figure captions | Yamada et al. 2025, 139 cites | HIGH | [39983a80] | VERIFIED-FULL-TEXT |
| C11 | ScienceAgentBench: Claude 3.5 Sonnet best at 34.3% (self-debug + knowledge); o1-preview 42.2%; primary failure = data loading (25% can't even load data) | Chen et al. 2024, 67 cites | HIGH | [45b7c744] | VERIFIED-FULL-TEXT |
| C12 | Confidence elicitation unreliable: models consistently over-confident; sample consistency (15 passes, measure agreement) gives ROC AUC 0.68-0.79 | Savage 2024 | MEDIUM | [via Gemini synthesis] | [TRAINING-DATA] |
| C13 | FunSearch (DeepMind): LLM + evolutionary search produced genuinely novel mathematical results (cap sets, bin packing) | Nature 2024, 705 cites | HIGH | [d32ba885] | VERIFIED-ABSTRACT |
| C14 | Med-PRM: medical reasoning with stepwise guideline-verified process rewards | arXiv, 13 cites | LOW | [1585c43b] | VERIFIED-ABSTRACT |
| C15 | Robin: multi-agent system for scientific discovery, 49 cites | 2025 | MEDIUM | [799017d2] | SAVED-NOT-READ |
| C16 | Recursive Causal Discovery (JMLR 2025): removable variables reduce problem size, fewer CI tests, near-optimal worst case | JMLR 26, 2025 | HIGH | [Mokhtarian et al. 2025] | [SOURCE: jmlr.org] |

---

## Axis 1: Causal Discovery — Can Agents Learn DAGs From Data?

### What exists now

**causal-learn** (CMU, pip-installable) is the practical toolkit. Implements:
- **Constraint-based:** PC (fastest, assumes no latent confounders), FCI (handles latent variables), CD-NOD
- **Score-based:** GES (greedy equivalence search), exact search
- **Functional:** NOTEARS (continuous optimization, differentiable), LiNGAM (non-Gaussian)
- **Hidden causal representation:** various methods

`[SOURCE: arXiv:2307.16405, Zheng et al. 2023]`

**Practical reality:** PC algorithm skeleton (undirected graph) is often accurate; edge orientation is the hard part and frequently wrong. `[SOURCE: Salesforce CausalAI docs]`

**Causal-Copilot** automates the full pipeline — discovery, inference, algorithm selection, hyperparameter optimization — via LLM agent. 20+ methods integrated. Live demo at causalcopilot.com. 7 citations, very new. `[SOURCE: arXiv:2504.13263]`

### LLM priors for discovery

Three papers converge on a finding: **LLMs can provide useful structural priors but cannot do causal discovery alone.**

- **Harmonized Prior** (Ban et al. 2025, TKDE, 21 cites): Instead of asking LLM for pairwise causal judgments, ask single-aspect questions (temporal order, common cause existence, etc.) separately, then combine into structural constraints. Significantly improves PC/GES on real data. `[VERIFIED-ABSTRACT]`

- **LLM-Initialized Differentiable Causal Discovery** (2024, 4 cites): Use LLM to initialize NOTEARS optimization. Helps convergence. `[VERIFIED-ABSTRACT]`

- **"LLM Cannot Discover Causality"** (2025, 3 cites): Argues LLMs should be restricted to non-decisional support — providing priors, not making causal judgments. `[VERIFIED-ABSTRACT]`

### What we should build

**Tool: `dag_suggest.py`** — Given a dataset + variable descriptions, run causal-learn PC algorithm to produce a candidate DAG skeleton, then use LLM priors (temporal ordering, domain knowledge) to orient edges. Output: suggested DAG for human validation via existing `/causal-dag` skill.

**Integration pattern:**
1. Agent describes variables to LLM → temporal ordering + domain priors
2. `causal-learn` PC algorithm on data → skeleton
3. Combine priors + skeleton → oriented candidate DAG
4. Human validates via `/causal-dag` Phase 2
5. `dag_check.py` validates adjustment set

**Effort:** ~1 day. `causal-learn` is pip-installable, pure Python.
**Risk:** False confidence if agent treats suggested DAG as ground truth. Must be clearly labeled as SUGGESTION.

---

## Axis 2: Sensitivity Analysis — Quantifying Robustness

### The gap

Our current scaffolding validates a DAG but doesn't answer: **"How wrong could the DAG be before our conclusions change?"** This is the sensitivity analysis gap.

### PySensemakr (ready now)

Python implementation of Cinelli & Hazlett (2020) OVB framework. `pip install PySensemakr`.

**What it does:**
- Takes a statsmodels OLS result
- Computes **Robustness Value (RV):** how strong would an omitted confounder need to be (in terms of partial R²) to reduce the effect to zero or make it non-significant
- Produces contour plots showing bias as function of confounder strength
- Benchmarks against observed covariates: "An omitted confounder would need to be X times as strong as [education] to explain away the effect"

`[SOURCE: pysensemakr.readthedocs.io, Cinelli & Hazlett 2020]`

### What we should build

**Phase 6 for `/causal-dag` skill:** After regression specification (Phase 5), automatically run sensitivity analysis.

```
Phase 6: Sensitivity Analysis
  - Compute Robustness Value
  - Benchmark against observed confounders
  - Report: "An omitted confounder would need to explain ≥X% of
    residual variance of both treatment and outcome to change conclusions"
  - If RV < 1x strongest observed covariate: FLAG as fragile
```

**Effort:** ~2 hours. PySensemakr wraps statsmodels directly.
**Risk:** Low. This is purely additive — never changes the estimate, just quantifies fragility.

---

## Axis 3: Reasoning Verification — Can We Check Agent Reasoning?

### Process Reward Models (PRMs)

**ThinkPRM** (Khalifa et al. 2025, 56 cites) is the headline finding:
- Generative PRM that produces a verification chain-of-thought
- Trained on only **1% of PRM800K labels** — radically data-efficient
- Outperforms discriminative PRMs on ProcessBench, MATH-500, AIME'24
- **Out-of-domain:** +8% on GPQA-Diamond (science), +4.5% on LiveCodeBench (code)
- Open-source: github.com/mukhal/thinkprm

`[SOURCE: arXiv:2504.16828]`

**Key insight:** ThinkPRM works by generating verbal verification ("Let me check step 3..."), not by learned classification. This means it leverages the reasoning model's own capabilities for verification. It scales better than LLM-as-Judge under fixed compute budget (+7.2% on ProcessBench).

**Med-PRM** (2025, 13 cites): Medical reasoning with guideline-verified process rewards. Shows PRMs CAN extend beyond math to clinical reasoning. `[VERIFIED-ABSTRACT]`

### White-box verification (CRV)

Circuit-based Reasoning Verification (Zhao et al. 2025): analyzes attribution graphs of correct vs incorrect CoT steps. Finds **domain-specific structural fingerprints of errors** — failures in different reasoning tasks create distinct computational patterns. Can even correct errors by intervening on specific features.

**Practical for us?** No — requires model internals access. But the finding is important: reasoning errors have structural signatures, they're not random.

### What we should build

**Near-term (cheap):** Use ThinkPRM-style verification as a second pass on causal reasoning:
1. Agent produces DAG + adjustment set reasoning
2. Second call asks model to verify each step: "Check: is education really pre-treatment? Is items_complete really a descendant?"
3. Flag disagreements

This is basically a structured self-consistency check. No new infrastructure needed — just a verification prompt template in the `/causal-dag` skill.

**Medium-term:** If ThinkPRM releases a version fine-tuned on scientific reasoning, integrate it as a verification step.

---

## Axis 4: Analogical Reasoning — The Hardest Gap

### Current state

**GPT-4 analogical reasoning is shallow.** Lewis & Mitchell (2024, 40 cites) tested letter-string analogies:
- Humans: **0.753** accuracy across all conditions
- GPT-4: **0.452** overall, drops to **~0.1** on symbolic (non-letter) alphabets
- GPT-4 relies on **approximate retrieval** from training data, not structural mapping
- 32.67% of GPT-4 errors: applied a related but wrong rule

`[SOURCE: b69ae70a, verified full text via Gemini]`

**Emergent analogical reasoning** (Webb et al. 2022, 446 cites) claimed GPT-3 showed emergent analogy. Lewis & Mitchell's counterfactual tests showed this was largely pattern matching, not genuine structural analogy.

### Scientific discovery agents

**AI Scientist v2** (Yamada et al. 2025, 139 cites):
- 1/3 papers accepted at ICLR workshop (scores 6, 7, 6)
- BUT: 57% train/test overlap in experiments, hallucinated figure captions, confused embedding vs hidden states
- The accepted paper was a **negative result** — regularization didn't help
- Agentic tree search architecture with experiment progress manager

**ScienceAgentBench** (Chen et al. 2024, 67 cites):
- Best: Claude 3.5 Sonnet at **34.3%** (self-debug + expert knowledge)
- o1-preview: **42.2%** (reference)
- **Primary failure: data loading** — 25% of failures can't even load data correctly
- Agents fail on specialized libraries (Geopandas, Biopsykit) — hallucinate API calls
- Success drops sharply with task complexity (>58 LoC)

**FunSearch** (DeepMind, Nature 2024, 705 cites): evolutionary search over LLM-generated programs. Produced **genuinely novel mathematical results** (cap sets, bin packing). Key: the LLM generates candidate solutions, an evaluator scores them, evolution selects. The LLM doesn't "discover" — it generates variation for search.

### What this means for us

Analogical reasoning scaffolding is premature. The capability gap is too large (GPT-4 at 0.452 vs human 0.753, and that's on simple letter analogies). No practical framework exists.

**However:** FunSearch's pattern is interesting — LLM as hypothesis generator + deterministic evaluator. Our `dag_check.py` is already a deterministic evaluator. We could build:
- Agent generates multiple candidate DAGs
- `dag_check.py` evaluates each
- Best-of-N selection on adjustment set validity

---

## Axis 5: Temporal Reasoning + Metacognition

### Temporal reasoning

Three benchmarks saved (TimeBench, TRAM, "LLMs Can Learn Temporal Reasoning") but agents didn't fetch full text. From abstracts and training data:

- Temporal reasoning is a **known weakness** of LLMs `[TRAINING-DATA]`
- Fine-tuning can improve temporal reasoning (5ff337e, 165 cites) `[VERIFIED-ABSTRACT]`
- Our existing Phase 1 (temporal ordering in variable classification) is more valuable than we realized — it compensates for a real LLM weakness

### Metacognitive monitoring

**Think² (Elenjical et al. 2026):** Operationalizes Ann Brown's regulatory cycle (Planning → Monitoring → Evaluation) as structured prompting:
- **3x increase in successful self-correction** on Llama-3/Qwen-3 (8B models)
- **84% human preference** for trustworthiness over standard/CoT baselines
- Uses a dual-process MetaController for adaptive effort allocation

`[SOURCE: arXiv:2602.18806] [PREPRINT, 0 cites, tested on 8B models — pre-frontier evidence]`

**Sample consistency** (Savage 2024): Running 15 passes and measuring agreement gives ROC AUC **0.68-0.79** for detecting errors. Better than asking the model to rate its own confidence. `[TRAINING-DATA]`

### What we should build

**Think²-style regulatory prompting for causal reasoning:**

Add to `/causal-dag` skill:
```
Phase 4b: Self-Check (Metacognitive Audit)
  PLAN: "I will verify each edge direction and each variable classification"
  MONITOR: For each edge, re-examine: "Is [A -> B] temporally ordered?
           Could the arrow be reversed? What evidence supports this direction?"
  EVALUATE: "Which classifications am I least confident about?
            What would change if those edges were wrong?"
```

Cost: zero (prompt-only). Expected benefit: catches temporal ordering errors like `education -> sex` before they propagate.

---

## Priority-Ranked Build List

| # | What | Value | Maintenance | Composability | Rationale |
|---|------|-------|-------------|---------------|-----------|
| 1 | **PySensemakr integration** — Phase 6 for `/causal-dag` | HIGH | None (pure library) | High — any OLS workflow | Ready now, pure additive, quantifies DAG fragility |
| 2 | **Metacognitive audit** — Phase 4b self-check prompt | MEDIUM | None (prompt) | Medium — causal skill only | Zero-cost prompt addition, catches temporal errors |
| 3 | **Verification prompt** — ThinkPRM-style second-pass check | MEDIUM | None (prompt) | Medium — any reasoning skill | Structured self-consistency for DAG reasoning |
| 4 | **`dag_suggest.py`** — causal-learn PC + LLM priors | MEDIUM | Low (pip dep) | High — feeds dag_check.py | Data-driven DAG suggestion, high false-confidence risk |
| 5 | **Best-of-N DAGs** — generate multiple, evaluate with dag_check.py | LOW-MED | None | Medium — FunSearch pattern | FunSearch pattern applied to causal specification |
| 6 | **DoWhy backend for dag_check.py** — replace custom backdoor check with DoWhy's 4 strategies + ID algorithm | HIGH | Low (mature library v0.14) | High — optimal adjustment sets | Mature library, replaces custom code with maintained dependency |

### Deferred (prerequisites missing)

| What | Prerequisite / Blocker |
|------|----------------------|
| Analogical reasoning scaffolding | Capability gap too large (GPT-4: 0.45 vs human: 0.75) — wait for frontier improvement |
| PRM integration for causal reasoning | No domain-specific PRM exists yet; ThinkPRM is math-focused |
| White-box CRV verification | Requires model internals access (not available) |
| Full Causal-Copilot integration | causal-learn alone is sufficient; Copilot adds maintenance for no composability gain |
| interwhen-style interleaved verification | Preprint only (Microsoft Research, Feb 2026) — no production implementation |

---

## What's Uncertain

1. **Think² tested on 8B models only.** Will the 3x self-correction improvement hold on frontier models that already have some metacognitive ability? Unknown.
2. **LLM priors for causal discovery** — the Harmonized Prior paper shows improvement on benchmarks, but real-world DAGs may be more adversarial than benchmark DAGs.
3. **PySensemakr assumes linear models.** Our current scaffolding doesn't constrain functional form — sensitivity analysis for nonlinear models is much harder.
4. **ThinkPRM's out-of-domain performance** (+8% GPQA) is promising but not tested on causal reasoning specifically.

---

## Papers Saved to Corpus (30 total)

Key new papers from this session:
- Causal-Copilot (9a2024c0), LLM-Driven Causal Discovery Harmonized Prior (3658e58d)
- ThinkPRM (f38c5beb), Med-PRM (1585c43b), CRV computational graph verification (19a52c55)
- Think² metacognition (8edf5087), Counterfactual analogies (b69ae70a)
- AI Scientist v2 (39983a80), ScienceAgentBench (45b7c744), FunSearch (d32ba885)
- Robin multi-agent discovery (799017d2), Emergent analogical reasoning (3cbffab9)
- TimeBench (f37d1ef3), TRAM (811f451f), LLMs Can Learn Temporal (5ff337e9)
- Recursive Causal Discovery (JMLR 2025, via web search)

---

## Companion Memo

Full reasoning verification deep-dive (Axis 3 expanded): `reasoning-trace-verification.md`

Key findings from that memo not duplicated here:
- **DoWhy v0.14** provides 4 backdoor strategies, ID algorithm, front-door criterion, optimal adjustment sets — should replace dag_check.py backend
- **VRPM** (rule-based verifiers): +20% F1 over neural PRMs in structured domains — validates our dag_check.py architectural approach
- **interwhen** (Microsoft Research, Feb 2026): interleave generation with verification at controllable granularity — natural fit for DAG construction
- **No PRM targets causal reasoning** — confirmed negative result across extensive search
- **Self-consistency has special power for causal reasoning** because conclusions are formally verifiable (generate 5 DAGs, formally check each, vote among those that pass)
- **Verification gap is in DAG CONSTRUCTION, not DAG ANALYSIS** — formal tools verify adjustment sets with certainty; no tool verifies "is this DAG correct?"

<!-- knowledge-index
generated: 2026-03-21T23:52:37Z
hash: 01e7bc9d5fb3

table_claims: 16

end-knowledge-index -->
