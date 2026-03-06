# Divergent vs Convergent Thinking in LLMs

**Date:** 2026-03-05
**Status:** Initial synthesis
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

### What NOT to build (low ROI or premature)

- **Automatic mode detection from conversation context.** Tempting but requires semantic classification that's unreliable. Better to make mode explicit via prompts/skill parameters.
- **Per-turn temperature optimization.** The entropy turning point research is interesting but requires model-specific calibration we can't do through the API. Wait for API-level support.
- **Divergent thinking evals for every session.** Measurement overhead would exceed benefit. Better as periodic audits.

## Synthesis: The Core Tension

LLMs are convergent machines being asked to do divergent work. The same training objective (predict most likely next token) that makes them excellent at convergent tasks makes them mediocre at genuine novelty. Every technique that improves divergent thinking works by **fighting the default** — higher temperature fights probability concentration, denial prompting fights pattern anchoring, explicit mode switching fights the tendency to blur exploration with evaluation.

Our infrastructure currently doesn't fight the default at all. We rely on the model's baseline divergent capability, which the research shows is "good at quantity and statistical diversity, poor at genuine novelty." The constitutional heuristic "divergent → convergent" is the right shape but has no enforcement, no tooling, and no measurement.

The lowest-hanging fruit: make divergent/convergent mode a first-class concept in skills and research workflows, with different system prompts and explicit phase transitions. Not temperature control (we can't via API), but prompt-level framing that tells the model "generate alternatives without evaluating" vs "evaluate and select."

## Key Papers to Track

- LiveIdeaBench (arxiv 2412.17596) — monthly-updated divergent thinking benchmark
- Denial prompting / NEOGAUGE (NAACL 2025, aclanthology 2025.naacl-long.141)
- Entropy turning point (arxiv 2502.05234) — task-adaptive temperature
- HAIExplore (arxiv 2512.18388) — brainstorm→refine workflow design
- Persona-guided divergent/convergent (arxiv 2510.26490)
- CS4 creativity under constraints (arxiv 2410.04197)

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
