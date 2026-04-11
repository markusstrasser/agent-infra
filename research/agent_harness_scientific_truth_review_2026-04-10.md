# Agent Harness / Scientific-Agent / Truth-Seeking Review

**Question:** What recent papers from February to April 2026 matter for harness engineering, scientific agents, and truth-seeking / verification agents?  
**Tier:** Standard  
**Date:** 2026-04-10

## Scope

- Window searched: 2026-02-01 through 2026-04-10
- Focus:
  - harness engineering / agent evaluation infrastructure
  - scientific-agent benchmarking and design
  - truth-seeking / verification-oriented agent architectures
- Excluded from main list:
  - older benchmark baselines outside the window
  - generic surveys unless they introduced a new 2026 framework or benchmark

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | The strongest recent harness-engineering seam is moving evaluation from ad hoc wrappers to explicit control-plane objects: versioned snapshots, budget gates, traces, and standardized observation interfaces. | VeRO and the standardization papers all center the harness itself as the unit of control rather than just the agent or benchmark. | HIGH | `arXiv:2602.22480`, `arXiv:2602.18029`, `arXiv:2603.15798` | VERIFIED |
| 2 | The strongest recent scientific-agent benchmarking seam is shifting from “write a paper and let an LLM judge it” toward executable or rediscovery-based evaluation. | FIRE-Bench, SciVisAgentBench, and SciNav all bias toward verifiable outputs or diagnostic evaluation. | HIGH | `arXiv:2602.02905`, `arXiv:2603.29139`, `arXiv:2603.20256` | VERIFIED |
| 3 | The most relevant truth-seeking paper in this window is AutoVerifier, which treats verification as layered evidence processing rather than one-shot judging. | It decomposes claims into triples and runs six verification layers, including intra-document, cross-source, and external corroboration. | HIGH | `arXiv:2604.02617` | VERIFIED |
| 4 | The ecosystem is converging on “evaluation as an operating discipline” rather than “a final benchmark score.” | Recent papers repeatedly frame evaluation as a runtime control function, not a scoreboard. | MEDIUM | `arXiv:2602.18029`, `arXiv:2602.22480`, `arXiv:2603.15798` | VERIFIED |
| 5 | For scientific coding tasks, relative comparison / ranking inside search now looks more promising than absolute scoring alone. | SciNav explicitly argues for pairwise relative judgments in top-K tree search and reports gains over OpenHands and Self-Debug. | MEDIUM | `arXiv:2603.20256` | VERIFIED |

## Key Papers

### 1. VeRO: An Evaluation Harness for Agents to Optimize Agents

