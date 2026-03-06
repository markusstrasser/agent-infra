# Verifying Agent Reasoning Traces: Faithfulness, Correctness, and Formal Methods

*Date: 2026-03-05. Models in scope: Opus 4.6, GPT-5.x, Gemini 3.1 Pro.*
*Context: We built causal scaffolding (DAG skills, hooks, validator). Question: how to verify the agent reasons correctly WITHIN that structure.*

---

## Question

How can we verify that an agent's reasoning trace is faithful and correct? Specifically: correct DAG but wrong adjustment set, correct mediator identification but wrong classification, etc.

## Tier: Deep | Axes: 4

**Ground truth inventory:**
- CoT faithfulness memo exists (`cot-faithfulness-evidence.md`): 7-13% baseline unfaithfulness on clean prompts
- VersaPRM, GenPRM, PRISM, Socratic-PRMBench already in corpus
- Cross-model review failure modes documented (`cross-model-review-failure-modes.md`)
- We built `dag_check.py` for backdoor criterion validation

---

## Axis 1: Process Reward Models (PRMs) — Current State 2025-2026

### What exists beyond math

**Recitation of key evidence before synthesis:**

1. **VersaPRM** (Zeng et al., ICML 2025, arXiv:2502.06737, 22 cites): First multi-domain PRM. Trained on synthetic CoT data across MMLU-Pro categories (Law, Philosophy, Biology, Chemistry, CS, Engineering, Physics). Law: +7.9% over majority voting baseline vs Qwen2.5-Math-PRM's +1.3%. Open-source. [SOURCE: arXiv:2502.06737, ICML 2025 proceedings] [VERIFIED in corpus]

2. **ThinkPRM** (Khalifa et al., Apr 2025, arXiv:2504.16828, 56 cites): Generative PRM — produces verification chain-of-thought rather than scalar scores. Uses only 1% of PRM800K labels (~8K). Surpasses discriminative verifiers by 8% on GPQA-Diamond (out-of-domain). Outperforms LLM-as-Judge by 7.2% on ProcessBench under equal token budget. Open-source: github.com/mukhal/ThinkPRM. [SOURCE: arXiv:2504.16828] [VERIFIED via Exa /answer]

3. **GenPRM** (Zhao et al., Apr 2025, arXiv:2504.00891, 56 cites): Explicit CoT reasoning + code verification for each step. 1.5B GenPRM outperforms GPT-4o; 7B outperforms Qwen2.5-Math-PRM-72B on ProcessBench. Open-source. [SOURCE: arXiv:2504.00891] [IN CORPUS]

4. **Med-PRM** (Yun et al., EMNLP 2025, arXiv:2506.11474, 13 cites): First domain-specific PRM with retrieval-augmented verification against medical knowledge bases. Plug-and-play: improves base models AND fine-tuned systems. 8B model surpasses 80% on MedQA for first time. Average +2.44% across 7 medical benchmarks. [SOURCE: arXiv:2506.11474, ACL Anthology] [SAVED to corpus]

5. **VRPM** (Pronesti et al., Jan 2026, arXiv:2601.17223): Verifiable PRMs — replaces neural scoring with deterministic rule-based verifiers for structured domains (risk-of-bias assessment). +20% F1 over SOTA, +6.5% over verifiable outcome rewards. [SOURCE: arXiv:2601.17223] [PREPRINT]

6. **CRV — Circuit-based Reasoning Verification** (Zhao et al., Meta FAIR, Oct 2025, arXiv:2510.09312, 3 cites): White-box approach. Extracts attribution graphs of correct vs incorrect CoT steps, trains classifier on structural features. Novel: identifies WHY a computation fails, not just whether. [SOURCE: arXiv:2510.09312] [SAVED to corpus]

### Can PRMs verify frontier model outputs?

**ReasonFlux-PRM** (Zou et al., NeurIPS 2025, arXiv:2506.18896): Designed specifically for long CoT from reasoning models (DeepSeek-R1 style). Dual-level supervision: step-level + trajectory-level. 7B model outperforms Qwen2.5-Math-PRM-72B on AIME (+12.1% in SFT data selection). [SOURCE: arXiv:2506.18896]

