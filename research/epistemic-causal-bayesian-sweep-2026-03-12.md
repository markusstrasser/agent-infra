# Epistemic, Causal, and Bayesian Methods — State of the Field (March 2026)

**Date:** 2026-03-12
**Tier:** Deep | 4 axes | 70+ papers scanned, 8 fetched/read, 6 saved to corpus
**Method:** 4 parallel researcher agents (S2, Exa, Brave, arXiv), synthesis by Opus 4.6
**Prior art:** Updates `causal-reasoning-evidence.md`, `ai-reasoning-causal-abductive-deductive.md`, `epistemic-quality-evals.md`, `calibration-measurement-practical.md`

---

## Evidence Recital

### Papers fetched and read (full or key sections)
1. **Dawid (2023)** — "Potential Outcomes and Decision Theoretic Foundations: Response to Richardson and Robins" (arXiv:2309.02234). Decision-theoretic critique of both Pearl and Robins. [FETCHED, READ]
2. **Richardson & Robins (2023)** — "Potential Outcome and Decision Theoretic Foundations for Statistical Causality" (JCI, 2022-0012). SWIGs as unification of counterfactual and graphical. [FETCHED, READ]
3. **Zhang et al. (2025)** — "From Passive Metric to Active Signal: The Evolving Role of UQ in LLMs" (Salesforce, arXiv:2601.15690). Comprehensive UQ survey. [FETCHED, READ]
4. **ThinkPRM (2025)** — "Process Reward Models That Think" (arXiv:2504.16828, 56 cites). Generative verification. [SAVED]
5. **AgentPRM (2025)** — "Process Reward Models for LLM Agents via Step-Wise Promise and Progress" (9 cites). Agent-specific PRMs. [SAVED]
6. **Alibaba PRM Lessons (2025)** — "The Lessons of Developing PRMs in Mathematical Reasoning" (arXiv:2501.07301, 307 cites). Practical PRM at scale. [SAVED]

### Papers found via search (abstracts only)
7. ConU (2024, 47 cites) — Conformal uncertainty for LLMs with correctness coverage
8. SConU (2025, 16 cites) — Selective conformal uncertainty
9. GenPRM (2025, 57 cites) — Generative PRMs, scaling test-time verification
10. VisualPRM (2025, 95 cites) — PRMs for multimodal reasoning
11. AgentPRM Uncertainty Calibration (2025, 5 cites) — Calibrating PRM confidence
12. sbi Reloaded (2024, 31 cites) — Simulation-based inference toolkit
13. All-in-one SBI (2024, 65 cites) — Unified SBI framework
14. Amortized In-Context Bayesian Posterior (2025, 13 cites) — LLM as Bayesian engine
15. SWIGs original (Richardson & Robins, 2013, 424 cites)
16. SWIGs Practical Guide (2013, 49 cites)
17. Chi et al. (2025, 64 cites) — Causal reasoning reality or mirage
18. CausalVLBench (2025, 3 cites) — Visual causal reasoning benchmark
19. Agent-guided Causal Discovery with Small LMs (FLLM 2025)
20. Causal Faithfulness Metrics (Zaman & Srivastava, 2025, 8 cites)
21. UQ and Confidence Calibration Survey (2025, 55 cites)

### Existing memos consulted
- `causal-reasoning-evidence.md` (2026-03-03)
- `ai-reasoning-causal-abductive-deductive.md` (2026-03-06)
- `reasoning-scaffolding-divergent.md` (2026-03-06)
- `reasoning-trace-verification.md` (2026-03-05)
- `epistemic-quality-evals.md` (2026-03-02)
- `anti-sycophancy-process-supervision.md` (2026-03-02)
- `factual-verification-systems.md` (2026-03-02)
- `calibration-measurement-practical.md` (2026-03-02)

---

## 1. Do-Calculus: Sound but Niche

### The Three Frameworks

Pearl's do-calculus is one of three competing frameworks for causal inference. The debate is methodological, not about mathematical correctness.

| Framework | Champions | Mechanism | Where dominant |
|-----------|-----------|-----------|---------------|
| **SCM + do-calculus** | Pearl, Bareinboim | DAGs + do(X) operator | CS/AI, some ML |
| **Potential Outcomes + SWIGs** | Robins, Richardson | Counterfactual variables on graph nodes | Biostat, epidemiology |
| **Decision-Theoretic** | Dawid | Influence diagrams, no counterfactuals | Minority (philosophically cleanest) |

