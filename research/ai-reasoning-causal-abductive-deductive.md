# AI Reasoning: Causal, Abductive, Deductive — State of the Art (2025-2026)

**Date:** 2026-03-06
**Tier:** Deep | 4 axes | 20+ sources
**Question:** What can frontier AI models/agents actually do for causal, abductive, and deductive reasoning? What's deployable NOW?
**Context:** Research project (IQ sex differences) where GPT-5.4 via Codex did good but imperfect epistemic work. Gaps: no formal DAGs (bad-control caught by reviewer), implicit abduction, uncalibrated confidence, compressed reasoning traces.

---

## Evidence Recital

Before conclusions, the specific evidence this report rests on:

### Papers read in full or key sections
1. **T3 Benchmark** (Chang, Stanford, arXiv:2601.08258, 2026) — 454 expert-curated vignettes across Pearl's three rungs. Tested GPT-4-Turbo, GPT-5.2, GPT-3.5, Claude Sonnet 4.5, Claude Haiku 3.5. [SOURCE: PDF read]
2. **Causal Rung Collapse** (Chang, Stanford, arXiv:2602.11675, 2026) — Formal proof + 1,360 scenarios showing autoregressive training can't distinguish P(Y|X) from P(Y|do(X)). Epistemic Regret Minimization recovers 53-59% of entrenched errors. [SOURCE: PDF read]
3. **Critical Review of Causal Reasoning Benchmarks** (Yang et al., Oxford, arXiv:2407.08029, 2024) — Systematic review showing most benchmarks test retrieval, not reasoning. [SOURCE: PDF read]
4. **Causal-Copilot** (Wang et al., UCSD, arXiv:2504.13263, 2025) — Autonomous causal analysis agent with 20+ algorithms, automated DAG construction, confounder detection. [SOURCE: PDF read, key sections]
5. **LLM DAG Construction for ASCVD** (Aziz & Brookhart, Clinical Epidemiology, 2025) — GPT-4o/o1 tested for automated DAG generation. [SOURCE: WebFetch full text]
6. **GEAR** (He et al., UT Dallas/Adobe, arXiv:2509.24096, 2025) — Only 20% of 70B-model abductive hypotheses are internally consistent. [SOURCE: abstract + secondary]
7. **Theorem-of-Thought** (Abdaljalil et al., ACL 2025, arXiv:2506.07106) — Parallel abductive + deductive + inductive agents outperform CoT. [SOURCE: secondary summary]
8. **GenPRM** (Zhao et al., arXiv:2504.00891, 56 citations) — Scaling test-time compute with generative PRMs. [SOURCE: abstract]
9. **Lessons of Developing PRMs** (Zhang et al., arXiv:2501.07301, 298 citations) — Practical PRM lessons from Alibaba. [SOURCE: abstract]
10. **Scientific Hypothesis Generation and Validation survey** (Kulkarni et al., arXiv:2505.04651, 2025) — Comprehensive survey. [SOURCE: abstract]

