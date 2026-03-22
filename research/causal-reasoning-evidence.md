# Causal and Abductive Reasoning in LLMs: What the Evidence Says

**Date:** 2026-03-03
**Tier:** Synthesis from user-supplied findings, unverified against primary sources
**Status:** Source-graded [F3] throughout — these are secondary summaries. Primary sources need fetching before acting on specific numbers.

---

## Summary

Seven papers across 2025-2026 converge on the same structural diagnosis: LLMs retrieve causal associations rather than reason causally, and the gap is 30-40pp on novel vs. familiar tasks. The fixes range from RL fine-tuning to parallel reasoning architectures, but none are deployed in production. One finding has direct operational implications: constrained output formatting actively suppresses reasoning capability.

---

## 1. Causal Rung Collapse (Chang, arXiv:2602.11675, 2026)

**Claim:** Autoregressive training cannot distinguish P(Y|X) from P(Y|do(X)). This is architectural — not a prompting problem.

**Evidence:** Formal proof + 1,360 causal scenarios. Fix: Epistemic Regret Minimization recovers 53-59% of entrenched errors.

**Source grade:** [F3] — secondary summary, paper not fetched. arXiv:2602.11675 is the identifier. The "formal proof" claim needs verification against the actual paper before citing in investment analysis.

**Why it matters:** Pearl's causal hierarchy distinguishes three rungs: association (P(Y|X)), intervention (P(Y|do(X))), and counterfactual. Autoregressive training maximizes P(next token | context) — it's fundamentally rung-1. Any causal claim from a standard LLM is implicitly a rung-1 association dressed as rung-2 intervention. This explains why LLMs fail consistently on "what would happen if we changed X" questions even when they know X correlates with Y.

**Implication for this project:** Every causal claim our pipeline produces (e.g., "billing spike caused by scheme X") is a correlation-dressed-as-causation unless we explicitly instrument causal reasoning. The Epistemic Regret Minimization fix is worth investigating — 53-59% error recovery is substantial if the paper's numbers hold.

**Frontier model note:** Thinking models (Opus 4.6, o3, Gemini with extended thinking) trained with RL may have different characteristics — RL training on verifiable outcomes could partially recover counterfactual reasoning. Unverified.

---

## 2. Level-1 vs Level-2 Causal Reasoning Gap (Chi et al., arXiv:2506.21215, 63 citations, 2025)

**Claim:** GPT-4 and Claude drop from ~70-75% on familiar causal tasks to ~35-45% on novel ones — a 30-40pp gap. This proves retrieval not reasoning.

**Evidence:** CausalProbe-2024 benchmark. G²-Reasoner (goal-oriented prompt + knowledge retrieval) improves novel causal task performance.

**Source grade:** [F3] — secondary summary, paper not fetched. 63 citations suggests the benchmark has traction. arXiv:2506.21215.

**The 30-40pp gap interpretation:** If performance on familiar tasks (~70-75%) reflected genuine causal reasoning, it would generalize to novel tasks. The collapse on novel tasks is diagnostic of pattern-matching over training distribution rather than compositional reasoning. The model "knows" that smoking causes cancer (training data) but cannot reason about novel causal structures it hasn't seen.

**G²-Reasoner:** Goal-oriented prompting + knowledge retrieval improves novel task performance. Mechanism plausible — retrieval of relevant causal principles before answering may partially compensate for the retrieval-not-reasoning failure.

**Level-1 / Level-2 distinction (inferred):** Level-1 = familiar causal relationships in training data (retrievable). Level-2 = novel causal configurations requiring compositional reasoning. The nomenclature echoes Pearl's hierarchy but may be paper-specific.

---

## 3. GEAR Abductive Reasoning Failures (He et al., arXiv:2509.24096, UT Dallas/Adobe, 2025)

**Claim:** Only 20% of 70B-model hypotheses achieve internal consistency on abductive reasoning tasks. 80% of valid hypotheses are falsely rejected by benchmarks using single gold-answer evaluation.

**Evidence:** GEAR benchmark. Proposes Consistency, Generalizability, Diversity metrics. Fix: momentum-based curriculum learning.

**Source grade:** [F3] — secondary summary. UT Dallas/Adobe affiliation suggests institutional credibility. arXiv:2509.24096.

