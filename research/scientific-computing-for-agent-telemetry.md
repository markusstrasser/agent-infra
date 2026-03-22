---
title: Scientific Computing Tools for Agent Telemetry
date: 2026-03-19
---

# Scientific Computing Tools for Agent Telemetry

Date: 2026-03-19
Status: Research complete — assessment per tool

## Current State

Our ~10 measurement scripts use **zero external scientific dependencies**. All statistics come from Python's `statistics` module (`mean`, `stdev`) and hand-rolled arithmetic. The scripts:

| Script | What it measures | Statistical methods used |
|--------|-----------------|------------------------|
| `session-shape.py` | Structural anomaly detection | z-score (manual: `abs(val - mean) / stdev`) |
| `calibration-canary.py` | Answer-confidence calibration | Brier score (manual: `(predicted - outcome)**2`) |
| `fold-detector.py` | Behavioral sycophancy | Regex pattern matching, no statistics |
| `trace-faithfulness.py` | Tool-trace mismatches | Set intersection, no statistics |
| `pushback-index.py` | Sycophancy word detection | Regex counting, ratios |
| `supervision-kpi.py` | Human supervision load | Correction counting, ratios |
| `tool-trajectory.py` | Tool utilization drift | z-score (manual), `mean`/`stdev` |
| `session-features.py` | Behavioral feature extraction | Raw feature vectors, no analysis |
| `compaction-canary.py` | Post-compaction invariant loss | Keyword matching, no statistics |
| `safe-lite-eval.py` | Factual precision | Accuracy ratio |

**Current dependency weight: 0.** Only stdlib + `anthropic` (for LLM calls in canaries).

---

## Tool-by-Tool Assessment

### 1. SPC Libraries (statistical process control)

**Candidates:** `pyspc` (235 stars, GPL-3, last push 2023), `statprocon` (16 stars, MIT, 2024), `pyshewhart` (264 downloads/mo, MIT), `spychart` (NHS origin, MIT, 2025)

**What it would replace:** The z-score anomaly detection in `session-shape.py` and `tool-trajectory.py`. SPC adds: Western Electric rules (run detection), CUSUM (cumulative drift), EWMA (exponentially weighted averages).

**Honest assessment: Cool but unnecessary.** Our z-score approach is 15 lines of code and does the job. SPC's value is in manufacturing where you need multiple detection rules running simultaneously on continuous data streams. We have ~5-20 sessions/day — not enough data density for SPC rules (which need 20-25 baseline points minimum per chart). Western Electric Rule 2 ("9 consecutive points on one side of center") needs 9 consecutive sessions in one direction — at our volume that's 2+ days of data. The z-score is the right tool for sparse, bursty data.

**Dep weight:** `pyspc` pulls numpy + matplotlib + plotly. `statprocon` is zero-dep (data only, no charts) — the lightest option. But we'd import a library to do what `abs(val - mean) / stdev` does.

**Verdict: Skip.** If we ever need CUSUM or EWMA for drift detection, the formulas are 5-10 lines each — simpler to inline than to manage a dependency with 264 downloads/month.

### 2. scipy.stats for Telemetry

**What it would add:** Proper statistical tests (KS test for distribution shifts, Mann-Whitney U for comparing session populations, chi-squared for categorical data). Also: `scipy.stats.zscore()` replaces our manual z-score.

**What it would replace:** Nothing directly — we don't do hypothesis testing today.

**Honest assessment: Genuine value, but not yet.** The gap isn't that we lack scipy — it's that we lack enough data points. With 30-100 sessions/week, most statistical tests are underpowered. The z-score anomaly detector doesn't need `scipy.stats.zscore()` — our 3-line version is correct. Where scipy *would* help: if we wanted to detect distribution shifts between weeks (e.g., "did fold rate change after deploying the anti-sycophancy hook?"). That's a real question, but today we answer it by eyeballing dashboard numbers.

**Dep weight:** scipy is ~35MB installed. Heavy for what we'd use.

**Verdict: Defer.** When we have 500+ session data points and want to do pre/post comparisons for hook deployments, `scipy.stats.mannwhitneyu` or `scipy.stats.ks_2samp` would be the right tool. Not now.

### 3. R `forecast`/`anomalize` Packages

**Candidates:** R's `anomalize` (STL decomposition + GESD/IQR), `forecast::tsoutliers()`, `tsoutliers` package. Python equivalents: `statsmodels.tsa` for STL, `adtk` for anomaly detection.

**What it would replace:** Could replace `session-shape.py`'s anomaly detection with proper time-series decomposition (trend + seasonality + remainder, flag based on remainder).

