---
title: Epistemic Architecture v3 — Domain-Branched Checks and Balances
date: 2026-03-13
---

# Epistemic Architecture v3 — Domain-Branched Checks and Balances

**Date:** 2026-03-13
**Tier:** Deep | 3 axes | 3 parallel research agents + direct scite/S2 searches
**Prior art:** Updates `epistemic-v2-synthesis.md`, `epistemic-measurement-concepts.md`. Companion to `domain-specific-agent-biases.md` (written same session).
**Research inputs:** 2 agent reports (frontier epistemics, domain biases), 6 scite queries, 2 S2 queries, existing 25+ research memos

---

## Evidence Recitation

Before synthesis, the concrete findings I'm drawing from:

### From frontier-epistemics agent (full report)
1. **Agentic Confidence Calibration (ACC)** — Zhang et al., Salesforce, arXiv:2601.15778, Jan 2026. 48 trajectory-level features → ECE 0.031 (vs 0.656 verbalized confidence). Tested on GPT-4.1, GPT-4o, DeepSeek-v3.1, Qwen3-235B. General Agent Calibrator (GAC) transfers across domains. [SOURCE: arXiv:2601.15778, FETCHED+READ]
2. **Multi-Agent Debate questioned** — Wu et al. (arXiv:2511.07784): MAD may be ensembling, not deliberation. Choi et al. (arXiv:2510.07517): identity-driven sycophancy corrupts debate; anonymization mitigates. [SOURCE: abstracts only]
3. **KalshiBench** — Nel, arXiv:2512.16030. Prediction market questions with resolved outcomes for epistemic calibration. [SOURCE: Exa summary]
4. **Reflection-Bench** — Li et al., ICML 2025, arXiv:2410.16270. Benchmark for epistemic agency: belief construction, adaptation, monitoring. [SOURCE: S2 abstract]
5. **Uncertainty compounds across agent steps** — confirmed by ACC paper citing Zhao et al. ACL 2025. [SOURCE: arXiv:2601.15778]
6. **Reasoning-style poisoning** — Zhou & Wang, arXiv:2512.14448. Novel attack on reasoning process, not content. [SOURCE: abstract]

### From domain-biases agent (full memo at `domain-specific-agent-biases.md`)
7. **Trading — Bias echo/amplification** — Winder et al. 2025, PLOS ONE. LLMs mirror and amplify user's investment biases. [SOURCE: DOI 10.1371/journal.pone.0325459, FETCHED]
8. **Trading — Product/ticker bias** — Dimino et al. 2025, arXiv:2510.05702. Systematic large-cap favoritism. [SOURCE: S2]
9. **Trading — Disposition effect mirroring** — Vidler & Walsh 2025, arXiv:2501.16356. Hold bias on losing positions. [SOURCE: FETCHED]
10. **Scientific — Citation prestige bias** — arXiv:2512.09483. LLM search engines cite fewer unique sources with concentration in high-profile outlets. [SOURCE: Exa]
11. **Scientific — Consensus hallucination** — LLMs fabricate false consensus where literature is divided. [OBSERVED + INFERENCE]
12. **Scientific — Screening sensitivity** — Delgado-Chaves et al. 2025, PNAS. Minor criteria wording changes cause large screening swings. [SOURCE: DOI 10.1073/pnas.2411962122]
13. **Engineering — Reward hacking generalizes** — Nature 2025 (DOI 10.1038/s41586-025-09937-5): narrow finetuning → broad misalignment. [SOURCE: Exa]
14. **Engineering — Premature convergence** — Dang et al. 2026, arXiv:2602.11779: temperature as meta-policy for exploration-exploitation. [SOURCE: S2]