**The two failure modes are distinct:**
1. **Model failure:** Only 20% of generated hypotheses are internally consistent — the model produces incoherent explanations.
2. **Benchmark failure:** 80% of valid hypotheses are falsely rejected because benchmarks expect a single "gold" answer. Abductive reasoning is fundamentally many-to-one (multiple hypotheses can explain the same evidence). This is a measurement problem, not a capability problem, and means existing abductive benchmarks underestimate model capability by up to 4x.

**Implication:** Our investigation workflow does abductive reasoning (generate hypotheses to explain observed billing patterns). If we're evaluating hypothesis quality against single ground-truth answers, we're applying the wrong metric. The proposed Consistency + Generalizability + Diversity metrics are more appropriate.

**Frontier model note:** Thinking models with extended CoT may have better internal consistency. Unverified — the 20% figure is for 70B models, not Opus 4.6 or o3.

---

## 4. Theorem-of-Thought: Parallel Abductive + Deductive + Inductive Reasoning (Abdaljalil et al., ACL 2025, arXiv:2506.07106)

**Claim:** Parallel abductive + deductive + inductive agents outperform CoT and Self-Consistency. Bayesian belief propagation resolves conflicts between agents.

**Source grade:** [F3] — secondary summary. ACL 2025 is a strong venue. arXiv:2506.07106.

**Architecture:** Three specialized agents run in parallel, each applying a different reasoning mode:
- Abductive: "What's the best explanation for the evidence?"
- Deductive: "Given premises, what follows?"
- Inductive: "Given examples, what's the general rule?"

Conflicts resolved via Bayesian belief propagation — weights each agent's conclusion by its prior reliability, updates on the aggregate.

**Why this beats Self-Consistency:** Self-Consistency (majority voting over multiple CoT runs) uses the same reasoning mode each time. ToT uses structurally different reasoning modes — less correlated failures, more orthogonal error patterns. The information-theoretic argument from Failure Mode 6 in agent-failure-modes.md applies: heterogeneous channels access more of the information space.

**Operationalizability:** This architecture is implementable with Claude Code's multi-agent infrastructure. Three specialist prompts + a synthesis pass with Bayesian weighting. Closest analog: our current multi-model review uses model heterogeneity; ToT adds reasoning-mode heterogeneity.

---

## 5. RL vs SFT for Counterfactual Reasoning (arXiv:2510.01539)

**Claim:** RL fine-tuning on executable counterfactuals generalizes to new domains (1.5-2x gains vs. SFT); SFT does not generalize.

**Source grade:** [F3] — secondary summary, paper not fetched. arXiv:2510.01539.

**The mechanism:** SFT learns to mimic counterfactual examples in the training set — this is exactly the retrieval-not-reasoning failure. RL on executable counterfactuals requires the model to actually work out "what would have happened" in a verifiable environment, which forces genuine counterfactual computation rather than pattern matching. The 1.5-2x generalization gain is consistent with this interpretation.

**"Executable counterfactuals":** Implies counterfactuals with ground-truth answers that can be verified programmatically (e.g., code that actually runs, math with checkable answers). This is the same mechanism behind o3's strong performance on formal reasoning — verifiable outcomes force genuine computation.

**Implication:** If we ever fine-tune a model for our fraud detection / investment analysis work, use RL on verifiable counterfactuals, not SFT on example analyses. This is consistent with the broader RL > SFT finding for generalization.

---

## 6. CRANE Constrained Decoding Paradox (ICML 2025, arXiv:2502.09061)

**Claim:** Grammar constraints that only allow final answers in specific formats REDUCE reasoning capability. Fix: allow intermediate reasoning, enforce constraints only at output.

**Source grade:** [F3] — secondary summary. ICML 2025 is a top venue. arXiv:2502.09061.

**The paradox:** Constrained decoding forces the model to only generate tokens that conform to a grammar (e.g., "answer must be one of: A, B, C"). Intuition says this should help — fewer bad outputs, forced structure. Reality: the grammar constraint interferes with the model's internal reasoning process by restricting what tokens it can generate during chain-of-thought. You can't reason your way to a correct answer if you're not allowed to generate intermediate reasoning tokens.

**Fix:** Apply constraints only at the final output step, not during intermediate reasoning. The model reasons freely, then the final token is constrained.

**Practical implication for our prompts:**
- BAD: "Give me one cause for this billing anomaly." (output-format constraint at the start)
- GOOD: "Analyze this billing anomaly. What might explain it? [reasoning...] Summarize the single most likely cause." (constraint at the end)