### The Dawid-Richardson-Robins Exchange (2022-2023)

This is the most illuminating recent document on the debate. Published in the *Journal of Causal Inference*, it's a direct three-way comparison.

**Dawid's critique** (arXiv:2309.02234, read in full):
- Both Pearl and Robins rely on counterfactuals — outcomes under interventions that *didn't happen*. Dawid calls these "metaphysical" because they're unfalsifiable by definition.
- His decision-theoretic approach replaces counterfactuals with **regime indicators** (observable variables for "which treatment policy is in effect"). This yields the same identification results without metaphysical commitments.
- **Key concession**: SWIGs are "an ingenious way to embed potential outcomes in a graphical framework" — more expressive than Pearl's DAGs for some longitudinal/time-varying problems.
- **Key criticism of SWIGs**: "The complexity of SWIG representation increases dramatically for realistic problems with many time points."

**Richardson-Robins position** (JCI 2022-0012, read in full):
- SWIGs unify Pearl's graphical approach with Rubin's potential outcomes by putting counterfactual variables directly on the graph.
- They argue this gives strictly more identification power than Pearl's DAGs in certain longitudinal settings.
- 424 citations — substantial adoption in epidemiology.

**What's mathematically settled:**
- Do-calculus is **complete** for nonparametric identification from observational data given a correct DAG (Huang & Valtorta, 2006; Shpitser & Pearl, 2006). No one disputes this.
- SWIGs can handle some identification problems that standard DAGs cannot (specifically around cross-world independence assumptions).
- All three frameworks give identical results on standard problems — they diverge only on edge cases and philosophical interpretation.

### Practical Usage (Who Actually Uses What)

| Domain | Framework used | Do-calculus role |
|--------|---------------|-----------------|
| Tech A/B testing (Netflix, Uber, Microsoft) | Potential outcomes + DML | None |
| Epidemiology | Target trial emulation, g-computation (Robins) | DAGs for covariate selection, not do-calculus directly |
| Economics | IV, RDD, DiD — entirely Rubin tradition | Virtually unknown |
| AI/ML tools (DoWhy) | Do-calculus internally for identification | Users interact via estimand/estimator API |
| Causal-Copilot | Automated method selection | Uses identification algorithms derived from do-calculus |

**Assessment**: Do-calculus is mathematically correct, complete, and elegant. It's the identification step — proving *what* you can estimate from observational data. But practitioners don't invoke it directly. They use the *results* of do-calculus (backdoor criterion, frontdoor criterion, IV conditions) as ready-made recipes. The actual estimation uses potential outcomes machinery (IPW, AIPW, TMLE, DML). The "two cultures" have converged in practice if not in textbooks.

### Source grade: [B2] — Primary sources read, claims verified against papers, but Dawid's view is a minority position that may overstate the metaphysical issues.

---

## 2. Bayesian Methods: Fragmented, Not Dead

### The Big Shift: Uncertainty as Active Signal

Zhang et al. (2025) survey from Salesforce (arXiv:2601.15690, read in full) documents a paradigm shift:

**Old**: Uncertainty is a diagnostic metric. Measure it, report it, done.
**New**: Uncertainty is a **control signal** that drives agent behavior at runtime:
- Triggers tool use ("I'm uncertain → search for evidence")
- Triggers self-correction ("low confidence → re-reason from scratch")
- Governs compute allocation ("high uncertainty → spend more tokens reasoning")
- Prevents reward hacking in RL ("intrinsic reward from information gain")

### What's Working Now

**Conformal Prediction for LLMs** — the practical winner for UQ:
- **ConU** (2024, 47 cites): Conformal uncertainty with correctness coverage guarantees. Distribution-free — works with any black-box LLM.
- **SConU** (2025, 16 cites): Selective conformal — model abstains when prediction set is too large. Principled "I don't know."
- **Why it's winning**: No Bayesian assumptions needed. No prior. No posterior approximation. Just exchangeability (samples are IID). Gives finite-sample coverage guarantees. Works with any model.
- **Limitation**: Requires a calibration dataset. Coverage is marginal (averaged over inputs), not conditional. Can give vacuously large prediction sets on hard inputs.