### From my own scite searches
15. **Girolli 2026** — SSRN 6286458. Frontier-model financial AI benchmark (Claude Sonnet 4.5, GPT-4.1, Gemini 2.5 Flash). ACTFIT governance +22pp accuracy; CRISPE governance WORSE than baseline (41.1% vs 44.9%, 49.1% hallucination). **Bad epistemic scaffolding is worse than none.** [SOURCE: scite]
16. **Schmidgall et al. 2024** — npj Digital Medicine. BiasMedQA: 1273 questions testing 7 cognitive biases. GPT-4 most resilient; smaller models large drops. [SOURCE: scite, pre-frontier]
17. **Hintze et al. 2025** — Nonlinear probability transformation in LLMs. Claude 3.0 showed strong recency bias in economic choice. GPT-4.0 underweighted small probabilities. [SOURCE: scite, pre-frontier]
18. **Chergui et al. 2025** — Tutorial on cognitive biases in agentic AI with mathematical formulations and mitigation strategies. [SOURCE: scite, arXiv:2510.19973]

---

## 1. State of Our Epistemic Infrastructure

### What's Running (4 scripts)

| Script | Measures | Baseline | Gap |
|--------|----------|----------|-----|
| `safe-lite-eval.py` | Factual precision | 71.4% precision, 65% "unclear" | Unclear rate needs diagnosis |
| `epistemic-lint.py` | Unsourced claims | Severity-weighted | Doesn't check *selection* bias |
| `pushback-index.py` | Sycophancy words | 0 folds, 17 holds | Word-level only, misses behavioral folds |
| `trace-faithfulness.py` | Tool-claim matching | 91.8% faithful | ~48% citation "hallucination" (mostly path mismatches) |

### What's Designed but Not Built (I1-I8)

| Planned | Design Status | Blocked By |
|---------|---------------|------------|
| I1. VeriScore pre-filter | Detailed spec | Implementation time |
| I2. Fold detector | Detailed spec | Implementation time |
| I3. Claims reader | Detailed spec | Implementation time |
| I4. Cross-family verification | Detailed spec | llmx routing |
| I5. Calibration canaries | 20 queries designed | Curation + data accumulation |
| I6. SAFE-lite denominator fix | Detailed spec | VeriScore prompt engineering |
| I7. Compaction nuance | Data collected | No consumer script |
| I8. SPC dashboard | Skeleton exists | n≥20 data points needed |

### What's Researched but Not Even Designed

- Domain-specific bias detection (this memo fills the gap)
- Trajectory-level calibration (ACC/HTC — new finding)
- Consensus hallucination detection (scite now enables this)
- Cross-session belief drift measurement
- Solution diversity tracking for optimization

### The Problem Statement

**Research-heavy, implementation-light.** We know more about epistemic failure modes than almost any comparable project. But most of that knowledge lives in 25+ research memos, not in running code. The ratio of documented-failure-modes to measured-failure-modes is approximately 50:4.

**Domain-agnostic measurement.** Everything we measure is universal — factual precision, sycophancy, trace faithfulness. But the failure modes that cause real damage are domain-specific: bias echo in trading, citation selection bias in research, reward hacking in optimization. Universal checks are necessary but insufficient.

---

## 2. The Architecture: Domain-Branched Epistemic Layers

```
Layer 0: Universal (all domains) — PARTIALLY RUNNING
├── Factual verification (SAFE-lite) ✓
├── Source attribution (epistemic-lint) ✓
├── Trace faithfulness ✓
├── Sycophancy detection (pushback-index) ✓
├── Calibration canaries ○ (designed)
├── Fold detector ○ (designed)
├── Cross-family verification ○ (designed)
└── Trajectory-level calibration ○ (NEW — ACC/HTC)

Layer 1: Domain-Specific Bias Detection — NOT BUILT
├── Trading Branch
│   ├── Thesis challenge check
│   ├── Ticker/comp diversity audit
│   ├── Disposition asymmetry check
│   ├── Price anchoring sensitivity
│   └── Narrative vs data contradiction
├── Scientific Research Branch
│   ├── Citation diversity audit (journal distribution)
│   ├── Negative result coverage check
│   ├── Evidence hierarchy enforcement
│   ├── Consensus hallucination detection (scite stance)
│   └── Cross-disciplinary coverage check
└── Engineering Optimization Branch
    ├── Held-out eval metrics (reward hacking)
    ├── Solution diversity tracking
    ├── Distributional shift testing
    ├── Sensitivity analysis enforcement
    └── Architecture diversity audit

Layer 2: Meta-Epistemic Monitoring — SKELETON ONLY
├── Calibration drift (SPC charts) ○
├── Goodhart detection (metric correlation divergence) ○
├── Cross-session belief drift ○
└── Compaction nuance loss ○
```

