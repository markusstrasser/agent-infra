# Divergent vs Convergent Thinking in LLMs

**Date:** 2026-03-05
**Status:** v2 deployed (Phase 1 skill edits 2026-03-05, Phase 2 architecture 2026-03-06)
**Sources:** Perplexity Deep Research (35 citations, 2024-2026 literature), cross-referenced against known findings

## Core Finding: Fundamental Asymmetry

LLMs are **consistently strong at convergent thinking** (finding the correct answer, logical deduction, constraint satisfaction) and **variable at divergent thinking** (generating novel ideas, creative exploration). This is not a bug — it's structural. Next-token prediction optimizes for high-probability continuations, which is convergent by nature.

**Key numbers:**
- Human originality advantage on high-demand creative tasks: Cohen's d = 0.74, p < 0.001 [1]
- LLM advantage on "effectiveness" (coherent, well-structured output): partial eta-squared = 0.208 [1]
- On Alternative Uses Task (AUT): LLMs match/exceed top human groups on fluency and average originality, but through fundamentally different mechanisms (retrieval+recombination vs intentional meaning-making) [1][5]
- General intelligence metrics do NOT predict divergent thinking capability (LiveIdeaBench) [6][17]

## What Works for Divergent Thinking

### 1. Temperature & Sampling (obvious but nuanced)
- Higher temperature (0.8-1.0) promotes divergent exploration
- Lower temperature (0.1-0.3) promotes convergent precision
- **But:** optimal temperature is model-specific and task-specific. The "entropy turning point" (EntP) — where the entropy curve shifts concave→convex — correlates strongly with peak accuracy. Simple "high=creative, low=precise" is an oversimplification [32]
- Top-p and temperature interact unpredictably; adjust one, not both [2][4]
- Presence penalty maximizes lexical diversity (good for brainstorming); frequency penalty allows controlled repetition (good for creative writing) [4]

### 2. Denial Prompting (novel, empirically validated)
- Iteratively forbid techniques/strategies used in previous solutions
- Forces models into less-traveled semantic space
- On Codeforces (199 problems): as constraints increase, solution correctness drops but divergent creativity score continually rises [18]
- Formalized as NEOGAUGE metric (measures both convergent correctness and divergent novelty) [18]
- **Mechanism:** prevents anchoring on high-probability training-distribution solutions

### 3. Persona-Based Mode Switching
- Study: "Taylor" persona (divergent, temp=0.8) vs "Alex" persona (convergent, temp=0.3) [12]
- Users' subjective perception of which persona helped creativity sometimes diverged from objective measures
- Making mode shifts explicit and visually distinct improves creative process outcomes vs blurring them in single chat [12][29]

### 4. Multi-Stage Workflows (brainstorm then refine)
- HAIExplore study: explicit brainstorming stage → refinement stage [29]
- Mitigated design fixation, improved perceived controllability
- Key insight: divergent and convergent are complementary, not sequential — need fluid movement with branching and revisiting [29]

### 5. Inference-Time Scaling
- Reasoning models (o3, R1) spend more compute exploring multiple solution traces
- Creates emergent divergent-like capability: internal exploration before output
- o3 rated highly by experts for "generating and critically evaluating novel hypotheses" [25]
- But: limited direct research on whether this is genuine divergent thinking vs sophisticated convergent search

## Benchmarks

| Benchmark | What it measures | Key finding |
|-----------|-----------------|-------------|
| **LiveIdeaBench** [6][17] | Scientific divergent thinking (5 Guilford dimensions) across 22 domains, 1180 keywords | General intelligence ≠ divergent capability |
| **Alternative Uses Task** [5][8] | Semantic distance of novel uses for common objects | Inter-model agreement >0.7 (Spearman); models don't favor own outputs |
| **TTCW** [15] | Creative writing (fluency, flexibility, originality, elaboration) | Reference-based eval achieves 0.75 pairwise accuracy (+15% over prior methods) |
| **Divergent Association Task** [27] | Verbal creativity (generate 10 maximally different words) | Validated on ~9K participants, 98 countries |
| **CS4** [33] | Creativity under escalating constraints (up to 39) | All LLMs degrade with more constraints; rate varies by model |
| **NEOGAUGE** [18] | Combined convergent (correctness) + divergent (novelty) | Shows inverse relationship under denial prompting |

