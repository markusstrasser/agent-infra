---
title: Benchmark & Leaderboard Methodology Critique — GENIUS / SOLID / BS
date: 2026-06-14
tags: [evals, benchmarks, leaderboards, methodology, contamination, llm-judge]
status: complete
---

# Benchmark & Leaderboard Methodology Critique

**Question:** For each major AI benchmark/leaderboard — how is it constructed (scoring,
sampling, judge), is it valid, what is the strongest published critique, and what should we
ADOPT or AVOID for our own evals? Separate vendor self-report from independent measurement.

**Extends (do not redo):**
- `research/2026-06-11-aa-benchmark-instrument-validity.md` — Artificial Analysis instrument validity (target 4 mostly done there)
- `research/benchmarking-science-2026.md` — academic critique literature (Platinum, IRT, LLM-judge noise, SWE-bench contamination)
- `research/2026-06-14-composer-2.5-external-benchmarks.md` — Cursor Composer 2.5 external-vs-internal (target 7 Cursor done there)

**Provenance discipline:** Independent measurement and vendor self-report are tagged
[INDEP] / [VENDOR] throughout. The single most important meta-finding: the line between the
two is collapsing — the 2026 AI Index documents transparency falling 58→40, and the
Leaderboard Illusion shows even the "neutral" human-preference leaderboard is structurally
captured by the biggest vendors.

---

## Verdict table (skim this)

| # | Benchmark / Leaderboard | What it is | Verdict | One-line reason |
|---|---|---|---|---|
| 1 | Stanford HAI AI Index 2026 | Annual meta-report | **GENIUS** (as meta-instrument) | Best independent synthesis; its own headline = "benchmarks are losing their grip" |
| 2 | Stanford HELM (CRFM) | Holistic multi-metric eval | **GENIUS design / impractical at frontier** | Scenario×metric matrix + radical transparency is the gold standard; cost + staleness kill freshness |
| 3 | LMArena / Chatbot Arena | Human pairwise Elo | **SOLID method, BS-as-ranking** | Bradley-Terry is sound; the *leaderboard* is structurally captured (Leaderboard Illusion) |
| 4 | Artificial Analysis | Composite index | **SOLID screen, BS-as-composite** | Best independent aggregator, but 33% of weight flows through LLM judges; use per-axis views |
| 5 | SWE-bench → Verified | Agentic code repair | **Verified = SOLID; original = BS** | Human re-annotation removed ~⅓ broken/underspecified tasks; still contamination-exposed |
| 6 | LiveCodeBench / Terminal-Bench / Aider polyglot | Contamination-resistant | **GENIUS mechanisms** | Temporal cutoff / state-verification+adversarial-hardening / immutable-tests = real anti-gaming |
| 7 | Cursor CursorBench / OpenRouter rankings | Vendor instruments | **MARKETING-BS / usage-signal-not-quality** | In-house board cherry-picks; OpenRouter measures spend not capability |

---

## 1. Stanford HAI AI Index 2026 — GENIUS (as meta-instrument)

**Construction.** Annual ~400-page report from Stanford HAI; aggregates third-party benchmark
results, model releases, economic/policy data. NOT itself a benchmark — it's a meta-instrument
that reports on the benchmark ecosystem. Independent of any model vendor. [INDEP]

**What the 2026 edition concludes** (Perplexity web-grounded synthesis of 2026 report coverage;
the direct HAI fetch returned truncated JS, so these are secondary summaries cross-checked where
possible — flagged MED confidence on exact numbers, HIGH on direction):

- **Benchmarks are "losing their grip."** Tests designed to last years are saturating in
  months. Concrete 1-year jumps cited:
  - **SWE-bench Verified: ~60% → ~100%** (flagship saturation example)
  - **Humanity's Last Exam: +30 percentage points** in one year (was 8.8% best in 2025 Index)
  - **Terminal-Bench: ~20% → 77.3%**
  - **OSWorld: 12% → ~66%** (note: 66% = still fails 1-in-3, NOT saturated)
  - **Cybersecurity agents: ~15% (2024) → ~93% (2026)**