**Critical counter-evidence — DeepSeek-R1's rejection of neural PRMs:** DeepSeek-R1 (arXiv:2501.12948) explicitly chose NOT to use neural PRMs during large-scale RL, citing reward hacking vulnerability. They use rule-based rewards instead. This is the strongest deployed signal that neural PRMs don't scale for frontier model training. [SOURCE: arXiv:2501.12948]

### PRMs for causal reasoning specifically

**No published PRMs target causal reasoning or DAG verification.** This is a confirmed gap. [NEGATIVE RESULT]

The closest analog is VRPM's rule-based approach — for causal reasoning, deterministic checks (d-separation, backdoor criterion) are the natural "rule-based verifier" that could replace neural scoring.

### Robustness concerns

**Socratic-PRMBench** (in corpus): Best open-source PRM (Qwen2.5-Math-PRM) scores only 68.0% overall. Substantial performance gaps across reasoning pattern types. [SOURCE: arXiv:2505.23474]

**PRMProbe**: PRMs show reasonable invariance to rephrasing but fail to detect numerical inconsistencies, question shuffling, and hallucinated reasoning steps — they learn surface-level cues, not semantic understanding. [SOURCE: OpenReview]

### Axis 1 assessment for our use case

| Approach | Deployable now? | Works for causal reasoning? | Open-source? |
|----------|----------------|---------------------------|-------------|
| ThinkPRM | YES | Partially — generative verification generalizes | YES (github) |
| VersaPRM | YES | Partially — trained on diverse domains but not causal | YES |
| Med-PRM | YES | NO — medical knowledge bases only | YES |
| VRPM (rule-based) | YES — pattern fits | YES — our dag_check.py IS this | Concept yes |
| GenPRM | YES | Partially — code verification component helps | YES |
| CRV (white-box) | NO — requires model internals | Unclear | NO |

**Key insight:** For causal reasoning, VRPM's approach (rule-based verification) is more appropriate than neural PRMs. Our `dag_check.py` is already a rule-based PRM. The neural PRM ecosystem adds value for the NON-formalizable reasoning steps (e.g., "is this variable a confounder?" requires domain knowledge, not graph theory).

---

## Axis 2: Reasoning Trace Verification Without PRMs

### CoT faithfulness — current state

**Recitation:**
- ICLR 2026 submission: 7-13% unfaithful on clean prompts (GPT-4o-mini 13%, Haiku 3.5 7%) [EXISTING CORPUS]
- Oxford "CoT Is Not Explainability" (2025): Faithful = procedurally correct AND accurately reflects decision process. Current CoT satisfies neither reliably. [EXISTING CORPUS]
- FUR (EMNLP 2025): "Parametric faithfulness" — erasing info from reasoning steps in parameters measures effect on predictions. New methodology. [EXISTING CORPUS]
- Active debate: counter-paper "Is CoT Really Not Explainability?" (arXiv:2512.23032) argues CoT can be faithful without explicit hint verbalization. [EXISTING CORPUS]

**New finding — One-Token Verification (OTV)** (arXiv:2603.01025, Mar 2026): Estimates reasoning correctness in a single forward pass via a learnable token + LoRA. Activated during generation. Addresses latency of multi-sample verification. [SOURCE: arXiv:2603.01025] [PREPRINT] [FRONTIER]

**New finding — Uncertainty Heads** (ICLR 2026 submission, withdrawn): Lightweight uncertainty heads for step-level verification — cheaper than full PRMs. Framing: uncertainty quantification as verification proxy. [SOURCE: OpenReview svQuvBYaCA] [WITHDRAWN — treat as idea, not evidence]

### Self-consistency / majority voting for causal reasoning

**Self-consistency (Wang et al., 2023)** remains the simplest effective approach. Generate N reasoning traces, take majority vote on the answer. Improvements:
- **Ranked voting** (ACL 2025 Findings): Generate ranked answers per trial, use Borda count / IRR / MRR across responses. Outperforms standard majority voting. [SOURCE: ACL Anthology 2025.findings-acl.744]
- **MACA** (ICLR 2026 submission): Multi-Agent Consensus Alignment — RL post-training to favor trajectories aligned with majority consensus from multi-agent debate. Richer signals than single-round voting. [SOURCE: OpenReview, under review]