## Implications for Our Infrastructure

### What we currently model
- Constitution mentions "Divergent (explore) → convergent (build)" as process heuristic
- `model-review` skill has `convergent/critical` and `divergent/creative` modes
- No explicit parameter switching between modes
- No formal mode detection or transition signals
- No measurement of divergent vs convergent quality in outputs

### Gaps (ranked by actionability)

**1. No explicit mode switching in agent sessions.**
Research strongly suggests that making divergent/convergent transitions explicit — with different parameters, prompts, and visual framing — outperforms blurring them. Our agents treat every turn the same way. The model-review skill's mode parameter is the closest we have, but it's only for cross-model dispatch.

**2. No temperature/parameter differentiation.**
We use default temperature for everything. Research shows this is suboptimal for both modes — divergent tasks need higher temperature and presence penalties, convergent tasks need lower. The entropy turning point finding [32] suggests this could even be auto-tuned per task type.

**3. Denial prompting not used anywhere.**
The most creative technique in the literature — iteratively forbidding previous approaches — maps directly to research and brainstorming tasks. When we ask "what are alternative explanations?" we should be denying the first explanation to force genuine alternatives, not just asking for more.

**4. No divergent thinking benchmarks.**
We measure convergent quality (did the code work? did the commit pass tests?) but never measure divergent quality (was the solution space adequately explored? were non-obvious alternatives surfaced?). LiveIdeaBench's finding that general intelligence ≠ divergent capability is a warning: our agents might be getting smarter at convergent tasks while stagnating at divergent ones.

**5. Brainstorm→refine workflow not formalized.**
The HAIExplore finding — that explicitly separating brainstorming from refinement mitigates design fixation — maps directly to how we should structure research sessions. Currently research is a single-mode conversation. Should be: divergent phase (explore widely, no evaluation) → convergent phase (evaluate, select, refine).

**6. High-uncertainty decisions don't get extended divergence.**
The "uncertainty × irreversibility" heuristic for time allocation is absent. When the orchestrator encounters a high-stakes decision, it should automatically extend the divergent phase rather than converging on the first plausible approach.

### Not worth maintaining (wrong fit, not wrong effort)

- **Automatic mode detection from conversation context.** Requires semantic classification that's unreliable and would need ongoing tuning. Better to make mode explicit via prompts/skill parameters.
- **Per-turn temperature optimization.** Requires model-specific calibration we can't do through the API. Prerequisite: API-level temperature/effort control per-turn.
- **Divergent thinking evals for every session.** Ongoing measurement overhead exceeds value. Better as periodic audits (no maintenance between runs).

## Synthesis: The Core Tension

LLMs are convergent machines being asked to do divergent work. The same training objective (predict most likely next token) that makes them excellent at convergent tasks makes them mediocre at genuine novelty. Every technique that improves divergent thinking works by **fighting the default** — higher temperature fights probability concentration, denial prompting fights pattern anchoring, explicit mode switching fights the tendency to blur exploration with evaluation.

Our infrastructure currently doesn't fight the default at all. We rely on the model's baseline divergent capability, which the research shows is "good at quantity and statistical diversity, poor at genuine novelty." The constitutional heuristic "divergent → convergent" is the right shape but has no enforcement, no tooling, and no measurement.

