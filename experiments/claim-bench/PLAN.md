# Claim-Bench Build Plan — 2026-04-11

**Status:** Phase 0 complete (probe successful 2/2 mean=1.000) → Phase 1 active
**Owner:** agent-infra
**Location:** `experiments/claim-bench/PLAN.md` (tracked; `.claude/plans/` is gitignored in this repo)
**Replaces:** two orphan plans formerly in `genomics/docs/ops/plans/` (2026-04-10-scientific-agent-benchmark-integration-plan.md, 2026-04-10-claim-verification-benchmark-plan.md), neither registered in planctl, both removed during the Apr 11 relocation

**Question:** How do we build a claim-verification + scientific-agent benchmark that genomics, selve, the research skill, and any other consumer can use — without reinventing inspect_ai or FIRE-Bench?

## Decision

Build `experiments/claim-bench/` as an **inspect_ai extension package** that ships:

1. A **verdict-enum scorer** (`supported / contradicted / mixed / insufficient_evidence / not_verifiable`)
2. **Retrieval adapters** wrapping Exa / scite / S2 / Perplexity / Brave as inspect_ai `@tool` functions
3. **Process-quality scorers** that inspect_ai doesn't ship (`groundedness`, `calibration`, `trace_faithfulness`)
4. **Independence card + adequacy card** as inspect_ai `Task` metadata
5. A **claim corpus** schema, with adapters for genomics (`claim_registry.json`), selve health docs, and any other consumer
6. **FIRE-Bench-style atomic-claim P/R/F1** as a custom `Scorer` inspired by AutoVerifier's Subject-Predicate-Object decomposition

We do **not** build:
- A new framework — inspect_ai is the framework
- A new task manifest schema — inspect_ai's `Task` / `Sample` is the manifest
- A new run-record schema — inspect_ai's `EvalLog` is the run record
- A new tool adapter interface — inspect_ai `@tool` is the interface
- An LLM-judge-only scoring pipeline — must combine deterministic + judge

This collapses what was Phase 0 of the original plan (~60% of the work).

## Research basis

- `research/claim_verification_package_prior_art_2026-04-11.md` — the consume-vs-build verdict. inspect_ai (1,856 stars, MIT) wins. FIRE-Bench ships the scoring pattern. Three of eight Apr-10 scan papers ship usable code.
- `research/agent_harness_scientific_truth_review_2026-04-10.md` — the Feb-Apr scan that surfaced VeRO / FIRE-Bench / AutoVerifier / Meta-Harness / SciNav.
- `research/factual-verification-systems.md` — SAFE/FActScore/VeriScore/FINCH-ZK. These are evaluation metrics, not framework shells. Borrow patterns, don't depend on them.
- `research/epistemic-quality-evals.md` — SeekBench's groundedness/recovery/calibration triple is the model for the process-quality scorers.
- `research/benchmarking-science-2026.md` — Platinum Benchmarks, Benchmark² (CAD/DS/CBRC), Judgment-as-Noise. Informs the independence card design.
- `research/meta-harness-deep-dive-2026-03.md` — outer-loop optimization. Defer. Don't build until base harness is stable.

## Architecture

### Package boundary

```
agent-infra/experiments/claim-bench/        (this build, domain-neutral)
├── README.md
├── task.py                # inspect_ai Task definition
├── scorer.py              # verdict-enum + atomic-claim scorers
├── tools.py               # retrieval adapters wrapping Exa/scite/S2
├── process_metrics.py     # groundedness / calibration / trace faithfulness
├── cards.py               # independence + adequacy card derivation
├── cases/                 # gold cases (cross-domain to start)
│   ├── 001_supported_*.json
│   ├── 002_contradicted_*.json
│   └── ...
└── runs/                  # eval outputs (gitignored)

# Future, when a second consumer materializes:
agent-infra/claim_bench/                    (extracted package)
genomics/scripts/claim_bench_genomics/      (genomics adapter)
selve/scripts/claim_bench_selve/            (selve adapter)
```

