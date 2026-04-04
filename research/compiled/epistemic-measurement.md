---
type: compiled
concept: Epistemic Measurement and Verification
compiled: 2026-04-04
sources: 10
projects: [meta]
---

## Summary

Epistemic measurement and verification for LLM agents is a well-researched but under-deployed domain. No frontier agentic system (Devin, Cursor, OpenHands, SWE-agent) implements epistemic quality monitoring; all rely on end-to-end task metrics. The meta project has built the most comprehensive epistemic measurement infrastructure documented anywhere (4 running scripts, 8 designed improvements, 3-layer architecture), grounded in 60+ papers. The core tension: research outpaces implementation (ratio of documented-to-measured failure modes is ~50:4), and the evidence shows that bad scaffolding is worse than none (Girolli 2026), so each addition must be validated against a baseline.

## Key Claims

| # | Claim | Source | Project | Date | Grade |
|---|-------|--------|---------|------|-------|
| 1 | Cross-family model verification improves detection F1 by +39% and accuracy by +31.3pp over single-model | factual-verification-systems.md (FINCH-ZK, arXiv:2508.14314) | meta | 2026-03-02 | HIGH — ablation-verified |
| 2 | SAFE costs $0.19/response, wins 76% of human disagreements, 20x cheaper than humans — but nobody deploys it at scale | epistemic-quality-evals.md (arXiv:2403.18802); epistemic-scaffolding-evidence.md | meta | 2026-03-02 | HIGH — NeurIPS 2024, 122 cites |
| 3 | No frontier agentic coding system deploys epistemic measurement (sycophancy, citation checking, claim verification) | epistemic-scaffolding-evidence.md (Perplexity + Exa systematic search) | meta | 2026-03-02 | HIGH — verified absence |
| 4 | Answer frequency (sampling consistency) is the most reliable calibration signal; verbalized confidence is systematically biased | epistemic-quality-evals.md; calibration-measurement-practical.md (arXiv:2602.00279) | meta | 2026-03-02 | MEDIUM — 20 LLMs, 7 datasets, preprint |
| 5 | Hedging language is NOT a calibration signal (0.52-0.54 vs random 0.50) | calibration-measurement-practical.md (arXiv:2405.16908, EMNLP 2024) | meta | 2026-03-02 | HIGH — full text read |
| 6 | Within-session reasoning quality degrades 13.9-85% with context length, even when retrieval is perfect | epistemic-quality-evals.md; temporal-epistemic-degradation.md (arXiv:2510.05381) | meta | 2026-03-02 | HIGH — EMNLP 2025, replicated |
| 7 | Compaction provably loses epistemic nuance: ACE documents 18,282 to 122 token collapse; Kolagar & Zarcone confirm uncertainty flattening in summarization | temporal-epistemic-degradation.md; epistemic-v2-synthesis.md (arXiv:2510.04618, EACL 2024) | meta | 2026-03-02 | HIGH — convergent evidence |
| 8 | 7-13% of CoT reasoning traces are unfaithful on clean, non-adversarial prompts | epistemic-quality-evals.md (ICLR 2026 submission) | meta | 2026-03-02 | MEDIUM — verified |
| 9 | Multi-turn sycophancy quantifiable via Turn-of-Flip/Number-of-Flip; alignment tuning amplifies sycophancy | anti-sycophancy-process-supervision.md; epistemic-v2-synthesis.md (arXiv:2505.23840, EMNLP 2025) | meta | 2026-03-02 | HIGH — 17 LLMs tested |
| 10 | Sycophantic anchors detectable mid-generation at 74-85% accuracy via linear probes on activations | anti-sycophancy-process-supervision.md (arXiv:2601.21183) | meta | 2026-03-02 | HIGH — 200K+ rollouts |
| 11 | Self-reflection improves problem-solving +4.1% to +14.6% (GPT-4) but simpler ReAct outperforms complex Reflexion under production stress | epistemic-scaffolding-evidence.md (arXiv:2405.06682; arXiv:2601.06112, ICLR 2026) | meta | 2026-03-02 | HIGH — systematic, p<0.001 |
| 12 | Consistency is NOT correlated with accuracy (r=0.02 over 18 months); 60% pass@1 drops to 25% over 8 runs | epistemic-quality-evals.md; epistemic-v2-synthesis.md (arXiv:2602.16666, arXiv:2511.14136) | meta | 2026-03-02 | MEDIUM — multiple sources |
| 13 | Process supervision (PRMs) outperforms outcome supervision for math reasoning; extension to agent tasks via AgentPRM (promise + progress) | epistemic-causal-bayesian-sweep-2026-03-12.md (Lightman 2023, 1000+ cites; arXiv:2502.10325) | meta | 2026-03-12 | HIGH (math) / MEDIUM (agents) |
| 14 | Trajectory-level calibration (ACC) achieves ECE 0.031 vs verbalized confidence 0.121-0.656 | epistemic-architecture-v3.md (arXiv:2601.15778, Salesforce) | meta | 2026-03-13 | MEDIUM — tested on GPT-4.1/4o, not Claude |
| 15 | Bad epistemic scaffolding is worse than none: CRISPE governance produced 41.1% accuracy vs 44.9% baseline, 49.1% hallucination | epistemic-architecture-v3.md (Girolli 2026, SSRN 6286458, frontier-tested) | meta | 2026-03-13 | HIGH — Claude Sonnet 4.5, GPT-4.1, Gemini 2.5 Flash |
| 16 | Uncertainty as active control signal (triggering tool use, self-correction, compute allocation) is the emerging paradigm | epistemic-causal-bayesian-sweep-2026-03-12.md (Zhang et al. 2025, arXiv:2601.15690) | meta | 2026-03-12 | HIGH — full paper read |
| 17 | Tool-trace faithfulness: 91.8% baseline; correlation r=0.45 between determinism and faithfulness | epistemic-measurement-concepts.md; epistemic-v2-synthesis.md (arXiv:2601.15322) | meta | 2026-03-02 | MEDIUM — novel metric, no comparable system |
| 18 | Conformal prediction gives distribution-free UQ coverage guarantees for black-box LLMs (ConU, SConU) | epistemic-causal-bayesian-sweep-2026-03-12.md (ConU 47 cites, SConU 16 cites) | meta | 2026-03-12 | HIGH — established method |
| 19 | LLM evaluators flip judgments under casual user rebuttal with incorrect reasoning | epistemic-quality-evals.md (arXiv:2509.16533, EMNLP 2025 Findings) | meta | 2026-03-02 | MEDIUM — verified |
| 20 | Scaffolding that compensates for capability limitations gets eaten by model improvement; governance/accountability scaffolding persists | epistemic-scaffolding-evidence.md (Laminar taxonomy Jan 2026) | meta | 2026-03-02 | MEDIUM — inference backed by empirical |
| 21 | ~16% of verification benchmark annotations are wrong; all reported F1 scores have a noise floor | factual-verification-systems.md; epistemic-quality-evals.md (Seo et al., COLM 2025) | meta | 2026-03-02 | HIGH — 14 benchmarks analyzed |
| 22 | Scite citation stance data (1.6B+ classified citations) enables consensus hallucination detection — highest-ROI new capability | epistemic-architecture-v3.md | meta | 2026-03-13 | MEDIUM — capability assessment, not empirical validation |
| 23 | Capability-compensating scaffolding being eaten: Confucius Code Agent shows well-designed scaffolding lets Sonnet beat Opus (52.7% vs 52.0% on SWE-bench-Pro) | epistemic-scaffolding-evidence.md (arXiv:2512.10398v6) | meta | 2026-03-02 | HIGH — verified |
| 24 | Agent reliability plateaus at 85-90% on benchmarks; last 10-15% requires fundamentally different approaches | epistemic-causal-bayesian-sweep-2026-03-12.md (110-cite survey) | meta | 2026-03-12 | MEDIUM — abstract claim |
| 25 | Anthropic is the only lab publishing production agent monitoring data (turn duration, interrupt rates, risk classification on 998K tool calls) | epistemic-scaffolding-evidence.md (anthropic.com/research/measuring-agent-autonomy, Feb 2026) | meta | 2026-03-02 | HIGH — read in full |
| 26 | FActScore: ChatGPT has 58% factual precision on biography generation (42% claims unsupported) | epistemic-quality-evals.md (arXiv:2305.14251, 1,091 cites) | meta | 2026-03-02 | HIGH |
| 27 | No structural mechanism eliminates sycophancy; multiple mitigations needed | anti-sycophancy-process-supervision.md; epistemic-v2-synthesis.md | meta | 2026-03-02 | HIGH — convergent |
| 28 | Performative CoT is difficulty-dependent: 80% tokens are theater on easy tasks, genuine on hard tasks | epistemic-quality-evals.md (arXiv:2603.05488, DeepSeek-R1 671B, GPT-OSS 120B) | meta | 2026-03-02 | HIGH — preprint, frontier models |
| 29 | PRM data quality dominates model size for PRM training; curriculum training (easy to hard) improves accuracy | epistemic-causal-bayesian-sweep-2026-03-12.md (Alibaba PRM Lessons, 307 cites) | meta | 2026-03-12 | HIGH — widely cited |
| 30 | Our system's SDT operating point: almost all specificity, almost no sensitivity — need to increase sensitivity (catch more real problems) | epistemic-v2-synthesis.md; epistemic-measurement-concepts.md | meta | 2026-03-02 | HIGH — self-assessment with SDT framing |

