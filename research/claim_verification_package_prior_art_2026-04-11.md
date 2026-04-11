---
title: Claim Verification Package Prior Art — What to Reuse
date: 2026-04-11
tier: standard
ground_truth: factual-verification-systems.md, epistemic-quality-evals.md, benchmarking-science-2026.md, meta-harness-deep-dive-2026-03.md, genomics/docs/research/agent_harness_scientific_truth_review_2026-04-10.md
---

# Claim Verification Package Prior Art — What to Reuse

**Question:** Should we build a claim-verification / scientific-agent benchmark framework from scratch in `~/Projects/agent-infra/`, or consume / extract from an existing open-source framework?

**Tier:** Standard | **Date:** 2026-04-11

**Ground truth assumed (not re-derived):** SAFE/FActScore/VeriScore/SeekBench/FINCH-ZK/Claimify are covered in `factual-verification-systems.md` and `epistemic-quality-evals.md`. Benchmark meta-validity (Platinum, Benchmark², IRT, Judgment-as-Noise) is covered in `benchmarking-science-2026.md`. Meta-Harness is covered in `meta-harness-deep-dive-2026-03.md`. The Feb-Apr 10 paper scan is in `genomics/docs/research/agent_harness_scientific_truth_review_2026-04-10.md`.

---

## Bottom Line

