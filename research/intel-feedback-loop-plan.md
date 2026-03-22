---
title: "Action Plan: Close the Error-Correction Loop"
date: 2026-02-28
---

# Action Plan: Close the Error-Correction Loop

**Date:** 2026-02-28
**Source:** Cross-model review (Gemini 3.1 Pro + GPT-5.2) + codebase fact-check
**Generative principle:** "Maximize the rate at which the system corrects its own errors about the world, measured by market feedback."

## Diagnosis

The system has 28 signal scanners, rigorous Bayesian fusion, 141 datasets, and 212GB of data. It also has prediction tracking, backtesting, and paper trading **already built.** The binding constraint is not missing code — it's that the existing feedback loop isn't running.

### What EXISTS but is DORMANT

| Component | File | State |
|-----------|------|-------|
| Prediction tracker | `tools/prediction_tracker.py` | 24 predictions, 3 resolved. CLI works. |
| Prediction DuckDB tables | `tools/prediction_tables.py` | Code exists. **Tables never created** in state.duckdb. |
| Paper trading ledger | `tools/paper_ledger.py` | $100K portfolio, 2 positions (MRVL long $7.9K, HIMS short $3.1K), 3 trades. SHA-256 hash chain for tamperproofing. Signal→action mapping defined. |
| Backtest framework | `tools/backtest.py` | 28 scenarios (battery, copper, energy, health, semis, screens). PIT contamination tracking. |
| Experiment registry | `tools/prediction_tables.py` | `experiment_registry` table schema defined. Never created. |
| Orchestrator | `tools/orchestrator.py` | Built. Not on cron. Never run regularly. |
| Daily data refresh | `tools/daily_refresh.py` | Built. Cron entries documented in docstring. **Not installed** in crontab. |

### What's MISSING (actual gaps)

| Gap | Impact | Effort |
|-----|--------|--------|
| **Signal scanner → auto-predictions** | Signals fire into CSV void. No automated prediction creation from scanner output. | ~200 LOC (`emit_predictions.py`) |
| **Daily price resolver** | Expired predictions don't auto-resolve. The 3 resolutions were manual. | ~100 LOC (extend `prediction_tracker.py resolve`) |
| **Cron jobs for the pipeline** | Nothing runs automatically. daily_refresh, signal_scanner, resolver, mark-to-market — all manual. | ~20 lines crontab |
| **Calibration feedback** | Per-scanner hit rates don't feed back to LLR priors. `estimate_beta_alpha()` exists but isn't wired to prediction data. | ~200 LOC (`calibrate_scanners.py`) |
| **FDR control** | 28 scanners × 70 tickers = 1960 implicit tests/month. No multiple testing correction. | ~150 LOC |
| **Canary/null tests** | No way to verify edge isn't from data leakage. | ~100 LOC |

---

## Phase 1: Activate the Feedback Loop (Week 1)

**Goal:** Signals fire → predictions auto-created → daily resolver runs → you know which scanners work.

### 1.1 Create prediction tables in state.duckdb
```bash
cd ~/Projects/intel
uvx --with duckdb python3 tools/prediction_tables.py --migrate
```
**Effort:** 0 LOC, 1 command. Migrates 24 existing CSV predictions into DuckDB.
**Verify:** `SELECT COUNT(*) FROM prediction` returns 24.

### 1.2 Write `emit_predictions.py`
**What:** Read today's `datasets/alerts/signals_investment_YYYYMMDD.csv`. For each ticker with fused posterior > threshold, create a prediction in `prediction_tracker.py`.

**Design:**
```
Input: signals_investment_YYYYMMDD.csv (from signal_scanner)
Filter: posterior_prob >= 0.60 AND signal_type IN (CROSS_SIGNAL_CONVERGENCE, EVENT_CASCADE, MULTI_SIGNAL)
Output: For each qualifying ticker, call prediction_tracker add with:
  - ticker
  - claim: auto-generated from signal descriptions
  - direction: ABOVE (long bias for now)
  - target_value: entry_price * 1.10 (10% gain target, adjustable)
  - confidence_pct: posterior_prob * 100
  - timeframe_months: 3 (default horizon)
  - source: "signal_scanner:auto"
  - resolution_mode: TERMINAL
Dedup: skip if open prediction already exists for same ticker
```