### Why Three Layers

**Layer 0** catches universal failures — the agent fabricated a fact, cited something it didn't read, caved under pressure. These are domain-independent. They're the fire alarms.

**Layer 1** catches domain-specific biases — the agent amplified the user's investment thesis, fabricated consensus in a lit review, hacked a benchmark metric. These require knowing which domain the agent is operating in. They're the smoke detectors tuned to each room.

**Layer 2** catches meta-level drift — the measurements themselves are degrading, metrics are being Goodharted, beliefs are drifting across sessions. This is monitoring the monitors.

---

## 3. What Makes This "Based" (First Principles Analysis)

### Principle 1: Measure domain-specific damage, not domain-agnostic proxies

Current state: we measure "did the agent state facts correctly?" Unmeasured: "did the agent reinforce the user's pre-existing bias and make them more confident in a wrong trade?" The second failure mode causes more real-world damage than the first.

**Concrete implication:** For each domain, define the highest-damage failure mode and build measurement around it:
- **Trading:** Bias amplification → measure thesis challenge rate (does agent present counterarguments unprompted?)
- **Research:** Selection bias → measure citation diversity (journal impact factor Gini coefficient of cited sources)
- **Engineering:** Proxy gaming → measure held-out metric divergence (primary metric improving while secondary degrades)

### Principle 2: The agent's own confirmation bias is the biggest unmeasured threat

We measure sycophancy (agent → user agreement bias). We don't measure confirmation bias (agent → self agreement bias). When researching a thesis, the agent should actively disconfirm. Our researcher skill has Phase 4 (disconfirmation), but we don't measure whether Phase 4 actually surfaces contradictory evidence vs being performative.

**Measurement:** For claims in researcher output, check scite contrasting citations. If contrasting evidence exists in the literature but the agent's Phase 4 didn't find it → missed negative. Track the miss rate.

### Principle 3: Bad scaffolding is worse than none (Girolli 2026)

The Girolli 2026 paper (frontier-tested: Claude Sonnet 4.5, GPT-4.1, Gemini 2.5 Flash) found that CRISPE prompt governance produced WORSE accuracy than zero-shot baseline (41.1% vs 44.9%) with 49.1% hallucination rate. ACTFIT governance improved accuracy to 67%.

**Implication:** Every epistemic check we add must be validated against a baseline. A check that triggers false positives, confuses the agent, or adds noise to the prompt is net negative. The constitution already says "measure before enforcing" — this is empirical proof.

### Principle 4: Structural forcing > advisory checks > instructions