1. **Consume `inspect_ai`** (UK AISI, MIT, 1,856 stars, last push 2026-03-28) as the harness foundation. It is the right shape — `Task` / `Solver` / `Scorer` / `Dataset` abstractions, built-in tool use (bash, python, web_search, MCP, custom), `model_graded_fact()` + custom scorers, 100+ pre-built evals, 200 contributors, active. This matches the plan's P0 schemas almost exactly. Don't rebuild it. [SOURCE: https://github.com/UKGovernmentBEIS/inspect_ai, https://inspect.aisi.org.uk/]

2. **Consume FIRE-Bench's scoring pattern** (github.com/maitrix-org/FIRE-Bench, Python, last push 2026-03-03). It already decomposes both agent conclusions and ground-truth into atomic verifiable claims and computes Precision / Recall / F1 — the **exact pattern the claim-verification benchmark plan needs.** 30 research tasks, 14-category error taxonomy. Best agent (Claude Code Sonnet-4) hits 46.7 F1 — meaningful headroom. [SOURCE: https://firebench.github.io/, https://github.com/maitrix-org/FIRE-Bench]

3. **Exgentic + IBM Unitxt** (Apache 2.0, 48 + 211 stars) is the enterprise-grade backup option. It's the framework from the IBM "General Agent Evaluation" paper (arXiv:2602.22953) and is actively developed as an "Open General Agent Leaderboard" with AppWorld / τ²-bench / technical-support domains. Worth knowing about; probably heavier than we need. [SOURCE: https://github.com/Exgentic/exgentic, https://github.com/IBM/unitxt]

4. **Ignore the rest.** Of the 8 papers in the Apr 10 scan, only 3 ship real usable code (FIRE-Bench, Exgentic, SciVisAgentBench). CUBE is a standards proposal, not shipping code. AutoVerifier is a short demonstration paper without a release. VeRO, SciNav, and the Standardization position paper have no verifiable code in this sweep. `ragas` / `lm-evaluation-harness` / `promptfoo` / `langsmith` / `deepeval` are the wrong shape for this problem (see Q1 table).

5. **Build thin locally.** On top of inspect_ai + FIRE-Bench patterns, we only need: (a) genomics claim corpus adapter over `config/claim_registry.json`, (b) the verdict-enum scorer (`supported / contradicted / mixed / insufficient_evidence / not_verifiable`), (c) retrieval adapters wrapping our existing Exa / scite / S2 MCPs as inspect_ai tools, (d) custom groundedness + calibration + trace-faithfulness scorers (not shipped by inspect_ai), (e) independence card + adequacy card as inspect_ai Task metadata. Everything else the plan asked for is already in inspect_ai or FIRE-Bench.

**Implication for the plan ordering:** The `claim_verification_benchmark_plan`'s Phase 0 (benchmark contract) largely collapses — inspect_ai's `Task` / `Sample` / `Scorer` types ARE the contract. The real work shifts to writing the genomics adapter + custom scorers + 10 gold cases. This probably saves weeks.

---

## Q1 — General-purpose LLM eval framework packages

| Framework | Install | Maintained | Task/Solver/Scorer | Agent tool use | Groundedness / faithfulness | Claim verification fit | Verdict |
|---|---|---|---|---|---|---|---|
| **`inspect_ai`** (UK AISI) | `pip install inspect-ai` | ★1,856 / 200 contrib / last push 2026-03-28 / MIT | Yes (`@task`, `Solver`, `Scorer`, `Sample`) | Built-in: bash/python/text-edit/web_search/web_browser/computer, MCP/custom | Not built-in; custom scorers supported | `model_graded_fact()` shipped + 100+ pre-built evals; full custom scorer support | **CONSUME** — foundation |
| **`ragas`** (explodinggradients) | `pip install ragas` | v0.4.3 Jan 13 2026, actively maintained | Dataset/metric abstractions for RAG | Limited to RAG pipelines; no general agent/tool use | Yes — faithfulness scorer (claim-vs-context) shipped | Only if claim verification framed as RAG faithfulness | **EXTRACT** — borrow faithfulness scorer definition |
| **`deepeval`** (confident-ai) | `pip install deepeval` | Actively maintained | `EvaluationDataset`, `DAGMetric` | Yes — `ToolUse`, `TaskCompletion` metrics for multi-turn agents | Yes — `Faithfulness`, `Relevancy` metrics | Decent for agent-tool-use evals but less extensible than inspect_ai | **EXTRACT** — borrow metric definitions if inspect_ai gaps emerge |
| **`lm-evaluation-harness`** (EleutherAI) | `pip via github` | Actively maintained | Strong Task/Dataset YAML configs | No — single-turn QA / loglikelihood focus | No | Not a fit — no agent or tool-use framing | **IGNORE** — wrong shape |
| **`promptfoo`** | `npm install` (NOT pip) | Actively maintained | YAML testcase / provider abstractions | Yes — agent evals via YAML | No built-in; custom via LLM rubrics | Possible but Node/JS, language mismatch for a Python agent-infra stack | **IGNORE** — language barrier |
| **`langsmith`** (LangChain) | `pip via langchain` | Actively maintained | Dataset/evaluator abstractions | Agent traces / tool use | Via integrations (e.g. DeepEval) | Works but cloud-dependent (LangSmith platform) | **IGNORE** — platform lock-in |

### Why inspect_ai is the right answer

The framework's core abstractions literally are the plan's Phase 0 deliverables:

- **`Task`** = plan's "task manifest"
- **`Sample`** (`input`, `target`) = plan's "claim + gold verdict"
- **`Solver`** = plan's "retrieval / verification / end-to-end pipeline" (composable via `chain()`)
- **`Scorer`** = plan's "verdict accuracy + grounding + process metrics"
- **`Dataset`** = plan's "benchmark corpus"
- **Tools** (`web_search`, custom MCP adapters) = plan's "retrieval adapter interface"

Ships with `model_graded_fact()` which is the closest thing to a claim-verification scorer out of the box. The 100+ pre-built evals include a sycophancy eval, which is a form of factuality check. Extensions are provided as separate Python packages — exactly the model we want for "add a genomics claim-verification package". [SOURCE: https://github.com/UKGovernmentBEIS/inspect_ai, https://inspect.aisi.org.uk/scorers.html] [SOURCE: Perplexity synthesis of inspect_ai docs, Apr 2026]

**Known gap:** inspect_ai does NOT ship groundedness / trace-faithfulness / calibration metrics out of the box — these would need to be custom scorers. That's fine; the scorer API supports it natively. [SOURCE: inspect.aisi.org.uk/scorers.html]

---

## Q2 — Code availability for Feb-Apr 2026 scan papers

| Paper | arXiv | Submitted | Repo | Stars / last push | Ships code? | Verdict |
|---|---|---|---|---|---|---|
| VeRO — Evaluation Harness for Agents to Optimize Agents | 2602.22480 | 2026-02-25 | Abstract says "We release VERO". No repo verified in this sweep. The `github.com/vero-labs-ai/vero-eval` repo (★29) is an UNRELATED pre-existing project from Sep 2025 — not the Feb 2026 paper. | — | **Claimed but not located** | Chase the actual repo before citing |
| FIRE-Bench — Rediscovery of Scientific Insights | 2602.02905 | 2026-02-02 | [github.com/maitrix-org/FIRE-Bench](https://github.com/maitrix-org/FIRE-Bench) + [firebench.github.io](https://firebench.github.io/) | ★6 / last push 2026-03-03 / Python 85% | **Yes** — 30 tasks, atomic-claim P/R/F1 scoring, error taxonomy, run/eval scripts | **CONSUME** — scoring pattern matches plan |
| CUBE — Unifying Agent Benchmarks Standard | 2603.15798 | 2026-03-16 | Abstract is a proposal — "we call on the community to contribute to the development of this standard". No repo released. | — | **No (proposal)** | Ignore until shipping code exists |
| SciNav — General Agent Framework for Scientific Coding | 2603.20256 | 2026-03-11 | No explicit code release in abstract. | — | **No verified release** | Skip |
| SciVisAgentBench — Scientific Viz Agents | 2603.29139 | 2026-03-31 | Abstract: "The benchmark is available at this https URL" (URL redacted in crawler output — follow the arXiv PDF to recover) | — | **Yes (claimed)** | Follow the link in the PDF — likely usable since they mention 108 expert-crafted cases + code checkers + rule-based verifiers |
| AutoVerifier — Agentic Verification Framework | 2604.02617 | 2026-04-03 | 20 KB submission size; demonstrates on one contested quantum computing paper. No repo mentioned. | — | **No** | Extract pattern (6-layer verification) only |
| General Agent Evaluation / **Exgentic** | 2602.22953 | 2026-02-26 | [github.com/Exgentic/exgentic](https://github.com/Exgentic/exgentic) + built on [github.com/IBM/unitxt](https://github.com/IBM/unitxt) | Exgentic ★48 / 21 open issues / Apache 2.0 / Python 98.6% | **Yes** — "Open General Agent Leaderboard" (AppWorld, τ²-bench, technical support). Unitxt: ★211, "enterprise-grade evaluation of AI performance." | **EVALUATE** — serious alternative foundation to inspect_ai; heavier |
| Standardized AI Evaluation (position paper) | 2602.18029 | 2026-02-20 | Position paper; no code expected. | — | **N/A** | Cite for framing only |

**Takeaway:** Of the 8 scan papers, **three** ship usable code (FIRE-Bench, Exgentic/Unitxt, SciVisAgentBench). Two are position / standards proposals with nothing to consume. Three have no verified code release in this sweep.

The single most important code-shipping paper is **FIRE-Bench**, because its claim-level P/R/F1 decomposition is the exact scoring pattern the genomics claim-verification benchmark plan proposes to build. We can borrow the methodology (and likely the `run_eval.sh` script structure) directly.

---

## Q3 — Papers newer than Apr 10 memo (rolling 30 days, 2026-03-12 → 2026-04-11)

Ranked by relevance to claim-verification / scientific-agent / harness engineering. Only papers not already in `agent_harness_scientific_truth_review_2026-04-10.md`, `factual-verification-systems.md`, or `benchmarking-science-2026.md`. [SOURCE: Exa advanced search, arxiv.org domain, startPublishedDate 2026-03-12]

| # | Paper | arXiv | Date | Why it matters | Code |
|---|---|---|---|---|---|
| 1 | **BenchBrowser** — Retrieving Evidence for Evaluating Benchmark Validity (Diddee, Yauney, Swayamdipta, Ippolito) | 2603.18019v2 | 2026-04-09 (v2) | Retriever over 20 benchmark suites for content-validity and convergent-validity diagnosis. Directly relevant to the plan's "independence card" / adequacy card design. Answers "do these benchmarks actually measure what they claim?" | Not stated in abstract |
| 2 | **Natural-Language Agent Harnesses (NLAH)** + Intelligent Harness Runtime (IHR) (Pan et al.) | 2603.25723 | 2026-03-26 | Externalizes harness behavior as editable NL artifact. Complements Meta-Harness's code-based proposer. Could become the format our claim-verification harness is *written in*. | Not stated |
| 3 | **Cross-Context Verification: Hierarchical Detection of Benchmark Memorization** | 2603.21454v2 | 2026-04-02 | Black-box verification of whether LLMs genuinely reason or recall solutions in coding benchmarks. Directly relevant to contamination checks inside the independence card. | Not stated |
| 4 | **Plan-RewardBench / Aligning Agents via Planning** — Trajectory-level reward model benchmark | 2604.08178v1 | 2026-04-10 | Trajectory-level reward-model benchmarking for agentic planning in tool-augmented environments. Complements the "trace auditability" process metric the plan wants. | Not stated |
| 5 | **SkillsBench** — Benchmarking How Well Agent Skills Work Across Environments | 2602.12670 | 2026-03-13 | Agent skill evaluation across environments. Indirect relevance — informs how to think about tool-use evaluation in the retrieval adapter layer. | Not stated |
| 6 | **Externalization in LLM Agents: A Unified Review of Memory, Skills, and ...** | 2604.08224v1 | 2026-04-09 | Systems-level review of how modern LLM agents externalize cognition. Framing for the harness-as-control-plane thesis. | Review paper |
| 7 | **ARC-AGI-3: New Challenge for Frontier Agentic Intelligence** | 2603.24621v1 | 2026-03-24 | New interactive benchmark for frontier agentic intelligence; goal inference, environment modeling. Useful as an external calibration signal for how our agent ecosystem performs on general tasks. | Not stated |
| 8 | **MAP — Multi-Agent Inpatient Pathway Decision Support** | 2503.13205v1 | 2026-03-15 | Medical multi-agent framework. Adjacent to genomics use case — may inform cross-consumer design if `selve` or clinical workflows become benchmark consumers. | Not stated |

**Noise (relevant-sounding but off-topic):** AttackSeqBench (security), KVC (biometrics), AgentLeak (privacy leakage), AssertionForge (SystemVerilog), MatTools (materials science), RAG fairness. [SOURCE: Exa recency sweep, filtered]

**Net-new signal from the recency pass:** BenchBrowser (#1) is genuinely useful — it answers the question the plan's "independence card" is trying to answer (does this benchmark measure what it claims?). NLAH (#2) is a weaker complement to Meta-Harness. The rest are adjacent or noise. No paper from the last 30 days materially changes the "consume inspect_ai + FIRE-Bench" verdict.

---

## Implications for the claim_verification_benchmark plan

Folding these findings back into the plan in `~/Projects/genomics/docs/ops/plans/2026-04-10-claim-verification-benchmark-plan.md`:

### Phase 0 (benchmark contract) mostly collapses

inspect_ai's `Task` / `Sample` / `Scorer` / `Dataset` IS the contract. What remains:
- Decide how the claim verdict enum (`supported / contradicted / mixed / insufficient_evidence / not_verifiable`) maps to inspect_ai's `Score` type (likely a custom `Scorer` returning a `Score(value=str, answer=..., explanation=..., metadata=...)`).
- Decide how the independence card + adequacy card attach to inspect_ai `Task` metadata.

### Phase 1–2 (retrieval + verification adapters) become inspect_ai tools

- Wrap Exa / scite / S2 / Perplexity / Brave as inspect_ai `Tool` functions. These are not new adapter interfaces — they're inspect_ai `@tool` decorators.
- The verification-layer "scorers" (FINCH-ZK-style cross-family, SAFE-lite, VeriScore-lite) become inspect_ai `Scorer` implementations or `Solver` chains.

### Phase 3 (end-to-end) becomes `Solver` composition

- `chain(retrieve, verify, adjudicate)` is the natural inspect_ai pattern.
- FIRE-Bench's atomic-claim decomposition → P/R/F1 scoring can be lifted into a custom inspect_ai `Scorer` that operates on the claim-triple structure inspired by AutoVerifier (decompose into Subject-Predicate-Object triples, then score each atom).

### What actually needs to be written from scratch

1. **Genomics claim corpus adapter** — loads `config/claim_registry.json` as `inspect_ai.Sample` objects with `input=claim_text`, `target=gold_verdict`, `metadata=provenance`.
2. **Verdict-enum scorer** — custom `Scorer` that returns one of 5 verdict values and an evidence-grounding string.
3. **Process metric scorers** — groundedness, calibration, trace-faithfulness. Not shipped by inspect_ai; ~200-400 lines each.
4. **Independence card computation** — derives `label_leakage_risk`, `same_source_overlap` from provenance metadata. This is where BenchBrowser's methodology (paper #1 in Q3) becomes useful.
5. **Adequacy card** — `n_eval`, `split_strategy`, `metric_ci`, `decision_grade`. Simple aggregation from inspect_ai's `EvalLog`.
6. **Genomics policy wire** — bridges `bounded` / `promotion_grade` outputs to `config/surface_promotion_registry.json`.

That's ~1000-1500 lines of adapter code, not a new framework. **The Phase 0 benchmark registry schema and run_record schema were most of what the plan was proposing to build, and inspect_ai already has them.**

### Where to host the genomics package

Two options:
- **`~/Projects/agent-infra/claim_bench/`** — pure inspect_ai extension package, domain-neutral. Good if there will eventually be a second consumer (selve, review-ops skill, etc.).
- **`~/Projects/genomics/scripts/claim_bench/`** — genomics-local inspect_ai extension. Good if genomics is the only consumer for the foreseeable future.

Per the CLAUDE.md "three similar lines of code" rule: keep it in genomics physically until a second real consumer appears. Design the boundary as if it could be extracted (no genomics-specific imports in the scorer / retrieval adapter layers), and the eventual extraction becomes a `git mv` plus import-path fix.

### What is NOT answered by this research (real gaps remaining)

1. **Does inspect_ai's `Solver` chain cleanly represent AutoVerifier's 6 layers?** Probably yes via `chain()`, but needs a 1-hour probe. The 6 layers map to: (L1) corpus construction = `Dataset`, (L2) entity+claim extraction = pre-processing `Solver`, (L3) intra-doc verification = model-graded `Solver`, (L4) cross-source = multi-tool `Solver`, (L5) external corroboration = tool chain, (L6) hypothesis matrix = final `Scorer`. Plausible but untested.
2. **Exgentic vs inspect_ai comparison.** I did not evaluate Exgentic's `Dataset` / `Scorer` types in depth. If Exgentic's enterprise schema has patterns we care about (SLAs, cost tracking, run registries), we may want to borrow from both. Worth a 30-minute follow-up read of the Exgentic docs.
3. **SciVisAgentBench's hybrid LLM-judge + deterministic evaluator pattern.** The abstract mentions image metrics, code checkers, rule-based verifiers, case-specific evaluators. Code is claimed but I didn't follow the link. If we ever need multi-modal deterministic evaluators, this is the reference — worth a read if / when that comes up.
4. **VeRO paper repo.** The Feb 2026 VeRO paper claims release but I couldn't locate the repo in this sweep. Not critical — Meta-Harness already occupies the harness-optimization space more thoroughly.

None of these are blockers for starting the implementation.

---

## Search Log

| # | Tool | Query | Hits | Signal |
|---|------|-------|------|--------|
| 1 | WebFetch | inspect.aisi.org.uk — core abstractions | Task/Solver/Scorer/Dataset confirmed | HIGH |
| 2 | Perplexity | ragas/deepeval/lm-eval-harness/promptfoo/langsmith verdicts | 15 citations; clean verdicts | HIGH |
| 3 | Exa crawling | 8 arXiv abstract pages (Feb-Apr scan papers) | 8 abstracts retrieved | HIGH (half with code claims, half without) |
| 4 | Exa advanced | scientific agent benchmark harness 2026-03-12+ arxiv | 15 results; BenchBrowser, NLAH, Meta-Harness, Plan-RewardBench, Cross-Context Verification, SkillsBench, ARC-AGI-3, MAP | HIGH |
| 5 | Exa advanced | VeRO / FIRE-Bench / Exgentic / SciVisAgentBench code release | FIRE-Bench repo found (maitrix-org); VeRO unresolved | HIGH (FIRE-Bench full project page read) |
| 6 | Perplexity | inspect_ai tool use / scorers / factuality tasks | confirmed built-in web_search, model_graded_fact, 100+ pre-built evals | HIGH |
| 7 | Exa advanced | factuality LLM claim abstention benchmark (second factuality axis) | Mostly noise (RAG fairness, AssertionForge) | LOW |
| 8 | Exa crawling | BenchBrowser + NLAH + inspect_ai GitHub | inspect_ai 1,856★ MIT 200 contributors; BenchBrowser and NLAH abstracts | HIGH |
| 9 | Exa advanced | Exgentic + SciVisAgentBench + CUBE github | Exgentic repo (48★ Apache 2.0) + IBM Unitxt (211★) confirmed | HIGH |

Tool calls used: ~12. Budget: 15-20. Stopped before budget because signal converged.

**Disconfirmation searched for:**
- "inspect_ai unmaintained" / "inspect_ai deprecated" — no hits, 200 contributors, weekly commits
- "inspect_ai doesn't support tool use" — contradicted by docs showing web_search, python, bash, MCP built-in
- "FIRE-Bench retracted" / critique — no hits, ICLR 2026 submission

**Not verified (could not confirm in sweep):**
- VeRO (2602.22480) paper repo — claimed in abstract but not located
- SciVisAgentBench repo URL — mentioned in abstract, redacted in crawler output
- AutoVerifier / SciNav code availability — no evidence of release in abstracts

---

## Sources

- https://github.com/UKGovernmentBEIS/inspect_ai (MIT, ★1,856, last push 2026-03-28)
- https://inspect.aisi.org.uk/ (docs)
- https://inspect.aisi.org.uk/scorers.html (scorer API)
- https://firebench.github.io/ (FIRE-Bench project page)
- https://github.com/maitrix-org/FIRE-Bench (★6, last push 2026-03-03, Python)
- https://github.com/Exgentic/exgentic (Apache 2.0, ★48)
- https://github.com/IBM/unitxt (★211)
- https://arxiv.org/abs/2602.22480 VeRO
- https://arxiv.org/abs/2602.02905 FIRE-Bench
- https://arxiv.org/abs/2603.15798 CUBE
- https://arxiv.org/abs/2603.20256 SciNav
- https://arxiv.org/abs/2603.29139 SciVisAgentBench
- https://arxiv.org/abs/2604.02617 AutoVerifier
- https://arxiv.org/abs/2602.22953 General Agent Evaluation / Exgentic
- https://arxiv.org/abs/2602.18029 Towards More Standardized AI Evaluation
- https://arxiv.org/abs/2603.18019 BenchBrowser
- https://arxiv.org/abs/2603.25723 Natural-Language Agent Harnesses
- https://arxiv.org/abs/2603.21454 Cross-Context Verification
- https://arxiv.org/abs/2604.08178 Plan-RewardBench
- https://arxiv.org/abs/2604.08224 Externalization in LLM Agents
- https://arxiv.org/abs/2603.24621 ARC-AGI-3
- https://arxiv.org/abs/2602.12670 SkillsBench
- https://arxiv.org/abs/2503.13205 MAP (IPDS)
- Perplexity synthesis (Apr 2026) — ragas v0.4.3, deepeval metrics, lm-eval-harness scope, promptfoo YAML, langsmith platform

<!-- knowledge-index
generated: 2026-04-11T17:17:36Z
hash: e89217a2b3e3

title: Claim Verification Package Prior Art — What to Reuse
cross_refs: docs/ops/plans/2026-04-10-claim-verification-benchmark-plan.md, docs/research/agent_harness_scientific_truth_review_2026-04-10.md
table_claims: 21

end-knowledge-index -->