We start in `experiments/claim-bench/` because it's the agent-infra convention for builds-in-progress (cf. `experiments/toy-scorer/`). When a second consumer appears OR the build proves stable, extract to a top-level `claim_bench/` package and write thin domain adapters in genomics/selve.

### What lives where

| Concern | Location | Why |
|---|---|---|
| Verdict enum, scorer, atomic-claim P/R/F1 | `experiments/claim-bench/scorer.py` | Domain-neutral |
| Retrieval tools (Exa, scite, S2, ...) | `experiments/claim-bench/tools.py` | All MCPs are user-scope, domain-neutral |
| Process metrics | `experiments/claim-bench/process_metrics.py` | Domain-neutral |
| Cross-domain gold cases | `experiments/claim-bench/cases/*.json` | Test the schema first; genomics cases come later |
| Genomics gold cases | future `genomics/scripts/claim_bench_genomics/cases/` | Sourced from `claim_registry.json` and `docs/audit/*.md` |
| Domain verdict translation | future `<domain>/claim_bench_<domain>/translation.py` | E.g. genomics "supported" → "compatible with" per `epistemic_scope_2026-04-03.md` |
| Promotion gate wiring | future `<domain>/claim_bench_<domain>/promotion.py` | E.g. genomics `surface_promotion_registry.json` |

## Build phases

### Phase 0 — Inspect_ai probe (THIS WEEK)

**Goal:** Confirm inspect_ai's `Task` / `Solver` / `Scorer` / `Sample` types can cleanly represent a claim-verification benchmark.

**Deliver:**
- `experiments/claim-bench/task.py` — minimal Task with placeholder solver and a verdict-enum Scorer
- `experiments/claim-bench/cases/` — 2 hand-crafted cross-domain gold cases (1 supported, 1 contradicted)
- Run `inspect eval` and confirm the eval log structure has what we need
- `LEARNINGS.md` notes: schema gaps, what inspect_ai already covers, what needs custom code

**Exit:** one Task runs end-to-end against a placeholder solver, scorer returns one of the 5 verdicts, EvalLog has the metadata we need for cards.

**Why first:** This is the highest-leverage 1-hour probe. If inspect_ai can't represent the verdict enum cleanly, the entire architecture pivots.

### Phase 1 — Real solver + retrieval tools

**Deliver:**
- `tools.py` — `@tool exa_search()`, `@tool scite_search()`, `@tool s2_search()` wrapping the existing user-scope MCPs
- A real solver chain: retrieve → ground → adjudicate
- 4 more cases (mixed, insufficient_evidence, not_verifiable) — total 6

**Exit:** end-to-end run on 6 cases produces verdict + evidence trace + cost.

### Phase 2 — Process metrics (the inspect_ai gap)

**Deliver:**
- `process_metrics.py` — `groundedness_scorer()`, `calibration_scorer()`, `trace_faithfulness_scorer()`
- Each ~200-400 lines, custom inspect_ai `Scorer` implementations
- Validation: hand-grade 6 cases on each metric, compare to scorer output

**Exit:** the three metrics agree with hand-grading on ≥4/6 cases.

### Phase 3 — Atomic-claim P/R/F1 scorer (FIRE-Bench pattern)

**Deliver:**
- `scorer.py` extension: `atomic_claim_pr_f1_scorer()` that decomposes both prediction and gold into Subject-Predicate-Object triples (AutoVerifier pattern) and computes Precision / Recall / F1 (FIRE-Bench pattern)
- Cross-check: results should agree directionally with FIRE-Bench's published numbers on a borrowed task

**Exit:** atomic-claim scorer runs on the 6 cases, produces P/R/F1 per case.

### Phase 4 — Cards

**Deliver:**
- `cards.py` — derives `independence_card` (label_leakage_risk, same_source_overlap, non_independent_comparators) and `adequacy_card` (n_eval, ci_method, decision_grade) from EvalLog metadata
- BenchBrowser pattern (`arXiv:2603.18019`) informs the independence card heuristics
- Cards attach to inspect_ai `Task` metadata