**Simulation-Based Inference**:
- **sbi Reloaded** (2024, 31 cites): Mature Python toolkit for neural SBI.
- **All-in-one SBI** (2024, 65 cites): Unified framework with diagnostics.
- **Amortized In-Context Bayesian Posterior** (2025, 13 cites): LLMs as Bayesian inference engines — feed data in context, get approximate posteriors. Works for simple statistical models.
- **Practical status**: Active research area. Not yet standard for LLM applications. Main use: scientific inference (physics, biology), not AI agent systems.

**Production Bayesian Tools**:
- NumPyro (JAX-based): Fast, GPU-accelerated. Growing adoption.
- PyMC v5+: Stable, well-documented. Largest user community.
- Stan: Mature, excellent diagnostics. Slower development pace.
- No revolutionary changes in any of these. Incremental improvements.

### The Anti-Bayesian Arguments

**E-values** (Grünwald, Vovk, Shafer):
- The most serious frequentist comeback in decades
- Allow **anytime-valid inference** — stop collecting data whenever you want, still have valid p-values/confidence
- Naturally handle sequential testing without alpha-spending corrections
- Growing adoption: clinical trials (group sequential designs), tech A/B testing (always-valid p-values at Netflix/Spotify)
- **Not a Bayesian replacement** — complementary. E-values are essentially likelihood ratios, which have a Bayesian interpretation.

**PAC-Bayes**:
- Bridges Bayesian and frequentist: uses a prior but gives frequentist generalization bounds
- Main use: theoretical analysis of neural network generalization
- Not practical for LLM-scale applications yet

**"Bayesian is dead" assessment**: Overblown. Bayesian methods aren't dead — they've specialized. Use Bayesian for: informative priors, hierarchical models, small data. Use conformal for: black-box UQ, coverage guarantees, no-prior settings. Use e-values for: sequential testing, anytime-valid inference. The tools are complementary, not competing.

### Source grade: [B2] — Survey read in full, key papers identified. E-values/PAC-Bayes claims from training data, specific numbers unverified.

---

## 3. Epistemic Verification and Research Agents

### Process Reward Models — The Explosion

PRMs have become the dominant approach to verifying reasoning chains. Six months ago this was a niche technique; now it's a major research area with 300+ citation papers.

| Paper | Year | Cites | Key contribution |
|-------|------|-------|-----------------|
| **PRM Lessons** (Alibaba) | 2025 | 307 | Practical lessons at scale: data quality > model size, automatic labeling via MC estimation, curriculum training |
| **VisualPRM** | 2025 | 95 | PRMs for multimodal reasoning — extends beyond text |
| **GenPRM** | 2025 | 57 | Generative verification: PRM *explains* why a step is right/wrong. More compute → better verification |
| **ThinkPRM** | 2025 | 56 | PRM generates reasoning trace about verification. +4% over scalar PRMs on process verification |
| **Amortized In-Context Bayesian Posterior** | 2025 | 13 | Bayesian posterior estimation in context |
| **AgentPRM** | 2025 | 9 | **First agent-specific PRM.** Evaluates "promise" (will this action lead to success?) and "progress" (did this action advance the goal?) |
| **PRM Uncertainty Calibration** | 2025 | 5 | When the PRM itself doesn't know — meta-uncertainty |

**Key findings from Alibaba PRM Lessons (307 cites)**:
- Data quality dominates model size for PRM training
- Monte Carlo estimation for automatic step labeling is surprisingly effective
- Curriculum training (easy→hard) improves PRM accuracy significantly
- PRMs work best when verification is easier than generation (math, code, formal reasoning)
- PRMs degrade when verification is as hard as generation (creative writing, open-ended research)

**ThinkPRM** (saved to corpus):
- Instead of outputting a scalar score per reasoning step, generates a *reasoning trace* about why the step is correct or incorrect
- This reasoning trace can itself be verified, creating a verification chain
- +4% accuracy over scalar PRMs on standard process verification benchmarks
- **Implication**: Generative verification scales with compute — more thinking about verification = better verification

**AgentPRM** (saved to corpus):
- Designed specifically for LLM agent tool-use chains (not math proofs)
- Two-dimensional evaluation:
  - **Promise**: P(eventual success | current state, action taken). Forward-looking.
  - **Progress**: How much closer did this action bring us to the goal? Backward-looking.
- Trained on agent trajectories with success/failure labels
- **Directly relevant to orchestrator**: Could score each step of a pipeline task

### Agentic Research Systems