- **2025 vs 2026 distinction (important):** the *2025* Index declared MMLU/GSM8K/HumanEval
  "nearly saturated" and foregrounded HLE (8.8%), FrontierMath (~2%), BigCodeBench (35.5% vs
  human 97%) as the new unsolved frontier. The *2026* Index shows even those new frontier tests
  closing fast — the saturation treadmill accelerated.
- **Transparency is the choke point.** The companion **Foundation Model Transparency Index fell
  58/100 (2024) → 40/100 (2025)** [VERIFIED, confidence 1.0, Stanford CRFM primary]. Labs
  disclose less about training data, eval methods, and post-deployment behavior. This is the
  load-bearing finding for reproducibility: you cannot independently reproduce or trust a score
  when you don't know what the model trained on or how the eval was run.
- **Agentic evals = the new frontier**, treated as case studies (OSWorld, Terminal-Bench,
  SWE-bench variants, cyber agents) but flagged as *also* quickly gameable once optimized for.
- **Contamination: treated as background motivation, NOT a new quantitative audit.** The Index
  does not publish "X% of MMLU is in pretraining." Instead it implicitly addresses leakage by
  de-emphasizing old leaked benchmarks and highlighting held-out/private-set designs (HLE, GPQA).

**Strongest critique.** The Index is a *synthesis*, so it inherits the validity of its sources —
when it reports a vendor's self-reported HLE score, that number carries the vendor's contamination
risk. It also lags (annual cadence vs monthly model releases) and leans on lab self-reports for
headline capability numbers because independent reruns don't exist for closed models.

**Verdict: GENIUS** as the best independent ecosystem synthesis we have. Its own thesis validates
this entire memo: the measurement layer is being outrun.

**ADOPT:** The "saturation treadmill" framing as a standing assumption — *any* benchmark we adopt
has a shelf life; pre-register the expected saturation horizon and a replacement. And treat the
**transparency-decline finding as a first-class confound**: a score's trustworthiness is bounded
by the discloser's transparency. Our [INDEP]/[VENDOR] tagging is exactly the right instinct;
formalize it.

---

## 2. Stanford HELM (CRFM) — GENIUS design, impractical-at-frontier

**Construction.** [INDEP] Holistic Evaluation of Language Models (arXiv:2211.09110, CRFM).
Core innovations:
- **Scenario × metric taxonomy.** Explicitly taxonomizes the eval space into *scenarios*
  (use cases: QA, summarization, code, dialogue) × *metrics* (desiderata), then evaluates the
  cross-product. Pre-HELM, models were measured on ~17.9% of core scenarios with little overlap;
  HELM pushed this to ~96% dense coverage under standardized conditions.
- **Seven first-class metrics per scenario** (not just accuracy): **accuracy, calibration,
  robustness, fairness, bias, toxicity, efficiency**. Surfaces tradeoffs a single number hides
  (accurate-but-uncalibrated, capable-but-toxic).
- **Standardized prompting:** identical prompts/sampling/metrics across all models on a scenario
  → genuine comparability.
- **Radical transparency:** releases ALL raw prompts, model completions, and per-instance
  results; open-source Python framework. "Show all your work."
- **Living benchmark:** modular, meant to be continuously extended.

**Validity.** Highest construct validity of any general leaderboard — it is the one that treats
"what should an eval measure" as a research question rather than picking one accuracy number. The
multi-metric matrix directly answers Bean et al.'s construct-validity critique (61.2% of
benchmarks define composites but don't measure sub-components separately — HELM does).

**Strongest critique** (mostly self-acknowledged; no standalone takedown paper exists):
- **Compute/cost intensity.** Many scenarios × many metrics × many models is combinatorially
  expensive; reproducing the *full* HELM is realistically only feasible for well-resourced labs.
  Most users run subsets → comparability erodes.