**Effort:** ~150 LOC.
**Verify:** After running scanner + emitter, `prediction_tracker.py list --pending` shows new auto-predictions.

### 1.3 Wire daily prediction resolver to price data
**What:** Extend `prediction_tracker.py resolve` to auto-resolve expired predictions. Currently works but isn't called automatically.

**Check:** The resolve command already exists. The gap is:
- Does it handle TERMINAL mode correctly? (check close price on deadline)
- Does it pull from `prices` view in intel.duckdb?
- Does it compute Brier scores?

**Action:** Read `prediction_tracker.py` resolve logic. If it works, skip. If not, patch (~50 LOC).
**Verify:** `prediction_tracker.py resolve` resolves any expired predictions and updates CSV + DuckDB.

### 1.4 Set up cron pipeline
```crontab
# === Intel Investment Pipeline ===

# 1. Data refresh: 6am ET daily
0 6 * * * cd /Users/alien/Projects/intel && uvx --with requests python3 tools/daily_refresh.py >> logs/daily_refresh.log 2>&1

# 2. Signal scanner: 7am ET daily (after data refresh)
0 7 * * * cd /Users/alien/Projects/intel && uvx --with duckdb python3 tools/signal_scanner.py >> logs/signal_scanner.log 2>&1

# 3. Emit predictions from scanner output: 7:15am ET
15 7 * * * cd /Users/alien/Projects/intel && uvx --with duckdb python3 tools/emit_predictions.py >> logs/emit_predictions.log 2>&1

# 4. Resolve expired predictions: 7:30am ET
30 7 * * * cd /Users/alien/Projects/intel && uvx --with duckdb python3 tools/prediction_tracker.py resolve >> logs/resolve.log 2>&1

# 5. Mark-to-market paper portfolio: 7:45am ET
45 7 * * * cd /Users/alien/Projects/intel && uvx --with duckdb python3 tools/paper_ledger.py mark >> logs/mark.log 2>&1

# 6. Calibration report: 8am ET (after all above)
0 8 * * * cd /Users/alien/Projects/intel && uvx --with duckdb python3 tools/prediction_tracker.py score >> logs/calibration.log 2>&1

# 7. Hourly energy prices (trading hours only)
0 7-20 * * 1-5 cd /Users/alien/Projects/intel && uvx --with requests python3 tools/daily_refresh.py --source nyiso --source ercot >> logs/hourly_refresh.log 2>&1
```

**Effort:** ~20 lines crontab.
**Verify:** `crontab -l` shows the pipeline. Next morning, check logs.
**Risk:** `uvx` resolution in cron environment — may need full path to `uvx`. Test with `env -i HOME=$HOME PATH=$PATH crontab` or wrapper script.

### 1.5 Create `logs/` directory and ensure rotation
```bash
mkdir -p ~/Projects/intel/logs
```
Consider logrotate or simple date-stamped logs to prevent unbounded growth.

**Phase 1 Deliverable:** Every morning at 8am, you have: fresh data, today's signals, auto-created predictions, resolved expired predictions, marked-to-market portfolio, and a calibration score. **The error-correction loop is running.**

---

## Phase 2: Learn Which Scanners Work (Week 2-3)

**Goal:** Replace guessed LLR priors with empirical hit rates. Kill underperforming scanners.

### 2.1 Write `calibrate_scanners.py`
**What:** Query resolved predictions grouped by source scanner. Compute per-scanner:
- hit rate (P(alpha > 0 | signal fired))
- Brier score
- sample N
- empirical p_hit_h1 and p_hit_h0