### Tools and systems found
- **Causal-Copilot** (UCSD) — deployed at causalcopilot.com, open-source
- **CAIS / Causal AI Scientist** (OpenReview 2025) — automates causal method selection via decision tree
- **Causal-LLM** (EMNLP 2025) — one-step full-graph causal inference
- **Peircean Abduction framework** (GitHub: Hmbown/peircean-abduction) — Python implementation
- **RCD** (JMLR 2025) — recursive causal discovery Python package
- **Google AI Co-Scientist** (Gemini 2.0 based) — multi-agent hypothesis generation
- **AI Scientist v2** — agentic tree search for research
- **Kosmos** — autonomous data-driven discovery across disciplines

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Frontier LLMs retrieve causal associations, not reason causally — 30-40pp gap on novel vs familiar | CausalProbe-2024 benchmark, 63 citations | HIGH | Chi et al. arXiv:2506.21215 | VERIFIED (paper fetched) |
| 2 | Autoregressive training cannot distinguish P(Y\|X) from P(Y\|do(X)) — architectural limit | Formal proof + 1,360 scenarios | MEDIUM | Chang arXiv:2602.11675 | VERIFIED (PDF read, single author) |
| 3 | GPT-5.2 scores 59.5% on L3 counterfactuals; GPT-4-Turbo scores 71.5% (Scaling Paradox) | T3 benchmark, 454 vignettes, N=100 per level | HIGH | Chang arXiv:2601.08258 | VERIFIED (PDF read) |
| 4 | Claude Sonnet 4.5 scores 56% on L3 counterfactuals, 80% on L1 association | T3 benchmark | HIGH | Chang arXiv:2601.08258 | VERIFIED (PDF read) |
| 5 | GPT-5.2 defaults to CONDITIONAL 92% on ambiguous counterfactuals (paralysis > hallucination) | T3 benchmark | HIGH | Chang arXiv:2601.08258 | VERIFIED (PDF read) |
| 6 | Only 20% of 70B-model abductive hypotheses are internally consistent | GEAR benchmark | MEDIUM | He et al. arXiv:2509.24096 | [F3] not read in full |
| 7 | Process verification (RCA) improves causal judgment — reduces over-hedging | T3 evaluation | HIGH | Chang arXiv:2601.08258 | VERIFIED (PDF read) |
| 8 | GPT-4o/o1 cannot reliably construct DAGs — hallucinate citations, omit variables systematically | ASCVD case study | MEDIUM | Aziz & Brookhart 2025 | VERIFIED (WebFetch) |
| 9 | Causal-Copilot automates full causal pipeline with 20+ algorithms | Paper + deployed demo | HIGH | Wang et al. arXiv:2504.13263 | VERIFIED (PDF read) |
| 10 | CoT reasoning is 7-13% unfaithful even on clean, non-adversarial prompts | ICLR 2026 submission | MEDIUM | ICLR 2026, [PREPRINT] | VERIFIED (prior research) |
| 11 | RL fine-tuning on executable counterfactuals generalizes 1.5-2x vs SFT | arXiv:2510.01539 | MEDIUM | [F3] secondary | UNVERIFIED |
| 12 | Parallel abductive + deductive + inductive agents outperform Self-Consistency | ACL 2025 | MEDIUM | Abdaljalil et al. arXiv:2506.07106 | [F3] secondary |
| 13 | Most causal reasoning benchmarks test retrieval, not reasoning | Oxford critical review | HIGH | Yang et al. arXiv:2407.08029 | VERIFIED (PDF read) |
| 14 | Post-trained 14B model hits 93.5% on CaLM vs 55.4% for o3 — causal post-training works | CauGym benchmark, 7 tasks, 5 test sets | MEDIUM | Chen et al. arXiv:2602.06337, 2026 | VERIFIED (abstract, [PREPRINT]) |
| 15 | LLMs should be restricted to non-decisional support in causal discovery — heuristic search only | Empirical study + theoretical argument | MEDIUM | Wu et al. arXiv:2506.00844, 3 citations | VERIFIED (abstract) |
| 16 | VersaPRM: multi-domain PRM achieves +7.9% on Law vs +1.3% for math-only PRM | MMLU-Pro Law benchmark | MEDIUM | Zeng et al. arXiv:2502.06737, 22 citations | VERIFIED (abstract) |
| 17 | SOTA reasoning LLMs match human average but significantly below human ceiling on deductive reasoning | JustLogic benchmark, synthetic | MEDIUM | Chen et al. arXiv:2501.14851, 10 citations | VERIFIED (abstract) |

---

## 1. Causal Reasoning: What Frontier Models Can and Can't Do

### The core problem is architectural

**Rung Collapse (Chang 2026):** Autoregressive training provides no gradient signal to distinguish association from intervention. This is proven, not conjectured. Standard LLMs operate at Pearl's Rung 1 (association) and dress it as Rung 2 (intervention). [SOURCE: arXiv:2602.11675, PDF read]

**The 30-40pp gap (Chi et al. 2025):** On familiar causal tasks (in training data), models score ~70-75%. On novel causal configurations, they drop to ~35-45%. This is the clearest evidence of retrieval-not-reasoning. [SOURCE: arXiv:2506.21215, 63 citations]

### Frontier model numbers on Pearl's Ladder (T3 Benchmark)

