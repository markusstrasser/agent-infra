# Agent Skill Improvement: Frontier LLM Techniques (March 2026)

**Date:** 2026-03-17
**Tier:** Deep | 3 domains | ~30 sources scanned
**Question:** What recent (2025-2026) techniques outperform our current skill implementations for causal reasoning, competing hypotheses, and divergent thinking on frontier models?
**Ground truth:** Existing memos — `ai-reasoning-causal-abductive-deductive.md` (2026-03-06), `divergent-convergent-thinking-llms.md` (2026-03-05), `reasoning-scaffolding-divergent.md` (2026-03-06)

---

## Evidence Recital

### Papers read or key sections extracted
1. **Causal Reasoning in Pieces** (Kadziolka & Salehkaleybar, arXiv:2507.23488, Jul 2025) — Modular in-context pipeline for causal discovery on CORR2CAUSE. o3-mini achieves F1=0.84; 3x improvement over single-prompt baselines. [SOURCE: PDF read]
2. **POPPER** (Huang, Jin, Li et al., Stanford/ICML 2025, arXiv:2502.09858) — Agentic sequential falsification with Type-I error control. Matched PhD-level biologist performance, 10x faster. [SOURCE: key sections read]
3. **CRAwDAD** (arXiv:2511.22854, Nov 2025) — Dual-agent causal debate: one agent builds causal inferences, another adversarially evaluates. [SOURCE: Exa summary]
4. **BioDisco** (arXiv:2508.01285, Aug 2025) — Multi-agent hypothesis generation with dual-mode evidence (KG + literature), iterative feedback, temporal evaluation. [SOURCE: Exa summary]
5. **DAG-Think-Twice** (Deng et al., PAKDD 2025) — Causal structure-guided prompt elicitation using DAGs. [SOURCE: S2 metadata]
6. **InterveneBench** (arXiv:2603.15542, Mar 2026) — Benchmark for LLM intervention reasoning in social science contexts. [SOURCE: Exa summary]
7. **DeepCausa** (OpenReview 2025) — Post-training transforms LLMs into causal inference agents. [SOURCE: Exa summary]
8. **GRID** (arXiv:2509.16397) — Graph-based causal reasoning combining constraint methods + neural + LLM priors for HVAC fault diagnosis. [SOURCE: Exa summary]
9. **CausalPlan** (OpenReview 2025) — Multi-agent collaboration with explicit causal reasoning for plan generation. [SOURCE: Exa summary]
10. **LiveIdeaBench** (Nature Communications 2026) — Divergent thinking benchmark; 22 domains, 1180 keywords. Published version of earlier preprint. [SOURCE: Exa summary]
11. **Nature Human Behaviour** (2025) — Large-scale comparison of divergent creativity, humans > LLMs at distribution extremes. [SOURCE: Exa summary]
12. **CreativeDC** (2025) — Divergent-convergent two-phase prompting for creative problem generation, Guilford-inspired. [SOURCE: Exa summary]
13. **LLMs for Scientific Idea Generation survey** (arXiv:2511.07448, Nov 2025) — 5 approach categories: external knowledge, prompt steering, inference-time scaling, multi-agent, parameter-level. [SOURCE: Exa summary]
14. **Contestable AI for criminal intelligence analysis** (Frontiers in AI, 2025) — Semantic modeling + human oversight for hypothesis-driven analysis. [SOURCE: Exa summary]

### Tools/systems found (new since March 2026 memos)
- **POPPER** (Stanford, open-source) — Sequential falsification framework
- **BioDisco** — Multi-agent hypothesis generation
- **CRAwDAD** — Dual-agent causal debate
- **InterveneBench** — Intervention reasoning benchmark
- **DeepCausa** — Causal post-training benchmark

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Reasoning models (o3-mini, DeepSeek-R1) achieve 3x F1 improvement on causal discovery when scaffolded with modular in-context pipeline vs single prompt | CORR2CAUSE benchmark, o3-mini F1=0.84 vs ~0.28 baseline | HIGH | arXiv:2507.23488 | VERIFIED (PDF read) |
| 2 | Decomposing PC algorithm into 4 stages (skeleton → V-structures → Meek rules → hypothesis) is key — each stage produces intermediate artifacts | Stage-wise F1: skeleton 1.0, V-structures 0.99, Meek 0.95, hypothesis 0.84 for o3-mini | HIGH | arXiv:2507.23488 | VERIFIED (PDF read) |
| 3 | POPPER matches PhD-level biologist validation performance at 10x speed with Type-I error control | Expert user study, 9 PhD-level researchers | MEDIUM | arXiv:2502.09858, ICML 2025 | VERIFIED (key sections read) |
| 4 | Dual-agent adversarial debate (CRAwDAD) improves causal reasoning quality vs single-agent | Framework description | LOW | arXiv:2511.22854 | [SUMMARY ONLY] |
| 5 | Humans still exceed LLMs at extremes of creativity distribution | Large-scale comparison, Nature Human Behaviour 2025 | HIGH | Nature Human Behaviour 2025 | [SUMMARY: peer-reviewed] |
| 6 | 5 categories of divergent techniques: external knowledge, prompt steering, inference-time scaling, multi-agent, parameter-level | Survey of scientific idea generation methods | MEDIUM | arXiv:2511.07448 | [SUMMARY ONLY] |
| 7 | LiveIdeaBench confirmed: general intelligence metrics do NOT predict divergent capability in LLMs | Published Nature Communications 2026 | HIGH | Nature Comms 2026 | [SUMMARY: peer-reviewed] |
| 8 | No published work specifically automates Analysis of Competing Hypotheses (ACH) with LLMs | Search across S2, Exa, arXiv | MEDIUM | Absence of evidence | [INSUFFICIENT-EVIDENCE] |