This is consistent with the factor-listing anti-pattern (Failure Mode 4 in agent-failure-modes.md) — asking for "the top causes" forces list-mode reasoning rather than investigative reasoning.

---

## 7. The "Natural Experiment First" Research Gap

**Claim:** No published paper directly addresses temporal causal attribution with discrete structural changes (interrupted time series / regression discontinuity applied to LLM causal reasoning evaluation).

**Source grade:** [F3] — negative finding from search, not independently verified.

**What exists:** Econometric methods for natural experiments:
- Interrupted time series (ITS): before/after structural change
- Regression discontinuity (RD): sharp threshold creates quasi-randomized assignment

**What doesn't exist:** A benchmark or framework that evaluates LLM causal reasoning *about* natural experiments — specifically, can the model correctly identify when a discrete structural change (policy change, fraud scheme start, firm acquisition) caused a downstream effect vs. when it was coincidental?

**Why this matters for the intel project:** Our core analytical task is exactly this — "Did this billing pattern change because of a fraud scheme, or because of a policy change, or because of random variation?" This is temporal causal attribution with structural changes. No paper provides ground truth or evaluation framework for this task. We're operating in a genuine research gap.

**Closest approaches:** DiD (difference-in-differences) and synthetic control methods are the econometric standard. LLMs could be used as auxiliary reasoners to help identify valid control groups or structural break points — but no paper has validated this.

---

## Cross-Cutting Implications

### For our investigation workflow

The causal rung collapse (finding 1) + the Level-1/Level-2 gap (finding 2) together mean that **any causal statement our pipeline produces is suspect unless we explicitly structure around causal reasoning, not association retrieval.** Practical fixes:

1. **Frame queries as interventions, not associations.** Instead of "what correlates with fraud?" ask "if we removed the billing scheme, what would the claim distribution look like?"
2. **Use structural causal models (SCMs) explicitly.** State the causal graph as part of the prompt. Don't let the model infer it implicitly.
3. **Apply the CRANE constraint rule.** Never constrain output format at the start. Let the model reason freely, then format.
4. **Use the ToT parallel structure for high-stakes hypotheses.** Abductive + deductive + inductive in parallel, synthesized with Bayesian weighting.

### The benchmark validity problem

GEAR (finding 3) shows that abductive benchmarks using single gold-answer evaluation massively underestimate model capability. The same issue affects our internal evaluation:
- Are we evaluating fraud hypotheses against "the right answer" from enforcement data?
- If so, we're penalizing valid alternative explanations.
- Fix: evaluate hypotheses on consistency + generalizability + diversity, not ground-truth match.

### RL vs SFT for tool use (finding 5)

This connects to our observation that thinking models (o3, Opus 4.6) seem better at genuine reasoning tasks than instruction-tuned models. The RL training on verifiable outcomes is the likely mechanism. Implication: for tasks requiring genuine causal reasoning (not retrieval), prefer thinking models over standard instruction-tuned models.

---

## What Needs Verification

These findings are [F3] from secondary summary. Before citing specific numbers in investment analysis or entity files:

| Finding | Key claim to verify | How |
|---------|---------------------|-----|
| Chang (arXiv:2602.11675) | Formal proof of rung collapse, 53-59% recovery | Fetch PDF, read proof |
| Chi et al. (arXiv:2506.21215) | 30-40pp gap on CausalProbe-2024 | Fetch PDF, check experimental conditions |
| He et al. (arXiv:2509.24096) | 20% consistency, 80% false rejection | Fetch PDF, verify benchmark methodology |
| Abdaljalil et al. (arXiv:2506.07106) | Outperforms Self-Consistency | Fetch PDF, check datasets |
| arXiv:2510.01539 | 1.5-2x RL generalization | Fetch PDF, check what "executable counterfactuals" means |
| CRANE (arXiv:2502.09061) | Constraints reduce reasoning | Fetch PDF — ICML venue increases credibility |

---

*Added 2026-03-03. Sources: user-supplied findings from research sweep. All tagged [F3] pending primary source verification.*
*Frontier model caveat applies throughout: thinking models (Opus 4.6, o3, Gemini extended thinking) may have different characteristics from standard instruction-tuned models cited in these papers. RL training on verifiable outcomes is the likely differentiator.*

<!-- knowledge-index
generated: 2026-03-22T00:13:50Z
hash: 7e9d047a8338

table_claims: 6

end-knowledge-index -->