- **Coverage-vs-depth tradeoff.** Broad-but-shallow per scenario; specialized suites beat it on
  any single capability (e.g., code). Best for "landscape mapping," not fine-grained capability.
- **Scenario/metric selection is unavoidably normative.** "Holistic" is aspirational — the core
  set reflects the authors' value judgments about which use cases/harms matter.
- **Staleness.** Launched late-2022; the "living benchmark" promise has been hard to keep at the
  pace of 2025-2026 releases. Practitioners increasingly use newer agentic/reasoning suites.

**Verdict: GENIUS design / impractical at the frontier.** The *architecture* is the gold
standard; the *operational freshness* is where it loses to nimble single-metric boards.

**ADOPT (highest-value lesson in this memo):** The **scenario × metric matrix is exactly our
model.** For our own evals, never report a bare accuracy — report each task along
accuracy + calibration + robustness, and keep the matrix sparse-but-honest (measure what we
can, mark the gaps explicitly rather than pretending coverage). The transparency norm (store and
re-surface raw prompts + per-instance outputs, not just scores) is already our instinct in the
corpus ledger — HELM is the citable precedent.
**AVOID:** the combinatorial-completeness trap. HELM's own failure mode is trying to be
exhaustive. We run N=1 — pick the 35% of items that carry 93% of the ranking signal
(Benchmark² CAD/DS, per `benchmarking-science-2026.md`) and run those 3× more often.

---

## 3. LMArena / Chatbot Arena — SOLID method, BS-as-ranking

**Construction.** [INDEP harness, crowd-sourced votes] Users submit a prompt, get two anonymous
model responses, vote for the better one. Pairwise outcomes → **Bradley-Terry / Elo** model
produces a global ranking. The *statistical machinery is sound* — pairwise preference aggregation
is a legitimate, well-studied method.

**Why the METHOD is fine but the LEADERBOARD is not — "The Leaderboard Illusion"**
(Singh, Kapoor, Longpre, Hooker et al., arXiv:2504.20879, **52 citations**, Cohere + Princeton +
Stanford + AI2 — a heavyweight independent author list). [INDEP critique] Documented systematic
distortions:

1. **Private testing + selective disclosure.** Providers test many private variants and publish
   only the best. Concrete: **Meta tested 27 private LLM variants** in the lead-up to the Llama-4
   release, disclosing only the winner. This is a best-of-N selection bias baked into the
   headline number.
2. **Unequal data access (the big one).** Battle allocation is wildly skewed toward incumbents:
   - **Google: 19.2%** of all Arena data
   - **OpenAI: 20.4%** of all Arena data
   - **83 open-weight models combined: 29.7%** of total data
   Proprietary models get higher sampling and fewer removals.
3. **Data access → real overfitting.** "Even limited additional [Arena] data can result in
   relative performance gains of **up to 112%** on the Arena distribution." Access to the prompt
   distribution lets you fit the leaderboard, not general quality.
4. **Silent deprecation.** Open/older models are quietly removed, distorting the comparison pool.

**Other documented flaws (corroborating, from `benchmarking-science-2026.md` + prior work):**
- **Style/length bias.** Raw Arena scores correlate with response length and formatting; LMArena
  introduced "Style Control" to regress this out — an admission the raw signal was confounded.
- **Factor collapse in preference (Feuer et al.):** human/LLM preference can't cleanly separate
  style from correctness; ELO-style aggregation produces R²≈0.998 rankings that *mask* genuine
  latent uncertainty and non-transitivity.

**Verdict: SOLID method, BS-as-leaderboard.** Bradley-Terry on blind pairwise votes is a real
measurement; the *public ranking* is structurally captured by whoever has the most data access
and the most private variants to select from. It measures "who optimized for Arena," partly
decoupled from general capability.