---

## 1. Causal Reasoning Skills (causal-check, causal-dag, causal-robustness)

### What changed since our last memo (2026-03-06)

**The big finding: modular pipeline scaffolding is now validated.** Kadziolka & Salehkaleybar (Jul 2025) demonstrate that decomposing the PC algorithm into 4 explicit stages with intermediate artifacts yields F1=0.84 on o3-mini (vs ~0.28 for single-prompt). This directly validates the architectural pattern our `causal-dag` skill should use. The key numbers:

- o3-mini pipeline: Skeleton=1.00, V-structures=0.99, Meek=0.95, Hypothesis=0.84
- DeepSeek-R1 API pipeline: Skeleton=1.00, V-structures=0.99, Meek=0.90, Hypothesis=0.80
- DeepSeek-R1-70B pipeline: Skeleton=0.83, V-structures=0.76, Meek=0.70, Hypothesis=0.58

**Implication for Opus 4.6:** Reasoning-class models benefit massively from stage decomposition. Non-reasoning models (GPT-4o class) show much smaller gains. Opus 4.6 with extended thinking should behave more like the reasoning models here. Our `causal-dag` skill currently does a single-prompt DAG generation — it should decompose into explicit stages.

**New benchmarks to watch:**
- **InterveneBench** (Mar 2026) — Tests intervention reasoning (do-calculus level 2) in social science contexts. More ecologically valid than CORR2CAUSE.
- **DeepCausa** — Post-training benchmark showing targeted causal fine-tuning works. Not relevant for prompting-only approaches but signals direction.

**Dual-agent causal debate (CRAwDAD)** is architecturally interesting but unverified at scale. One agent constructs causal inferences, another adversarially challenges them. This maps to a potential `causal-robustness` upgrade where the skill spawns a critic subagent.

### Actionable recommendations

1. **Decompose `causal-dag` into 4-stage pipeline:** Skeleton extraction → collider identification → Meek-rule orientation → hypothesis validation. Each stage gets its own prompt with explicit intermediate output format. This is the highest-ROI change — validated 3x improvement on reasoning models.

2. **Add stage-level verification to `causal-check`:** Instead of checking the final DAG in one pass, verify each stage's output independently. The paper shows errors cascade — catching them at skeleton level prevents downstream corruption.

3. **Consider dual-agent pattern for `causal-robustness`:** CRAwDAD's builder/critic architecture maps naturally. Builder constructs DAG, critic searches for confounders, collider bias, missing paths. Lower confidence — no benchmark numbers on frontier models, but architecturally sound.

4. **Don't pursue causal post-training (DeepCausa).** We can't fine-tune Claude. The prompting + scaffolding approach (items 1-3) is what's available and what the evidence supports.

---

## 2. Competing Hypotheses / ACH

### State of the art: no direct ACH automation, but adjacent work is strong

**No published paper specifically automates the ACH matrix with LLMs.** I searched S2, Exa, arXiv, and Brave across multiple query formulations. The closest work:

**POPPER** (Stanford, ICML 2025) is the most relevant system. It doesn't implement ACH specifically, but it operationalizes Popperian falsification for hypothesis validation:
- Takes a free-form hypothesis
- LLM agents design falsification experiments targeting measurable implications
- Sequential testing framework ensures Type-I error control
- Matched 9 PhD-level biologists' performance at 10x speed

**Key POPPER design choices relevant to our ACH skill:**
- Sequential falsification (test one implication at a time, accumulate evidence)
- Strict statistical error control (not just LLM judgment)
- Agent-designed experiments (the LLM picks *what* to test, not just whether to believe)

