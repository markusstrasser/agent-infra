---
title: "/eval skill + evals-repo improvements — design grounded in repo audit + 2026-06 methodology delta"
date: 2026-06-11
tier: standard
status: active
---

# /eval Skill + evals Repo Improvements — Research Memo

**Question:** How should we improve ~/Projects/evals and/or build an /eval skill so agents design and scaffold evals carefully?
**Tier:** Standard | **Date:** 2026-06-11
**Ground truth:** `benchmarking-science-2026.md` (field state through 2026-03), `2026-05-31-eval-benchmark-methodology-delta.md` (judge/stats delta through 2026-05-31), fresh structural audit of ~/Projects/evals (Explore agent, this session), constitution constraints (vetoed: composite quality scores, standing leaderboards, mcp-eval dependency).

---

## 1. What the evals repo already does right (audit summary)

[DATA — Explore-agent audit of ~/Projects/evals, 2026-06-11]

The repo's *methodology* is ahead of most public frameworks: `BENCHMARKS.md` documents a reproducibility convention (EXPERIMENT.md, PREREGISTRATION.md committed first, snapshotted prompts, DECISIONS.md row on verdict), `graders/judge_v1.md` is a stable identity-blind judge, `stats.py` carries Wilson CI / exact McNemar / Cohen's κ, and recent bakeoffs (search, retrieval-backend) caught their own confounds mid-run and qualified verdicts honestly. The "eval is done only when it governs a production change" rule (DECISIONS.md) is the consumption-over-autonomy principle applied correctly.

**The gap is scaffolding and enforcement, not methodology:**

| Gap | Evidence |
|---|---|
| `stats.py` copy-pasted between extraction_bakeoff and search_bakeoff | identical files, two locations |
| No scaffold tool — each eval hand-writes the 8-point checklist from a prior copy | no `new_eval` recipe; convention lives only in BENCHMARKS.md prose |
| Pre-registration discipline inconsistent | extraction/search did it; retrieval-backend informal; sac_bakeoff post-hoc |
| Result schema drift across evals | extraction JSONL ≠ search JSONL fields; cross-eval queries are ad-hoc |
| Judge harness bespoke per eval | judge_intel.py / judge_phenome.py / judge.py each re-implement dispatch, blinding, concurrency |
| Confounds found mid-run, not pre-run | snippet-mode unfairness, autoquery skew — probe-before-build documented but unenforced |
| `evals.duckdb` promised in CLAUDE.md, never built | aspiration with no consumer yet |

