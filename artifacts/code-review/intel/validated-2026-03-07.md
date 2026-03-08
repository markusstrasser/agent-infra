# Intel Code Review Validation — 2026-03-07

## Scout: Gemini CLI (free, 43 batches, optimization focus)
## Validator: Claude Opus 4.6

### Validation Rate
- 19 HIGH findings checked
- 8 CONFIRMED (42%), 9 PARTIAL (47%), 2 FALSE POSITIVE (11%)
- **89% identified real issues** — line numbers unreliable (off by 30-110 lines)

### Confirmed & Actionable

1. **sf_entity_resolution.py** — 4× O(N×M) nested loops. Fix: pre-build `{name.upper(): data}` dict.
2. **download_usaspending.py** — O(N²) checkpoint writes. Fix: append-only CSV or write only new records.
3. **build_entity_file.py** — Correlated subquery on 227M-row parquet. Code already has try/except fallback.
4. **export_views_catalog.py** — 2× N+1 (columns + comments per view). Fix: single grouped query.
5. **expand_universe.py** — 2× N+1 per-ticker momentum/volatility. Fix: single GROUP BY query.
6. **discovery_scan.py** — Redundant view checks + N+1 COUNT per ticker×source. Fix: cache views, batch counts.
7. **benford_check.py** — N+1 over 5000 providers. Fix: batch data fetch, analyze in Python.
8. **download_h1b_lca.py** — CSV parsed twice across two COPY statements. Fix: materialize to temp table.

### Partial (real issue, wrong line numbers)
- emit_predictions.py — DuckDB connection churn per signal (lines off by ~80-110)
- divergence_score.py — per-ticker CSV re-reads (lines off by ~100)
- source_eval.py — repeated CSV reads (overstated severity)
- compute_negative_baselines.py:74 — LIKE fuzzy join is deliberate design tradeoff
- download_sec_metadata.py — re-downloads JSON per cache miss (only on cold cache)

### False Positives
- compute_negative_baselines.py:118 — line 118 is an exact equality join, not LIKE
- emit_predictions.py:282/333 — line numbers fabricated (actual issues at different locations)

### Meta-Pattern
Gemini identifies correct algorithmic patterns but fabricates line numbers. The scout→validate
pipeline is essential: Gemini finds candidates cheaply, Claude verifies against actual code.
