# Cross-Model Review: Evo → Intel Infrastructure Transfer

**Mode:** Review
**Date:** 2026-03-01
**Models:** Gemini 3.1 Pro, GPT-5.2
**Constitutional anchoring:** Yes (Meta CLAUDE.md constitution, Intel constitution, Meta GOALS.md)
**Extraction:** 56 items extracted, 39 included, 3 deferred, 1 rejected, 4 merged

---

## Where I (Claude) Was Wrong

| My Original Claim | Reality | Who Caught It |
|-------------------|---------|--------------|
| "Intel has zero introspection tooling" | Intel has `tools/evals/smoke_queries.py` with `--quick` and `--domain` flags | Fact-check |
| "Lessons scattered in narrative memory only" for Admiralty | `tools/lib/admiralty.py` already exists as structured Python — per-dataset, per-column, per-inference grades | Fact-check (G5 rejected) |
| "backtest.py at 109K" (implied LOC) | 109K bytes = 3,037 lines. Both models accepted uncritically. | Fact-check (FC1) |
| Architecture analysis should map Python scripts | Complexity lives in SQL layer (295 views, 610 datasets), not Python call graphs (G1, both models) | Gemini + GPT |
| Event sourcing ledger as medium-leverage transfer | Anti-pattern for 525GB bulk ingestion; data contract verification is the right analog (G2, G13, P1) | Both models |
| Analysis was "too generic software engineering" | Neglected intel-specific value: entity resolution quality, join integrity, backtest reproducibility (G21, P18-P21) | Both models |

## Gemini Errors (distrust)

| Claim | Why Wrong |
|-------|-----------|
| G5: "Admiralty grading is in narrative memory" | Already structured code in `tools/lib/admiralty.py` |
| G9: `duckdb_dependencies()` as easy DAG source | Function exists but may not track through complex CTEs/macros — Gemini flagged this itself (G24) |
| Temperature override note: Gemini's `-t 0.3` was ignored (locked at 1.0 for thinking model) | Output quality unaffected |

## GPT Errors (distrust)

| Claim | Why Wrong |
|-------|-----------|
| Accepted "109K" backtest.py without questioning | File is 3,037 lines (109K bytes). Should have asked for clarification. |
| P27: Effort estimates (40-90h for task runner, 120-300h for specs) | Likely inflated for a solo-dev + agent workflow. Task runner is ~4-8h, not 40-90h. Specs depends on scope. |
| P18-P21: Constitutional coverage percentages | Precise numbers with no measurement methodology — confident fabrication pattern. Directional assessment is useful, absolute scores are not. |

---

## Revised Priority List (Post-Review)

### Tier 1: High leverage, directly serves intel's error-correction mission

**1. DuckDB View Lineage DAG** (G1, G9, G15)
- Build `tools/arch/view_lineage.py` using DuckDB's `duckdb_dependencies()` or SQL parsing
- Output: `views_dag.json` + visualization
- Gate: pre-commit hook rejects view changes that break downstream
- Risk: dynamic SQL may defeat static analysis (G24, P2). Start with what `duckdb_dependencies()` gives, supplement with grep-based parsing.
- Verification: identifies ≥15% orphaned views; top 5 hotspots cover ≥50% of incident touchpoints (P12)

**2. Join-Quality SLOs** (P22, G4, P3)
- Cardinality monitors on canonical joins: null-rate, duplication, pre/post row counts, many-to-many detection
- Time leakage checks for backtests (feature timestamp must precede label timestamp)
- This is the "spec-as-database" pattern applied to where intel's actual risk lives: *semantic join correctness*, not schema types
- Verification: ≥30% reduction in silent data errors caught late (P22)

**3. Backtest Reproducibility Harness** (P23)
- Golden runs: frozen datasets + parameter sets, checksum outputs
- Regression detection on every material change to backtest infrastructure
- Verification: "backtest changed unexpectedly" incidents down ≥40% over 2 months

### Tier 2: High leverage, infrastructure improvement

**4. Task Registry** (G3, G8, P6, P11)
- Start with a simple `tasks.toml` or `Makefile` mapping the top 30 scripts by usage
- Include: script, required deps, expected inputs/outputs, DuckDB tables touched
- Later: expose via MCP for agent autonomy (G7) — but validate simple version first (G25)
- Add env pinning (P6): Python deps via `uv`, DuckDB version
- Verification: ≥70% recurring ops via runner within 4 weeks (P11)

