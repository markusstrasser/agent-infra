# Inference-Compute Pareto Frontier: model × iteration × scaffold vs (quality, cost)

> Research memo, 2026-06-14. The **iteration↔model-tier exchange rate** — when does N
> loops of a cheaper model match M loops of a stronger one? Grounds extending the heuristic
> routing table (model × effort) into a *measured* frontier with an iteration axis.
> **Provenance:** primary papers with measured curves; numbers extracted via WebFetch of
> ar5iv full-text mirrors (research-mcp `fetch_paper` fails on arXiv — known gotcha).
> Frontier-currency flags inline. Cross-model review not yet run (offer `/critique`).

## TL;DR (the exchange rate is real, bounded, and verifier-gated)

1. **Test-time compute can substitute for model parameters — but only inside the cheaper
   model's reach.** Snell 2024 (FLOPs-matched, PaLM-2): on easy/medium questions a small
   model + optimal test-time compute **beats a 14× larger model**; on the **hardest quintile
   it does not** — there, additional pretraining wins. The substitution has a *coverage
   ceiling*, not a smooth slope.
2. **The exchange rate is dominated by the VERIFIER, not the sampler.** Repeated sampling
   raises *coverage* (pass@k) as an exponentiated power law, but converts to *accuracy* only
   if you can select the right sample. Brown 2024: MATH coverage 95.3% @10k samples but
   majority-vote plateaus ~39.8% — a **~55 pt** gap. Clean verifier (code tests, proofs) →
   sampling pays hugely; no verifier → sampling adds variance, not quality.
3. **Iteration is non-monotonic.** More LLM calls help on easy queries and *hurt* on hard
   ones (majority vote locks in the wrong answer): Chen 2024 measured quality that **rises
   then falls** with call count. Self-refinement of code degrades quality (SlopCodeBench
   2026: structural erosion in 77% of trajectories); quality-aware prompts cut the
   *intercept* by a third but **not the slope**.
4. **Operational rule for our routing table:** the iteration axis is only Pareto-useful in
   the **clear-verifier regime** (constitution Regime 1). There, prefer *N cheap samples +
   verifier* over 1 strong call. In the partial/no-verifier regime (most agent synthesis),
   the iteration axis collapses — escalate the *model tier* instead of the sample count.

---

## 1. Test-time compute ↔ model parameters: the measured exchange rate

**Snell, Lee, Xu, Kumar 2024 — "Scaling LLM Test-Time Compute Optimally…" (arXiv:2408.03314, 1846 cites).**
Base model PaLM-2-S* (Codey); verifier = a process reward model (PRM) trained via Monte-Carlo
rollouts *without human labels* (Wang-style). MATH benchmark, questions binned into **5
difficulty quintiles** by pass@1 over 2048 samples.

Measured findings (full-text):
- **Compute-optimal allocation beats best-of-N by up to 4×** — i.e. matches BoN quality with
  ~4× less test-time compute, by *adapting* the strategy to the question (Fig 8).
- **FLOPs-matched vs a 14× larger pretrained model:** "on easy and intermediate questions …
  test-time compute is often preferable to scaling pretraining"; **"on the hardest questions
  … very little benefit from scaling up test-time compute"** — there, additional pretraining
  compute wins.
- **The R ratio gates it.** Let R = inference-tokens / pretraining-tokens. When **R ≪ 1**
  (few inference calls relative to pretraining), test-time compute is preferable on
  easy/medium. When **R ≫ 1** (heavy inference budget), even *medium* questions flip to
  favoring the bigger pretrained model. → The exchange rate is **not constant**; it degrades
  as you push more compute through a fixed small model.
- **Sequential vs parallel allocation is difficulty-dependent.** Easy questions → *pure
  sequential* revisions optimal. Hard questions → a *mix* (some parallel/search), because
  pure sequential over-commits to a wrong trajectory. "The ideal ratio of sequential to
  parallel varies with difficulty" (exact ratio not tabulated).