**BioDisco** (Aug 2025) is a multi-agent hypothesis generation framework with:
- Dual-mode evidence (knowledge graphs + literature retrieval)
- Iterative feedback loops between generation and evaluation agents
- Temporal evaluation (how hypotheses hold over time)

**Contestable AI for criminal intelligence** (Frontiers in AI, 2025) addresses hypothesis-driven analysis in law enforcement — closest to the intelligence analysis use case. Uses semantic modeling + human oversight. Not automated ACH but shows the field is moving toward structured, contestable analysis.

### What's missing from our ACH skill

Our `competing-hypotheses` skill currently:
1. Takes hypotheses + evidence items as input
2. Builds a consistency matrix (hypothesis × evidence)
3. Identifies diagnosticity (which evidence distinguishes hypotheses)

This is a good implementation of Heuer's original method. But the frontier work suggests:

### Actionable recommendations

1. **Add POPPER-style falsification step.** After building the ACH matrix, for each surviving hypothesis, the skill should generate specific falsification queries: "If H1 is true, we should see X in the data." Then execute those queries. This turns ACH from a static assessment into an active investigation tool.

2. **Add evidence *generation*, not just evaluation.** Current skill takes evidence as input. POPPER and BioDisco both generate evidence-seeking queries autonomously. The skill should suggest what evidence to *look for* based on the hypothesis structure — "These 3 hypotheses would be distinguished by checking Y."

3. **Add diagnosticity-weighted search.** Instead of evaluating all evidence equally, prioritize searching for evidence with high diagnosticity (evidence that distinguishes between hypotheses). This is a known ACH best practice that our skill could automate.

4. **Consider dual-evidence-mode (BioDisco pattern).** For research hypotheses, query both structured knowledge (databases, KGs) AND unstructured literature. The skill currently treats all evidence as homogeneous.

5. **Statistical error control is aspirational.** POPPER's Type-I error control is elegant but requires numerical data. Most ACH applications use qualitative evidence. Flag as `[ASPIRATIONAL]` — implement if we get quantified evidence streams.

---

## 3. Brainstorming / Divergent Thinking

### What changed since our last memo (2026-03-05)

**LiveIdeaBench is now published in Nature Communications (2026).** The key finding — general intelligence metrics do NOT predict divergent capability — is confirmed in peer review. This validates our architectural choice to use different prompting modes for divergent vs convergent phases.

**Nature Human Behaviour (2025)** large-scale comparison confirms: humans > LLMs at the *extremes* of the creativity distribution. LLMs are good at average creativity but can't match the best human ideas. This means our brainstorming skill should optimize for *volume and diversity* (where LLMs are competitive) rather than trying to produce individually brilliant ideas.

**Scientific Idea Generation survey** (arXiv:2511.07448) categorizes 5 approaches:
1. **External knowledge augmentation** — inject domain knowledge to expand solution space
2. **Prompt-based steering** — denial prompting, persona switching, constraint manipulation
3. **Inference-time scaling** — reasoning models explore more internally
4. **Multi-agent collaboration** — diverse agents with different perspectives
5. **Parameter-level** — fine-tuning for creativity (not available for Claude)

**CreativeDC** (2025) implements a two-phase Guilford-inspired approach:
- Phase 1 (divergent): Generate many ideas under minimal constraints
- Phase 2 (convergent): Filter and refine using problem structure

This maps almost exactly to what our brainstorming skill already does. No evidence of a fundamentally different approach outperforming it.

### What's NOT working / still missing

**No evidence that Opus 4.6 class models handle divergent thinking differently than earlier frontier models.** `[INSUFFICIENT-EVIDENCE]` LiveIdeaBench tested GPT-4o, Claude 3.5, Gemini, etc. — no published results on Claude 4/4.5/4.6 or GPT-5 class. The structural asymmetry (convergent > divergent) is likely architectural (next-token prediction) and persists across scales.

**Denial prompting (NEOGAUGE)** is still the most empirically validated technique for pushing LLMs into novel territory. No newer technique has displaced it. Our skill implements denial cascades — this is still correct.

**Temperature as creativity lever** — the "entropy turning point" finding from our March memo is not contradicted. Model-specific optimal temperature remains the key insight. No new evidence on Opus 4.6 specifically.

### Actionable recommendations

1. **No major architecture changes needed.** Our brainstorming skill's current approach (denial cascades, explicit divergent→convergent phases, constraint inversion) is aligned with the published state of the art. The scientific idea generation survey confirms these are the right approaches.

2. **Add external knowledge injection (category 1 from survey).** When brainstorming about a specific domain, inject 2-3 pieces of tangential domain knowledge before generating ideas. The survey finds this expands the solution space more effectively than prompt engineering alone. Our analogical forcing technique already does a lightweight version — could be made more systematic by querying Exa for adjacent-domain examples before brainstorming.

