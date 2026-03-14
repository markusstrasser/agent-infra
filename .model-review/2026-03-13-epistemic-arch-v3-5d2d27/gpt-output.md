Bottom line: **v3 is directionally strong, but it is still optimized for “more checks” more than for “less supervision.”** The best parts are deterministic routing, cheap measurement hooks, and anti-bias prompt hygiene. The weakest parts are **underpowered meta-statistics, proxy-heavy metrics, and no explicit autonomy KPI**.

## 1. Logical Inconsistencies

| Severity | Inconsistency | Evidence in plan | Why it matters | Repair |
|---|---|---:|---|---|
| High | **Principle 1 says “measure domain-specific damage first,” but only ~5/13 items are directly Layer-1** | Items 5,6,7,8,11 are clearly domain-specific; 1 partly; 4 are universal, 4 meta | You may improve measurement count without improving damage capture | Until domain coverage catches up, set a rule: **≥60% of new work must be Layer-1** |
| High | **“Agent confirmation bias is biggest unmeasured threat,” but only 2 items directly measure it** | #5 thesis challenge, #11 missed-negative rate | Biggest stated threat remains mostly uninstrumented | Add one reusable **counterevidence coverage** primitive across all domains |
| High | **“Measure before enforcing” conflicts with “structural forcing / stop hooks” without thresholds** | You reject advisory hooks and prefer forcing/stops | Without precision/coverage thresholds, you can lock in bad scaffolding (your own principle #3) | Require **shadow mode → validate → then enforce** |
| Medium | **“Fail open” conflicts with scite-based checks if coverage is sparse** | Q2 explicitly notes domain coverage may be thin | Sparse external coverage can create false confidence or false blocks | Every monitor needs **coverage + abstain semantics** |
| Medium | **“Recurring patterns (10+) become architecture” but 3-layer architecture is ahead of measured recurrence** | 25+ memos, 4 scripts; many patterns documented, few measured | Architecture may calcify around hypotheses, not observed failure frequencies | Promote only patterns with **measured recurrence or damage**, not memo count alone |
| Medium | **Single-path routing is too coarse for mixed projects** | genomics→research, intel→trading, autoresearch→engineering | Biotech investing / scientific engineering work will be misrouted | Support **multi-label routing or manual override in project root** |
| Medium | **ACC-lite is positioned as architecture before Q1 is answered** | Q1 asks whether trajectory calibration works without log-probs | You risk spending 2 days on a non-transferable result | Treat #10 as **experiment**, not core layer commitment |
| High | **Goodhart detection at n≥8 is statistically weak** | #13 explicitly uses n≥8 | At n=8, Pearson correlation is extremely unstable; \|r\| must be ~0.71 just to clear p<.05, and autocorrelation lowers effective n further | Raise gate to **n≥20–30** or use shrinkage/Bayesian estimates |
| Medium | **Citation-impact Gini is prestige concentration, not evidence quality** | #6 journal impact Gini coefficient | Easy to game; may reward “venue diversification” rather than stronger epistemics | Replace with **evidence-type diversity / contradiction coverage** |

## 2. Cost-Benefit Analysis (rank 13 items by ROI)

**Scoring:** `ROI ≈ (Impact 1–5 × Leverage 1–3 × Confidence 0–1) / Build hours`  
Assumption: personal-project usage is **mixed across the 3 domains**. If your workload is mostly research or trading, reorder accordingly.

| ROI Rank | Item | Hrs | Impact | Leverage | Conf. | ROI | Verdict |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | **#4 Anonymize model identities in review prompts** | 0.5 | 2.0 | 2.5 | 0.95 | **9.5** | **Build now** |
| 2 | **#9 Domain routing hook** | 2 | 3.0 | 3.0 | 0.90 | **4.1** | **Build now** |
| 3 | **#1 Wire scite into researcher Phase 4** | 2.5 | 4.0 | 3.0 | 0.75 | **3.6** | **Build now** |
| 4 | **#3 Add 5 KalshiBench canaries** | 2 | 2.5 | 2.0 | 0.75 | **1.9** | Build now |
| 5 | **#7 Research scite consensus check** | 6 | 4.0 | 2.0 | 0.65 | **0.87** | Build after #1 |
| 6 | **#5 Trading thesis challenge metric** | 8 | 4.0 | 2.0 | 0.70 | **0.70** | Build if trading is frequent |
| 7 | **#2 Fold detector** | 8 | 3.0 | 2.0 | 0.85 | **0.64** | Build if fold/compaction is recurring |
| 8 | **#11 Missed negative rate** | 8 | 3.5 | 2.0 | 0.55 | **0.48** | Build only after #1/#7 stabilize |
| 9 | **#8 Engineering solution diversity (Jaccard)** | 8 | 3.0 | 1.5 | 0.80 | **0.45** | Build if autoresearch volume exists |
| 10 | **#10 ACC-lite from transcripts** | 16 | 4.0 | 3.0 | 0.35 | **0.26** | **Experiment only** |
| 11 | **#12 Cross-session belief drift** | 8 | 2.5 | 1.5 | 0.50 | **0.23** | Defer |
| 12 | **#6 Citation diversity audit (impact Gini)** | 8 | 2.0 | 1.5 | 0.60 | **0.23** | **Replace metric** |
| 13 | **#13 Goodhart detection at n≥8** | 6 | 2.0 | 1.5 | 0.25 | **0.13** | **Defer / redesign** |

### Suggested execution order
**Now:** `#4 → #9 → #1 → #3`  
**Then:** `#7 or #5` depending on session mix  
**Hold:** `#10, #12, #13` until you have replay data and sample size

## 3. Testable Predictions

| Prediction | Metric | Time horizon | Success threshold | Falsifier |
|---|---|---|---|---|
| **P1. Coverage improves materially** | Measured failure modes / documented modes | End of Phase 2 | **≥11/50 = 22%** (from 8%) | <18% means routing/integration underdelivered |
| **P2. Layer-1 beats Layer-0 in actionability** | `% alerts causing output revision or added uncertainty` | 30 sessions | Layer-1 actionability **≥2×** Layer-0 | If similar/lower, domain-specific design is weak |
| **P3. Anonymization reduces model-brand bias** | Variance in model-review scores attributable to model label | 20 blind review pairs | **≥30% reduction** | <10% reduction suggests little reviewer bias |
| **P4. scite increases disconfirmation inclusion** | Contrasting citations per synthesis claim | 30 research sessions | **≥40% relative increase** | No increase or heavy abstention |
| **P5. Thesis challenge predicts downstream quality** | Bottom tertile challenge score vs later thesis revision / bad trade outcome | 20–30 trading theses | Low-challenge group has **≥1.5×** adverse outcomes | Flat ratio means weak signal |
| **P6. ACC-lite beats verbal confidence** | ECE on transcript-feature model vs self-reported confidence | 100+ episodes | **≥20% relative ECE improvement** | No improvement: shelve #10 |
| **P7. n≥8 Goodhart alerts are noisy** | False positive rate on replayed historical runs | 20 replays | **>25% FP rate** | If stable and useful, keep |
| **P8. Impact Gini is weak** | R² with manual memo quality / correction rate | 30 memos | **R² < 0.05** | If >0.15, keep it |

## 4. Constitutional Alignment (Quantified)

### Scoring model
`CAS = 0.35*Autonomy + 0.25*Architecture + 0.20*MeasureBeforeEnforce + 0.10*FailOpen + 0.10*RecurringPatterns`

| Principle | Weight | Score / 10 | Why |
|---|---:|---:|---|
| **Maximize autonomy via declining supervision** | 0.35 | **4.0** | No direct metric for manual review minutes, overrides, or intervention rate. More monitors may initially **increase** supervision |
| **Architecture over instructions** | 0.25 | **8.5** | Strong: mostly scripts, routing, hooks, not prompt advice |
| **Measure before enforcing** | 0.20 | **7.0** | Mostly measurement-oriented, but enforcement thresholds are missing |
| **Fail open** | 0.10 | **6.0** | Deterministic routing helps; sparse scite/meta-statistics hurt |
| **Recurring patterns become architecture** | 0.10 | **5.0** | Architecture is ahead of measured recurrence |

**Composite constitutional score: `6.0 / 10`**

### Key constitutional miss
Your constitution’s north-star is **declining supervision**, but the plan has **no explicit supervision metric**.

Use these:

| KPI | Definition | Desired trend |
|---|---|---|
| **SLI (Supervision Load Index)** | `manual review minutes/session + 5*hard stops + 2*overrides` | Down |
| **AIR (Alert Intervention Rate)** | `alerts accepted / alerts shown` | Up |
| **AGR (Autonomy Gain Rate)** | `- d(SLI)/dt` | Positive |

If SLI rises for 2–3 weeks after rollout, the architecture is not yet constitutionally aligned, even if measurement coverage improves.

## 5. Top 5 Recommendations (different from originals)

| Recommendation | Cost | Why it matters | Expected effect |
|---|---:|---|---|
| **1. Add shadow-mode promotion/kill criteria for every new metric** | 4–6 hrs once | Prevents “bad scaffolding worse than none” | Cuts false enforcement risk; operationalizes “measure before enforcing” |
| **2. Instrument supervision directly (SLI, AIR, AGR)** | 2–3 hrs | Your constitution is about autonomy, not script count | Lets you reject monitors that increase review burden |
| **3. Build a replay harness from archived sessions before live rollout** | ~1 day | Highest-leverage way to evaluate #10, #12, #13 cheaply | Backtests precision/actionability without user-facing cost |
| **4. Give every monitor an explicit `coverage / abstain / confidence` output** | 2–4 hrs | Necessary for fail-open behavior, especially with scite | Prevents sparse-data monitors from becoming pseudo-authoritative |
| **5. Replace proxy-heavy metrics with outcome-linked ones** | ~1 day | Impact Gini and n≥8 correlations are weak | Prioritize metrics tied to corrections, reversals, PnL misses, rerun hours |

## 6. Where I’m Likely Wrong

| My likely error | Why I might be wrong | What would change my mind |
|---|---|---|
| **I may be undervaluing scite** | If your corpus is heavily biomed / clinical / mainstream science, coverage is much better than I assume | scite abstains on **<20%** of target claims and materially changes outputs |
| **I may be too harsh on path-based routing** | If projects are cleanly partitioned by folder and rarely mixed-domain, deterministic routing is ideal | Misroute rate stays **<5%** over a month |
| **I may be underrating ACC-lite** | Transcript features may capture enough uncertainty without log-probs | Replay shows **meaningful ECE gain** over verbal confidence |
| **I may be underrating fold detector** | If compaction/folding is a common real failure in your workflow, it belongs much higher | It catches issues that cause **frequent downstream corrections** |
| **I may be overemphasizing “fail open”** | In high-cost domains, earlier hard gates may be justified even with imperfect metrics | You can show enforced checks reduce net bad outputs without raising SLI materially |

If you want, I can turn this into a **revised 90-day roadmap** with explicit build order, kill criteria, and weekly checkpoints.