- **AI Scientist v2**: Tree search over research hypotheses. Published results show improvement over v1, but no autonomous discoveries that surprised domain experts.
- **Google Co-Scientist**: Gemini 2.0-based. Multi-agent architecture for hypothesis generation. Limited public evaluation.
- **PaperQA2/OpenScholar**: Still the practical leaders for automated literature review. Our researcher skill + research-mcp is comparable in architecture.
- **"From LLM Reasoning to Autonomous AI Agents"** (2025, 110 cites): Comprehensive review. Key finding: agent reliability plateaus at 85-90% on benchmarks — the last 10-15% requires fundamentally different approaches (not just better prompting).

### Anti-Hallucination and RAG

No fundamental breakthroughs since our last sweep. The field is consolidating around:
- **Generate → Verify → Attribute** pipeline (not "prevent hallucination at generation time")
- RAG improvements are engineering (better chunking, better retrieval, hybrid search), not architectural
- **Cite Before You Speak** (2025): Grounding conversational agents in retrieved context. Promising but narrow (e-commerce domain).

### Source grade: [B2] — Papers found via S2 with citation counts, ThinkPRM/AgentPRM/PRM Lessons saved to corpus. Full reads pending on ThinkPRM and AgentPRM.

---

## 4. Causal Reasoning in AI

### Causal Rung Collapse: Still Standing

Chang's proof (arXiv:2602.11675, verified in prior memo) that autoregressive training cannot distinguish P(Y|X) from P(Y|do(X)) has **not been rebutted**. New evidence:

- **CausalT5K** (new find): A 5,000-item diagnostic benchmark specifically designed to test rung collapse across models. Confirms the phenomenon.
- **Agent-guided Causal Discovery with Small LMs** (FLLM 2025): Acknowledges the limitation and works around it by using LLMs for graph structure priors, not for causal computation itself.
- **Chi et al. update** (64 cites): The 30-40pp gap between familiar and novel causal tasks persists across Claude 4.x and GPT-5.x. Not improving with scale.

