---
title: "Agent / LLM Evaluation Frontier - Verification, Scientific Reasoning, and Genomics"
date: 2026-05-11
tier: standard
ground_truth: benchmarking-science-2026.md, epistemic-quality-evals.md, factual-verification-systems.md, genomics-benchmark-design.md
---

# Agent / LLM Evaluation Frontier - Verification, Scientific Reasoning, and Genomics

**Question:** What is newest along agent/LLM evaluation dimensions, especially new ways to evaluate and benchmark fact verification, scientific reasoning, genomics, and different verification setups?

**Date anchor:** 2026-05-11. This scan prioritizes 2026 papers and benchmarks, with 2025 work included only when it is now a live benchmark or directly explains a 2026 seam.

**Verdict:** The field has shifted from "does the final answer look right?" toward **process- and verifier-aware evals**: trace-level epistemics, claim-level audit trails, executable verification, repeated-run robustness, evaluator-channel blinding, and domain-specific biological/genomics tasks. For this repo, the useful move is not another broad leaderboard. It is a small, versioned verification harness that compares 3-5 setups on the same claim set: baseline answer, retrieval verifier, cross-model verifier, executable/database verifier where possible, and human/auditor adjudication for disagreements.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|---|---|---|---|---|
| 1 | Scientific-agent evals are now measuring epistemic process, not only task success. | AI scientists paper: >25,000 runs; reports evidence ignored in 68% of traces, refutation-driven belief revision in 26%, base model explains 41.4% of variance vs scaffold 1.5%. | MEDIUM | DOI: 10.48550/arXiv.2604.18805 | PREPRINT |
| 2 | Deep-research eval has split into answer-finding, synthesis, and rubric-compliance families. | BrowseComp, DEEPSYNTH, ResearchRubrics measure different constructs: hard web answer finding, multi-source structured synthesis, and expert-rubric compliance. | HIGH | OpenAI BrowseComp; DOI: 10.48550/arXiv.2511.07685; DEEPSYNTH ICLR 2026 page | VERIFIED |
| 3 | Claim-level fact verification is moving toward revisable benchmarks and auditors, not static labels. | DeepFact proposes Audit-then-Score; one-shot expert labeling hit 60.8% on hidden micro-gold, while auditor-mediated rounds raised accuracy to 90.9%. | MEDIUM | DOI: 10.48550/arXiv.2603.05912 | PREPRINT |
| 4 | Claim decomposition helps only when sub-claims have aligned evidence; repeated coarse evidence can degrade results. | Alignment Bottleneck evaluates SAE vs SRE and finds decomposition improvements depend on granular aligned evidence and reliable sub-claim labels. | MEDIUM | DOI: 10.48550/arXiv.2602.10380 | PREPRINT |
| 5 | Consensus/voting is not a substitute for verification in domains without external verifiers. | Consensus is Not Verification reports no consistent accuracy gains even at 25x inference cost; errors are strongly correlated across models and samples. | MEDIUM | DOI: 10.48550/arXiv.2603.06612 | PREPRINT |
| 6 | Cross-model verification is useful, but its value comes from diversity and targeted disagreement, not naive majority vote. | FINCH-ZK improves FELM hallucination detection F1 by 6-39% using fine-grained cross-model consistency; Consensus paper limits pure polling. | MEDIUM | DOI: 10.48550/arXiv.2508.14314; DOI: 10.48550/arXiv.2603.06612 | PREPRINT |
| 7 | Executable verification is now a distinct fact-checking benchmark class. | ClaimDB uses 80 real databases; verification requires programmatic interaction, and more than half of 30 models score below 55% accuracy. | MEDIUM | DOI: 10.48550/arXiv.2601.14698 | ACL 2026 main / arXiv |
| 8 | Genomics eval is splitting into raw-sequence behavior and gene-knowledge reasoning. | GenomeQA: 5,200 sequence tasks across six task families; SciHorizon-GENE: >540K gene-to-function questions over >190K human genes. | MEDIUM | DOI: 10.48550/arXiv.2604.05774; DOI: 10.48550/arXiv.2601.12805 | PREPRINT |
| 9 | General biological-agent work is converging on workflow-level evaluation: planning, tool use, feedback loops, reproducibility. | Briefings in Bioinformatics survey reviews 115 studies and uses a 5D taxonomy including evaluation strategies and resource integration. | HIGH | DOI: 10.1093/bib/bbag075 | PEER REVIEWED |
| 10 | Repeated-run robustness is becoming a first-class agent metric. | Claw-Eval uses `Pass^3`: success only if the agent passes the same task in all three independent runs. | MEDIUM | GitHub: claw-eval/claw-eval; DOI: 10.48550/arXiv.2604.06132 | TOOL / PREPRINT |
| 11 | Evaluator-channel leakage is becoming benchmarked directly. | AuditRepairBench studies leaderboard instability from evaluator-derived signals; screening-guided blinding patches reportedly reduce rank displacement by mean 62%. | LOW-MEDIUM | DOI: 10.48550/arXiv.2605.04624 | VERY NEW PREPRINT |