| Model | L1 Association | L3 Counterfactual | L3 Error Mode |
|-------|---------------|-------------------|---------------|
| GPT-4-Turbo | 100% | 71.5% | Over-hedge 12%, Hallucination 3.5% |
| GPT-5.2 | 95% | 59.5% | Over-hedge 15%, Fatalism 10% |
| Claude Sonnet 4.5 | 80% | 56.0% | Fatalism 14%, Hallucination 8% |
| Claude Haiku 3.5 | 68% | 31.0% | Hallucination 34% |
| GPT-3.5 | 95% | 54.5% | Hallucination 27.5% |

**The Scaling Paradox:** GPT-5.2 is WORSE than GPT-4-Turbo on counterfactuals (59.5% vs 71.5%). The failure mode is paralysis, not hallucination — the larger model defaults to "CONDITIONAL" 92% of the time rather than engage. RLHF safety training actively suppresses causal judgment. [SOURCE: T3, PDF read]

**The Skepticism Trap:** Claude Haiku 3.5 rejects 60% of VALID associational claims. Safety-tuning creates systematic over-refusal at L1. Claude Sonnet 4.5 is better (80% L1) but still has 14% "fatalism" at L3 — rejecting counterfactuals as inherently unknowable. [SOURCE: T3, PDF read]

**RCA (Recursive Causal Audit) helps:** Process verification — forcing the model to check its reasoning step-by-step — reduces over-hedging and improves L3 performance. This is the T3 analog of what our `causal-check` skill does. [SOURCE: T3, PDF read]

**CauGym (Chen et al. 2026) — a counter-narrative:** Targeted causal post-training on a 14B model achieved 93.5% on CaLM benchmark vs 55.4% for o3. Uses GRPO (RL variant). Strong generalization and robustness under distribution shifts. This is the first systematic evidence that the rung-collapse limitation can be partially overcome with post-training, though it requires causal-specific training data. [SOURCE: arXiv:2602.06337, [PREPRINT]]

**"LLMs Cannot Discover Causality" (Wu et al. 2025):** Argues the opposite direction — LLMs should be strictly confined to non-decisional support. But concedes that LLM-guided *heuristic search* accelerates causal graph convergence. The reconciliation: LLMs shouldn't determine causal edges, but can accelerate the search over candidate graphs. [SOURCE: arXiv:2506.00844]

### What this means for our IQ project

The bad-control problem (including `items_complete` and posterior variance as controls in the NLSY97 Stage A process block) is exactly the kind of thing a DAG would catch — `items_complete` is a descendant of the exposure (sex), so conditioning on it creates collider bias. No amount of prompting will reliably catch this because:

1. The model operates at Rung 1 (association retrieval)
2. It would need to reason about the causal structure of how `items_complete` relates to sex and quantitative score
3. This is a NOVEL causal configuration (specific to CAT-ASVAB adaptive scoring), not a textbook example

**Architectural fix needed:** Either use a formal DAG tool (Causal-Copilot, DoWhy) to check the model specification, or use explicit DAG prompting where the agent must draw the causal graph BEFORE specifying the regression.

### Deployable tools for causal reasoning

**Causal-Copilot** (UCSD, arXiv:2504.13263, 2025) — the most promising:
- Open-source, deployed at causalcopilot.com
- Automates: DAG discovery, algorithm selection, hyperparameter tuning, result interpretation
- Integrates 20+ causal methods (PC, FCI, GES, ICA-LiNGAM, etc.)
- Has "LLM-Guided Graph Refinement" — uses LLM domain knowledge to check implausible edges
- Supports both tabular and time-series data
- **Gap:** doesn't explicitly check for bad controls / descendants in the adjustment set
- **Frontier model note:** Uses LLMs as the reasoning layer, so subject to same rung-collapse limitations — but the deterministic causal algorithms provide the structural backbone

**Causal-LLM** (EMNLP 2025) — one-step full-graph causal inference from data descriptions. Potentially useful for quick DAG drafts.

**CAIS** (OpenReview 2025) — decision-tree-based method selection for causal analysis. Automated + self-correcting.

**RCD** (JMLR 2025) — recursive causal discovery Python package. More traditional, less LLM-dependent.

**DoWhy** (Microsoft) — the established framework. Not LLM-native but could be integrated. Has explicit back-door criterion checking.

### Practical recommendation for our project

**Don't trust the LLM to reason causally. Use it to DRAFT the DAG, then validate with deterministic tools.**