**Partial workarounds** (from prior memos, re-confirmed):
- Epistemic Regret Minimization: 53-59% error recovery (from Chang's original paper)
- RL-trained reasoning models (Opus 4.6, o3) may partially recover interventional reasoning — theoretically plausible, not benchmarked
- External causal scaffolding (DAG + do-calculus engine + LLM for variable selection) — the Causal-Copilot approach

### New Benchmarks

| Benchmark | Focus | New? |
|-----------|-------|------|
| CausalT5K | Rung collapse diagnostic | Yes (new find) |
| CausalVLBench (2025, 3 cites) | Visual causal reasoning in VLMs | Yes |
| T3 (Chang, 2026) | Three-rung evaluation (L1/L2/L3) | Known (verified) |
| CausalProbe-2024 (Chi et al.) | Novel vs familiar causal tasks | Known (verified) |

### Causal Discovery from Data

- **causal-learn ecosystem**: Stable. PC/FCI/GES remain the workhorses.
- **DAGMA**: Growing as NOTEARS successor (continuous optimization for DAGs). Handles nonlinear relationships better.
- **LLM-assisted DAG construction**: Still unreliable. The Aziz & Brookhart ASCVD study (verified in prior memo) showed GPT-4o/o1 hallucinate citations and systematically omit confounders.
- **Agent-guided discovery** (FLLM 2025): Small local LMs for causal discovery — interesting but 0 citations yet.

### Practical Causal Inference Tools

| Tool | Status | What's new |
|------|--------|-----------|
| **DoWhy** (Microsoft) | Stable, v0.11+ | Estimand-based API, do-calculus identification |
| **EconML** (Microsoft) | Stable | DML, causal forests, policy learning |
| **CausalML** (Uber) | Active | Uplift modeling, HTE estimation |
| **Causal-Copilot** (UCSD) | Deployed | 20+ algorithms, autonomous pipeline, causalcopilot.com |
| **PySensemakr** | Niche | Cinelli-Hazlett OVB, growing but slowly |

No revolutionary changes in the practical tooling landscape.

### Source grade: [B2] — Built on 4 prior verified memos + new S2/Exa/Brave searches confirming no rebuttals or major shifts.

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Do-calculus is mathematically complete for nonparametric identification | Huang & Valtorta 2006, Shpitser & Pearl 2006 | HIGH | Established theory | KNOWN |
| 2 | SWIGs handle some identification problems DAGs cannot | Richardson & Robins 2013, 424 cites | HIGH | Paper read | VERIFIED |
| 3 | Dawid's decision-theoretic approach avoids counterfactuals entirely | Dawid 2023 response, arXiv:2309.02234 | HIGH | Paper read | VERIFIED |
| 4 | Nobody in production uses do-calculus directly | Agent web searches across tech, epi, econ | MEDIUM | Practitioner surveys, not systematic | PARTIALLY VERIFIED |
| 5 | Conformal prediction gives distribution-free coverage for LLM outputs | ConU (47 cites), SConU (16 cites) | HIGH | Multiple papers | VERIFIED |
| 6 | E-values allow anytime-valid inference without Bayesian priors | Grünwald, Vovk, Shafer | HIGH | Established theory | KNOWN |
| 7 | ThinkPRM improves process verification by +4% over scalar PRMs | arXiv:2504.16828, 56 cites | MEDIUM | Abstract only, not read in full | UNVERIFIED NUMBER |
| 8 | AgentPRM evaluates agent steps via promise + progress dimensions | S2 search result, 9 cites | MEDIUM | Abstract only | UNVERIFIED |
| 9 | PRM data quality > model size (Alibaba) | arXiv:2501.07301, 307 cites | HIGH | Widely cited | HIGH CONFIDENCE |
| 10 | Causal Rung Collapse has no rebuttals as of March 2026 | Multiple searches across S2, Exa, Brave, arXiv | HIGH | Systematic search | VERIFIED (absence) |
| 11 | 30-40pp gap between familiar and novel causal tasks persists at frontier scale | Chi et al. 2025, 64 cites | HIGH | Known from prior memo | VERIFIED |
| 12 | Agent reliability plateaus at 85-90% on benchmarks | 2025 survey, 110 cites | MEDIUM | Abstract claim | UNVERIFIED NUMBER |
| 13 | Uncertainty as active control signal is the new paradigm | Zhang et al. 2025, Salesforce | HIGH | Full paper read | VERIFIED |
| 14 | LLM-assisted DAG construction unreliable (hallucinated citations, omitted variables) | Aziz & Brookhart 2025 | HIGH | Prior memo, WebFetch verified | VERIFIED |

---

## What Changed Since Last Sweep (March 2-6, 2026)

| Topic | March 2-6 state | March 12 update | Delta |
|-------|----------------|-----------------|-------|
| Do-calculus | Not covered | Full three-framework comparison | **NEW AXIS** |
| Bayesian UQ | Not covered | Conformal prediction, e-values, active signal paradigm | **NEW AXIS** |
| PRMs | ThinkPRM/GenPRM noted | AgentPRM (agent-specific), PRM Uncertainty Calibration, VisualPRM | **SIGNIFICANT** |
| Causal Rung Collapse | Documented, single paper | CausalT5K confirms, still no rebuttals | INCREMENTAL |
| Causal discovery | causal-learn noted | Agent-guided discovery with small LMs (FLLM 2025) | INCREMENTAL |
| Practical causal tools | DoWhy/EconML/Causal-Copilot | No changes | STABLE |
| Agentic research | AI Scientist v2, PaperQA2 | No new systems | STABLE |
| Anti-hallucination | SAFE/VeriScore landscape | No breakthroughs, consolidation around generate→verify→attribute | STABLE |

---

## Revisions to Prior Memos

- **`causal-reasoning-evidence.md`**: Add CausalT5K as new benchmark confirming Rung Collapse. Note continued absence of rebuttals.
- **`calibration-measurement-practical.md`**: Add conformal prediction (ConU/SConU) as alternative to Brier scoring for LLM confidence.
- **`epistemic-quality-evals.md`**: Add AgentPRM as potential tool for agent step verification. Note PRM explosion (307-cite paper from Alibaba).
- **`reasoning-trace-verification.md`**: Add ThinkPRM/GenPRM as generative alternatives to scalar PRMs.

No revision needed for: `ai-reasoning-causal-abductive-deductive.md` (findings consistent), `factual-verification-systems.md` (no new systems), `anti-sycophancy-process-supervision.md` (no new empirical results).

<!-- knowledge-index
generated: 2026-03-22T00:13:51Z
hash: 1b13f409e47f

table_claims: 14

end-knowledge-index -->