**For causal reasoning specifically:**
- **Baldo et al. (arXiv:2412.14019, revised Jul 2025):** "Retrieving Classes of Causal Orders with Inconsistent Knowledge Bases" — addresses LLM inconsistency in causal ordering. Generates multiple causal orderings, identifies maximally consistent subsets. Directly relevant: treats LLM causal outputs as noisy signals requiring consensus. [SOURCE: arXiv:2412.14019]
- **CRAwDAD** (arXiv:2511.22854): "Causal Reasoning Augmentation with Dual-Agent Debate" — two agents debate causal claims. [SOURCE: arXiv:2511.22854] [PREPRINT]

### Cross-model verification for reasoning steps

From our existing research (`cross-model-review-failure-modes.md`):
- Cross-family verification adds real value: FINCH-ZK shows cross-family improver (Llama correcting Claude) = 90.4% vs 59.1% same-model [EXISTING CORPUS]
- Same-model debate is a martingale — doesn't improve expected correctness [EXISTING CORPUS]
- But: ~60% wrong-answer agreement across models (correlated errors) [EXISTING CORPUS]

**New — interwhen** (arXiv:2602.11202, Microsoft Research): Test-time verification framework. Ensures output is valid w.r.t. a given set of verifiers. Key design: interleaves generation with verification at controllable granularity — verify partial output before continuing. Directly applicable: could interleave DAG construction with d-separation checks. [SOURCE: arXiv:2602.11202] [PREPRINT]

**New — "Evaluating Step-by-step Reasoning Traces: A Survey"** (Lee & Hockenmaier, EMNLP 2025 Findings): Comprehensive taxonomy of evaluation criteria: factuality, validity, coherence, utility. Reviews datasets, evaluator implementations. The canonical reference for this field. [SOURCE: ACL Anthology 2025.findings-emnlp.94]

### Axis 2 assessment for our use case

| Approach | Deployable now? | Effectiveness for causal | Cost |
|----------|----------------|------------------------|------|
| Self-consistency (N=5-10) | YES | HIGH for structural answers | 5-10x inference |
| Cross-model verification | YES | MEDIUM (correlated errors) | 2x inference |
| interwhen-style interleaving | 3 months | HIGH — natural fit | 1.5-2x inference |
| OTV (one-token) | NO — requires training | Unknown for causal | Low at inference |

**Key insight for causal reasoning:** Self-consistency is high-value because causal reasoning has VERIFIABLE answers. If the agent generates 5 DAGs and identifies adjustment sets, we can formally check which are correct. The vote isn't over opinions — it's over formally checkable claims.

---

## Axis 3: Formal Verification of Causal Claims

### Existing tools for automated causal verification

**This is where we have the strongest deployable advantage.** Unlike most LLM reasoning domains, causal claims about DAGs are formally verifiable.

#### Tool landscape

| Tool | Language | Key capabilities | Maturity | Relevance |
|------|----------|-----------------|----------|-----------|
| **DoWhy** (pywhy.org) | Python | `identify_effect()` with 4 backdoor strategies (maximal, minimal, exhaustive, efficient). ID algorithm (Shpitser-Pearl). Front-door criterion. Full causal pipeline. | v0.14, very mature | **PRIMARY** — can validate any adjustment set claim |
| **dagitty** | R + web | d-separation testing, testable implications, adjustment sets, interactive DAG editor. Textor 2021 protocol paper. | Mature, academic standard | **PRIMARY** for d-separation checks |
| **ananke** | Python | ADMGs, CADMGs, fixing operators, canonical DAG construction, identification algorithms. Focus on graphs with hidden variables. | Moderate | Useful for complex graphs with latent variables |
| **pcalg** | R | `backdoor()` function for generalized backdoor criterion on PAGs. Discovery + validation. | Very mature | Standard for PAG-based analysis |
| **CIfly** | Python + R | Declarative framework — algorithms specified in rule tables. Rust backend, linear-time. | New (2024-2025) | Fast d-separation, modern design |
| **CausalTestingFramework** | Python | Causal testing using DAGs. v14.1.0 (Aug 2025). MIT license. | Active development | Testing-focused — good for CI/CD integration |
| **causaldag** | Python | DAG operations, interventions, Markov equivalence classes | Moderate | Lightweight alternative |
| Our **dag_check.py** | Python | Backdoor criterion validation, d-separation | Custom | Already integrated |

#### What can be formally verified

