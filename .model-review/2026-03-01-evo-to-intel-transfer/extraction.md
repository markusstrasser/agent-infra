# Extraction & Disposition — Evo→Intel Transfer Review

## Extraction: gemini-output.md

G1. [Architecture analysis should target DuckDB view DAG, not Python call graphs — complexity lives in SQL layer]
G2. [Event sourcing is anti-pattern for 525GB bulk data — need pipeline versioning and data-diffing instead]
G3. [Task runner should be machine-readable registry (JSON + MCP-exposed), not static Makefile]
G4. [Missed: crosswalk integrity enforcement via specs — "the join is the moat" not addressed by original analysis]
G5. [Missed: Admiralty grading should be structured config, not narrative memory — pipelines can query it]
G6. [Missed: Falsification scaffolding — structured pipeline for injecting null models/randomized data into backtests]
G7. [Missed: Expose task registry through MCP for autonomous agent chaining]
G8. [Upgrade task runner: tools/registry.json → MCP-exposed for agent autonomy]
G9. [Alternative arch analysis: duckdb_dependencies() for view DAG, orphaned views, bottlenecks]
G10. [Agree spec-as-db with refinement: must include freshness SLA + Admiralty grade]
G11. [Agree failure modes: tie into thesis-check skill for automatic querying]
G12. [Upgrade testing: fast (<1s) view SQL dry-run, medium (<10s) entity graph checks, slow (min) backtest regression]
G13. [Disagree event sourcing: use Data Contract Verification (like dbt tests) instead]
G14. [Agree dry-run: DDL diff output prevents blast radius]
G15. [Priority 1: DuckDB view lineage + integrity DAG with pre-commit hook]
G16. [Priority 2: Structured failure modes → thesis-checker pipeline]
G17. [Priority 3: Data quality specs with freshness/Admiralty enforcement]
G18. [Priority 4: Machine-readable task registry via MCP]
G19. [Priority 5: Multi-tier fast-feedback hooks (pre-commit view compilation)]
G20. [Violation: Meta "measure before enforcing" — speed tiers proposed without profiling current runtimes]
G21. [Violation: Intel "join is the moat" — analysis skewed toward generic software engineering]
G22. [Well-served: Meta "recurring patterns become architecture" — failure modes extraction]
G23. [Well-served: Intel "quantify before narrating" — dataset_specs forces quantification]
G24. [Blind spot: DuckDB dependency tracking may not handle complex CTEs/cross-file macros]
G25. [Blind spot: MCP-exposed registry may consume too much context — simple Makefile + LLM pretraining might work better]
G26. [Blind spot: If bottleneck is agent code read/write, code-level arch analysis matters more than I credited]

## Extraction: gpt-output.md