## Contradictions and Open Questions

### Contradictions

**Self-reflection: helps or hurts?** Renze & Guven (2024) show +4-15% improvement across 9 LLMs on clean benchmarks. ReliabilityBench (ICLR 2026) shows simpler ReAct outperforms complex Reflexion under production stress. The resolution is task-dependent: self-reflection helps for single-step error correction with clear feedback, hurts for multi-step sequential reasoning where the reflection infrastructure compounds errors and consumes context. (epistemic-scaffolding-evidence.md vs epistemic-scaffolding-evidence.md, same memo surfaces both sides)

**More scaffolding = better?** Girolli 2026 shows bad scaffolding (CRISPE governance) is worse than none (41.1% vs 44.9%). ACTFIT governance improves accuracy to 67%. This contradicts a simple "more checks = better" assumption. Resolution: each epistemic check must be validated against a baseline. The constitution already says "measure before enforcing" — Girolli is empirical proof. (epistemic-architecture-v3.md)

**Consistency as truth signal.** The calibration literature (arXiv:2602.00279) says sampling consistency is the "most reliable calibration signal." But Princeton (arXiv:2602.16666) shows r=0.02 between consistency and accuracy over 18 months. Resolution: consistency is useful for detecting uncertainty (claims the agent is uncertain about) but is NOT a truth proxy. Cross-model disagreement flags problems; agreement does not confirm correctness. (epistemic-quality-evals.md vs epistemic-v2-synthesis.md)