**Honest assessment: Overkill.** These are designed for high-frequency time series (hourly/daily data with seasonal patterns). Agent sessions don't have seasonality — there's no "Monday effect" or "afternoon drift" worth modeling. Our data is: 5-20 sessions/day, irregularly spaced, with no periodic structure. STL decomposition needs at minimum 2 full seasonal cycles (so >14 days at daily granularity). We'd be fitting a seasonal model to non-seasonal data.

The one transferable idea from R's `anomalize`: using IQR-based bounds instead of z-scores (more robust to outliers). That's one line of code: `Q1 - 1.5*IQR` / `Q3 + 1.5*IQR`. No library needed.

**Dep weight:** R packages need rpy2 bridge (~complex), or switch to `statsmodels` (~15MB). `adtk` is lighter but unmaintained (last release 2021).

**Verdict: Skip.** Extract the IQR idea (one line of code). Don't import the ecosystem.

### 4. PyMC / ArviZ for Bayesian Calibration

**Candidates:** PyMC (Bayesian modeling), ArviZ (visualization/diagnostics), `simuk` (simulation-based calibration from ArviZ team, 56 stars).

**What it would replace:** `calibration-canary.py`'s Brier score computation and calibration assessment.

**Honest assessment: Massively overkill.** Our calibration system asks 25 canary questions across 3 runs and computes Brier score with `(predicted - outcome)**2`. That's the entire computation. PyMC would let us build a hierarchical Bayesian model of calibration per category, estimate posterior distributions of accuracy, etc. — but with 25 canaries x 3 runs = 75 data points, we'd be fitting a model with more parameters than observations.

`simuk` (simulation-based calibration checking) is designed for validating Bayesian model posteriors — completely different problem from "does the agent answer correctly at the confidence it reports."

ArviZ's `plot_calibration` could generate reliability diagrams from our data. That's the one useful thing, but `matplotlib` alone does it in 10 lines.

**Dep weight:** PyMC pulls theano/pytensor + scipy + numpy + arviz. ~200MB+ installed. `simuk` alone is lighter but still needs numpy + scipy.