**ADOPT:** Pairwise blind comparison + Bradley-Terry is a *good internal pattern* for ranking our
own model/prompt variants on tasks where we lack a hard verifier — BUT only because we control
both sides and have no incentive to game ourselves. Keep blind ID (already in our judge-bias
controls).
**AVOID:** (a) Trusting public Arena rank as a capability signal for vendor selection — it's a
data-access leaderboard. (b) Any leaderboard where the entity being ranked also controls
submission/variant-selection. (c) Raw preference without style/length control — regress it out or
it dominates (we already learned this in `2026-06-11-frontier-judge-bias-measured.md`).

---

## 4. Artificial Analysis — SOLID screen, BS-as-single-number

**(Mostly covered in `2026-06-11-aa-benchmark-instrument-validity.md` — summary + the Composer
ranking question here.)**

**Construction.** [INDEP aggregator] Composite "Intelligence Index" (v4 weights): GDPval-AA 16.7%,
TB-Hard 16.7%, AA-Omniscience 12.5%, HLE 12.5%, τ² 8.3%, SciCode 8.3%, LCR/IFBench/GPQA/CritPt
6.25% each. Runs models itself in its own harness — genuinely independent, the strongest
third-party aggregator. But **~33% of index weight flows through LLM judges** (GDPval-AA is a
single Gemini-3.1-Pro preference Elo; HLE uses LLM equality-checking).

**The Composer 2.5 #3 question (from the dispatch).** AA ranks Composer 2.5 **3rd** on its Coding
Agent Index (score 62 vs Opus 4.7 max 66, GPT-5.5 xhigh 65), at 10-60× lower cost. Per
`2026-06-14-composer-2.5-external-benchmarks.md`: this is the **one independent corroboration** of
Cursor's positioning, and it ranks Composer *below* frontier — i.e., AA is being *honest here*,
not inflating a vendor. The #3 placement is sound as a coarse "near-frontier-ish coder" screen.
The index is NOT sound as a single capability scalar: it hides per-axis inversions (capability vs
calibration; a model can rank high on the composite while being badly uncalibrated).

**Strongest critique.** It's a weighted average of heterogeneous instruments, ~⅓ of which are
LLM-judge-mediated → the composite inherits judge noise and preference bias, and the weights are
AA's editorial choice (not validated against any downstream outcome). Composite scores mask the
tradeoffs that actually drive routing decisions.

**Verdict: SOLID as an independent screen, BS as a single number.** Best-available neutral
aggregator; never a verifier.

**ADOPT:** Use AA's *per-eval views* (it publishes them) — never the composite — for model
routing. The aggregator-runs-it-itself model is the right independence property.
**AVOID:** Quoting "Intelligence Index = X" as if it were a capability measurement. Decompose to
the sub-eval that matches the actual workload (this is the silent-proxy rule).

---

## 5. SWE-bench → SWE-bench Verified — Verified is SOLID, original was BS

**Construction.** [INDEP benchmark, vendor-run scores] SWE-bench: real GitHub issues + PRs from
12 Python repos; agent must produce a patch that passes the repo's hidden test suite. Outcome-
verified (tests pass/fail) — a *clear verifier in principle*.

**Why original SWE-bench was broken (the problems that forced Verified):**
- **Underspecified/unsolvable tasks.** Many issues lacked the info needed to solve them, or the
  "gold" tests checked behavior not described in the issue → agents penalized for tasks no human
  could solve from the prompt.
- **Broken/flaky test environments.** Some tasks had tests that failed regardless of patch
  correctness, or required exact-match solutions.
- **Solvability ceiling unknown** — you couldn't tell capability failure from task brokenness.

**SWE-bench Verified (OpenAI, in collaboration with the SWE-bench authors):** [INDEP construction]
**human re-annotation of 500 tasks by professional developers** who filtered out underspecified,
unsolvable, and broken-environment tasks. Result: a subset where a passing score actually means
"solved the stated problem." This is the **Platinum Benchmark pattern** (Vendrow et al.) applied
in the wild — re-label until the ceiling is real, so you measure the *reliability frontier* not
label noise.

