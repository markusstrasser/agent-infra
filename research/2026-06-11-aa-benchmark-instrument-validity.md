# AA Benchmark Suite — Instrument Validity Read

**Question:** What do the benchmarks behind the Artificial Analysis leaderboard (2026-06-11 snapshot) actually measure, and do our routing/trust conclusions survive contact with the instruments?
**Tier:** Standard | **Date:** 2026-06-11
**Ground truth:** Prior session analyzed the AA leaderboard snapshot and proposed model-guide/llmx-routing deltas (trust table from AA-Omniscience, IFBench routing row, GDPval-AA as workload proxy). All four primary papers fetched and read via research-mcp; AA methodology page fetched.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | AA-Omniscience hallucination rate = i/(p+i+a): share of not-fully-correct answers that were confidently wrong (partial counts as non-hallucinated miss) | §2.4.3 formula, read in full text | HIGH | [SOURCE: arXiv:2511.13029] | VERIFIED |
| 2 | Models are explicitly told to abstain if unsure ("it is better that you say this than get the wrong answer") — measured hallucination is *despite* an abstention invitation | Appendix A.1 answerer prompt | HIGH | [SOURCE: arXiv:2511.13029] | VERIFIED |
| 3 | AA-Omniscience questions are expert-hard, short-exact-answer, closed-book, GPT-5-generated from authoritative sources; difficulty-filtered against frontier models | §2.2, §5 (model-reliance limitation acknowledged in-paper) | HIGH | [SOURCE: arXiv:2511.13029] | VERIFIED |
| 4 | Omniscience grading is short-answer equivalence classification (CORRECT/INCORRECT/PARTIAL/NOT_ATTEMPTED) by Gemini Flash judge, validated against human grading; OI std <0.005 over 10 reps | §2.3 + AA methodology page | HIGH | [SOURCE: arXiv:2511.13029] | VERIFIED |
| 5 | GDPval-AA Elo is judged by a single LLM — Gemini 3.1 Pro Preview, blind pairwise + Bradley-Terry — on OpenAI's 220-task gold subset, run in AA's Stirrup harness (web/search/shell, 100-turn cap) | AA methodology page | HIGH | [SOURCE: artificialanalysis.ai/methodology] | VERIFIED |
| 6 | Original GDPval human–human inter-rater agreement is only 71%; OpenAI's automated grader hits 66% and shows documented self-preference on capable OpenAI models | §2.5, §A.6.2 | HIGH | [SOURCE: arXiv:2510.04374] | VERIFIED |
| 7 | GDPval tasks are one-shot, fully-specified, non-interactive deliverable production ("in real life it often takes effort to figure out the full context") | §5 Limitations | HIGH | [SOURCE: arXiv:2510.04374] | VERIFIED |
| 8 | IFBench's 58 constraints are majority adversarial-synthetic (every-Nth-word-Japanese, prime-length words, odd/even syllable alternation), minority realistic (word-count range, CSV/date format, options-only) | Appendix A constraint table, read in full | HIGH | [SOURCE: arXiv:2507.02833] | VERIFIED |
| 9 | IFBench rank partly reflects RLVR constraint-training, which measurably *degrades* general response quality (judge score 7.0→6.4 after IF-RLVR); constraint-following and answer quality trade off | §5 Reward Hacking | HIGH | [SOURCE: arXiv:2507.02833] | VERIFIED |
| 10 | τ²-Telecom is dual-control (user holds device-side tools; agent diagnoses + instructs), success verified deterministically via environment assertions — a clear verifier | §3.3, Appendix A | HIGH | [SOURCE: arXiv:2506.07982] | VERIFIED |
| 11 | τ² telecom user-simulator critical-error floor ≈6% → the 94-99 frontier band sits at the instrument's noise ceiling; only low scores (Sonnet 76, Haiku 55) are informative | §4.3 Table 2 + leaderboard | HIGH | [SOURCE: arXiv:2506.07982] | VERIFIED + INFERENCE |
| 12 | AA Intelligence Index v4 weights: GDPval-AA 16.7%, TB-Hard 16.7%, Omniscience 12.5% ((acc+non-halluc)/2), HLE 12.5%, τ² 8.3%, SciCode 8.3%, LCR/IFBench/GPQA/CritPt 6.25% each | AA methodology page | MED (small-model extraction of JS-heavy page) | [SOURCE: artificialanalysis.ai/methodology] | VERIFIED |

## Per-instrument verdicts