**Scaffolding durability vs model improvement.** GPT-5.2 claims agents need "less extensive scaffolding." But Confucius Code Agent shows well-designed scaffolding lets weaker models beat stronger ones. The Laminar taxonomy resolves this: capability-compensating scaffolding gets eaten, governance/accountability scaffolding persists. Our epistemic monitoring is a mix of both. (epistemic-scaffolding-evidence.md)

### Open Questions

**Q1: Does trajectory-level calibration work without log-probabilities?** ACC (arXiv:2601.15778) achieves ECE 0.031 using 48 features including log-prob-based ones. Claude Code API doesn't expose log-probs. Proxy features (step count, tool failures, backtracking) are proposed but untested. Status: UNKNOWN. (epistemic-architecture-v3.md)

**Q2: Is our Phase 4 (disconfirmation) actually effective?** No measurement exists of whether the researcher skill's disconfirmation phase finds contradictions that actually exist in the literature. The missed negative rate is undefined. Status: UNKNOWN. (epistemic-architecture-v3.md)

**Q3: Does consensus hallucination detection work via scite?** Scite coverage skews biomedical. For trading/financial claims, contrasting citation coverage may be thin. Untested. Status: UNKNOWN. (epistemic-architecture-v3.md)

**Q4: What is FActScore-style factual precision as f(output position)?** Du et al. prove reasoning degrades with context length. But nobody has measured whether factual precision of claims at token 5000 differs from token 500 within a single generation. A genuine gap and straightforward experiment. Status: GAP. (temporal-epistemic-degradation.md)

**Q5: Does cross-session belief drift compound?** DrunkAgent shows memory corruption propagates indefinitely. No empirical measurement of MEMORY.md precision at sessions 1, 10, 25, 50 has been run. Status: GAP. (epistemic-v2-synthesis.md)