**5. Structured Failure Modes → Thesis-Check Integration** (G11, G16, P7, P14)
- Consolidate `memory/analytical_reasoning.md`, `docs/download_agent_lessons.md`, CLAUDE.md `<gotchas>` into `resources/failure_modes.json`
- Wire into `thesis-check` skill: agent queries failure DB before generating hypothesis
- CRITICAL: must have ingestion mechanism (P7) — each incident produces an entry, or it becomes stale docs
- Verification: top 10 failure modes have linked tests; recurrence ≤1/month (P14)

**6. Multi-Tier Testing with Gates** (G12, G19, P8, P15)
- Acknowledge: `tools/evals/smoke_queries.py` and 24 test files already exist
- Formalize: `bb test:smoke` (<30s, view compilation + basic smoke queries), `bb test:integrity` (<2min, entity graph checks, join cardinality), `bb test:backtest` (minutes, golden run regression)
- Enforce: smoke tier runs on every commit; integrity on every data rebuild
- Verification: regressions down ≥25%, MTTR down ≥20% (P15)

### Tier 3: Medium leverage, worth doing when Tier 1-2 are stable

**7. ER Evaluation Bench** (P24)
- Labeled benchmark set for entity resolution precision/recall/F1
- Canary entities with known ground truth
- Weekly tracking
- Verification: ER F1 tracked; "wrong entity" incidents down ≥30%

**8. Provenance Enforcement at Output** (P25)
- Strict schema for signals/claims: value, entity_id, asof_ts, provenance label, source_uri, NATO grade, pipeline_run_id
- Reject outputs missing fields
- Verification: ≥95% outputs pass provenance gate; supervision waste from 21% → ≤15%

**9. Falsification Scaffolding** (G6)
- Standard API to inject null models/randomized data into backtests
- Pre-trade falsification checklist
- Serves Principle 11 directly

**10. Operational Telemetry** (P26, G20)
- Structured logs: job_id, inputs, outputs, runtime, row counts, failure class
- DORA-style dashboards: MTTD, MTTR, change-failure rate
- Serves Meta "measure before enforcing" — need baseline data before adding more gates
- Verification: MTTR down ≥25%, ≥80% failures auto-classified

### Deferred / Rejected

| Item | Status | Reason |
|------|--------|--------|
| Event sourcing ledger (broad) | DEFER | Anti-pattern for bulk data (G2, G13, P1). If scoped to entity mutations only, reconsider as part of #7 ER Bench |
| Three-primitive kernel | REJECT | Category error from UI to research (P5). Intel's operations are too heterogeneous. |
| Documentation landing page | DEFER | Low leverage (P10). CLAUDE.md `<reference>` section partially serves this role |
| Dry-run extension beyond setup_duckdb.py | DEFER | setup_duckdb.py already has --dry-run. Extend to build_entity_tables.py when warranted |
| Code-level arch analysis (Python call graphs) | DEFER | Low leverage vs. view DAG. Reconsider if agent code navigation proves to be the bottleneck (G26) |

---

## Constitutional Gaps Identified

The strongest critique from both models: my original analysis was **generic software engineering** that neglected intel's domain-specific constitutional principles. The revised priority list addresses:

- **"The Join Is the Moat"** → #2 Join-Quality SLOs, #7 ER Bench (was barely touched in original)
- **"Falsify Before Recommending"** → #9 Falsification Scaffolding, #3 Backtest Reproducibility (absent from original)
- **"Portfolio Is the Scorecard"** → Still underserved. None of the proposals directly integrate portfolio performance as an integration test. (P20: 20% coverage)
- **"Size by Fractional Kelly"** → Still underserved. No sizing engine integration. (P21: 15% coverage)
- **"Fast Feedback"** → Well-served by task runner + testing tiers + dry-run

The two lowest-scored principles (Portfolio as Scorecard, Fractional Kelly) require *application-level* work, not infrastructure patterns. They're out of scope for an infra transfer analysis.

---

## Key Takeaway

The original evo→intel analysis was useful as a starting point but treated intel as a generic codebase. The cross-model review correctly identified that intel's highest-leverage improvements are **domain-specific**: join integrity, backtest reproducibility, entity resolution quality. The evo patterns (specs-as-data, testing tiers, task runner) are valid *mechanisms* but must be applied to intel's actual error surfaces — which are semantic and data-level, not code-level.