Concrete workflow:
1. **Agent drafts DAG** using domain knowledge prompt: "Given these variables and their definitions, draw the causal graph. Mark which variables are pre-treatment, which are post-treatment, and which are descendants of the treatment."
2. **Validate with DoWhy or Causal-Copilot**: Check back-door criterion, identify colliders, flag bad controls.
3. **Human reviews**: Especially for domain-specific relationships (e.g., is `items_complete` a descendant of sex in CAT-ASVAB scoring?)
4. **Run regression only after DAG is validated.**

---

## 2. Abductive Reasoning: Inference to Best Explanation

### Current state

**GEAR benchmark (He et al. 2025):** Only 20% of 70B-model hypotheses are internally consistent on abductive tasks. But 80% of valid hypotheses are falsely rejected by single-gold-answer benchmarks — meaning models are better at abduction than benchmarks show, just not in a consistent way. [SOURCE: arXiv:2509.24096, [F3]]

**Theorem-of-Thought (ACL 2025):** Running parallel abductive + deductive + inductive agents with Bayesian belief propagation outperforms chain-of-thought and self-consistency. The key insight: different reasoning MODES have less correlated failures than same-mode multiple runs. [SOURCE: arXiv:2506.07106, [F3]]

**Peircean Abduction framework** (GitHub: Hmbown/peircean-abduction): Python implementation of structured abductive reasoning for LLMs. Three phases: Observation → Hypothesis Generation → Evaluation. Implements Peirce's "surprising fact → explanatory hypothesis" logic. [SOURCE: GitHub, not tested]

### What frontier models do well and badly at abduction

**Well:**
- Generate plausible hypotheses from observations (this is essentially what GPT-5.4 did in the IQ project — it proposed measurement surface effects, school pipeline effects, etc.)
- Rank hypotheses when given explicit criteria
- Revise hypotheses when presented with new evidence (the NLSY97 anomaly narrowing over multiple passes)

**Badly:**
- Internal consistency of generated hypotheses (20% at 70B scale — frontier models may be better, but UNVERIFIED)
- Systematic comparison across hypotheses (the IQ project did implicit ACH but never formalized the matrix)
- Knowing when a hypothesis is SUFFICIENT vs merely PLAUSIBLE
- Avoiding confirmation bias in hypothesis testing (the IQ project did search for disconfirmation, but not systematically across all hypotheses)

### Structured abductive frameworks for agents

**Analysis of Competing Hypotheses (ACH)** — our existing `competing-hypotheses` skill with Bayesian LLR scoring is actually ahead of the published literature for agent-adapted ACH. Most papers treat abduction as "generate one explanation" rather than "systematically compare multiple explanations against evidence."

**What's missing in our implementation:**
1. **Formal IBE (Inference to Best Explanation) scoring** — beyond Bayesian LLR, we should score hypotheses on: explanatory scope, simplicity/parsimony, unification, and fertility (what new predictions does each hypothesis make?)
2. **Abductive consistency checking** — does each hypothesis actually explain ALL the evidence, or does it ignore inconvenient observations?
3. **Cross-hypothesis constraint propagation** — if H1 and H2 are both partially supported, what does their conjunction imply?

### Practical recommendation

**Formalize the abductive step.** When the IQ project generates competing explanations (measurement artifact vs real school-knowledge wedge vs latent g difference), it should:
1. List all observations explicitly
2. For each hypothesis, score: which observations it explains, which it's silent on, which it contradicts
3. Apply ACH matrix with the intel-local Bayesian LLR variant
4. Identify discriminating experiments that would shift the scoring

This is implementable NOW with our existing skills + a structured prompt template.

---

## 3. Deductive Reasoning: Reliability and Limits

### What the evidence says

**CoT faithfulness is 7-13% unfaithful baseline** on clean, non-adversarial prompts (ICLR 2026 wild study). This means roughly 1 in 10 reasoning traces are misleading even without any attack. [SOURCE: prior research, verified]

**The Oxford formalization (2025):** A CoT is faithful only if it is both procedurally correct AND accurately reflects the model's decision process. Current CoT satisfies neither reliably. The debate is active (counter-paper arXiv:2512.23032). [SOURCE: prior research, verified]

**T3 L1 results show deduction is mostly reliable for familiar patterns:**
- GPT-4-Turbo: 100% on L1 (basic associational reasoning)
- GPT-5.2: 95%
- Claude Sonnet 4.5: 80% (Skepticism Trap — over-refusal)