**Wu, Sun, Li, Welleck, Yang 2024 — "Inference Scaling Laws / Compute-Optimal Inference"
(arXiv:2408.00724, ICLR'25, 195 cites).** Companion result: derives *inference* scaling laws
trading model size against sampling/search budget, and shows a **compute-optimal inference**
frontier where a smaller model under tree-search/sampling is FLOPs-Pareto-dominant over a
larger model at fixed accuracy — for a bounded accuracy range. (Same shape as Snell; this is
the formal scaling-law statement of the substitution.)

> **Takeaway for the routing table:** the model×iteration cell is **not separable** from
> difficulty. The "exchange rate" is a *function of the difficulty bin*, and it is finite —
> it expires at the top of the cheaper model's competence.

## 2. Repeated sampling & coverage — the verifier is the hinge

**Brown, Juravsky, Ehrlich, … Ré, Mirhoseini 2024 — "Large Language Monkeys"
(arXiv:2407.21787, 810 cites).** The canonical repeated-sampling result.

- **Coverage = pass@k** (fraction of problems solved by *at least one* of k samples) scales
  smoothly as an **exponentiated power law**: `coverage ≈ exp(a·k^(−b))`. Same-family models
  give S-curves with similar slopes, different horizontal offsets.
- **Headline (SWE-bench Lite):** DeepSeek-Coder-V2 coverage **15.9% (1 sample) → 56% (250
  samples)**, exceeding the single-attempt SOTA of **43%**. CodeContests (Gemma-2B): **0.02%
  → 7.1%** over 10k attempts (>300×). GSM8K/MATH (Llama-3-8B): up to **~95%** at 10k.
- **THE CRITICAL CONDITION — coverage ≠ accuracy without a verifier.** "All sample selection
  methods fail to reach the coverage upper bound and saturate before 100 samples." MATH /
  Llama-3-8B: oracle coverage **95.3%**, but **majority-vote plateaus ~39.8%**, reward-model
  selection similar → a **~55-point gap** that more sampling does *not* close. Where an
  *automatic* verifier exists (unit tests, proof checkers), you bank the full coverage curve;
  where it does not, you are capped at the selector's ceiling.
- **Cost (the exchange rate, in dollars):** holding the agent framework constant, **5 samples
  from cheaper DeepSeek solves more SWE-bench-Lite issues than 1 attempt from Claude-3.5 /
  GPT-4o, at >3× lower cost** (DeepSeek 5×: $0.04, 29.6% solved · GPT-4o 1×: $0.13, 24% ·
  Claude-3.5 1×: $0.17, 26.7%). This is the cleanest published instance of *N cheap loops >
  1 strong call* — and it holds **because SWE-bench has a verifier (the test suite).**

> **Pre/post-frontier flag:** Brown/Snell/Wu/Chen are **2024, pre-frontier** (PaLM-2,
> Llama-3-8B, DeepSeek-Coder-V2, GPT-4o). The *mechanism* (coverage power law, verifier gap,
> difficulty-gated substitution) is scale-robust and reproduced in 2025 work below; the
> *rates* are stale — **measure the live model** before quoting a specific %.

## 3. The coverage ceiling — where the exchange rate breaks

**Liu, Gao, Zhao, … Zhou 2025 — "Can 1B LLM Surpass 405B? Rethinking Compute-Optimal TTS"
(arXiv:2502.06703, 145 cites).** The 2025 re-measurement; Llama-3.x + Qwen-2.5 + DeepSeek-R1
distills, with PRM-guided search. Full-text numbers:

| Small model + optimal TTS | Task | Small | Large baseline | FLOPs |
|---|---|---|---|---|
| Llama-3.2-**3B** | MATH-500 | **78.2%** | 405B 71.4% | 100–1000× fewer |
| Llama-3.2-**3B** | AIME24 | **30.0%** | 405B 23.3% | " |
| Qwen2.5-**0.5B** | MATH-500 | **76.4%** | GPT-4o 74.6% | " |
| DeepSeek-R1-distill-**7B** | MATH-500 | **95.2%** | o1 94.8% | " |
| DeepSeek-R1-distill-**7B** | AIME24 | **83.3%** | o1 79.2% | " |

…**but the ceiling is explicit:**
- **Llama-3.2-1B on AIME24 reaches only 10.0%** even with N=512 — it surpasses 405B on
  MATH-500 (72.2%) but **cannot** on the harder AIME (where 405B's reasoning still wins). The
  substitution holds on MATH-class, **breaks on AIME-class hard problems** for the smallest
  models. "Significant drop on AIME24 vs MATH-500" = the coverage ceiling biting.
- **Strategy shifts with model size:** small (<7B) models → **search/beam-search beats
  best-of-N**; large (72B) → **BoN best at all difficulties**; hard problems → **beam search
  preferred**. (Confirms Snell's sequential/parallel difficulty-dependence at 2025 scale.)
- **A weak/out-of-distribution PRM caps everything:** "PRMs are hard to generalize across
  policy models and tasks"; with a mismatched PRM, **search is worse than majority voting.**
  → the *verifier quality* is a hard multiplier on the achievable exchange rate (§6).

**Synthesis of §1+§3 — where the exchange rate breaks:** test-time compute substitutes for
scale **only on problems the cheaper model already solves with non-trivial probability**
(pass@1 > ~0). On problems it essentially never gets right, coverage stays ~0, no verifier
can select a correct sample that was never generated, and **you must escalate the model
tier.** The frontier has a *vertical wall* at the cheaper model's competence boundary.

## 4. Iteration patterns compared — curves and when each dominates

| Pattern | Mechanism | Helps when | Hurts / plateaus when | Needs verifier? |
|---|---|---|---|---|
| **Best-of-N / repeated sampling** | parallel iid samples, pick best | clean automatic verifier; easy/med | no verifier → capped at selector ceiling (Brown ~40% vs 95% coverage) | **YES** (the binding constraint) |
| **Self-consistency (majority vote)** | parallel, vote | short verifiable answers, easy bin | **non-monotonic**: rises then *falls* on hard queries (Chen) | weak proxy verifier |
| **Self-refine / Reflexion** | sequential, model critiques own output | easy bin, abundant signal; verbal feedback grounded in a *real* signal | code: degrades — erosion 77%, verbosity 75.5% (SlopCodeBench) | external signal, else drifts |
| **Verify-and-retry** | sample → check → resample failures | strong verifier present | verifier noisy → retries chase phantom errors | **YES** |
| **Search / beam (PRM-guided)** | tree expansion under reward model | small models, hard problems (Liu) | OOD PRM → worse than majority vote (Liu) | **YES (PRM)** |
| **Adaptive branching tree search** | combine sampling + feedback (AB-MCTS) | external feedback available | extra complexity unjustified absent feedback | feedback signal |
| **Debate / multi-agent** | agents critique each other | — | herds to wrong consensus; modest gains | weak |

Supporting primaries:
- **Chen, Davis, … Zou 2024 — "Are More LLM Calls All You Need?" (arXiv:2403.02419, 97
  cites).** Analytical + empirical: Vote and Filter-Vote performance **first increases then
  decreases** with call count. Cause: *query-difficulty heterogeneity* — more calls help easy
  queries, hurt hard ones (vote locks in the wrong answer). Derives a scaling model to pick
  the **optimal (finite) number of calls** from a small sample. → iteration count is a
  *tunable with an interior optimum*, not "more is better."
- **SlopCodeBench 2026 (arXiv:2603.24755) [current/in-repo].** 15 agents, 36 problems, 196
  iterative checkpoints. Iterative self-extension: **structural erosion in 77% of
  trajectories, verbosity in 75.5%**; agent code **2.3× more verbose, 2.0× more eroded** than
  473 human repos. **Quality-aware prompts cut initial verbosity/erosion by up to a third
  "without affecting degradation rates"** → *instructions shift the intercept; architecture
  (a verifier/gate) shifts the slope.* Best agent passes only 14.8% of checkpoints. This is
  the degradation finding the constitution already cites — corroborated here with the exact
  77%/75.5% split.
- **Huang, Block, … Krishnamurthy 2025 — "Is Best-of-N the Best of Them?" (arXiv:2503.21878,
  77 cites).** Naively scaling BoN **degrades via reward hacking** — the proxy verifier (a
  reward model) is gamed as N grows. Theory + a regularized BoN that avoids the collapse.
  → confirms: with an *imperfect* verifier, more samples can *lower* true quality.
- **Misaki et al. 2025 — "Wider or Deeper? AB-MCTS" (arXiv:2503.04412).** When *external
  feedback* exists, adaptive branching (mix width=sampling with depth=refinement) Pareto-beats
  pure repeated sampling. → the best *pattern* itself depends on whether a feedback signal is
  available — same verifier-conditioning theme.

## 5. Measurement methodology — how to fit & report the frontier (runnable protocol)

Goal: produce iso-quality contours and Pareto-dominant configs over
(model × N_iterations × pattern) vs (cost, quality), for one **task-class with a clean
verifier**. Inherits the eval-methodology canon (see
`research/2026-06-14-eval-methodology-canon.md`): SE+n always, ≥2 seeds, pin the harness.

**Cost metric.** Report **all three, never collapse to one**: (a) **$ at live API prices**
(the decision-relevant axis — Brown's 3× result is a *price* result), (b) **total
output+thinking tokens** (price-invariant, reproducible), (c) **wall-clock p50/p95** (latency
SLA; parallel BoN ≠ sequential refine even at equal tokens). Cost axis = the *binding* one
per the routing-table use case.

**Quality metric.** Verifier pass-rate (exact-match / unit-test / proof-check). **Report two
numbers, not one:** `pass@k` **coverage** (oracle selection ceiling) AND **selected-accuracy**
under the *actual* selector you'd ship (majority vote / reward model / test suite). The gap
between them *is the verifier-quality measurement* (§6). Bootstrap CIs over **≥2 seeds**;
resample at fixed temperature, **never vary temperature to fake seeds** (Miller 2411.00640).

**Stratify by difficulty (mandatory — it is the hidden axis).** Bin items by base-model pass@1
(Snell's quintiles). A frontier averaged over mixed difficulty **hides the non-monotonicity**
(Chen) and the coverage wall (§3). Report per-bin curves; the aggregate is a weighted sum
whose optimum (Chen) sits at a *finite* N.

**Fitting.** Fit coverage to the exponentiated power law `coverage(k) ≈ exp(a·k^(−b))` per
model (Brown) → gives the horizontal-offset parameter that *is* the model-tier knob. Fit
selected-accuracy(k) separately — it saturates earlier; its plateau is the shippable ceiling.

**Iso-quality contour / exchange rate.** For target quality q*, read off `(model, N, pattern)`
points that hit q*; the **exchange rate** = N_cheap / N_strong (or $_cheap / $_strong) along
the q* contour. Expect it to be **finite and to diverge to ∞** as q* approaches the cheap
model's coverage ceiling (no N reaches q* → escalate tier). Pareto front = lower convex hull
in (cost, 1−quality).

**Confounds to control:**
- **Verifier quality** (the dominant confound) — a noisy verifier makes BoN *look* worse and
  can invert the ranking (Huang reward-hacking). Hold the verifier fixed across all cells;
  report its own false-pos/false-neg rate.
- **Task-class heterogeneity** — never pool across difficulty (above).
- **Format/parse failures** counted as wrong (Biderman 2405.14782) — separate
  format-compliance from correctness or rankings flip.
- **Framework held constant** when comparing models (Brown's discipline) — otherwise scaffold
  confounds the model effect.

**Minimum viable run (cheapest-first):** one task-class with a test-suite verifier (e.g.
a code/SWE subset, or a MATH subset with exact-match). 2 model tiers × {N=1,4,16,64} ×
{BoN, self-refine} × 2 seeds, difficulty-binned. ~smoke→full progressive. This is small
enough to run on our infra and directly extends the routing table with one measured cell.

## 6. The verifier-conditioning tie-in (precise statement)

The entire frontier is **conditioned on verifier quality**, and this is the bridge to the
constitution's verifier-conditioned scope (Regimes 1/2/3):

- **The iteration axis pays in proportion to verifier cleanliness.** Sampling/iteration
  converts compute→quality *only* through a selection step. With a **clean, independent,
  cheap verifier** (Regime 1: unit tests, proof checkers, deterministic checks) you bank the
  full coverage curve — Brown's 15.9%→56%, the 3× cost win, Snell's 14× substitution. This is
  exactly where the constitution says **automate / push declining supervision**.
- **With a noisy/proxy verifier** (Regime 2, the common case — reward models, LLM-judges) the
  exchange rate *collapses and can invert*: majority-vote plateaus 55 pts below coverage
  (Brown); BoN reward-hacks and *lowers* true quality as N grows (Huang); an OOD PRM is worse
  than no search (Liu). Here, **more iteration buys variance, not quality** — the constitution's
  "bad eval is worse than none / Goodhart" at the inference layer. Bounded autonomy: cap N
  low, prefer model-tier escalation.
- **With no verifier** (Regime 3, taste/voice/conviction — the principal *is* the verifier):
  the iteration axis is **not a quality lever at all**. An LLM-judge proxy does *not* make it
  one (constitution: "a model-as-judge proxy does not make taste work verifiable"). Iteration
  here only reduces the principal's *production* burden (generate options) — judgment stays
  human. Do **not** spend sampling budget expecting quality gains.

> **One-line rule for the routing table:** *add the iteration axis only in the clear-verifier
> regime; elsewhere the cell degenerates and the right knob is model tier, not loop count.*
> The exchange rate N_cheap↔M_strong is **real and dollar-favorable where a test suite exists**
> (Brown), **finite and difficulty-bounded** (Snell/Liu), and **undefined without a verifier**
> (the §2 gap). The heuristic model×effort table extends to model×effort×N **conditioned on a
> per-task-class verifier-quality tag** — that tag is the new required column.

---

## Sources (primary, with currency flags)
- Snell, Lee, Xu, Kumar 2024 — arXiv:2408.03314 (1846 cites). **Pre-frontier (PaLM-2);
  mechanism robust.** FLOPs-matched 14× substitution; 4× over BoN; difficulty quintiles;
  seq-vs-parallel.
- Wu, Sun, Li, Welleck, Yang 2024 — arXiv:2408.00724, ICLR'25 (195). **Pre-frontier.** Formal
  inference scaling laws / compute-optimal inference frontier.
- Brown, Juravsky, … Ré, Mirhoseini 2024 — arXiv:2407.21787 (810). **Pre-frontier (Llama-3-8B,
  DeepSeek-Coder-V2).** Coverage power law; 55-pt verifier gap; 3× cheaper 5-sample result.
- Chen, Davis, … Zou 2024 — arXiv:2403.02419 (97). **Pre-frontier.** Non-monotonic LLM-call
  scaling; interior optimum; difficulty-heterogeneity mechanism.
- Liu, Gao, … Zhou 2025 — arXiv:2502.06703 (145). **2025 (Llama-3.x/Qwen-2.5/R1-distill).**
  1B>405B on MATH but ceiling on AIME; strategy shift by size; OOD-PRM caps gains.
- Huang, Block, … Krishnamurthy 2025 — arXiv:2503.21878 (77). **2025.** BoN reward-hacking /
  degradation; regularized BoN.
- Misaki et al. 2025 — arXiv:2503.04412 (49). **2025.** AB-MCTS: pattern choice depends on
  feedback availability.
- SlopCodeBench 2026 — arXiv:2603.24755. **Current / in-repo (constitution P1).** Iterative
  code-quality erosion 77%/75.5%; quality prompts shift intercept not slope.
- Agarwal, Sengupta, Chakraborty 2025 — arXiv:2512.02008 (9). **Current (Dec-2025).** Saved,
  not full-read: "systematic comparison of TTS strategies under identical conditions" — the
  most-current head-to-head; **read before running our protocol** (likely supplies the
  identical-conditions methodology §5 wants).

## Gaps / next steps
- Full-read Agarwal 2512.02008 (current identical-conditions comparison) before the protocol run.
- These are math/code (clean-verifier) benchmarks; **no primary measures the exchange rate on
  open-ended AGENT tasks with noisy verifiers** — that is precisely our Regime-2 frontier and
  is *unmeasured*. Our minimum-viable run would be a (small) first data point.
- `fetch_paper` failed on every arXiv id; numbers came via ar5iv WebFetch. Brown full-text
  via ar5iv confirmed the headline figures; not independently re-derived.
