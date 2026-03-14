# Constitutional Principle
Maximize the rate agents become more autonomous, measured by declining supervision.
Key rules: Architecture over instructions. Measure before enforcing. Fail open. Recurring patterns (10+) become architecture.
This is a personal project (1 developer, $25/day cap, not enterprise).

# Epistemic Architecture v3 — Plan Under Review

## Problem
We have 25+ research memos on epistemic failures but only 4 running measurement scripts. The ratio of documented-to-measured failure modes is ~50:4. All measurements are domain-agnostic, but real damage is domain-specific.

## Proposed 3-Layer Architecture

**Layer 0 (Universal, partially running):** Factual verification (SAFE-lite), source attribution (epistemic-lint), trace faithfulness, sycophancy detection (pushback-index), calibration canaries, fold detector, cross-family verification, trajectory-level calibration (NEW from ACC paper).

**Layer 1 (Domain-Specific, NOT built):**
- Trading: thesis challenge check, ticker diversity audit, disposition asymmetry check, price anchoring, narrative vs data contradiction
- Scientific Research: citation diversity audit, negative result coverage, evidence hierarchy, consensus hallucination detection via scite, cross-disciplinary coverage
- Engineering Optimization: held-out eval metrics (reward hacking), solution diversity tracking, distributional shift testing, sensitivity analysis, architecture diversity

**Layer 2 (Meta-Monitoring, skeleton only):** Calibration drift (SPC), Goodhart detection (metric correlation divergence), cross-session belief drift, compaction nuance loss.

## 6 First Principles
1. Measure domain-specific damage, not domain-agnostic proxies
2. Agent's own confirmation bias is biggest unmeasured threat
3. Bad scaffolding worse than none (Girolli 2026: CRISPE governance → 41.1% accuracy with 49.1% hallucination, WORSE than 44.9% baseline; frontier-tested on Claude 4.5/GPT-4.1/Gemini 2.5)
4. Structural forcing > advisory checks > instructions
5. Scite (1.6B classified citations) enables consensus hallucination detection
6. Trajectory-level calibration (ACC paper: ECE 0.031 from 48 trajectory features) beats verbalized confidence (ECE 0.656)

## Domain Routing
Project-path based: intel→trading, genomics→research, autoresearch→engineering. Extending existing companion skill auto-loader pattern.

## 13-Item Implementation Plan

**Phase 1 (this month):**
1. Wire scite into researcher Phase 4 — auto-check contrasting citations for synthesis claims (2-3 hrs)
2. Implement fold detector — already designed (1 day)
3. Add 5 KalshiBench prediction market questions to calibration canaries (2 hrs)
4. Anonymize model identities in model-review prompts (30 min)

**Phase 2 (next month):**
5. Trading: thesis challenge metric in intel sessions (1 day)
6. Research: citation diversity audit — journal impact Gini coefficient (1 day)
7. Research: scite consensus check for "literature supports X" claims (built on #1)
8. Engineering: solution diversity in autoresearch — Jaccard distance (1 day)
9. Domain routing hook extending companion auto-loader (2 hrs)

**Phase 3 (month 3):**
10. ACC-lite: trajectory features from JSONL transcripts (2 days)
11. Missed negative rate: compare agent disconfirmation vs scite contrasting citations (1 day)
12. Cross-session belief drift: version MEMORY.md claims (1 day)
13. Goodhart detection: metric pair correlation at n≥8 (already in dashboard skeleton)

## What NOT to Build
- No monolithic bias detection system (small composable scripts)
- No advisory hooks for domain biases (use structural forcing or stop hooks)
- No LLM-based domain detection (project-path is deterministic and free)
- Don't measure all 30 biases — pick highest-damage per domain first

## Key Evidence
- ACC/HTC paper (Salesforce, Jan 2026): 48 trajectory features, ECE 0.031, tested GPT-4.1/4o/DeepSeek-v3.1/Qwen3-235B
- Girolli 2026 (SSRN): frontier-tested financial AI, bad governance worse than none
- Winder et al. 2025 (PLOS ONE): LLMs amplify user investment biases
- Nature 2025: narrow finetuning → broad misalignment (reward hacking generalizes)
- Wu et al. 2025: MAD may be ensembling, not genuine deliberation
- 30 domain-specific biases documented across 3 domains (companion memo)

## Open Questions
Q1: Does trajectory calibration work without log-probs? (Need proxy features from transcripts)
Q2: Is consensus hallucination measurable via scite? (Coverage may be thin outside biomedicine)
Q3: Does thesis challenge rate predict investment outcomes?
Q4: Is our researcher Phase 4 (disconfirmation) actually effective?