- Date: 2026-02-25
- Link: https://arxiv.org/abs/2602.22480
- Why it matters:
  - VeRO is one of the clearest statements that agent optimization is not ordinary SWE.
  - Its core objects are the right ones: versioned snapshots, budget-enforced evaluation, structured traces, permission control, reproducible execution, and a standardized observation interface. [SOURCE: https://arxiv.org/abs/2602.22480] [PREPRINT]
  - This is directly relevant if you want a harness that can optimize agents or compare optimization strategies without fooling itself.
- Useful details:
  - The paper formalizes the optimizer, the observation function, and the budgeted evaluation loop. [SOURCE: https://arxiv.org/abs/2602.22480] [PREPRINT]
  - It treats the harness as infrastructure for fair comparison, not just convenience glue. [SOURCE: https://arxiv.org/abs/2602.22480] [PREPRINT]

### 2. Towards More Standardized AI Evaluation: From Models to Agents

- Date: 2026-02-20
- Link: https://arxiv.org/abs/2602.18029
- Why it matters:
  - This is not a benchmark paper; it is a conceptual reset.
  - The paper’s central move is to say evaluation for agents is a control function, not a final checkpoint. [SOURCE: https://arxiv.org/abs/2602.18029] [PREPRINT]
  - It is strongest as framing for why agent harnesses need auditability, behavior-over-time measurement, and explicit lifecycle discipline.
- Useful details:
  - It distinguishes model evaluation from agent evaluation by focusing on trajectories, variability, environment setup, and hidden harness assumptions. [SOURCE: https://arxiv.org/abs/2602.18029] [PREPRINT]
  - Its strongest practical implication is that scores without harness transparency are closer to theater than measurement. [INFERENCE from paper’s framing]

### 3. FIRE-Bench: Evaluating Agents on the Rediscovery of Scientific Insights

- Date: 2026-02-02
- Link: https://arxiv.org/abs/2602.02905
- Why it matters:
  - This is the best recent paper on evaluating scientific agents without collapsing into subjective “paper quality” judging.
  - Its core trick is constrained rediscovery: agents get a high-level research question from a published paper, but not the original implementation or conclusion, and are evaluated on whether they rediscover the verified finding. [SOURCE: https://arxiv.org/abs/2602.02905] [PREPRINT]
- Useful details:
  - The paper states that even the strongest agents remain below `50` F1 on rediscovery and show high variance across runs. [SOURCE: https://arxiv.org/abs/2602.02905] [PREPRINT]
  - It explicitly diagnoses failures by research stage rather than only final score. [SOURCE: https://arxiv.org/abs/2602.02905] [PREPRINT]
- Why this is a better benchmark pattern:
  - It avoids the worst failure mode of “LLM judges a generated paper.”
  - It avoids trivial leaderboard optimization.
  - It grounds evaluation in verifiable scientific conclusions rather than vibes. [INFERENCE]

### 4. CUBE: A Standard for Unifying Agent Benchmarks

- Date: 2026-03-16
- Link: https://arxiv.org/abs/2603.15798
- Why it matters:
  - CUBE is the sharpest “benchmark integration tax” paper in this window.
  - It argues that benchmark fragmentation is becoming a research bottleneck and proposes a standard built around separable layers: task, benchmark, package, and registry. [SOURCE: https://arxiv.org/abs/2603.15798] [PREPRINT]
- Useful details:
  - The paper explicitly targets wrap-once / use-everywhere interoperability. [SOURCE: https://arxiv.org/abs/2603.15798] [PREPRINT]
  - It is more useful as an interface standard than as a semantics standard. That is, it standardizes benchmark plumbing, not truth. [INFERENCE]
- Relevance:
  - Strong for cross-benchmark evaluation infra.
  - Weak as a substitute for an internal epistemic ledger or claim graph.

### 5. Meta-Harness: End-to-End Optimization of Model Harnesses

- Date: 2026-03-30
- Link: https://arxiv.org/abs/2603.28052
- Why it matters:
  - This is the cleanest “harness engineering is first-class” paper in the window.
  - It treats harness code itself as the search target and uses an outer-loop agent to search over harness variants using source code, scores, and execution traces of prior candidates. [SOURCE: https://arxiv.org/abs/2603.28052] [PREPRINT]
- Useful details:
  - It reports `+7.7` points over a prior context-management baseline in online text classification while using `4x` fewer context tokens. [SOURCE: https://arxiv.org/abs/2603.28052] [PREPRINT]
  - It reports a `+4.7` point average gain on `200` IMO-level retrieval-augmented math problems across five held-out models. [SOURCE: https://arxiv.org/abs/2603.28052] [PREPRINT]
  - Its most important design claim is that richer access to prior traces and code beats compressed, memoryless feedback for harness optimization. [SOURCE: https://arxiv.org/abs/2603.28052] [PREPRINT]

### 6. SciVisAgentBench: A Benchmark for Evaluating Scientific Data Analysis and Visualization Agents

- Date: 2026-03-31
- Link: https://arxiv.org/abs/2603.29139
- Why it matters:
  - This is one of the most credible recent domain-specific scientific-agent benchmarks because it combines expert-authored cases with multimodal, outcome-centric evaluation.
  - It contains `108` expert-crafted cases and combines LLM-based judging with deterministic evaluators such as image metrics, code checkers, rule-based verifiers, and case-specific evaluators. [SOURCE: https://arxiv.org/abs/2603.29139] [PREPRINT]
- Useful details:
  - The benchmark includes a validity study with `12` SciVis experts to compare human and LLM judgments. [SOURCE: https://arxiv.org/abs/2603.29139] [PREPRINT]
- Relevance:
  - Strong signal that serious scientific-agent benchmarks are becoming hybrid: LLM judges plus hard evaluators.

### 7. SciNav: A General Agent Framework for Scientific Coding Tasks

- Date: 2026-03-11
- Link: https://arxiv.org/abs/2603.20256
- Why it matters:
  - Unlike open-ended “AI scientist” systems, SciNav is aimed at scientific coding tasks with executable outputs.
  - Its main idea is Top-K Comparative Tree Search using pairwise relative judgments instead of relying on absolute scores or task-specific reward shaping during search. [SOURCE: https://arxiv.org/abs/2603.20256] [PREPRINT]
- Useful details:
  - The paper reports up to `24%` relative gain in success rate over Self-Debug on ScienceAgentBench and `7.8` absolute points improvement in VER. [SOURCE: https://arxiv.org/abs/2603.20256] [PREPRINT]
  - It reports a `29` absolute-point gain on DA-Code data-manipulation and statistical-analysis tasks. [SOURCE: https://arxiv.org/abs/2603.20256] [PREPRINT]
- Relevance:
  - Good evidence for “comparative selection inside search” as a practical design pattern for scientific agents under limited budget.

### 8. AutoVerifier: An Agentic Automated Verification Framework Using Large Language Models

- Date: 2026-04-03
- Link: https://arxiv.org/abs/2604.02617
- Why it matters:
  - This is the most directly relevant truth-seeking / verification architecture in the window.
  - The framework decomposes technical assertions into claim triples and runs six layers: corpus construction, entity and claim extraction, intra-document verification, cross-source verification, external signal corroboration, and final hypothesis matrix generation. [SOURCE: https://arxiv.org/abs/2604.02617] [PREPRINT]
- Useful details:
  - It explicitly separates surface factuality from methodological validity. [SOURCE: https://arxiv.org/abs/2604.02617] [PREPRINT]
  - It uses provenance classes for claims and down-weights correlated sources via author/institution/citation overlap. [SOURCE: https://arxiv.org/abs/2604.02617] [PREPRINT]
- Relevance:
  - If the target is “truth-seeking agent” rather than “agent that looks smart,” this is the most useful design in the set.

## Themes That Actually Matter

### A. Harness is becoming the control plane

Recent work is converging on the idea that the harness is not a wrapper around the model. It is the system that:

- defines observation boundaries
- enforces budget
- versions changes
- stores traces
- standardizes evaluation conditions
- decides what experience is visible to optimization loops

The papers that say this most clearly are VeRO, Meta-Harness, and the standardization paper. [SOURCE: https://arxiv.org/abs/2602.22480] [SOURCE: https://arxiv.org/abs/2603.28052] [SOURCE: https://arxiv.org/abs/2602.18029]

### B. The field is moving away from “paper generation judged by LLMs”

The strongest scientific-agent papers in this window avoid pure paper-level judging:

- FIRE-Bench uses rediscovery of known findings
- SciVisAgentBench uses deterministic evaluators plus LLM judges
- SciNav focuses on executable scientific coding tasks

This is a healthy direction. It privileges verifiability over spectacle. [INFERENCE]

### C. Truth-seeking is becoming layered, not monolithic

AutoVerifier is important because it does not ask one model for one verdict. It turns verification into a pipeline:

- evidence ingestion
- claim extraction
- local coherence
- cross-source contradiction analysis
- external corroboration
- explicit hypothesis assessment

That is much closer to a real verification workflow than debate-only or judge-only systems. [SOURCE: https://arxiv.org/abs/2604.02617]

### D. Relative comparison is beating absolute scoring in some agent loops

Meta-Harness and SciNav both push in this direction from different angles:

- richer access to prior traces and outcomes
- pairwise or comparative judgment
- outer-loop optimization over harness or solution structure

This matters because scalar reward or one-shot absolute scoring appears too lossy for agent design loops. [INFERENCE from `Meta-Harness` and `SciNav`]

## What Looks Most Useful For Us

### Highest-signal ideas

1. **VeRO’s harness requirements**  
   Versioned snapshots, budget enforcement, standardized observation interfaces, and structured traces are the most reusable control-plane ideas in this set. [SOURCE: https://arxiv.org/abs/2602.22480]

2. **FIRE-Bench’s rediscovery framing**  
   If you want to measure “scientific reasoning” without theater, rediscovery of verified findings is the best pattern here. [SOURCE: https://arxiv.org/abs/2602.02905]

3. **AutoVerifier’s layered verification stack**  
   This is the strongest truth-seeking architecture in the list. [SOURCE: https://arxiv.org/abs/2604.02617]

4. **Meta-Harness’s richer memory for optimization**  
   The strongest harness-engineering result is not just “search over prompts,” but “search over harness code with full prior traces available.” [SOURCE: https://arxiv.org/abs/2603.28052]

5. **SciNav’s pairwise relative selection**  
   Useful where scientific coding quality is hard to score directly but easy to compare. [SOURCE: https://arxiv.org/abs/2603.20256]

### Lower-signal or more infrastructure-heavy

- **CUBE** is useful if the main pain is benchmark integration tax. It is less useful if the main pain is epistemic truth or claim semantics. [SOURCE: https://arxiv.org/abs/2603.15798]
- **General Agent Evaluation** is valuable for broad agents, but less specific to scientific truth-seeking than FIRE-Bench or AutoVerifier. [SOURCE: https://arxiv.org/abs/2602.22953] [PREPRINT]

## Bottom Line

The last three months do not show one single dominant architecture. They show a convergence on three separable layers:

1. **Harness / control plane**  
   VeRO, Meta-Harness, CUBE, and the standardization paper all say the harness is where trust and comparability are engineered.

2. **Scientific-agent benchmark shape**  
   FIRE-Bench, SciVisAgentBench, and SciNav all move toward executable, rediscovery-based, or hybrid deterministic evaluation rather than pure subjective judging.

3. **Truth-seeking / verification loop**  
   AutoVerifier is the clearest example of layered, provenance-aware, cross-source verification.

If forced to compress the whole scan into one line:

> The center of gravity is shifting from “build a clever agent” to “build a measurable harness, evaluate it on verifiable scientific tasks, and use layered verification rather than one-shot judging.” [INFERENCE]

## Sources

- VeRO: https://arxiv.org/abs/2602.22480
- Towards More Standardized AI Evaluation: https://arxiv.org/abs/2602.18029
- FIRE-Bench: https://arxiv.org/abs/2602.02905
- General Agent Evaluation: https://arxiv.org/abs/2602.22953
- CUBE: https://arxiv.org/abs/2603.15798
- SciNav: https://arxiv.org/abs/2603.20256
- Meta-Harness: https://arxiv.org/abs/2603.28052
- SciVisAgentBench: https://arxiv.org/abs/2603.29139
- AutoVerifier: https://arxiv.org/abs/2604.02617