**Q6: CRPS for prediction intervals.** Continuous Ranked Probability Score generalizes Brier to prediction ranges. Entirely unexplored for LLM agents. Could be first application. Status: UNEXPLORED. (epistemic-v2-synthesis.md, epistemic-measurement-concepts.md)

## Timeline

**2026-03-02 (Day Zero):** Five deep-tier research memos written simultaneously covering five axes of epistemic measurement: factual verification systems, calibration measurement, anti-sycophancy/process supervision, temporal degradation, and an overall synthesis. 25+ papers surveyed. Established baselines: pushback index 13.4%, fold rate 0.0%, claims verified rate 76.5%, trace faithfulness 91.8%, SAFE-lite precision 71-100% (65% unclear). Four scripts running (safe-lite-eval, epistemic-lint, pushback-index, trace-faithfulness). Eight improvements designed (I1-I8) with phased implementation plan. Key frameworks imported: Signal Detection Theory, Boyd's OODA Loop, Proper Scoring Rules, SPC, Goodhart mitigation. (epistemic-v2-synthesis.md, calibration-measurement-practical.md, anti-sycophancy-process-supervision.md, temporal-epistemic-degradation.md, factual-verification-systems.md)

**2026-03-12 (Bayesian/Causal Sweep):** Extended epistemic measurement into Bayesian UQ and process reward models. Key new findings: conformal prediction as distribution-free UQ for LLMs (ConU, SConU); PRM explosion (AgentPRM, ThinkPRM, 307-cite Alibaba lessons); uncertainty-as-active-signal paradigm shift (Zhang et al. Salesforce survey). Confirmed Causal Rung Collapse still uncontested. (epistemic-causal-bayesian-sweep-2026-03-12.md)