Evidence ranking of enforcement mechanisms:
1. **Structural forcing** (output format requires evidence of discipline): Researcher Phase 4 requires disconfirmation section. Autoresearch git-reset requires passing eval. These work because the agent can't skip them.
2. **Advisory checks** (hooks that warn but don't block): epistemic-lint, pushback-index. Useful but ignorable.
3. **Instructions** (CLAUDE.md rules): "0% reliable" per EoG (IBM). Necessary for simple predicates but not sufficient for complex epistemic discipline.

**Implication:** Domain-specific checks should be structural where possible. The thesis-check skill in intel is the right pattern — it's a structured workflow, not an advisory hook.

### Principle 5: Scite is the consensus hallucination detector we lacked

Before scite MCP, we had no way to verify "does the literature actually support claim X?" We could verify individual facts (SAFE-lite) but not synthesis claims. Scite's citation stance data (1.6B+ classified as supporting/contrasting/mentioning) enables a new check:

```
Agent claims: "The literature supports X"
Scite check: search for contrasting citations on X
If contrasting citations exist but agent didn't mention them → consensus hallucination
```

This is the single highest-ROI new capability from recent tool additions.

### Principle 6: Trajectory-level calibration beats verbalized confidence

ACC paper finding: verbalized confidence ECE = 0.121–0.656 (terrible). Trajectory-level feature ECE = 0.031 (good). The features that predict agent failure are observable from execution traces:
- **Positional:** first-step and last-step confidence (strongest single signals)
- **Stability:** within-step variance
- **Dynamics:** cross-step confidence evolution

Even without token log-probabilities (which Claude Code doesn't expose), we can extract proxy features from JSONL transcripts:
- Step count (more steps → less confident outcome)
- Tool failure rate (failures → lower reliability)
- Backtracking frequency (reformulated queries → uncertain territory)
- Search query reformulation count
- Time spent in disconfirmation vs confirmation phase

A logistic model trained on session-analyst ratings as labels could predict session reliability.

---

## 4. Domain Detection (The Routing Problem)

Domain-specific checks require knowing which domain the agent is in. Three approaches:

| Approach | Mechanism | Pros | Cons |
|----------|-----------|------|------|
| **Explicit** | User declares domain (`/research --domain=trading`) | Zero ambiguity | Requires user action |
| **Project-based** | Project path determines domain (intel → trading) | Automatic | Cross-domain sessions break it |
| **Content-based** | Hook analyzes prompt for domain signals | Fully automatic | False positives, latency |

**Recommended:** Project-based as default, with content-based override. Most sessions in intel ARE trading. Most sessions in genomics ARE scientific research. Cross-domain is rare enough to handle with explicit override.

**Implementation:** Extend `pretool-companion-remind.sh` pattern. It already detects bio/medical → epistemics skill. Add:
- `intel/` → trading bias checks active
- `genomics/`, research sessions → scientific review checks active
- `autoresearch`, `experiments/` → engineering optimization checks active

---

## 5. Implementation Plan

### Phase 1: Quick Wins (This Week → This Month)

| # | What | Maintenance | Composability | Expected Impact |
|---|------|-------------|---------------|-----------------|
| 1 | **Wire scite into researcher Phase 4** — after synthesis, auto-check contrasting citations for top 3 claims | None (skill prompt addition) | High — any research workflow | Catches consensus hallucination, the highest-damage scientific review bias |
| 2 | **Implement fold detector (I2)** — already fully designed in epistemic-v2-synthesis | Low (script + schema) | High — feeds supervision-kpi | Upgrades pushback measurement from word-level to behavioral |
| 3 | **Add 5 KalshiBench questions to calibration canary set** — resolved prediction market questions as ground truth | None (data addition) | High — calibration system | External calibration ground truth (markets, not human labels) |
| 4 | **Anonymize model identities in model-review** — remove "GPT-5" / "Gemini" labels from cross-model review prompts | None (prompt change) | Low — model-review only | Mitigates identity-sycophancy (Choi et al.) |

### Phase 2: Domain Branches

| # | What | Maintenance | Composability | Expected Impact |
|---|------|-------------|---------------|-----------------|
| 5 | **Trading: Thesis challenge metric** — measure whether agent presents counterarguments unprompted in intel sessions | Low (measurement script) | Medium — intel-specific | First domain-specific bias measurement |
| 6 | **Research: Citation diversity audit** — compute journal impact factor Gini coefficient of researcher output citations | Low (measurement script) | Medium — researcher output | Detects citation prestige bias |
| 7 | **Research: Scite consensus check** — for any "literature supports X" claim, verify contrasting citations don't exist | None (extends #1) | High — any synthesis | Structural consensus hallucination detection |
| 8 | **Engineering: Solution diversity in autoresearch** — track Jaccard distance between successive proposed solutions | Low (metric addition) | Medium — autoresearch only | Detects premature convergence |
| 9 | **Domain routing hook** — extend companion auto-loader to activate domain-specific checks by project | Low (hook config) | High — all projects | Automatic domain detection |

### Phase 3: Meta-Epistemic (prerequisite: sufficient measurement data)

| # | What | Maintenance | Composability | Expected Impact |
|---|------|-------------|---------------|-----------------|
| 10 | **ACC-lite: trajectory features from transcripts** — extract proxy features (step count, failures, backtracking) from JSONL | Low (parser + schema) | High — feeds dashboard, alerts | Trajectory-level reliability prediction |
| 11 | **Missed negative rate** — compare agent disconfirmation results against scite contrasting citations | Low (joins two data sources) | Medium — researcher quality metric | Measures confirmation bias of the agent itself |
| 12 | **Cross-session belief drift** — timestamp and version MEMORY.md claims, measure change velocity | Medium (needs claim tracking) | Medium — prerequisite: claim schema | Detects silent belief drift |
| 13 | **Goodhart detection** — correlate metric pairs (pushback_rate × factual_precision) at n≥8 | None (already in dashboard) | High — meta-monitoring | Catches performative metrics |

---

## 6. What NOT to Build

Per constitution: "Instructions that stay instructions forever are cruft."

- **Don't build a monolithic bias detection system.** Domain-specific checks should be small, composable scripts — one per bias type. Same pattern as existing epistemic scripts.
- **Don't build advisory hooks for domain biases.** Advisory hooks have ~0% effect on complex epistemic behaviors. Use structural forcing (output format) or stop hooks (block on detected pattern).
- **Don't build domain detection via LLM classification.** Project-path detection is deterministic and free. LLM classification adds latency and false positives.
- **Don't try to measure all 30 identified biases.** Pick the highest-damage one per domain (bias echo, consensus hallucination, reward hacking) and measure that first. Expand only after the first measurement works.

---

## 7. Open Questions

### Q1: Does trajectory-level calibration work without log-probabilities?
- **Status:** UNKNOWN
- **Why it matters:** Claude Code doesn't expose token log-probs. The ACC paper's 48 features include log-prob-based features. Our proxy features (step count, failures, backtracking) may or may not predict as well.
- **Test:** Train logistic model on proxy features using session-analyst ratings as labels. If AUROC > 0.65, it's useful.

### Q2: Is consensus hallucination measurable via scite?
- **Status:** UNKNOWN
- **Why it matters:** Scite's coverage skews biomedical. For trading/financial claims, contrasting citation coverage may be thin.
- **Test:** Run 10 researcher synthesis claims through scite. Measure coverage rate (% of claims where scite has any stance data).

### Q3: Does thesis challenge rate predict investment outcome quality?
- **Status:** UNKNOWN
- **Why it matters:** If pushing back on user thesis doesn't improve outcomes, it's just annoying. Need to measure whether challenged theses produce better risk-adjusted returns than unchallenged ones.
- **Test:** Retrospective analysis of intel sessions with thesis-check vs without. Compare against market outcomes.

### Q4: Is our Phase 4 (disconfirmation) actually effective?
- **Status:** UNKNOWN — no measurement exists
- **Why it matters:** Phase 4 is the primary structural defense against confirmation bias in the researcher skill. If it's performative (searches but doesn't find contradictions that exist), it provides false confidence.
- **Test:** For 10 research memos, manually verify whether contrasting evidence exists that Phase 4 missed. The missed negative rate is the key metric.

---

## Disconfirmation

Searched for evidence against the core proposal (domain-branched epistemic layers):

1. **"Domain-agnostic checks are sufficient"** — Contradicted by Girolli 2026 showing domain-specific prompt governance (ACTFIT for finance) dramatically outperforms generic approaches. And by Schmidgall 2024 showing bias vulnerability varies by model and domain.

2. **"More scaffolding always helps"** — Contradicted by Girolli 2026 showing CRISPE governance WORSE than baseline. And by ReliabilityBench showing SimpleReAct > ComplexReflexion under stress. Scaffolding must be validated.

3. **"Agent biases mirror human biases exactly"** — Partially contradicted: some biases are amplified (bias echo), some are novel (product bias from training distribution), some are inverted (temporal citation bias — LLMs favor recent, humans favor classics). Domain-specific checks must account for LLM-specific bias patterns, not just replicate human debiasing.

4. **"Trajectory-level calibration is better than everything"** — Not contradicted but limited: ACC paper tests on GPT-4.1/4o but not Claude. Feature transferability is unverified. And it requires a labeled dataset for training, which we'd need to build from session-analyst ratings.

---

## Sources

### Fetched and Read (full or partial)
- Zhang et al. 2026 — "Agentic Confidence Calibration" (arXiv:2601.15778) [FETCHED+READ by agent]
- Winder et al. 2025 — "Biased Echoes" (PLOS ONE, DOI: 10.1371/journal.pone.0325459) [FETCHED by agent]
- Corazzini et al. 2025 — "Decision and Gender Biases in LLMs" (arXiv:2511.12319) [FETCHED by agent]
- Vidler & Walsh 2025 — "Evaluating Binary Decision Biases" (arXiv:2501.16356) [FETCHED by agent]
- Mann et al. 2025 — "AI and Future of Academic Peer Review" (arXiv:2509.14189) [FETCHED by agent]

### Found via Search (abstracts/summaries)
- Girolli 2026 — "Prompt Governance in Financial AI" (SSRN 6286458) [scite — frontier-tested]
- Nel 2025 — "KalshiBench" (arXiv:2512.16030) [Exa summary]
- Li et al. 2025 — "Reflection-Bench" (arXiv:2410.16270, ICML 2025) [S2 abstract]
- Wu et al. 2025 — "Can LLM Agents Really Debate?" (arXiv:2511.07784) [S2 abstract]
- Choi et al. 2025 — "When Identity Skews Debate" (arXiv:2510.07517) [S2 abstract]
- Zhou & Wang 2025 — "Reasoning-Style Poisoning" (arXiv:2512.14448) [S2 abstract]
- Dimino et al. 2025 — "Representation Bias for Investment" (arXiv:2510.05702) [S2]
- Delgado-Chaves et al. 2025 — "Transforming Literature Screening" (PNAS, DOI: 10.1073/pnas.2411962122) [scite]
- Scherbakov et al. 2025 — "LLMs as Tools in Literature Reviews" (JAMIA, DOI: 10.1093/jamia/ocaf063) [scite]
- Schmidgall et al. 2024 — "Cognitive Biases in Medical LLMs" (npj Digital Medicine) [scite — pre-frontier]
- Hintze et al. 2025 — "Nonlinear Probability Transformation" (RS preprint) [scite — pre-frontier]
- Chergui et al. 2025 — "Cognitive Biases in Agentic AI" (arXiv:2510.19973) [scite]
- Anthropic 2025 — Emergent misalignment paper [Exa]
- Nature 2025 — "Narrow Training → Broad Misalignment" (DOI: 10.1038/s41586-025-09937-5) [Exa]
- Dang et al. 2026 — Temperature as Meta-Policy (arXiv:2602.11779) [S2]

<!-- knowledge-index
generated: 2026-03-22T00:15:43Z
hash: db37caf02be6

title: Epistemic Architecture v3 — Domain-Branched Checks and Balances
table_claims: 3

end-knowledge-index -->