**Design:**
```sql
-- Per-scanner hit rate from resolved predictions
SELECT
    p.strategy AS scanner_type,
    COUNT(*) AS n_resolved,
    AVG(CASE WHEN pr.final_outcome = 'hit' THEN 1.0 ELSE 0.0 END) AS hit_rate,
    AVG(pr.brier) AS mean_brier,
    STDDEV(pr.brier) AS brier_std
FROM prediction p
JOIN prediction_resolution pr ON p.pred_id = pr.pred_id
GROUP BY p.strategy
HAVING COUNT(*) >= 5  -- minimum sample for estimates
ORDER BY hit_rate DESC
```

**Output:** `datasets/calibration/scanner_calibration_YYYYMMDD.csv` with:
- scanner_type, n_resolved, hit_rate, brier, estimated_p_hit_h1, estimated_p_hit_h0
- Flag scanners with hit_rate < baseline (currently ~10% prior) as candidates for removal

**Effort:** ~200 LOC.
**Blocked by:** Need ~50+ resolved predictions for meaningful calibration. At 1-3 new predictions/day, this takes 2-3 months. Start the pipeline now, expect first calibration by May.

### 2.2 Wire calibration back to signal_scanner.py
**What:** Instead of hardcoded `p_hit_h1=0.20, p_hit_h0=0.05` in each scanner, read from calibration CSV if available, else fall back to current defaults.

**Design:**
```python
def get_calibrated_priors(signal_type, default_h1, default_h0):
    """Read empirical priors from calibration file, fallback to defaults."""
    cal_file = ALERTS_DIR.parent / "calibration" / "scanner_calibration_latest.csv"
    if not cal_file.exists():
        return default_h1, default_h0
    # ... read and return empirical values with Bayesian shrinkage toward defaults
```

**Effort:** ~100 LOC.
**Verify:** Scanner output changes when calibration file is present.

### 2.3 Signal dropout ablation (experiment, minimal code)
**What:** Run signal scanner with each scanner disabled one at a time. Compare fused posterior quality.

**Design:** Simple loop:
```bash
for scanner in insider_activity price_extremes options_surface ...; do
    uvx --with duckdb python3 tools/signal_scanner.py --disable $scanner > /tmp/ablation_$scanner.csv
done
```
Requires adding `--disable SCANNER_NAME` flag to signal_scanner.py (~20 LOC, skip the scanner function call).

**Verify:** If disabling a scanner doesn't change any fused posteriors, it's dead weight.
**Effort:** ~20 LOC for the flag + a shell script.

### 2.4 Canary ticker null test
**What:** Run signal scanner on 20 random S&P 500 tickers that are NOT on the watchlist. If the scanner finds the same rate of "anomalies" as on watchlist tickers, your signals are noise.

**Design:**
```bash
uvx --with duckdb python3 tools/signal_scanner.py --canary --n-canary 20
```
`--canary` mode: temporarily replace WATCHLIST with N random tickers from `company_profiles`, run all scanners, report signal density.

**Effort:** ~50 LOC.
**Verify:** Canary signal density should be significantly lower than watchlist signal density. If it's comparable, you have a false discovery problem.

---

## Phase 3: Shadow Portfolio → Paper Trading Validation (Week 3-4)

**Goal:** Prove the system generates positive alpha before any real money.

### 3.1 Wire `paper_ledger.py evaluate` to auto-execute
**What:** `paper_ledger.py evaluate` already has signal→action mapping (ENTRY_SIGNALS, EXIT_SIGNALS, RESIZE). But it's manual. Wire to cron after signal scanner.

**Add to crontab:**
```
# 8. Auto-evaluate paper trades from today's signals: 8:15am ET
15 8 * * * cd /Users/alien/Projects/intel && uvx --with duckdb python3 tools/paper_ledger.py evaluate >> logs/paper_trades.log 2>&1
```

**Check first:** Run `paper_ledger.py evaluate --dry-run` to see what trades it would make. Review the signal→action mapping — are the thresholds reasonable?