P1. [Event sourcing ledger needs storage/retention plan at 525GB scale — can slow feedback (Principle 5)]
P2. [Architecture analysis assumes static dependencies — dynamic SQL may invalidate static DAG]
P3. [Spec-as-database catches schema errors but intel's main risk is semantic (leakage, survivorship, incorrect joins)]
P4. [Dry-run conflicts with "fast feedback" unless it prevents expensive rollbacks at higher rate than added latency]
P5. [Three-primitive kernel is category error from UI to research pipelines — bypass risk high]
P6. [Task runner ≠ reproducibility without environment pinning and data snapshot identifiers]
P7. [Failure-modes-as-data needs feedback ingestion mechanism or becomes documentation in disguise]
P8. [Multi-tier testing incomplete without enforceable speed budgets + merge gates]
P9. [ROI ranking: task runner > testing > failure modes > arch analysis > spec-as-db > dry-run > REPL > ledger > docs > kernel]
P10. [YAGNI: three-primitive kernel, landing page, broad event sourcing ledger]
P11. [Testable prediction: task runner — ≥70% recurring ops via runner, ≥30% operator time drop in 4 weeks]
P12. [Testable prediction: arch analysis — identifies ≥15% dead scripts/views, top hotspots ≥50% of incidents]
P13. [Testable prediction: spec-as-db — ≥40% reduction in schema/constraint failures, ≥25% fewer silent join drops]
P14. [Testable prediction: failure modes — ≥30 gotchas normalized, recurrence ≤1/month for top 10]
P15. [Testable prediction: testing tiers — smoke <3 min, regressions down ≥25%, MTTR down ≥20%]
P16. [Testable prediction: event ledger (scoped) — ≥90% entity changes diffable, "what changed?" from days to <30 min]
P17. [Testable prediction: dry-run — catches ≥60% breaking changes pre-write, rollbacks down ≥30%]
P18. [Constitutional coverage: Autonomous Decision Test 55%, Skeptical but Fair 30%, Every Claim Sourced 35%]
P19. [Constitutional coverage: Quantify Before Narrating 40%, Fast Feedback 70%, Join Is Moat 60%]
P20. [Constitutional coverage: Honest Provenance 50%, Use Every Signal 25%, Portfolio Is Scorecard 20%]
P21. [Constitutional coverage: Compound Don't Start Over 45%, Falsify Before Recommending 30%, Fractional Kelly 15%]
P22. [GPT top rec 1: Join-quality SLOs — cardinality/leakage monitors on canonical joins, ≥30-50% silent error reduction]
P23. [GPT top rec 2: Backtest reproducibility harness — golden runs with checksums, ≥25% regression debugging reduction]
P24. [GPT top rec 3: ER evaluation bench — labeled benchmark set, precision/recall/F1, canary entities]
P25. [GPT top rec 4: Provenance enforcement at output layer — strict schema for signals/claims, ≥60-80% reduction in unsourceable claims]
P26. [GPT top rec 5: Operational telemetry — DORA-style metrics (MTTD/MTTR), structured logs, ≥25% MTTR reduction]
P27. [Effort estimates: task runner 40-90h, arch analysis 80-200h, spec-as-db 120-300h, testing 120-260h]
P28. [Blind spot: may underestimate task runner leverage if operational friction is extreme]
P29. [Blind spot: may over-index on silent data corruption — actual bottleneck might be infra (disk, networking)]
P30. [Blind spot: event sourcing ROI sensitive to update frequency — no evidence on actual churn rate]

## Fact-Check Results

FC1. **backtest.py is 3,037 lines, NOT 109K.** My original analysis said "109K" — that was the file size in bytes, not lines. Both models accepted this uncritically. GPT used it to justify "high regression surface." The point stands but the number was misleading.

FC2. **Intel already has `tools/lib/admiralty.py`** — structured Python dict with per-dataset, per-column, and per-inference grades. Gemini's claim (G5) that Admiralty grading is "in narrative memory" is WRONG. It's already code.

FC3. **Intel already has `tools/evals/smoke_queries.py`** — a proto-test tier with `--quick` and `--domain` flags. The claim that intel has "no smoke test" is partially wrong. It exists but isn't CI-gated or formalized into tiers.

FC4. **Intel has 24 test files** in `tools/tests/` covering address, alt data, CFPB velocity, congressional, cross-signal, data health, FAERS, filings, fraud, insider, macro, options, prediction, price, regulatory, etc. The claim "no tier structure" is correct but "minimal testing" undersells it.

FC5. **`duckdb_dependencies()` function** — Gemini (G9) suggests using this. Grep found zero references in intel codebase. Need to verify this is actually a DuckDB function. It likely is (`duckdb_dependencies()` is a system table in DuckDB), but it may not track view-to-view dependencies through complex SQL.

FC6. **`setup_duckdb.py --dry-run` already exists** — 4300+ line file with dry-run support. My original proposal and Gemini's agreement are redundant for this specific script. The gap is extending dry-run to OTHER scripts (build_entity_tables.py, etc.).

---

## Disposition Table

| ID | Claim (short) | Disposition | Reason |
|----|--------------|-------------|--------|
| G1 | View DAG > Python call graphs | INCLUDE — Tier 1 | Both models agree; verified that SQL layer is where complexity lives |
| G2 | Event sourcing anti-pattern for bulk | INCLUDE — advisory | Both models flag; scoping is key |
| G3 | Machine-readable task registry | INCLUDE — Tier 2 | Upgrades my task runner proposal; agent autonomy alignment |
| G4 | Crosswalk integrity specs | INCLUDE — Tier 1 | Directly serves "join is the moat" |
| G5 | Admiralty as structured config | REJECT | Already exists as `tools/lib/admiralty.py` — Gemini didn't know |
| G6 | Falsification scaffolding for backtests | INCLUDE — Tier 3 | Novel; serves Principle 11; not in my analysis |
| G7 | MCP-exposed task registry | MERGE WITH G3 | Same idea |
| G8 | registry.json → MCP | MERGE WITH G3 | Same idea |
| G9 | duckdb_dependencies() for view DAG | INCLUDE — Tier 1 | Specific implementation path for G1; needs verification |
| G10 | Specs need freshness SLA + grade | INCLUDE — refinement | Enhances spec-as-db |
| G11 | Failure modes → thesis-check integration | INCLUDE — Tier 2 | Novel wiring; high leverage |
| G12 | Testing tier upgrade (fast/medium/slow) | INCLUDE — Tier 2 | Refines my proposal; acknowledges smoke_queries.py exists |
| G13 | Data contract verification > event sourcing | INCLUDE — replaces #6 | Better fit for bulk data |
| G14 | DDL diff for dry-run | DEFER | setup_duckdb.py already has --dry-run; extend to others later |
| G15-G19 | Gemini priorities | INCLUDE — as synthesis input | |
| G20 | Measure before enforcing violation | INCLUDE — advisory | Valid critique of my analysis |
| G21 | Join-is-the-moat neglected | INCLUDE — advisory | Valid; my analysis was too generic |
| G22-G23 | Well-served principles | INCLUDE — for record | |
| G24 | DuckDB dependency tracking limits | INCLUDE — risk flag | Real concern |
| G25 | MCP context consumption risk | INCLUDE — risk flag | Real concern |
| G26 | Code-level arch may matter more | DEFER | Depends on actual bottleneck data |
| P1 | Ledger needs retention plan | MERGE WITH G2 | Same concern |
| P2 | Dynamic SQL invalidates static DAG | INCLUDE — risk flag | MERGE WITH G24 |
| P3 | Semantic errors > schema errors | INCLUDE — Tier 1 | Key insight: leakage/survivorship/join semantics |
| P4 | Dry-run latency tradeoff | INCLUDE — advisory | Valid only if dry-run is mandatory |
| P5 | Three-primitive kernel is category error | INCLUDE — confirms reject | Confirms lower-leverage assessment |
| P6 | Task runner needs env pinning | INCLUDE — refinement | Enhances task runner proposal |
| P7 | Failure modes needs ingestion mechanism | INCLUDE — Tier 2 | Without it, it's documentation |
| P8 | Testing needs speed budgets + gates | INCLUDE — refinement | Enhances testing proposal |
| P9 | GPT ROI ranking | INCLUDE — for synthesis | |
| P10 | YAGNI: kernel, landing page, broad ledger | INCLUDE — confirms | Validates my lower-leverage calls |
| P11-P17 | Testable predictions | INCLUDE — all | Valuable falsifiable criteria |
| P18-P21 | Constitutional coverage scores | INCLUDE — for synthesis | Shows gaps in my analysis |
| P22 | Join-quality SLOs + cardinality monitors | INCLUDE — Tier 1 | Novel; directly serves "join is the moat" |
| P23 | Backtest reproducibility harness | INCLUDE — Tier 1 | Novel; high ROI given backtest importance |
| P24 | ER evaluation bench | INCLUDE — Tier 2 | Novel; entity resolution quality is foundational |
| P25 | Provenance enforcement at output | INCLUDE — Tier 2 | Novel; makes Principle 3/7 executable |
| P26 | Operational telemetry (DORA metrics) | INCLUDE — Tier 3 | Novel; "measure before enforcing" |
| P27 | Effort estimates | INCLUDE — for reference | Calibration data |
| P28-P30 | GPT blind spots | INCLUDE — risk flags | |

## Coverage Check

- Total extracted: 56 (G1-G26 = 26, P1-P30 = 30)
- Included: 39
- Deferred: 3 (G14, G26, P4 partial)
- Rejected: 1 (G5 — already exists)
- Merged: 4 (G7→G3, G8→G3, P1→G2, P2→G24)
- Confirmed/validated: 9 (P5, P10, G22-G23, etc.)