The lowest-hanging fruit: make divergent/convergent mode a first-class concept in skills and research workflows, with different system prompts and explicit phase transitions. Not temperature control (we can't via API), but prompt-level framing that tells the model "generate alternatives without evaluating" vs "evaluate and select."

## Additional Findings (second research pass, 2026-03-05)

### The "Artificial Hivemind" Effect (CREATIVEDC, arxiv 2512.23601)
The strongest paper found. Names the core problem: LLMs exhibit **intra-model repetition** (same model generates similar outputs) AND **inter-model homogeneity** (different models converge on the same outputs). RLHF amplifies this — alignment pushes toward statistically average responses, reducing creativity.

**CREATIVEDC method:** Two-phase prompting that explicitly scaffolds divergent then convergent thinking. Phase 1: "Think about different elements, objects, scenarios... push for unusual, surprising, unconventional ideas." Phase 2: "From your brainstormed ideas, select one and connect it with the required constraints."

**Results:** Semantic novelty +51.5% over baseline, +63.5% over CoT. No significant reduction in utility. At K=100 sampled outputs, CREATIVEDC generates 72% more effectively distinct problems than CoT (measured by Vendi Score). The diversity advantage *grows* with more samples — exactly the scaling property you want.

**Key insight:** Simply increasing temperature increases surface-level diversity but does NOT improve originality — and can reduce creativity. The two-phase scaffolding is what matters, not parameter tweaking. This validates your skepticism about meta-prompt libraries vs just using a normal prompt — but the "normal prompt" needs to explicitly separate "explore without constraints" from "now satisfy constraints."

### "Functional Fixedness" in LLMs
LLMs exhibit the same cognitive bias as humans — they fail to use familiar objects innovatively in creative problem-solving benchmarks. This is a training artifact: the model has learned conventional uses and struggles to override them. Explicit scaffolding (like CREATIVEDC's phase separation) overcomes this, but simply asking "be creative" does not.

### TinyTim: Specialized Divergent Models (arxiv 2508.11607)
Radical approach: fine-tune a small model on James Joyce's Finnegans Wake to create a *dedicated divergent generator*. The result: Yule's K lexical richness score 24x higher than baseline LLMs. But benchmark performance drops to 52% (vs 91% for baselines). The model is a "lexical inventor" — useful only when paired with a convergent system for filtering.

**Architectural implication:** Divergent and convergent might be better as **separate models** in an ensemble rather than trying to get one model to do both. The TinyTim→convergent-LLM pipeline is analogous to how the brain pairs Default Mode Network (divergent) with Executive Control Network (convergent).

This is interesting but impractical for us — we can't fine-tune models. The insight to take: when dispatching to multiple models in model-review brainstorming mode, one model could be prompted as the "wild ideas" generator while the other evaluates/refines.

### Nature Human Behaviour: Large-Scale Comparison (2025)
100,000 humans vs LLMs on DAT and creative writing. LLMs surpass average human performance but remain below the **top half** of human participants. Key: temperature and linguistic strategy prompts produce "reliable gains in semantic divergence for several models" — prompt design matters, but there's a ceiling.

### CreativityPrism (arxiv 2510.20091)
Holistic benchmark spanning multiple creativity dimensions (not just divergence). Argues existing evals are too narrow — real creativity involves convergent selection too, not just idea volume.

### "Beyond Divergent Creativity" (arxiv 2601.20546, Jan 2026)
Argues DAT focuses too much on novelty and ignores other creativity dimensions. LLM creativity assessment needs to be grounded in human creativity theory, not just semantic distance metrics.

### CogRouter: "Think Fast and Slow" for Agents (Feb 2026)
Dynamically adjusts cognitive depth per reasoning step, inspired by ACT-R cognitive theory. Not creativity-specific but relevant: agents should spend more compute on divergent/exploration steps and less on routine convergent steps. Adaptive compute allocation by step type.

### Multi-Agent Debate for Divergent Thinking (899 citations)
Liang et al. (EMNLP 2024): multi-agent debate encourages divergent thinking in LLMs for complex reasoning. Most cited paper in this space. The adversarial pressure from disagreeing agents forces exploration of alternatives — structurally similar to denial prompting but through social dynamics rather than explicit constraints.

### Hallucination-Creativity Connection
Survey (arxiv 2402.06647, 56 citations): Hallucinations and creativity share a mechanism — both involve generating low-probability continuations. The difference is whether the output is evaluated against ground truth (hallucination) or against novelty (creativity). This explains why techniques that reduce hallucination (RLHF, safety training) also reduce creativity.

### "550 Hallucinations, Zero Discoveries" (Feb 2026)
Forcing Claude to "invent mathematics" produced 550 hallucinations and zero genuine discoveries. Pure divergent generation without domain structure = noise. Divergent thinking needs constraints and domain knowledge to be productive — unconstrained generation is hallucination, not creativity.

## Updated Synthesis

The second pass reinforces the core finding but adds important nuance:

1. **The Artificial Hivemind is the real enemy, not "lack of creativity."** LLMs can be creative — they just converge on the *same* creative outputs. The problem isn't that any single output is bad; it's that 100 outputs look alike. CREATIVEDC shows that two-phase scaffolding fixes this at scale (72% more distinct outputs at K=100).

2. **Temperature is a red herring for originality.** Multiple papers now confirm: higher temperature increases surface diversity (different words) without improving semantic novelty (different ideas). The CREATIVEDC result is definitive — scaffolding beats parameter tweaking.

3. **The hallucination-creativity tradeoff is real and structural.** RLHF/safety training reduces both. "Be creative" fights against alignment training. Explicit phase separation ("now explore freely, evaluation comes later") is the workaround.

4. **Multi-agent debate ≈ denial prompting through social dynamics.** Both force the model off its default trajectory. Our model-review brainstorming mode already does this (two models generating independently). Could be enhanced by having them explicitly disagree and iterate.

5. **Unconstrained divergence = hallucination.** The "550 Hallucinations" finding is a corrective — divergent thinking isn't "generate randomly." It's "explore broadly *within domain structure*." CREATIVEDC's Phase 1 works because it's still thematically anchored.

## Key Papers to Track

- LiveIdeaBench (arxiv 2412.17596) — monthly-updated divergent thinking benchmark
- Denial prompting / NEOGAUGE (NAACL 2025, aclanthology 2025.naacl-long.141)
- Entropy turning point (arxiv 2502.05234) — task-adaptive temperature
- HAIExplore (arxiv 2512.18388) — brainstorm→refine workflow design
- Persona-guided divergent/convergent (arxiv 2510.26490)
- CS4 creativity under constraints (arxiv 2410.04197)
- CREATIVEDC / Artificial Hivemind (arxiv 2512.23601) — two-phase scaffolding, Vendi Score scaling
- TinyTim divergent models (arxiv 2508.11607) — specialized divergent fine-tuning
- Nature Human Behaviour large-scale comparison (doi 10.1038/s41562-025-02331-1)
- CreativityPrism holistic benchmark (arxiv 2510.20091)
- CogRouter adaptive cognitive depth (Feb 2026)
- Multi-agent debate for divergence (arxiv 2305.19118, 899 citations)

## Citations

[1] PMC 12942112 — Human vs LLM creativity comparison (propositional + creative writing)
[2] promptengineering.org — Temperature and top-p guide
[4] promptingguide.ai — LLM inference settings
[5] arxiv 2411.15560 — Inter-model agreement on AUT creativity assessment
[6][17] arxiv 2412.17596 — LiveIdeaBench
[12] arxiv 2510.26490 — Persona-guided divergent/convergent interfaces
[15] arxiv 2504.15784 — TTCW automated evaluation
[18] NAACL 2025.naacl-long.141 — Denial prompting, NEOGAUGE
[25] OpenAI o3/o4-mini announcement
[27] datcreativity.com — Divergent Association Task
[29] arxiv 2512.18388 — HAIExplore brainstorm→refine
[32] arxiv 2502.05234 — Entropy turning point, adaptive temperature
[33] arxiv 2410.04197 — CS4 creativity under constraints

<!-- knowledge-index
generated: 2026-03-22T00:13:51Z
hash: d04d4b4e4e72


end-knowledge-index -->