**Remaining critique (contamination — still unsolved):** Per `benchmarking-science-2026.md`,
Prathifkumar et al. (arXiv:2512.10218): models do **3× better on SWE-bench-Verified than on
BeetleBox/SWE-rebench** (same task type, different/newer repos), and **6× better at file
localization without context** — a task "logically impossible" without memorization. So Verified
fixed *solvability/label-noise* but NOT *training-data leakage* (the repos are public and old).
The 2026 AI Index's "~100% SWE-bench Verified" headline must be read through this lens — partly
memorization. **Scores are vendor-self-reported** against the public benchmark; the construction
is independent, the leaderboard numbers are not independently rerun for closed models.

**Verdict: Verified = SOLID (genuine improvement); original = BS (label noise dominated);
both contamination-exposed.**

**ADOPT (the central lesson):** **Human re-annotation to establish a real solvability ceiling is
the single highest-leverage eval-quality move.** Before trusting any pass-rate, audit a sample for
"is this actually solvable from the given info, and is the checker correct?" Our calibration
canaries need exactly this "platinum" audit (already flagged in `benchmarking-science-2026.md`
§6.1). A score on a benchmark you haven't solvability-audited is measuring label noise as much as
capability.
**AVOID:** Comparing current frontier models on SWE-bench numbers as a capability ranking —
contamination makes the deltas misleading. Prefer temporally-fresh repos (SWE-rebench/BeetleBox).

---

## 6. Contamination-resistant designs — GENIUS mechanisms (steal these)

The most directly adoptable section. Each has a *specific* anti-gaming mechanism:

**LiveCodeBench — temporal cutoff.** [INDEP] Continuously ingests new contest problems
(LeetCode/AtCoder/Codeforces), each **annotated with a public release date**. For a model with
training cutoff T, evaluate ONLY on problems released *after* T → cannot have been in training
data. Hidden contest test cases prevent trivial cheats. **Mechanism: time-windowing by release
date relative to training cutoff + continual fresh ingestion.** This is the cleanest
contamination defense in existence — it's structural, not detective.

**Terminal-Bench — state verification + adversarial hardening.** [INDEP] Agents act in isolated
Docker containers (Harbor harness). Crucially, scoring **does NOT read the agent's text output —
separate verification scripts inspect the actual container final state** (files, running
services, configs). "They check the reality of the system, not what the agent says about the
system." Plus an **adversarial exploit agent** that actively tries to cheat each task (e.g.,
`touch success.txt`, monkey-patch the verifier); when it finds an exploit, the test is rewritten.
"Hired a robot to rob their own bank." **Mechanism: outcome/state-based verification + adversarial
red-team hardening of the checker itself.**

**Aider polyglot — immutable tests + enforced edit format.** [INDEP] 225 hardest Exercism
problems across C++/Go/Java/JS/Python/Rust (selected: solved by ≤3 of 7 top models). Model must
edit pre-existing files in a **specified machine-readable diff/whole-file format** (tracked as
"edit format accuracy"), validated by **language-specific unit tests it is explicitly forbidden to
modify** ("The tests are correct, don't try and change them"). Two attempts; 2nd sees test errors.
**Mechanism: immutable hidden unit tests + machine-parsable edit-format protocol** → can't game by
altering tests, printing expected output, or claiming success in prose. (Note: targets
evaluation robustness, NOT temporal contamination — pair it with LiveCodeBench's date filter for
both.)

**Verdict: GENIUS mechanisms, all three.** These are the design patterns the whole field is
converging on because they resist the three gaming vectors: contamination (LiveCodeBench),
self-report inflation (Terminal-Bench state checks), and test-tampering/format-cheats (Aider).

**ADOPT — direct transfers to our evals:**
1. **Temporal holdout by default.** Where we eval on anything that could be in training data
   (papers, code, facts), prefer post-cutoff items and record the cutoff. This is our existing
   "frontier timeliness" rule given an eval mechanism.