**Effort:** 1 cron line + review of mapping constants.

### 3.2 Add CLV (Closing Line Value) tracking
**What:** For each prediction, track the price trajectory over the prediction window, not just the final price. Did the signal predict a price *drift* before any catalyst?

**Design:** Add to `prediction_outcomes`:
```
clv_5d_drift: price change in first 5 days after prediction
clv_pre_catalyst_max: max favorable move before any 8-K/earnings event
```

**Effort:** ~100 LOC in resolver.
**Why it matters:** Separates "the signal knew before the market" from "got lucky on earnings."

### 3.3 Weekly performance report
**What:** `paper_ledger.py report --format weekly` already exists. Add:
- Alpha vs IWM (cumulative)
- Drawdown tracking (is -15% pause triggered?)
- Per-scanner attribution (which scanner's trades are winning?)

**Effort:** ~100 LOC if not already implemented. Check existing `report` command first.

### 3.4 Constitutional circuit breakers
Verify these are wired:
- [ ] -15% drawdown → pause all new positions
- [ ] -25% drawdown → human re-authorization required
- [ ] Max 20% single position
- [ ] Max 20% sector concentration
- [ ] 20% cash floor

`paper_ledger.py` has: `STOP_LOSS_PCT = -15.0`, `MAX_POSITION_PCT = 8.0`, `MAX_SECTOR_PCT = 25.0`, `CASH_FLOOR_PCT = 20.0`. These are close but not exactly constitutional. Review and align.

---

## Phase 4: Multiple Testing Control + Hardening (Week 4-5)

### 4.1 FDR gating
**What:** Apply Benjamini-Hochberg correction to signal alerts. Only allow top-K predictions per week based on false discovery rate control.

**Design:**
```python
def fdr_gate(predictions, alpha=0.10):
    """Filter predictions by Benjamini-Hochberg FDR control.

    Sort by p-value (1 - posterior_prob). Reject H0 for predictions
    where p_i <= (i/m) * alpha. Controls expected false discovery rate.
    """
```

**Effort:** ~150 LOC.
**Where to wire:** In `emit_predictions.py` before writing to prediction table.

### 4.2 Entity mapping audit
**What:** FAERS NDC→drug→ticker mapping (`build_ndc_drug_map.py`) has no confidence scores or manual overrides. A wrong mapping → confidently wrong signal.

**Action:**
- Add `confidence` column to `faers_drug_ticker_map` (exact name match = 1.0, fuzzy = 0.5, manual = 0.9)
- Add `manual_override` table for corrected mappings
- Log mapping audit trail

**Effort:** ~200 LOC.
**Priority:** Medium. Only matters once FAERS scanner is calibrated.

### 4.3 PIT provenance
**What:** Add `fetched_ts` column to download scripts. Currently downloads don't record when data was fetched — PIT safety relies on file modification timestamps.

**Action:** For each `download_*.py`, append a `_metadata.json` sidecar with `{"fetched_ts": "...", "source_url": "...", "rows": N}`.

**Effort:** ~50 LOC template + propagation across ~20 actively used downloaders.
**Priority:** Low for predictions (forward-only), high for backtesting (historical).

---

## Phase 5: Backtesting at Scale (Month 2)

### 5.1 Systematic scanner backtest
**What:** Run all 28 scanners against 2022-2024 historical data using the existing backtest.py framework. Score each scanner independently.

**Blocked by:** Phase 2 calibration infrastructure (need scoring framework). Also need clean PIT provenance for historical data.

**Design:**
- Create monthly backtest scenarios: 2022-01 through 2024-12 (36 scenarios)
- For each, run signal_scanner with cutoff-filtered data
- Score predictions against actual returns
- Output: per-scanner hit rate, Brier score, alpha by time period

**Effort:** ~300 LOC (batch scenario creator + scorer).
**Risk (critical):** Look-ahead bias. The `backtest.py` framework has contamination tracking — USE IT. Both models flagged this as existential risk.

### 5.2 Kill underperforming scanners
Based on Phase 2 calibration + Phase 5.1 backtest:
- Scanners with hit rate < baseline AND Brier > 0.25: REMOVE
- Scanners with N < 10 resolved: KEEP but flag as unvalidated
- Target: reduce from 28 to 10-15 validated scanners

---

## Sequencing Summary

```
Week 1 (ACTIVATE):
  Day 1: Run prediction_tables.py --migrate
  Day 1: Write emit_predictions.py (~150 LOC)
  Day 2: Test resolve pipeline manually
  Day 2: Install crontab (7 jobs)
  Day 3: Verify pipeline ran overnight. Check logs.
  → Deliverable: loop running, auto-predictions firing

Week 2-3 (LEARN):
  Write calibrate_scanners.py (~200 LOC)
  Add --disable flag to scanner (~20 LOC)
  Run dropout ablation experiment
  Run canary ticker null test (~50 LOC)
  → Deliverable: know which scanners produce signal vs noise

Week 3-4 (VALIDATE):
  Wire paper_ledger evaluate to cron
  Add CLV tracking (~100 LOC)
  Align constitutional circuit breakers
  → Deliverable: paper portfolio running, tracked vs IWM

Week 4-5 (HARDEN):
  FDR gating (~150 LOC)
  Entity mapping audit (~200 LOC)
  PIT provenance for downloaders
  → Deliverable: false discovery rate controlled, mappings auditable

Month 2 (BACKTEST):
  Batch scenario creator
  Run 36-month backtest
  Kill underperformers
  → Deliverable: validated scanner ensemble, empirical LLR priors
```

## Total New Code Estimate

| Component | LOC | Priority |
|-----------|-----|----------|
| emit_predictions.py | 150 | P1 (Week 1) |
| crontab setup | 20 | P1 (Week 1) |
| calibrate_scanners.py | 200 | P2 (Week 2) |
| --disable flag | 20 | P2 (Week 2) |
| --canary flag | 50 | P2 (Week 2) |
| Calibration→scanner wiring | 100 | P2 (Week 3) |
| CLV tracking | 100 | P3 (Week 3) |
| FDR gating | 150 | P4 (Week 4) |
| Entity mapping audit | 200 | P4 (Week 4) |
| Batch backtest creator | 300 | P5 (Month 2) |
| **Total** | **~1,290** | |

Compare: Wave 2-7 was 976 LOC for new scanners. This plan is ~1,290 LOC to make ALL 28 scanners actually useful.

## What NOT to Build

- ~~More signal scanners~~ — freeze signal breadth until calibration proves which ones work
- ~~IB API integration~~ — blocked by paper trading validation (this plan)
- ~~Orchestrator on cron~~ — wire the simpler pipeline first. Orchestrator is for entity refresh, not the prediction loop
- ~~Internal prediction market (Gemini idea)~~ — over-engineered for one person
- ~~Replace scoring.py with tally (Gemini idea)~~ — the math framework is correct, the inputs need calibration, not replacement
- ~~Regime tags~~ — second-order optimization. Requires prediction data first
- ~~Outcome taxonomy beyond price~~ — price resolution is sufficient for calibration MVP

## Success Criteria

| Metric | Current | Target (3 months) |
|--------|---------|-------------------|
| Predictions in ledger | 24 | 200+ |
| Resolved predictions | 3 | 50+ |
| Per-scanner calibration | 0 scanners calibrated | 10+ scanners with N≥10 |
| Paper portfolio days tracked | 2 | 60+ |
| Paper alpha vs IWM | unknown | measured (any value is fine, signal > noise) |
| Cron pipeline uptime | 0% | >95% |
| Scanners with empirical priors | 0/28 | 10+/28 |
| FDR-controlled predictions | 0% | 100% |

<!-- knowledge-index
generated: 2026-03-22T00:15:43Z
hash: 388512ccf036

title: Action Plan: Close the Error-Correction Loop

end-knowledge-index -->