### AA-Omniscience — trust conclusions STRENGTHENED
What it measures: closed-book recall of expert-hard, long-tail facts + abstention discipline under an explicit "better to say you don't know" instruction. The headline trust numbers (GPT-5.5 86% hallucination-on-miss, Fable 5 55% vs Opus 4.8 36%) are *despite* an abstention invitation — worse than the naive reading, not better.
Scope limits: (a) absolute rates don't transfer to everyday claims — questions are deliberately at the edge of model knowledge; the *ranking* is the signal. (b) GPT-5 generates all questions — wording-bias, if any, favors GPT models, making Claude's #1 accuracy robust but flagging GPT-unfavorable comparisons as conservative. (c) Grading is near-deterministic equivalence checking, not preference — high construct quality.
Routing residue intact: paper's own framing matches ours — well-calibrated low-knowledge models (Haiku-class) suit tool-routing; intelligence does not predict calibration (in-paper finding, §3.2).

### GDPval-AA — "closest to our workload" QUALIFIED
What it actually measures: which agent's one-shot deliverable a single Gemini 3.1 Pro judge prefers, for fully-specified knowledge-work tasks executed in a minimal generic harness. Three construct discounts: (1) LLM-preference Elo, not ground truth — the original's human–human agreement is just 71%, so the construct is taste-adjacent even before swapping in an LLM judge (constitution: model-as-judge ≠ verifiable); (2) non-interactive and pre-contextualized — our daily work is interactive and context-discovery-heavy; (3) judge is cross-lab for the Claude #1 result (a rival-lab judge prefers Fable's deliverables — and ranks its own family 18th, so family-favoritism isn't driving it), but verbosity/style biases are unmeasured. Treat big Elo gaps (Fable/Opus vs GPT-5.5, ~160) as real, small ones (Fable vs Opus, 42) as within construct noise.

### IFBench — proposed routing row RETRACTED, reframed
What it measures: generalization of mechanical output-constraint satisfaction to unseen, largely adversarial-synthetic constraints — i.e., how hard a lab trained RLVR constraint-following, a skill that measurably trades against answer quality (7.0→6.4). Claude family bottom-5 placement ≠ "bad at following instructions"; it is consistent with prioritizing task quality over arbitrary mechanical compliance (and with the system card's "strong steerability" claim — different skill). Residue that survives: don't rely on any Claude (or any model) for letter-exact counts/formats in prose mode — enforce with schemas/validators (architecture over instructions, now benchmark-backed); for unschematizable count-critical prose output GPT-5.5 is moderately better (76 vs 63), a weak preference not a routing rule.

### τ²-Bench Telecom — saturation CONFIRMED mechanically
Good construct (deterministic state assertions, dual-control coordination), but the frontier sits at its ~6% user-simulator noise ceiling: 94-99 is one equivalence class. Use only as a negative screen (Sonnet 4.6 at 76 and Haiku at 55 are real signals of weak dual-control tool discipline).

### Composite Intelligence Index — use per-eval views only
33% of index weight (GDPval-AA 16.7% + HLE 12.5% via LLM equality-checking + parts of others) flows through LLM judges; the single heaviest component is an LLM-preference Elo. The composite is a screen, never a verifier (silent-proxy rule). Per-axis inversions (capability vs calibration) are the routing signal and the composite hides them.

## What's uncertain
- AA methodology page details extracted via WebFetch small-model summarization of a JS-heavy page — index weights and harness configs should be re-checked against the page before being committed into model-guide numbers.
- Fable "(with fallback)" config: Health-domain Omniscience questions may trip bio classifiers → some answers are Opus-by-fallback. Direction of bias unknown but Opus is better-calibrated, so pure-Fable calibration could be marginally worse than measured.
- AA's current judge models (Gemini 3 Flash for Omniscience grading, Gemini 3.1 Pro for GDPval-AA) postdate the papers; judge-validation claims in the papers cover earlier judge versions.

## Sources
- AA-Omniscience: arXiv:2511.13029 (read in full)
- IFBench: arXiv:2507.02833 (read: §1-2, §5, Appendix A; not read: RLVR training sections §3-4 — training methodology, not instrument-relevant)
- GDPval: arXiv:2510.04374 (read: §2.5, §5, §A.6; not read: results/occupation appendices)
- τ²-bench: arXiv:2506.07982 (read: abstract, §3.3, §4.3; not read: domain policy appendices)
- AA Intelligence Index methodology: https://artificialanalysis.ai/methodology/intelligence-benchmarking
- All four papers saved to research corpus with quality cards (none vetoed; all preprint-grade [PREPRINT])