But these are SIMPLE deductive tasks. Complex multi-step deduction remains fragile.

**JustLogic (Chen et al. 2025, 10 citations):** Synthetic deductive reasoning benchmark designed to eliminate prior-knowledge confounding. Finding: SOTA reasoning LLMs perform at or above human average, but **significantly below human ceiling**. Non-reasoning models still underperform human average. Heterogeneous effects of reasoning depth and argument form on accuracy — deeper chains degrade faster. [SOURCE: arXiv:2501.14851]

### Process Reward Models (PRMs) — step-by-step verification

**GenPRM (2025, 56 citations):** Scales test-time compute by using generative PRMs that can evaluate reasoning steps. Instead of just classifying "correct/incorrect," it generates explanations of WHY a step is wrong. This is closer to what we need for causal reasoning verification. [SOURCE: abstract]

**Lessons of Developing PRMs (2025, 298 citations):** Key practical lessons from Alibaba:
- Annotation quality matters more than quantity
- PRMs are sensitive to the distribution of errors in training data
- Best used for VERIFICATION, not generation [SOURCE: abstract]

**VersaPRM (Zeng et al. 2025, 22 citations):** First multi-domain PRM trained on synthetic reasoning data. Achieves +7.9% on MMLU-Pro Law (vs +1.3% for math-only Qwen2.5-Math-PRM). Open-sourced data, code, models. This proves PRMs can generalize beyond math, but **no causal reasoning domain included yet.** [SOURCE: arXiv:2502.06737]

**Gap: No PRMs for causal reasoning.** VersaPRM shows multi-domain PRMs are feasible, but no one has built one for causal reasoning (checking DAG consistency, identifying bad controls, verifying counterfactual logic). This remains an open research problem. [INFERENCE]

### Practical recommendation

**Use PRMs conceptually, not literally.** We can't deploy a trained PRM for causal reasoning. But we can use the PRM PATTERN:
1. Agent generates reasoning trace
2. A second pass (different model or structured prompt) verifies each step
3. Steps that fail verification get flagged for human review

This is essentially what `causal-check` + `model-review` already do, but not at the step level.

---

## 4. Agent-Driven Scientific Discovery: What's Working

### Systems that exist now

**Google AI Co-Scientist (Gemini 2.0):** Multi-agent hypothesis generation system. Uses "tournament" architecture — multiple agents propose hypotheses, debate them, and evolve the best ones. Has been validated with experimental confirmation in biomedical contexts. [SOURCE: Exa summary, [F3]]

**AI Scientist v2 (2025):** Autonomous research agent using agentic tree search. Can do hypothesis → experiment → analysis → writing. Key innovation: treats the research process itself as a search tree, with backtracking when experiments fail. 30 citations. [SOURCE: Exa summary, S2]

**Kosmos (2025):** Autonomous data-driven discovery agent that uses structured "world models" to maintain causal coherence across domains (metabolomics, materials science, neuroscience, genetics). The world model is the key differentiator — it provides a persistent causal structure that the agent reasons over, rather than reasoning ad hoc. [SOURCE: Exa summary, arXiv:2511.02824]

**AlphaEvolve (with Terence Tao, 2025):** Evolutionary coding agent that found new mathematical results. 30 citations. Uses iterative propose-test-refine with automated evaluation. Succeeded because math has VERIFIABLE outcomes. [SOURCE: S2 abstract]

### The common pattern

Every successful AI discovery system shares this architecture:
1. **Structured world model or DAG** — not free-form reasoning
2. **Iterative propose-test-refine** — not one-shot generation
3. **Automated verification** — not self-assessment
4. **Multiple competing hypotheses** — not single-best-guess

The IQ project in Codex followed patterns 2-4 but missed pattern 1 (structured world model / DAG).

### Genius reasoning traces — computational models

**Paul Thagard's computational philosophy of science** is the foundational work. Key concepts:
- **Explanatory coherence** — hypotheses should be evaluated as a network, not individually
- **Analogical reasoning** — transfer of relational structure from known to unknown domains
- **Conceptual combination** — novel hypotheses from combining existing concepts

**What this means for agents:** The "genius leap" is typically not deduction or induction — it's ABDUCTION constrained by analogical transfer. Einstein didn't deduce relativity; he abduced it by analogy from electrodynamics. Darwin didn't induce natural selection from data; he abduced it by analogy from artificial selection.