**Exit:** every benchmark run produces both cards alongside the score.

### Phase 5 — First domain adapter (genomics)

**Deliver:**
- `genomics/scripts/claim_bench_genomics/corpus.py` — loads `config/claim_registry.json` as inspect_ai Samples
- 4 genomics cases from existing `docs/audit/biomedical-fact-check-*` material
- Verdict translation layer (general enum → epistemic_scope language)
- Wire into `config/surface_promotion_registry.json` so a `bounded` result blocks shipping

**Exit:** genomics-claim-verification eval runs end-to-end, produces a real shippable score that the surface promotion registry consumes.

### Phase 6 — Extract package (only if second consumer appears)

If selve, the research skill, or another project starts consuming the experiment, extract `experiments/claim-bench/` to top-level `agent-infra/claim_bench/` as a real package, and write thin domain adapters in each consumer.

If no second consumer in 3 months, leave it in `experiments/`.

## What needs more research (open gaps)

1. **Does inspect_ai's `Solver` chain cleanly represent AutoVerifier's 6 layers?** Likely yes via `chain()`, but unverified. Phase 0 probe should test this — write a 3-layer chain (corpus → extract → adjudicate) and see if the abstraction holds.
2. **Exgentic vs inspect_ai comparison** — I did not deeply evaluate Exgentic / IBM Unitxt's schema. If inspect_ai hits a blocker on enterprise features (cost tracking, SLAs, run registries), this is the alternative. ~30min doc read.
3. **SciVisAgentBench's hybrid LLM-judge + deterministic evaluator pattern** — relevant when multi-modal evaluation arrives. Defer until needed.
4. **VeRO repo** — the Feb 2026 paper claims release but the repo wasn't located in the prior-art sweep. Not blocking; Meta-Harness (already deep-dived) covers the harness-optimization space.

## Vetoed approaches (do not re-derive)

- **Building a new framework from scratch.** inspect_ai is the framework. ~$0 to consume, weeks to rebuild.
- **One blended score across unlike tools.** Retrieval, verification, and end-to-end adjudication get separate scores per the consume-inspect_ai memo. Don't collapse.
- **LLM-judge-only scoring.** Per `benchmarking-science-2026.md` (Judgment-as-Noise), LLM judges have >90% unexplained variance. Combine with deterministic evaluators (FIRE-Bench pattern) wherever possible.
- **Outer-loop optimization (Meta-Harness) before the base harness is stable.** Per `meta-harness-deep-dive-2026-03.md`, this only pays off after traces are trusted and failure decomposition is useful.
- **Cross-model debate as the verification mechanism.** Per the Debate-or-Vote finding (`agent-reliability-benchmarks.md`), debate is a martingale. Use cross-family verification as an *uncertainty signal*, not as a *consensus mechanism*.

## Task families (preserved from genomics integration plan)

When the experiment moves to real cases, organize the corpus into four families. These are domain-neutral; the genomics adapter populates them with genomics-specific instances.

- **Family A: Rediscovery** — agent given a research question, must rediscover the published finding. FIRE-Bench pattern. Genomics example: predictor demotion case (JARVIS/MACIE).
- **Family B: Verification** — agent given a claim + sources, must verify or refute. Genomics example: scientific claim governance case from `claim_registry.json`.
- **Family C: Null / adversarial** — agent must abstain or surface contradiction on weak evidence. Genomics example: null variant set (no real signal).
- **Family D: Bounded scientific coding** — agent must choose between candidate analysis plans. Optional, only where executable comparison exists. SciNav pattern.

## First concrete step

Run `inspect eval experiments/claim-bench/task.py` after Phase 0 stub is in place. That probe answers the only question that can change the architecture: does inspect_ai represent the verdict enum cleanly?

Everything else builds on the answer to that probe.