## 2. Claims table — external findings

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Judge-score variance decomposes into scenario/generation/judge/residual; round-robin (cyclic) judge-to-scenario assignment eliminates judge bias at the cost of a single-judge run | controlled experiments, MT-Bench + MindEval | MED (B/2, ARR preprint) | [SOURCE: openreview.net/forum?id=XFsjnvL4eG] CyclicJudge | VERIFIED (abstract) |
| 2 | For contemporary (post-2025) judges, verbalized confidence is now a robust soft-scoring signal — often better than logprob-based G-Eval; flips the pre-2025 orthodoxy | 18 LLMs, SummEval + AggreFact | MED (B/2) | [SOURCE: openreview.net/forum?id=X2NIpkT2eY] | VERIFIED (abstract) |
| 3 | Criterion/rubric type explains ~9× more judge-reliability variance than scoring architecture (η²=0.215 vs 0.024, n.s.) — invest in criterion design, not pipeline elaboration | 13 architectures × 44 criteria, 572 pairs | MED (B/2); converges with 2026-04 "criterion matters more than judge" | [SOURCE: openreview.net/forum?id=QXXfdv4zOb] | VERIFIED (abstract) |
| 4 | Hidden evaluator output-contracts dominate code-gen benchmark variance (one format condition flips ICC 0.964→0.035); report prompt-variance (ICC, Best/WorstPrompt), not single-prompt scores | 5 models × 2 benchmarks × 12 prompt variants | MED (B/2) | [SOURCE: openreview.net/forum?id=Q4bJa0PnhX] | VERIFIED (abstract) |
| 5 | LLM auditors of gold labels re-solve and trust their own answer: wrong-reference detection falls 68%→9% as task scale grows, FPs on clean items rise 44%→88%; code-reading audits hold at 80% → audit golds mechanically/by construction, never by LLM re-check | 2,400 audits, defects injected by design | MED-HIGH (B/2, clean design) | [SOURCE: openreview.net/forum?id=mzh9d3dooN] Auditing by Re-Solving | VERIFIED (abstract) |
| 6 | Rubrics are measurement specifications: no raw rubric source is simultaneously reliable, preference-predictive, and adversarially robust; high inter-rater agreement ≠ low exploitability | PReMISE audit framework (Amazon AGI) | MED (B/2) | [SOURCE: arxiv.org/html/2605.30803v1] | VERIFIED (full-text intro) |
| 7 | Standard judge-quality proxies (position bias, transitivity, pairwise agreement) are dominated by close-rank-gap pairs and correlate weakly with ranking accuracy vs gold — assess judges rank-gap-conditionally against human gold | Bradley-Terry analysis + 2 human-rated corpora | MED (B/2) | [SOURCE: openreview.net/forum?id=wxRkUMwf5P] | VERIFIED (abstract) |
| 8 | Judge decoding temperature is a task-dependent reliability/exploration knob — pin it low for reproducible verdicts | systematic study | LOW-MED (C/2) | [SOURCE: openreview.net/forum?id=jYrQ1oshpP] | VERIFIED (abstract) |
| 9 | Public eval-harness frameworks (Inspect AI + inspect-evals-template, promptfoo, evalh, harness-evals, frontier-evals-harness) converge on: config-driven runs, versioned/hashed prompt sets, traces as source of truth, paired bootstrap CIs, candidate-vs-incumbent regression gates | repo/doc survey | HIGH (direct inspection of READMEs) | [SOURCE: github.com/Generality-Labs/inspect-evals-template, github.com/regokan/evalh, github.com/jsp2195/frontier-evals-harness, youngju.dev 2026-05-14 comparison] | VERIFIED |
| 10 | Harness/scaffold choice moves identical weights 10–20 points on public leaderboards; contamination is a spectrum, triangulate static + arena + agentic | practitioner methodology guide | LOW-MED (C/2, blog) | [SOURCE: digitalapplied.com LLM Benchmark Methodology 2026] | UNVERIFIED numbers |

All ARR submissions are preprints under review (provenance ceiling B); treat single-paper findings as strong leads, not consensus. Claims 3 and 7 corroborate the already-memoed 2026-04/05 "criterion > judge" and "panels ≈ 2 effective votes" line — that direction is now multi-paper.

## 3. Pre-Build Check: adopt an existing framework?

**Considered and deferred: Inspect AI** (UK AISI) — the mature dependency candidate; has an official template repo and an evals registry pattern. Deferred because: (a) it is solver/task-oriented for *model* evals and CI-style regression suites, while our evals are one-shot decision-grade bakeoffs whose verdict retires into DECISIONS.md; (b) it would bypass llmx transport (losing subscription routing, cost logging to llmx-usage.jsonl, and the Gemini-503/exit-6 discipline); (c) the mcp-eval due-diligence precedent — heavy LLM-coupled eval deps fail our maintenance filter. Pattern-extract instead: its `src/<eval>/` + registry + per-eval config layout is the right scaffold shape. [INFERENCE]

The smaller harnesses (evalh, frontier-evals-harness, harness-evals) are single-author/low-star — fail bus-factor due diligence as dependencies; useful only as convention references (suite hashing, paired bootstrap deltas).

## 4. Recommendations

### A. Repo architecture (evals repo, mostly deterministic enforcement)