2. **State/outcome verification over self-report.** Never let a model's claim of success BE the
   success signal — check ground-truth state (this is literally our constitution's
   "never let a proxy stand in for the principal check" + P8 "fail loud on a dead data plane").
   Terminal-Bench is the external citation for it.
3. **Adversarially harden our own checkers.** Before trusting a verifier/grader, run a red-team
   pass that tries to pass it without doing the work (we have `tool_hallucination_probe.py` and
   the defending-harness grade→judge two-tier; the adversarial-exploit-agent is the missing
   discipline — run it once per new grader). This is the highest-value NEW practice here.
4. **Immutable-tests discipline** for any code eval we build — tests the model can see but not
   edit, format it must conform to.

---

## 7. Vendor-locked claims — MARKETING-BS / usage-signal-not-quality

**Cursor CursorBench / Composer methodology.** [VENDOR]
(Detail in `2026-06-14-composer-2.5-external-benchmarks.md`; verdict here.) Cursor's blog reports
SWE-Bench-Multilingual 79.8%, Terminal-Bench-2.0 69.3%, and **CursorBench v3.1 63.2% — an
in-house benchmark**. HN flagged it directly: "Scores higher than Opus 4.6 on their in-house
benchmark? Sounds legit" [sarcasm]. Cursor cherry-picks boards where it wins (SWE-Multilingual,
CursorBench) and is quiet where GPT-5.5 leads (Terminal-Bench 2.0: 82.7 vs 69.3). The model can't
be run outside Cursor, so it appears on essentially zero neutral leaderboards — **the only
independent measurement is Artificial Analysis (#3, below frontier).**
**Verdict: MARKETING-BS for the in-house board; the independent AA number is the honest read.**
A vendor benchmark named after the vendor, run by the vendor, on a model only the vendor can run,
is a marketing instrument by construction.

**OpenRouter rankings.** [VENDOR — usage telemetry, NOT capability] OpenRouter's "rankings" are
**token-usage / spend-based** — they rank models by how much traffic flows through OpenRouter's
API gateway, not by any quality measurement. This measures *adoption/popularity/price-performance
perception*, which is real signal about *what people are paying for*, but is **not an eval** and
must never be read as a capability ranking. It's also reflexive (defaults, free-tier promotions,
and which models are *available* on OpenRouter drive the numbers).
**Verdict: usage-signal-not-quality.** Trustworthy as a *market* signal (what's being used),
useless as a *capability* signal. Useful to us only for "what are people actually deploying" —
which is a different question than "what's best."

**ADOPT:** Nothing methodologically — but OpenRouter usage data is a fine *market-awareness* input
(treat exactly like the AA "what's deployed" lens, never like a benchmark).
**AVOID:** Any vendor's self-named benchmark as evidence of capability. Flag it as marketing in
the same breath as citing it. The tell: vendor runs it + vendor picks the tasks + model isn't
independently runnable → marketing instrument.

---

## Cross-cutting: what separates GENIUS from BS (the pattern)

The genius designs share three properties; the BS instruments lack ≥1:

1. **The scorer is independent of the scored.** HELM, AA, LiveCodeBench, Terminal-Bench run the
   model themselves. Arena's *method* is independent but its *data access* isn't → capture.
   CursorBench fails this outright.
2. **Ground-truth verification, not self-report or preference.** SWE-bench tests, Terminal-Bench
   state checks, Aider immutable tests = clear verifiers. Arena/GDPval = preference (taste-
   adjacent). The more LLM-judge/preference in the loop, the lower the construct validity.
3. **Contamination is designed against, not assumed away.** LiveCodeBench (temporal) and
   Verified (re-annotation) confront it; original SWE-bench and any static public benchmark
   don't, and their frontier numbers are partly memorization.

**Our eval stack scorecard against this:** we already have (1) — we run our own; we already
believe (2) — constitution's verifier-conditioned autonomy + "no proxy for principal check"; we
partially have (3) — the frontier-timeliness rule, but **no eval-level temporal-holdout
mechanism and no adversarial-checker-hardening pass.** Those two are the concrete net-new
adoptions from this research.

---

## Top adoptable lessons (ranked by value, gated by maintenance)

| # | Lesson | Source | Value | Maintenance | Status vs our stack |
|---|---|---|---|---|---|
| 1 | **Human-audit solvability ceiling before trusting any pass-rate** (Platinum/Verified) | SWE-bench Verified, Vendrow | HIGH | low (one-time per eval) | Flagged for canaries, not done |
| 2 | **Adversarially red-team your own grader** before trusting it | Terminal-Bench exploit agent | HIGH | low (one pass per new grader) | NET-NEW — adopt |
| 3 | **Temporal holdout as an eval mechanism** (post-cutoff items, record cutoff) | LiveCodeBench | HIGH | low | Have the rule, lack the mechanism |
| 4 | **State/outcome verification, never self-report** as success signal | Terminal-Bench | HIGH | none (already a principle) | Have it; cite TB as precedent |
| 5 | **Scenario × metric matrix, never bare accuracy** (report calibration+robustness too) | HELM | MED-HIGH | medium | Partial; formalize |
| 6 | **Per-axis views, never the composite** for routing decisions | AA critique | MED | low | Have the instinct |
| 7 | **Tag every score [INDEP] vs [VENDOR]**; trust bounded by discloser transparency | AI Index / FMTI 58→40 | MED | low | This memo formalizes it |
| 8 | **Prune to the ~35% of items carrying 93% of ranking signal**, run 3× more often | Benchmark² CAD/DS | MED | medium | Flagged, not done |

**AVOID list:** public Arena rank as capability signal (data-access leaderboard); any single
composite scalar (AA Index, etc.) as a verifier; vendor self-named benchmarks (CursorBench) as
capability evidence; OpenRouter usage as quality; static public benchmark frontier numbers
(contaminated) for current-model ranking; combinatorial-completeness in our own evals (HELM's own
failure mode — we're N=1).

---

## Sources

| Source | Type | Authority | Used for |
|---|---|---|---|
| 2026 AI Index (via Perplexity high-context synthesis of report coverage) | Meta-report | [INDEP] | Target 1; MED conf on exact numbers, HIGH on direction |
| Foundation Model Transparency Index 58→40 | Stanford CRFM | [INDEP] VERIFIED conf 1.0 | Transparency/reproducibility finding |
| HELM (arXiv:2211.09110) + crfm.stanford.edu/helm | Benchmark paper | [INDEP] | Target 2 |
| The Leaderboard Illusion (arXiv:2504.20879, 52 cites, Cohere/Princeton/Stanford/AI2) | Critique | [INDEP] | Target 3 — load-bearing |
| LiveCodeBench / Terminal-Bench (Harbor) / Aider polyglot | Benchmark designs | [INDEP] | Target 6 anti-gaming mechanisms |
| `2026-06-11-aa-benchmark-instrument-validity.md` | Prior memo | internal | Target 4 |
| `2026-06-14-composer-2.5-external-benchmarks.md` | Prior memo | internal | Target 7 Cursor |
| `benchmarking-science-2026.md` | Prior memo | internal | SWE-bench contamination, LLM-judge noise, Platinum |

**Confidence caveats:**
- AI Index 2026 *exact* one-year jump numbers are from secondary coverage (direct HAI page
  returned truncated JS); directions and the "losing their grip" thesis are robust, individual
  percentages are MED confidence — re-verify against the primary PDF before quoting a specific
  number in a decision.
- Leaderboard Illusion numbers (27 Meta variants; 19.2%/20.4%/29.7%; up to 112%) are from the
  arXiv abstract/paper page via WebFetch — HIGH confidence (specific, primary-sourced, heavily
  cited paper).
- SWE-bench-Verified contamination (3×/6×) is from Prathifkumar et al. via the prior memo
  (abstract-level), not full-text re-read here.