Given a DAG stated by the agent, these are DECIDABLE questions:

1. **"Is Z a valid adjustment set for the effect of X on Y?"** — DoWhy `identify_effect()` or pcalg `backdoor()`. Our `dag_check.py` does this.
2. **"What is the minimal/optimal adjustment set?"** — DoWhy's `efficient-adjustment` mode (Smucler & Rotnitzky, Biometrika 2022).
3. **"Is X d-separated from Y given Z?"** — dagitty, DoWhy, ananke, CIfly. All implement this.
4. **"Does the stated DAG imply testable conditional independencies?"** — dagitty `impliedConditionalIndependencies()`. Can check against data.
5. **"Is the causal effect identifiable from observational data?"** — DoWhy ID algorithm (Shpitser-Pearl 2006).
6. **"Is M a mediator on the path from X to Y?"** — d-separation after removing direct X->Y edge.
7. **"Does the agent's adjustment set contain a collider descendant?"** — Graph traversal. Both dagitty and DoWhy detect this.

#### What CANNOT be formally verified (requires domain knowledge)

1. **"Is this DAG correct?"** — The DAG itself encodes assumptions. No formal method validates assumptions against reality without data or domain expertise.
2. **"Should this variable be in the DAG at all?"** — Completeness is a domain question.
3. **"Is the functional form correct?"** — Linear vs nonlinear, interactions, etc.
4. **"Is this edge direction correct?"** — Requires temporal/domain knowledge.

### Recommended architecture: formal verification layer

```
Agent reasoning trace
    |
    v
[1] Parse DAG from agent output (structured output or regex)
    |
    v
[2] Validate graph structure (acyclicity, connectedness)
    |
    v
[3] For each causal claim:
    |-- "Adjust for {Z}" --> DoWhy: check backdoor criterion
    |-- "X causes Y"     --> Check path exists in DAG
    |-- "M mediates X->Y" --> Check M on directed path X->...->Y
    |-- "No confounding"  --> DoWhy: check if effect identified without adjustment
    |
    v
[4] Compare agent's stated adjustment set vs DoWhy's optimal set
    |-- Match: PASS
    |-- Subset: WARN (valid but suboptimal)
    |-- Superset with collider descendants: FAIL
    |-- Disjoint: FAIL
    |
    v
[5] Report: which claims are formally valid, which need review
```

This is a **deterministic verifier** — no neural network, no probabilistic judgment. It either passes or fails. This is the VRPM pattern applied to causal reasoning.

---

## Axis 4: Calibration of Causal Claims

### How confident should an agent be in causal conclusions?

Two distinct uncertainty sources:

1. **Structural uncertainty** — Is the DAG correct? (Which edges exist?)
2. **Parametric uncertainty** — Given the DAG, what's the effect size?

#### Bayesian Model Averaging over DAGs

**Recitation of key evidence:**

- **Kaplan & Lee (2016, 24 cites):** BMA over DAGs for predictive performance of SEMs. Foundational methodological work. [SOURCE: S2, DOI:10.1080/10705511.2015.1092088]
- **Toth et al. (AISTATS 2025, arXiv:2402.14781, 7 cites):** "Effective Bayesian Causal Inference via Structural Marginalisation and Autoregressive Orders." Addresses epistemic model uncertainty by marginalizing over DAG structures rather than selecting one. [SOURCE: arXiv:2402.14781]
- **ProDAG** (Thompson et al., arXiv:2405.15167, 1 cite): Projected variational inference for DAGs. Addresses computational challenge of posterior over DAG space. [SOURCE: arXiv:2405.15167]
- **cyclinbayes** (Lee et al., 2026, arXiv:2602.21170): R package for Bayesian causal discovery with spike-and-slab priors. Handles both DAGs and directed cyclic graphs. [SOURCE: arXiv:2602.21170] [FRONTIER]

#### Practical calibration for agent causal claims

**No published work on calibrating LLM confidence specifically for causal claims.** [NEGATIVE RESULT]

However, we can apply general calibration principles from our existing research (`calibration-measurement-practical.md`):