1. **Extract `evalcore/`** — shared package inside the evals repo: `stats.py` (Wilson, exact McNemar, κ, paired bootstrap), `judge.py` (llmx dispatch wrapper enforcing candidate-blind + stakes-neutral prompts, pinned temperature, schema validation, optional verbalized-confidence field, optional cyclic judge assignment), `results.py` (canonical result-row schema: eval, item_id, variant, metric, value, n, provenance, prompt_hash). This clears the proven-common bar (stats.py already implemented identically in 2 evals; judge dispatch in 3) — same test that admitted corpus_core.
2. **`just new-eval <slug>` scaffold** — generates the directory with EXPERIMENT.md + PREREGISTRATION.md templates that *embed the checklist as fill-in fields*: construct + decision the verdict will change, decision rule, screening-vs-confirmatory declaration with minimum-detectable-effect at the planned N (make the 2026-05-31 discordant-pairs insight a computed field, not prose), per-item contamination provenance, 10-item discrimination probe plan, cost guard.
3. **Pre-registration enforcement hook** (architecture over instructions): commit guard — results files cannot land unless PREREGISTRATION.md exists in an earlier commit; warn if the decision-rule hash changes after results exist. Deterministic, fail-open warn.
4. **Gold-label hygiene rule in the template:** golds must be mechanically checkable or human-verified ("platinum"); explicitly ban LLM re-solve audits of references (claim 5).
5. **Defer `evals.duckdb`** until a cross-eval query consumer actually recurs (consumption-over-autonomy). The canonical result schema (A1) is the cheap prerequisite that keeps the option open.

### B. /eval skill (the semantic layer hooks can't enforce)

Phase arc: **0 dedup** (survey ~/Projects/evals + DECISIONS.md + vetoed-decisions before designing anything) → **1 design** (name the construct; name the decision the verdict will change and its consumer; classify verifier regime — deterministic grader vs judge; criterion design effort > pipeline effort) → **2 scaffold** (`just new-eval`) → **3 probe** (10-item discrimination probe before full spend; does the instrument separate anything?) → **4 run + stats** (per-stratum reporting, paired tests, prompt-variance check where applicable) → **5 verdict** (DECISIONS.md row + production wiring or explicit no-change).

Embedded anti-patterns: composite quality scores (vetoed 2×), standing leaderboards (vetoed), judge panels as truth (≈2 effective votes), single global accuracy across strata, judge sees candidate identity, items lifted from public benchmarks, eval with no consumer.

### C. Judge defaults (encode in evalcore + skill)

One strong judge + one diverse-family disagreement instrument (κ + per-item flags), never majority-of-panel as truth; cyclic assignment when multiple judges × scenarios (claim 1); stakes-neutral, candidate-blind prompts; pinned low temperature (claim 8); warrant-explicit rubrics for entailment-type judgments (ForceBench, prior memo); human-anchor gold on small-N sets; collect verbalized confidence as a soft signal (claim 2 — cheap to add, newly defensible).

## 5. What's uncertain

- All 2026-06 judge findings are unreviewed ARR submissions; magnitudes may not transfer to our frontier judges (mechanisms likely do).
- Whether the /eval skill should live in ~/Projects/skills (shared) or evals/.claude/skills — eval authoring happens in genomics/intel too, which argues shared; propagation = propose per constitution.
- CyclicJudge's optimality proof assumes a fixed judge-call budget across multiple scenarios — our single-scenario bakeoffs may not benefit; apply only where judges × scenarios ≥ 2×2.

## 6. Search log

| Tool | Query | Signal |
|---|---|---|
| Explore agent | ~/Projects/evals structural audit | HIGH — gaps table §1 |
| local grep/read | research/ eval memos (benchmarking-science, 2026-05-31 delta) | HIGH — frontier already 90% covered locally |
| Exa advanced | eval harness frameworks / scaffolding best practice (2025-06+) | MED — framework survey, claim 9-10 |
| Exa advanced (research paper, 2026-05-28+) | eval methodology delta | HIGH — claims 1-8, all post-dating the 2026-05-31 memo |

Disconfirmation: the framework axis was itself the disconfirmation check on "build a scaffold" (does this already exist?) — answer: patterns yes, drop-in fit no (§3).