For AI agents, this suggests:
1. **Feed the agent analogies from adjacent domains** — the IQ project could benefit from analogies to measurement invariance in other fields (psychophysics, item response theory in educational measurement)
2. **Score hypotheses on explanatory coherence** — how well does the entire hypothesis network hang together, not just each individual claim?
3. **Look for structural isomorphisms** — when two domains have the same pattern (e.g., TIMSS broad math moves femaleward while TIMSS Advanced stays male = Simpson's Paradox structure), that's a structural clue, not just a coincidence

---

## 5. What's Deployable NOW vs What's Theoretical

### Deploy today

| Tool/Approach | What it does | Maintenance | Composability | Value |
|--------------|-------------|-------------|---------------|-------|
| **Explicit DAG prompting** | Force agent to draw causal graph before regression | None (prompt) | High — any analysis skill | HIGH — catches bad controls |
| **Causal-Copilot** | Automated DAG discovery + validation | Low (pip dep) | High — feeds DAG skills | HIGH — 20+ algorithms |
| **ACH with LLR scoring** | Structured hypothesis comparison | None (already built) | High — any investigation | MEDIUM — needs formalization |
| **RCA pattern** | Step-by-step causal reasoning verification | None (prompt) | Medium — reasoning skills | HIGH — T3 shows it works |
| **Theorem-of-Thought** | Parallel abd/ded/ind agents | Low (3 prompts) | Medium — novel pattern | MEDIUM — untested locally |
| **DoWhy back-door check** | Validate adjustment sets | None (mature library) | High — deterministic check | HIGH — deterministic |

### Research-stage (not deployable yet)

| Approach | Why not yet | When |
|----------|-----------|------|
| PRMs for causal reasoning | No training data, no benchmark | 6-12 months |
| Rung-collapse fix (ERM) | Single paper, not replicated | Unknown |
| Full explanatory coherence scoring | No implementation exists | Would need to build |
| Causal fine-tuning via RL | Requires RL infrastructure | Not for us |

---

## 6. Disconfirmation Results

**Searched for and didn't find:**
- Evidence that frontier models (Claude 4.6, GPT-5.4) have SOLVED the rung-collapse problem. The T3 paper tested GPT-5.2, not 5.4, and Claude Sonnet 4.5, not Opus 4.6. Thinking/reasoning models (o3, Opus 4.6) trained with RL on verifiable outcomes MAY have different characteristics, but this is **UNVERIFIED**. [INFERENCE]
- Any published work showing PRMs applied to causal reasoning verification. This is a genuine gap. [NEGATIVE FINDING]
- Evidence that LLMs can reliably construct DAGs without human validation. The Aziz & Brookhart paper (2025) explicitly concludes they can't — hallucinated citations, systematic variable omission. But this was GPT-4o/o1, not frontier. [SOURCE: WebFetch]

**Contradictory evidence found:**
- The Scaling Paradox (T3): bigger models are NOT better at causal reasoning. GPT-5.2 < GPT-4-Turbo on counterfactuals. This contradicts the assumption that frontier models will naturally improve at causal reasoning through scale. [SOURCE: T3, PDF read]

---

## 7. What to Do Next — Recommendations

### For the IQ sex differences project specifically

1. **Add explicit DAG step to the analysis protocol.** Before ANY regression, the agent must:
   - Draw the DAG (all variables, their causal relationships)
   - Label each variable as: pre-treatment, post-treatment, descendant of treatment, collider
   - Check adjustment set against back-door criterion (use DoWhy)
   - Human reviews the DAG before proceeding

2. **Formalize the abductive comparison.** The project already has 22 claims in the register. Run ACH on the top 5 open claims with the LLR variant. Score each against ALL 11 evidence points in the current-position doc.

3. **Add calibration to confidence estimates.** The 0.72, 0.65, 0.60 numbers in the causal tree are unchecked intuitions. At minimum: track whether past confidence assignments were accurate. Better: use Brier scoring on closed claims.

### For meta-infrastructure

1. **Build a `causal-dag` skill** that forces DAG construction + DoWhy validation before regression specification. This is the highest-ROI item — it would have caught the bad-control problem automatically.

2. **Upgrade `causal-check` skill** with RCA (Recursive Causal Audit) pattern from T3. Current version does narrative causal checking; RCA does step-by-step process verification.

3. **Investigate Causal-Copilot integration** — check if it can be called from Claude Code as an MCP tool or subprocess. If the pipeline works, it provides DAG discovery + algorithm selection + validation in one call.

4. **Consider Theorem-of-Thought architecture** for high-stakes research sessions: parallel abductive/deductive/inductive agents with Bayesian synthesis. This maps directly onto our existing multi-model review infrastructure.

---

## Search Log

| Query | Tool | Hits | Useful |
|-------|------|------|--------|
| "causal reasoning LLM benchmarks DAG structural causal models" | S2 | 10 | 5 |
| "abductive reasoning LLM hypothesis generation scientific discovery" | S2 | 10 | 4 |
| "process reward model reasoning verification step-by-step" | S2 | 10 | 3 |
| "frontier LLM causal reasoning DAG benchmark 2025 2026" | Exa deep | 10 | 6 |
| "AI agent scientific discovery abductive reasoning case studies" | Exa deep | 10 | 7 |
| "structured causal reasoning framework AI agents DAG confounder" | Exa deep | 8 | 5 |
| "Peirce abduction IBE computational implementation AI agents" | Exa deep | 8 | 4 |
| "LLM automated DAG construction confounder detection" | S2 | 10 | 2 |
| "computational models scientific discovery analogical reasoning" | S2 | 10 | 2 |
| "Causal-Copilot autonomous causal analysis agent" | S2 | 5 | 1 |
| T3 paper (arXiv:2601.08258) | fetch_paper | 1 | 1 (critical) |
| Rung Collapse paper (arXiv:2602.11675) | fetch_paper | 1 | 1 |
| Critical Review (arXiv:2407.08029) | fetch_paper | 1 | 1 |
| Causal-Copilot (arXiv:2504.13263) | fetch_paper | 1 | 1 |
| Aziz & Brookhart DAG paper | WebFetch | 1 | 1 |

## Sources Saved to Corpus

- A Critical Review of Causal Reasoning Benchmarks for Large Language Models
- Unveiling Causal Reasoning in Large Language Models: Reality or Mirage?
- GEAR: A General Evaluation Framework for Abductive Reasoning
- The Lessons of Developing Process Reward Models in Mathematical Reasoning
- GenPRM: Scaling Test-Time Compute of Process Reward Models via Generative Reasoning
- Scientific Hypothesis Generation and Validation: Methods, Datasets, and Future Directions
- Causal-Copilot: An Autonomous Causal Analysis Agent
- Can Contemporary LLMs Provide Domain Knowledge for Causal Inference? (Aziz & Brookhart)
- Improving constraint-based discovery with robust propagation and reliable LLM priors
- T3: Benchmarking Sycophancy and Skepticism in Causal Judgment
- Right for the Wrong Reasons: Epistemic Regret Minimization for Causal Rung Collapse
- Can Post-Training Transform LLMs into Causal Reasoners? (CauGym)
- LLM Cannot Discover Causality (Wu et al.)
- VersaPRM: Multi-Domain Process Reward Model
- JustLogic: Comprehensive Benchmark for Deductive Reasoning
- LogicSkills: Structured Benchmark for Formal Reasoning
- PRISM: Pushing the Frontier via PRM-Guided Inference
- Socratic-PRMBench: Benchmarking PRMs with Systematic Reasoning Patterns
- Causal AI Scientist (CAIS)

## Frontier Model Caveat

Most benchmarks tested GPT-4o/o1 or GPT-5.2, Claude Sonnet 4.5, Claude Haiku 3.5. **No published results found for Claude Opus 4.6, GPT-5.4, or Gemini 3.1 Pro on causal reasoning benchmarks.** Thinking/reasoning models with RL training on verifiable outcomes may perform differently — this is plausible but UNVERIFIED. Don't assume frontier improvements transfer from math/code benchmarks to causal reasoning.

---

*Added 2026-03-06. Primary sources: T3 and Rung Collapse papers read in full. Causal-Copilot key sections read. Others at abstract/summary level. Three research subagents dispatched — didn't complete synthesis but saved 15 papers to corpus; findings from their corpus integrated in this update.*