1. **Sample consistency**: Generate N causal analyses (N=5-10). If 8/10 produce the same DAG structure, structural confidence is higher. If 5/10 produce different DAGs, flag high uncertainty.
2. **Edge-level confidence**: For each edge in the DAG, count how often it appears across N samples. Report per-edge confidence. This is analogous to bootstrap confidence for causal discovery.
3. **Formal sensitivity analysis**: For the chosen DAG, use DoWhy's sensitivity analysis to quantify how robust the causal effect estimate is to unmeasured confounding.
4. **Cromwell's rule**: Never assign 0% or 100% to DAG structure correctness. The DAG is always a model, not ground truth.

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | ThinkPRM uses 1% of PRM800K, surpasses discriminative verifiers by 8% on GPQA-Diamond OOD | arXiv:2504.16828 | HIGH | Verified via Exa /answer + paper | VERIFIED |
| 2 | No published PRM targets causal reasoning or DAG verification | Extensive search (S2, Exa, Perplexity) | HIGH | Negative result | VERIFIED-NEGATIVE |
| 3 | CoT unfaithfulness baseline is 7-13% on clean prompts | ICLR 2026 submission | HIGH | Existing corpus | VERIFIED |
| 4 | DoWhy provides automated backdoor criterion checking with 4 strategies | pywhy.org/dowhy/v0.14 docs | HIGH | Official documentation | VERIFIED |
| 5 | DeepSeek-R1 rejected neural PRMs for large-scale RL due to reward hacking | arXiv:2501.12948 | HIGH | Published paper | VERIFIED |
| 6 | Best open-source PRM scores 68% on Socratic-PRMBench | arXiv:2505.23474 | HIGH | In corpus | VERIFIED |
| 7 | Med-PRM is the first domain-specific PRM with RAG verification | arXiv:2506.11474, EMNLP 2025 | MEDIUM | Published but "first" is hard to verify | SOURCE-VERIFIED |
| 8 | VRPM rule-based approach outperforms neural by +20% F1 | arXiv:2601.17223 | MEDIUM | Preprint, single paper | PREPRINT |
| 9 | No published work on calibrating LLM confidence for causal claims | Extensive search | HIGH | Negative result | VERIFIED-NEGATIVE |
| 10 | Cross-family LLM verification (Llama correcting Claude) = 90.4% vs 59.1% same-model | FINCH-ZK, arXiv:2508.14314 | HIGH | Existing corpus | VERIFIED |

---

## Key Findings

### 1. Rule-based verification > neural PRMs for causal reasoning

Our `dag_check.py` approach is architecturally correct. For causal claims where the answer is formally decidable (adjustment sets, d-separation, identifiability), deterministic verification outperforms neural PRMs. This is confirmed by VRPM's finding that rule-based verifiers beat neural scoring by +20% F1 in structured domains. Neural PRMs add value only for the non-formalizable parts (domain knowledge about which variables to include).

### 2. The verification gap is in DAG CONSTRUCTION, not DAG ANALYSIS

Formal tools can verify "given this DAG, is the adjustment set correct?" with certainty. But no formal tool can verify "is this DAG correct?" That requires domain knowledge, and this is where LLM reasoning is most unreliable and hardest to verify. The agent might draw a plausible-looking DAG that omits a critical confounder.

**Mitigation:** Self-consistency across N samples + cross-model review of DAG structure + literature-grounded edge justification.

### 3. ThinkPRM is the most promising neural verifier for non-math reasoning

Its generative approach (producing verification CoT) generalizes better than discriminative PRMs. 1% data efficiency makes it practical. Open-source. The 8% OOD improvement on GPQA-Diamond suggests it works beyond math. But: not tested on causal reasoning specifically.

### 4. interwhen-style interleaved verification is the ideal architecture

Rather than verify after the full trace, interleave generation with formal checks. Agent proposes DAG -> run d-separation checks -> agent proposes adjustment set -> run backdoor criterion -> agent states effect -> check identification. This prevents error propagation.

### 5. Self-consistency has special power for causal reasoning

Unlike most LLM tasks, causal conclusions are often formally verifiable. This means self-consistency voting isn't just "which answer is most common" — it's "which answer passes formal checks." Combine: generate 5 traces, formally verify each, take majority among those that pass.

---

## What's Uncertain

1. **ThinkPRM on causal reasoning**: No one has tested generative PRMs on causal/DAG reasoning. The OOD generalization results are promising but unverified for this domain. [INSUFFICIENT-EVIDENCE]