**2026-03-13 (Architecture v3):** Proposed domain-branched epistemic layers: Layer 0 universal (partially running), Layer 1 domain-specific bias detection (not built), Layer 2 meta-monitoring (skeleton only). Introduced ACC trajectory-level calibration (ECE 0.031). Found Girolli 2026 evidence that bad scaffolding is worse than none. Identified confirmation bias as the biggest unmeasured threat (agent's own, not user-directed sycophancy). Scite recognized as consensus hallucination detector. 18 new papers integrated. (epistemic-architecture-v3.md)

**2026-03-21 (Concepts Memo):** Consolidated concepts reference document covering all measurement vocabulary: canary queries, fold detection, trace faithfulness, SPC, Goodhart mitigation, Brier scoring, provenance tags, claim severity weighting, null result preservation, pertinent negatives. Documented "What NOT to Build" list (13 rejected concepts with evidence). Listed "What to Watch" (7 promising-but-premature items). (epistemic-measurement-concepts.md)

**As of 2026-04-04:** The I1-I8 improvements from the v2 synthesis have been partially implemented. Claims reader (I3), fold detector (I2), and calibration canary system (I5) are built. SPC dashboard (I8) has sparkline trends. SAFE-lite denominator fix (I1) and compaction tracking (I7) status unclear from the memos alone. The architecture-v3 domain-specific branches (Layer 1) remain unbuilt.

## Cross-References

| Source | Title | Date | Role |
|--------|-------|------|------|
| `research/epistemic-quality-evals.md` | Epistemic Quality Evaluation for LLM Agent Systems | 2026-03-02 | Benchmarks and proven findings (SeekBench, SAFE, FActScore, VeriScore, calibration) |
| `research/epistemic-measurement-concepts.md` | Epistemic Measurement Concepts | 2026-03-21 | Reference vocabulary, frameworks, baselines, rejected concepts |
| `research/epistemic-architecture-v3.md` | Domain-Branched Checks and Balances | 2026-03-13 | Three-layer architecture, domain routing, ACC trajectory calibration |
| `research/epistemic-v2-synthesis.md` | Epistemic Quality System v2 Research Synthesis | 2026-03-02 | Core synthesis: 22 findings, I1-I8 plan, ROI assessment, measurement redesign |
| `research/epistemic-scaffolding-evidence.md` | Epistemic Scaffolding: What the Evidence Says | 2026-03-02 | External landscape: who does/doesn't do this, scaffolding vs model improvement |
| `research/epistemic-causal-bayesian-sweep-2026-03-12.md` | Epistemic, Causal, and Bayesian Methods Sweep | 2026-03-12 | PRMs, conformal UQ, uncertainty-as-signal, do-calculus frameworks |
| `research/calibration-measurement-practical.md` | Practical Calibration Measurement | 2026-03-02 | Minimum samples, hedging vs accuracy, scoring rules |
| `research/anti-sycophancy-process-supervision.md` | Anti-Sycophancy and Process Supervision | 2026-03-02 | Fold detection methodology, sycophantic anchors, PRMs for agents |
| `research/temporal-epistemic-degradation.md` | Temporal Epistemic Degradation | 2026-03-02 | Context rot, compaction loss, cross-session drift |
| `research/factual-verification-systems.md` | Factual Verification Systems | 2026-03-02 | FINCH-ZK cross-model verification, VeriScore filtering, production landscape |

## Gaps

**1. Domain-specific epistemic checks are entirely unbuilt.** The v3 architecture defines Layer 1 (trading bias detection, scientific citation audit, engineering reward hacking) but none have been implemented. The highest-damage failure modes (bias amplification in trading, consensus hallucination in research) are domain-specific and unmeasured.

**2. Confirmation bias of the agent itself is unmeasured.** Sycophancy (agent agreeing with user) is measured. The agent's own tendency to confirm its initial hypothesis during research (searching for supporting evidence, ignoring contradictions) is not. The Phase 4 disconfirmation effectiveness is unknown. A "missed negative rate" comparing agent disconfirmation output against scite contrasting citations would close this gap.

**3. No controlled experiment on compaction's epistemic cost.** The theoretical case is strong (ACE, Kolagar, Data Processing Inequality). But no one has run a before/after comparison of epistemic quality metrics across a compaction event in Claude Code specifically. Blocked by absence of a PostCompact hook.

**4. Calibration on open-ended research tasks.** Canary calibration measures calibration on known-answer questions. Agent research outputs involve open-ended claims where ground truth is expensive to establish. The gap between canary calibration and production calibration is unbridged.

**5. Trajectory-level features without log-probabilities.** ACC's best results use token log-probs. The proxy features proposed for API-only access (step count, failures, backtracking) have never been validated. Whether AUROC > 0.65 is achievable with proxy features only is unknown.

**6. Cross-session belief drift measurement.** DrunkAgent and theoretical frameworks predict that persistent memory corrupts over time. The specific experiment (measure MEMORY.md precision at session intervals) has never been run. The velocity of belief change and whether it correlates with error is undefined.

**7. Process reward models for epistemic (non-math) tasks.** PRMs are proven for math and coding where intermediate verification is tractable. For epistemic quality ("is this claim well-sourced?", "is this reasoning faithful?"), the evaluation is itself uncertain. AgentPRM's promise/progress dimensions could apply but need a labeled corpus of good/bad research traces.

**8. Position-dependent factual precision within a generation.** Du et al. prove reasoning degrades with context. Nobody has measured whether claims later in a long agent output are less factually precise than early claims. Straightforward FActScore experiment on first-quartile vs last-quartile output.

**9. Production validation of the "What NOT to Build" kills.** Thirteen concepts were rejected (Smithson tags, Wigmore charts, probabilistic databases, etc.) based on cross-model review and theoretical arguments. Some rejections (hedging as calibration signal) have strong empirical backing. Others (Dung argumentation, ClinGen taxonomy) were rejected on overhead grounds that might change as agent capabilities improve. No re-evaluation schedule exists.

<!-- knowledge-index
generated: 2026-04-04T17:35:25Z
hash: 1e3573bcd45b

cross_refs: research/anti-sycophancy-process-supervision.md, research/calibration-measurement-practical.md, research/epistemic-architecture-v3.md, research/epistemic-causal-bayesian-sweep-2026-03-12.md, research/epistemic-measurement-concepts.md, research/epistemic-quality-evals.md, research/epistemic-scaffolding-evidence.md, research/epistemic-v2-synthesis.md, research/factual-verification-systems.md, research/temporal-epistemic-degradation.md
table_claims: 30

end-knowledge-index -->