## What Changed Since The March Memos

### 1. The strongest new seam is process epistemics

The April 2026 scientific-agent paper is the most directly relevant new result. It evaluates LLM-based scientific agents across eight domains and more than 25,000 runs, then separates model/scaffold performance from epistemic behavior. The headline is not just that agents fail. It is that outcome success can hide unscientific reasoning: evidence gets ignored, refutation rarely changes belief, and multi-test convergence is rare. [SOURCE: https://arxiv.org/abs/2604.18805]

This updates our older stance from "agent eval should include traces" to a stricter rule: **scientific-agent evals should score trace behavior as a target construct, not as debugging metadata.** For genomics and scientific claim work, final-answer accuracy is insufficient if the agent skipped contradictory evidence or failed to revise after a failed source lookup.

### 2. Deep research eval has fragmented into three different jobs

The new benchmarks are not interchangeable:

- **BrowseComp** measures persistent web answer-finding. It is intentionally hard to find but easy to verify once found. OpenAI reports human trainers solved 29.2% of the verification-campaign problems within the two-hour rule, Deep Research scored 51.5%, and best-of-N / voting strategies improved performance by 15-25% over a single attempt. [SOURCE: https://openai.com/index/browsecomp/]
- **DEEPSYNTH** measures multi-source synthesis with structured outputs. It has 120 tasks across seven domains and reports very low scores even for deep-research agents; the project page reports top F1 of 8.97. [SOURCE: https://agentdeepsynthesis.github.io/deepsynth.github.io/]
- **ResearchRubrics** measures long-form research quality against expert-written rubric criteria. It uses 2,800+ hours of human labor and 2,500+ rubric criteria, and reports leading DR systems below 68% average compliance. [SOURCE: https://openreview.net/forum?id=ErnvfmSX0P]

Implication: do not ask "which benchmark is best?" Ask which construct matters. For our research outputs, ResearchRubrics is closer to memo quality, BrowseComp is closer to source discovery, and DEEPSYNTH is closer to structured evidence synthesis.

### 3. Static fact-check labels are losing authority

DeepFact is important because it attacks the benchmark construction problem itself. It argues that deep research report factuality is hard enough that even PhD-level specialists only reached 60.8% one-shot accuracy on a hidden micro-gold set, but became much more reliable as auditors in a revisable benchmark process. [SOURCE: https://arxiv.org/abs/2603.05912]

This maps well to the repo's claim-governance work: the durable object should not just be a label; it should be a **versioned verdict with rationale, evidence, and revision history**. A verifier disagreeing with the benchmark should submit evidence, not just a score.

### 4. Decomposition is conditional, not magic

The Alignment Bottleneck paper is the best current warning against naive "break every answer into claims and verify each one." Decomposition improves verification only when the evidence is aligned to each sub-claim. Reusing the same broad evidence bundle for every sub-claim can fail or degrade verification. [SOURCE: https://arxiv.org/abs/2602.10380]

For genomics, this means a claim like "variant X likely affects drug Y via gene Z" should not be checked against one pile of papers. The variant, gene function, drug mechanism, guideline, and population-frequency sub-claims need separate evidence objects and separate uncertainty states.

### 5. Cross-model review needs a verifier boundary

Two results now bracket the right use of cross-model setups:

- FINCH-ZK supports cross-model consistency as a black-box hallucination detection/mitigation method, with reported F1 improvements over baselines. [SOURCE: https://arxiv.org/abs/2508.14314]
- Consensus is Not Verification says pure polling/aggregation does not reliably scale truthfulness in verifier-absent domains, even with much more inference compute. [SOURCE: https://arxiv.org/abs/2603.06612]

The synthesis: use cross-model review to find disagreement, catch model-family blind spots, and propose repairs. Do not treat agreement as proof. The proof comes from external evidence, executable checks, or adjudicated source review.

### 6. Executable verification is becoming a benchmark class

ClaimDB is the cleanest 2026 example. The evidence cannot be stuffed into context; the verifier has to run database queries. The benchmark stresses abstention as well as true/false verification, and more than half of evaluated models scored below 55%. [SOURCE: https://arxiv.org/abs/2601.14698]

This is directly relevant to genomics and agent-infra. Many real claims are not "find the sentence in a paper"; they are "compute whether the artifact, registry, VCF, table, or KG supports this statement." That should be evaluated with tool-execution traces, not prose judging.

### 7. Genomics-specific LLM eval is finally becoming concrete

Two 2026 genomics benchmarks are worth tracking:

- **GenomeQA** tests general-purpose LLMs on raw genome sequence tasks, 5,200 samples, sequence lengths 6-1,000 bp, six task families. It finds models can exploit local signals like GC content and motifs but degrade on indirect or multi-step sequence inference. [SOURCE: https://arxiv.org/abs/2604.05774]
- **SciHorizon-GENE** tests gene-to-function reasoning over curated biological databases, with >540K questions covering >190K human genes and explicit failure dimensions: attention sensitivity, hallucination tendency, completeness, and literature influence. [SOURCE: https://arxiv.org/abs/2601.12805]

These are not substitutes for WGS-pipeline validation. They test LLM behavior around genomic sequence and gene knowledge. For personal genomics verification, they are useful as **agent reasoning benchmarks**, while GIAB/hap.py/PharmCAT/ClinVar/gnomAD checks remain the primary biological truth surfaces.

## Comparing Verification Setups

| Setup | Best For | Failure Mode | Current Evidence |
|---|---|---|---|
| Single-model answer + citations | Cheap first pass | Fluent unsupported synthesis | Not enough for high-stakes scientific claims |
| Retrieval verifier | Dynamic factual claims with web/paper evidence | Bad retrieval amplifies false confidence | SAFE/VeriScore line; DeepFact pushes this toward auditable report factuality |
| Claim decomposition | Complex claims with separable components | Hurts if sub-claims share coarse evidence or labels are noisy | Alignment Bottleneck |
| Cross-model verifier | Surfacing disagreement and model-family blind spots | Agreement is not truth; correlated errors | FINCH-ZK plus Consensus is Not Verification |
| Executable verifier | Structured data, code, pipeline artifacts, databases | SQL/tool errors mixed with reasoning errors | ClaimDB |
| Repeated-run robustness | Agent reliability under stochastic trajectories | Expensive; can still share blind spots | Claw-Eval Pass^3, BrowseComp 64-trial analysis |
| Human/auditor adjudication | Gold labels and high-stakes disagreements | Slow; one-shot labelers are noisy | DeepFact Audit-then-Score |
| Process-level trace scoring | Scientific reasoning quality | Requires rubric discipline; judge reliability risk | SeekBench, AI Scientists, ResearchRubrics |

## Recommendations For This Repo

1. **Build a small comparative verifier harness, not a new benchmark.** Use 30-50 claims from existing genomics/agent-infra artifacts, each with a canonical source route. Run the same claims through: baseline model, retrieval verifier, cross-model verifier, executable verifier where applicable, and human/auditor adjudication for conflicts.

2. **Make evidence alignment the unit of design.** Store sub-claim -> evidence object links. A claim should not be "verified" because a broad source bundle was retrieved. Each sub-claim should know which evidence span, table query, artifact hash, or database record supports it.

3. **Track process failures separately from outcome failures.** Add trace-level flags: ignored contradiction, no evidence recovery after weak result, overconfident unsupported claim, failed abstention, verifier-channel leakage, and tool result misread.

4. **Use cross-model review as a disagreement finder.** It belongs before adjudication, not after as a verdict. Agreement between Claude/GPT/Gemini should at most lower priority; it should not close scientific claims.

5. **For genomics, split eval lanes.** LLM reasoning benchmarks like GenomeQA and SciHorizon-GENE evaluate agent cognition. Pipeline validation remains GIAB/hap.py/PharmCAT/ClinVar/gnomAD/source-attestation. Do not collapse them into one "genomics benchmark."

6. **Adopt revisable labels for research factuality.** DeepFact's Audit-then-Score model matches the repo's claim-governance direction: labels should be mutable only through evidence-bearing adjudication and versioned rationale.

## Open Questions

- Does cross-model verification still help once every model has seen the same public benchmark and public paper set? The Consensus paper suggests correlated errors are structural; FINCH-ZK suggests fine-grained diversity still helps. The boundary is not settled.
- Which process metrics predict downstream correctness in scientific/genomics agents? AI Scientists and SeekBench show process failures, but the causal relationship to later artifact quality needs local measurement.
- How much of ResearchRubrics-style compliance transfers to biological/genomics reports? Its rubric families are promising, but the benchmark is domain-diverse rather than genomics-specific.
- Can a 30-50 claim local harness produce stable enough signal to compare verifier setups? Likely yes for error taxonomy, not for leaderboard-style model ranking.

## Search Log

- Local ground truth: `research/benchmarking-science-2026.md`, `research/epistemic-quality-evals.md`, `research/factual-verification-systems.md`, `research/genomics-benchmark-design.md`.
- Queries: `LLM agent scientific reasoning benchmark epistemic process evaluation 2026`; `LLM fact verification benchmark claim decomposition cross model verification 2026`; `LLM genomics benchmark gene reasoning genome sequence understanding 2026`; `LLM benchmark construct validity reliability label noise contamination 2026`.
- Live sources opened: AI Scientists, GenomeQA, SciHorizon-GENE, MIMeBench reasoning evaluation, DeepFact, ResearchRubrics, SeekBench, DEEPSYNTH, BrowseComp, Alignment Bottleneck, FINCH-ZK, ClaimDB, PCC fact-checking, Consensus is Not Verification, biological AI agents survey, Claw-Eval, AuditRepairBench.

## Sources

- AI scientists produce results without reasoning scientifically - https://arxiv.org/abs/2604.18805
- GenomeQA - https://arxiv.org/abs/2604.05774
- SciHorizon-GENE - https://arxiv.org/abs/2601.12805
- A Comprehensive Evaluation of LLM Reasoning - https://arxiv.org/abs/2601.13243
- DeepFact - https://arxiv.org/abs/2603.05912
- ResearchRubrics - https://openreview.net/forum?id=ErnvfmSX0P and https://arxiv.org/abs/2511.07685
- SeekBench - https://arxiv.org/abs/2509.22391
- DEEPSYNTH - https://agentdeepsynthesis.github.io/deepsynth.github.io/
- BrowseComp - https://openai.com/index/browsecomp/
- Alignment Bottleneck - https://arxiv.org/abs/2602.10380
- FINCH-ZK - https://arxiv.org/abs/2508.14314
- ClaimDB - https://arxiv.org/abs/2601.14698
- PCC fact-checking - https://arxiv.org/abs/2601.02574
- Consensus is Not Verification - https://arxiv.org/abs/2603.06612
- Artificial Intelligence agents for biological research: a survey - https://doi.org/10.1093/bib/bbag075
- Claw-Eval - https://github.com/claw-eval/claw-eval
- AuditRepairBench - https://arxiv.org/abs/2605.04624