2. **interwhen deployment timeline**: The framework is a preprint (Feb 2026). No production deployments documented. Implementation effort for causal verification integration is unknown. [PREPRINT]

3. **Self-consistency sample size for causal reasoning**: General literature suggests N=5-10, but the specific convergence rate for causal DAG agreement is unmeasured. [UNVERIFIED]

4. **CRV (white-box verification) applicability**: Requires access to model internals (attribution graphs). Not available for API-accessed models (Claude, GPT). Research-only. [LIMITATION]

---

## Deployable Actions (Now to 3 Months)

### Immediate (this week)

1. **Upgrade dag_check.py to use DoWhy as backend.** DoWhy provides 4 backdoor strategies, ID algorithm, front-door criterion, optimal adjustment sets. Our custom implementation covers a subset. DoWhy is pip-installable, MIT-licensed, v0.14.
   ```
   pip install dowhy
   # model.identify_effect() replaces our manual backdoor check
   ```

2. **Add formal verification hook**: After any agent causal reasoning step, extract the DAG and stated adjustment set, run DoWhy verification, compare against optimal adjustment set. This is the VRPM pattern — deterministic, no neural network.

3. **Self-consistency for DAG construction**: Generate N=5 causal analyses for the same question, extract DAGs, compute edge-level agreement. Flag edges with <60% agreement as uncertain.

### Near-term (1-3 months)

4. **Interleaved verification**: Implement interwhen-style pattern — after each reasoning step that produces a causal claim, pause and formally verify before continuing. Prevents cascading errors.

5. **ThinkPRM evaluation**: Run ThinkPRM on a small set of causal reasoning traces to assess OOD performance. If it works, integrate as secondary verifier for non-formalizable claims ("is this variable a confounder?").

6. **Cross-model DAG review**: Generate DAG with primary model, have secondary model (different family) critique the DAG structure. Per our cross-model research, cross-family review catches different error types.

---

## Disconfirmation Results

- **Searched for**: "PRMs don't generalize beyond math", "process reward model failure", "CoT verification doesn't work"
- **Found**: DeepSeek-R1 explicitly rejected neural PRMs for large-scale RL (reward hacking). PRMProbe shows PRMs learn surface cues, not semantics. Socratic-PRMBench shows 68% ceiling for best open-source PRM.
- **Implication**: Neural PRMs alone are NOT sufficient. The rule-based verification approach (our dag_check.py, VRPM pattern) is more robust for formally verifiable domains.

---

## Search Log

| Query | Tool | Results | Signal |
|-------|------|---------|--------|
| PRMs for non-math reasoning 2025-2026 | Perplexity Deep Research | Comprehensive — VersaPRM, ThinkPRM, GenPRM, Med-PRM, VRPM, CRV | HIGH |
| Formal verification causal DAG adjustment set | Exa | DoWhy, dagitty, pcalg, CIfly, CausalTestingFramework, ananke | HIGH |
| Cross-model verification reasoning traces | Exa | CRV, OTV, interwhen, self-verifying reflection, EMNLP survey | HIGH |
| Self-consistency for causal reasoning | Exa | Baldo et al. causal orders, CRAwDAD, ranked voting | MEDIUM |
| BMA over DAGs | S2 | Kaplan 2016, Toth 2025, ProDAG, cyclinbayes | MEDIUM |
| ThinkPRM 1% claim verification | Exa /answer | Confirmed | HIGH |
| PRM for causal reasoning | S2 + Exa | Nothing found — confirmed gap | NEGATIVE |
| Process reward model scientific reasoning (arXiv) | arXiv search | 0 relevant results — arXiv search poor for this | LOW |

## Sources Saved to Corpus

- CRV: `19a52c55cefd6e8ad814e6df04ab99e8bdc13ba0`
- Med-PRM: `1585c43b9c584854bcb42ce4e56416c6b3bc54f3`
- ThinkPRM: `f38c5bebea05d763ab3f60ac0ea7f4f4a2151bc2`
- GenPRM (pre-existing): `bd94932b7604933a11d1538b0de6f9543089711f`
- VersaPRM (pre-existing): `35603018ff166b30425e879c574612145d113c11`
- Socratic-PRMBench (pre-existing): `09933d534525fb65672a10d83d7e26dcdc12523b`