**Verdict: Skip.** The Brier score is a one-liner. When we scale to 100+ canaries with temporal tracking, `sklearn.metrics.brier_score_loss` is the right step up (see #9 below), not PyMC.

### 5. ruptures (Changepoint Detection)

**Candidates:** `ruptures` (Python, 1.6K+ stars, academic paper arXiv:1801.00826, actively maintained). Implements: PELT, Binary Segmentation, Window-based, Dynamic Programming, Kernel CPD.

**What it would replace:** Nothing directly — we don't do changepoint detection today. But this answers a real question: "when did the agent's behavior shift?"

**Honest assessment: This is the most interesting candidate.** Concrete use cases:
- Detect when fold rate changed (pre/post hook deployment)
- Detect regime shifts in supervision-kpi trends
- Detect when tool utilization patterns shifted
- Segment session-shape features into behavioral epochs

The PELT algorithm is O(n) and designed for exactly our problem: given a time series of metric values, find the points where the statistical properties changed. Our current approach is "eyeball the dashboard" or "compare this week to last week."

**Dep weight:** `ruptures` depends only on numpy. ~2MB installed. Light.

**Risks:**
- We'd need to accumulate enough data points first (~50+ observations per metric). Some metrics run daily (canaries), some are per-session.
- False positives with small datasets — PELT's penalty parameter needs tuning.
- We'd be adding numpy as a transitive dependency (currently zero numpy in the project).

**Verdict: CANDIDATE — defer until data volume justifies it.** When we have 60+ daily metric observations, `ruptures.Pelt` with `model="rbf"` is the right tool to detect behavioral regime shifts. Estimated integration: ~30 lines in a new `metric-changepoints.py` script. Monitor data accumulation in `metrics.jsonl` and revisit when any metric has 60+ observations.

### 6. STUMPY (Matrix Profiles)

**Candidates:** `stumpy` (3K+ stars, Numba JIT-compiled, actively maintained). Finds motifs (repeated patterns) and discords (anomalies) in time series.

**What it would replace:** Could complement `session-shape.py` — instead of z-score on individual features, find sessions that are *unlike any previous session* in multi-dimensional feature space.

**Honest assessment: Wrong granularity.** Matrix profiles shine on long, dense time series (1000+ data points at regular intervals) — EKG signals, server metrics, sensor data. Our session data is: 10 features per session, 5-20 sessions/day, irregular spacing. STUMPY needs a subsequence length parameter (the "window") and computes pairwise distances between all windows. With 100 sessions, that's a 100x100 distance matrix — trivially computable without a library.

The real power of matrix profiles (finding repeated behavioral patterns across sessions) is interesting but requires reframing: instead of "is this session anomalous?" we'd ask "are there recurring session archetypes?" That's a different question, and k-means on feature vectors is simpler.

**Dep weight:** numpy + numba (~100MB for numba alone). Heavy.

**Verdict: Skip.** The problem is tractable with simpler methods. If we ever want session archetype discovery, `sklearn.cluster.KMeans` on feature vectors is 5 lines and more interpretable than matrix profile discords.

### 7. Genomics QC Methodology (FastQC-like)

**What it would replace:** No direct replacement — this is a design pattern, not a library.

**Transferable ideas from FASTQC:**
1. **Multi-metric dashboard with pass/warn/fail per metric.** FastQC runs ~12 quality modules and gives each a traffic-light status. We could apply this to our metrics: fold_rate < 0.1 = pass, 0.1-0.2 = warn, > 0.2 = fail.
2. **Automatic baseline from first N observations.** FastQC establishes quality thresholds from sequence characteristics. We could auto-calibrate thresholds from the first 30 sessions.
3. **Report aggregation (MultiQC pattern).** MultiQC aggregates FastQC reports across samples. We have `dashboard.py` doing this for our metrics — the pattern already exists.

**Honest assessment: We already implement the core pattern.** `dashboard.py` aggregates metrics with color-coded output. `doctor.py` does pass/warn/fail health checks. The gap is that our thresholds are hardcoded rather than data-derived. That's a 20-line enhancement to any existing script, not a library.

**Verdict: Extract the idea, not the tool.** Add adaptive thresholding (percentile-based from historical data) to `session-shape.py` and `dashboard.py`. No dependency needed.

### 8. Great Expectations (Data Validation)

**Candidates:** `great_expectations` (9K+ stars, actively maintained), `pandera` (lighter alternative, pandas-focused).

**What it would replace:** Could validate our `metrics.jsonl`, `session-receipts.jsonl`, `hook-triggers.jsonl`, and SQLite data.

**Honest assessment: Sledgehammer for a thumbtack.** Great Expectations is designed for data pipeline teams managing petabytes of warehouse data with schema evolution, data contracts between teams, and regulatory compliance. Our data validation needs: "does this JSONL line have the expected keys?" and "is this number in range?" We write these checks inline where data is produced.

GX requires: a data context, expectation suites (YAML/JSON), checkpoints, data docs generation. The configuration ceremony is larger than our entire measurement codebase. Pandera is lighter but still assumes pandas DataFrames — we work with raw JSON and sqlite3.

**Dep weight:** `great_expectations` pulls ~50+ dependencies. `pandera` pulls pandas + scipy. Both are heavier than our entire project.

**Verdict: Skip.** Our data validation is 5-10 lines per script, inline. A dedicated validation framework would cost more in configuration than it saves in bugs. If we start getting data corruption issues, `sqlite3` CHECK constraints and Python `assert` statements are the right scale.

### 9. sklearn Brier Score / Calibration

**Candidates:** `sklearn.metrics.brier_score_loss`, `sklearn.calibration.calibration_curve`, `sklearn.calibration.CalibrationDisplay`.

**What it would replace:** The manual `(predicted - outcome)**2` computation in `calibration-canary.py`.

**Honest assessment: The Brier score itself is trivial — one line either way.** But sklearn's `calibration_curve` does something we don't: it bins predictions into buckets and computes per-bucket accuracy, producing a reliability diagram. Our current approach reports a single aggregate Brier score and per-category accuracy. We don't know if the model is overconfident at 70% and underconfident at 90% — that's the gap a calibration curve fills.

However: with 25 canaries x 3 runs = 75 data points, binning into 10 calibration buckets gives ~7.5 points per bin. That's too sparse for a meaningful curve. We'd need 200+ predictions to get useful calibration curves.

**Dep weight:** sklearn pulls numpy + scipy + joblib. ~80MB installed.

**Alternative:** The calibration curve computation is ~15 lines without sklearn:
```python
bins = defaultdict(list)
for conf, outcome in zip(confidences, outcomes):
    bucket = round(conf, 1)  # 0.0, 0.1, ..., 1.0
    bins[bucket].append(outcome)
calibration = {b: mean(o) for b, o in bins.items() if len(o) >= 3}
```

**Verdict: Inline the calibration curve logic (~15 lines) rather than pulling sklearn.** When we have 200+ canary observations, revisit. The Brier score itself doesn't benefit from a library.

### 10. Smith-Waterman for Session Transcript Comparison

**Candidates:** Biopython's `Bio.Align.PairwiseAligner`, custom implementations.

**What it would replace:** Nothing — we don't currently compare session transcripts for similarity.

**Possible use case:** Find sessions that followed similar tool-call sequences. E.g., detect when an agent falls into the same failure pattern across sessions ("session X had the same tool sequence as the failed session Y").

**Honest assessment: Wrong abstraction.** Smith-Waterman aligns character/amino-acid sequences with substitution matrices tuned to biological evolution. Our "sequences" are tool-call lists (Read, Grep, Edit, Bash...) with ~20 distinct symbols. The right tool for comparing short sequences of categorical symbols is:
- **Levenshtein distance** (edit distance) — stdlib `difflib.SequenceMatcher`
- **Longest common subsequence** — `difflib.SequenceMatcher.get_matching_blocks()`
- **Cosine similarity on tool-count vectors** — 3 lines with stdlib

Smith-Waterman's gap penalties and substitution matrices are calibrated for biological sequences (BLOSUM62, PAM250). We'd have to design a custom substitution matrix for tool calls ("how similar is Read to Grep?") — which is just reinventing cosine similarity with extra steps.

**Dep weight:** Biopython ~30MB. Or custom implementation ~50 lines.

**Verdict: Skip.** Use `difflib.SequenceMatcher` (stdlib) for tool-sequence similarity if we ever need it. No biological alignment library required.

---

## Summary Decision Table

| Tool | Replaces | Dep Weight | Reduces Complexity? | Verdict |
|------|----------|-----------|--------------------|---------  |
| SPC libraries | z-score in 2 scripts | numpy+matplotlib | No — adds ceremony to a 3-line computation | **Skip** |
| scipy.stats | nothing yet | ~35MB | Not yet — insufficient data volume | **Defer** |
| R forecast/anomalize | session-shape anomaly detection | rpy2 or statsmodels | No — non-seasonal data | **Skip** (extract IQR idea) |
| PyMC/ArviZ | calibration-canary | ~200MB | No — 75 data points, massively overfit | **Skip** |
| **ruptures** | nothing yet (new capability) | numpy only (~2MB) | **Yes** — answers "when did behavior shift?" | **Candidate** (at 60+ observations) |
| STUMPY | session-shape | numpy+numba (~100MB) | No — wrong granularity for sparse data | **Skip** |
| FastQC methodology | design pattern only | 0 | **Yes** — adaptive thresholds, no dep needed | **Extract idea** |
| Great Expectations | inline data validation | ~50 deps | No — configuration > our entire codebase | **Skip** |
| sklearn calibration | calibration-canary | ~80MB | Marginal — 15-line inline version works | **Inline logic** |
| Smith-Waterman | nothing | ~30MB | No — difflib.SequenceMatcher is better fit | **Skip** |

## Actionable Items

1. **Now (zero-dep):** Add IQR-based bounds as alternative to z-score in `session-shape.py`. One line: `Q1 - 1.5*IQR` / `Q3 + 1.5*IQR`. More robust to outliers than z-score.

2. **Now (zero-dep):** Add calibration curve computation to `calibration-canary.py` — bin predictions by decile, compute per-bin accuracy. ~15 lines, no sklearn needed.

3. **Now (zero-dep):** Add adaptive thresholding to `dashboard.py` — derive pass/warn/fail thresholds from historical metric percentiles instead of hardcoding. FastQC pattern.

4. **When data accumulates (60+ obs per metric):** Evaluate `ruptures` for changepoint detection on metric time series. This is the one tool that provides a genuinely new capability we can't trivially hand-roll. PELT algorithm is non-trivial (~100 lines to implement correctly vs `pip install ruptures`).

5. **When canaries scale to 200+:** Inline calibration curve logic (already described above). Still no sklearn needed.

6. **When sessions reach 500+/week and we want pre/post hook comparisons:** `scipy.stats.mannwhitneyu` for non-parametric two-sample tests. This is the point where scipy earns its 35MB.

## Key Insight

The bottleneck in our measurement system is **data volume, not statistical sophistication.** With 5-20 sessions/day and 25 calibration canaries, most statistical tools are underpowered. The right investments now are: (a) accumulate more data consistently, (b) add the 3 zero-dep improvements above, (c) monitor data volume for when `ruptures` becomes viable. Adding heavyweight scientific computing libraries to a system with 75 calibration data points is like buying a mass spectrometer to check if your coffee is hot.

<!-- knowledge-index
generated: 2026-03-22T00:15:44Z
hash: 7c6f0b5d8346

title: Scientific Computing Tools for Agent Telemetry

end-knowledge-index -->