3. **Optimize for volume + diversity, not individual brilliance.** Nature Human Behaviour confirms LLMs can't match top-human creative peaks. Generate 15-20 ideas, then filter ruthlessly. Currently our skill generates 5-10 — increase the divergent phase output.

4. **Multi-agent divergence is underexplored in our setup.** The survey identifies multi-agent collaboration as a distinct category. We could spawn 2-3 brainstorming subagents with different persona constraints (the persona-based mode switching from our March memo), then merge their outputs. This is architecturally easy with Claude Code subagents but we haven't tried it.

5. **Inference-time scaling (reasoning mode) for brainstorming is unvalidated.** The survey notes this as a category but the evidence is thin. Extended thinking in Opus 4.6 might help with convergent refinement but is unlikely to help with divergent generation (reasoning = convergent by nature). Don't use ultrathink for brainstorming phases.

---

## Disconfirmation Search

### For causal reasoning
- **Causal Rung Collapse** (Chang, arXiv:2602.11675) — formal proof that autoregressive models can't distinguish P(Y|X) from P(Y|do(X)) — remains uncontested. Scaffolding helps but doesn't solve the architectural limit. Our approach (external DAG validation, not LLM-internal causal reasoning) is correct.
- No evidence that the 4-stage modular pipeline *fails* — but it's tested only on CORR2CAUSE (synthetic benchmark). Real-world causal discovery is harder.

### For ACH
- POPPER's falsification approach has a known limitation: it requires *measurable implications* that can be tested with data. Many intelligence analysis scenarios involve qualitative evidence where this doesn't apply.
- No evidence ACH automation actually improves intelligence analysis outcomes (no RCT, no field study). `[INSUFFICIENT-EVIDENCE]`

### For divergent thinking
- **Constraint-satisfaction tradeoff** is real: NEOGAUGE shows correctness drops as divergent novelty rises under denial prompting. Our skill should track this tradeoff explicitly.
- LLM creativity benchmarks may be measuring retrieval of training-data combinations, not genuine creativity. The Nature Human Behaviour comparison doesn't resolve this philosophical question.

---

## Summary of Recommendations by Priority

### High priority (validated, high ROI)
1. **Decompose `causal-dag` into 4-stage pipeline** — 3x validated improvement [SOURCE: arXiv:2507.23488]
2. **Add POPPER-style falsification to `competing-hypotheses`** — generates evidence-seeking queries after matrix construction [SOURCE: arXiv:2502.09858]
3. **Increase brainstorming volume from 5-10 to 15-20 ideas** — optimize for diversity, not individual brilliance [SOURCE: Nature Human Behaviour 2025]

### Medium priority (promising, less validated)
4. **Add diagnosticity-weighted evidence search to ACH** — automate "what would distinguish these hypotheses?" [INFERENCE from ACH theory + POPPER]
5. **Add stage-level verification to `causal-check`** — catch errors at skeleton level before cascade [SOURCE: arXiv:2507.23488]
6. **External knowledge injection for brainstorming** — query adjacent domains before divergent phase [SOURCE: arXiv:2511.07448]

### Low priority (interesting, unvalidated on frontier models)
7. **Dual-agent causal debate (CRAwDAD pattern)** for `causal-robustness` [SOURCE: arXiv:2511.22854, summary only]
8. **Multi-agent persona divergence** for brainstorming [INFERENCE from survey categories]
9. **Dual-evidence-mode (KG + literature)** for ACH [SOURCE: BioDisco, arXiv:2508.01285]

---

## What's Uncertain

- How Opus 4.6 specifically performs on CORR2CAUSE or InterveneBench — no published results. `[UNVERIFIED]` The modular pipeline likely helps (reasoning-class model) but we don't have numbers.
- Whether POPPER's sequential falsification works for qualitative intelligence analysis scenarios (it's tested on data-rich domains: biology, economics).
- Whether multi-agent brainstorming actually produces more diverse ideas than single-agent with denial prompting on frontier models.
- The CreativeDC paper — only Exa summary available, not read in full. May contain technique details beyond what the summary shows. `[UNVERIFIED]`

## Sources Saved
- arXiv:2507.23488 (Causal Reasoning in Pieces) — downloaded, read in full
- arXiv:2502.09858 (POPPER) — downloaded, key sections read

<!-- knowledge-index
generated: 2026-03-21T23:52:37Z
hash: f2b7c50d9a37

sources: 2
  INFERENCE: from ACH theory + POPPER
  INFERENCE: from survey categories
table_claims: 8

end-knowledge-index -->
