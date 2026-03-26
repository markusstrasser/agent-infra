---
title: Portable Patterns from AI Scientist v2
date: 2026-03-26
status: active
tags: [autonomous-research, verification, self-improvement]
---

# Portable Patterns from AI Scientist v2

**Source:** Sakana AI, "The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery"
- Nature paper: https://www.nature.com/articles/s41586-026-10265-5
- Blog: https://sakana.ai/ai-scientist-nature/
- [SOURCE: Nature 2026, Sakana AI blog 2026-03-26]

## What It Is

Autonomous ML research agent. Full lifecycle: ideation, literature review, experiment (parallelized agentic tree search), paper writing (LaTeX + vision-model feedback on figures), automated self-review.

A generated paper scored 6.33 at ICLR 2025's ICBINB workshop — above human acceptance threshold, beat 55% of human papers. Automated Reviewer achieved 69% balanced accuracy vs human reviewers (F1 exceeds NeurIPS 2021 inter-human agreement).

## Patterns Worth Porting

### 1. Pre-Output Quality Gate (Automated Reviewer)

**Pattern:** Run verification *before* finalizing output, not as post-hoc check.
**Their implementation:** Automated Reviewer scores papers before "submission."
**Our implementation:** Wired `verify_claim` into research-cycle's verify phase (2026-03-26). When executed item produces research memos, extract 3-5 factual claims and verify via Exa before marking PASS. Contradicted claims (confidence >0.7) trigger revert flow.
**Why it matters:** Hooks currently check "did you cite something?" (provenance tags). The new gate checks "is what you cited correct?" (factual accuracy). Different failure modes.

### 2. Agentic Tree Search vs Evolutionary Mutation

**Their approach:** Parallelized tree search — branch, evaluate, prune bad branches early. Structured search space.
**Our approach:** `autoresearch.py` — evolutionary mutation with deterministic eval, git reset on regression. Works well when fitness landscape is noisy.
**Assessment:** Different tools for different problems. Tree search better when search space has structure (prune early). Evolutionary better for noisy landscapes. No evidence our current approach is inferior for code optimization tasks. Worth testing tree search if we extend autoresearch to design/architecture tasks where the search space is more structured.
**Status:** [DEFERRED] — no measured gap in autoresearch performance.

### 3. Scaling Law (Output Quality ~ Model Capability)

**Their finding:** Paper quality correlates directly with foundation model capability. As models improve, output quality increases.
**Our implication:** Validates frontier-model-first strategy. Using Opus/GPT-5.4 for research and Gemini Pro for review is the right call — don't downgrade to save cost on research quality. Cost savings come from routing (Flash for simple tasks), not from using weaker models for hard tasks.
**Status:** Already aligned with our practice. No action needed.

### 4. Their Limitations = Our Existing Mitigations

| AI Scientist limitation | Our existing mitigation |
|---|---|
| Hallucinated citations | `epistemics` skill anti-fabrication rules, `subagent-source-check-stop.sh` |
| Methodological rigor failures | `verify_claim` + quote-anchored verification, `stop-research-gate.sh` |
| Figure duplication | Not applicable (we don't generate visual research artifacts) |
| Susceptibility to naive ideas | Cross-model review (`/model-review`), blind first-pass principle |

### 5. Vision-Model Feedback for Artifacts

**Pattern:** Use multimodal model to review generated figures/visualizations.
**Assessment:** Only relevant if research-cycle ever produces visual artifacts (plots, diagrams). Currently doesn't. Low priority.
**Status:** [DEFERRED] — no visual artifact generation in pipeline.

## What We Did NOT Port

- **LaTeX paper generation** — our output is research memos (.md), not papers
- **IRB/ethics review process** — not applicable to our domain
- **Their specific training pipeline** (SFT + RL on research tasks) — we use frontier models directly

## Context-1 Connection

Same session also evaluated Chroma's Context-1 (21B retrieval subagent). Ported the quote-matching verification technique from their data-gen pipeline into `exa_verify.py:exa_verify_with_quote`. Model weights available but inference harness not yet public — tracking for future evaluation.

<!-- knowledge-index
generated: 2026-03-26T22:43:25Z
hash: 40842a338e1c

title: Portable Patterns from AI Scientist v2
status: active
tags: autonomous-research, verification, self-improvement

end-knowledge-index -->
