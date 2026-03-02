# CONTEXT: Cross-Model Review — Evo Infrastructure Patterns → Intel Transfer

## PROJECT CONSTITUTION (Meta)
Review against these principles, not your own priors.

### Generative Principle
> Maximize the rate at which agents become more autonomous, measured by declining supervision.

### Key Constitutional Principles
1. Architecture over instructions. Instructions alone = 0% reliable. If it matters, enforce with hooks/tests/scaffolding.
2. Measure before enforcing. Log every hook trigger to measure false positives.
3. Self-modification by reversibility + blast radius.
4. Research is first-class. Divergent → convergent → eat your own dogfood.
5. Recurring patterns become architecture. If used/encountered 10+ times → hook, skill, or scaffolding.
6. Cross-model review for non-trivial decisions.

## PROJECT GOALS (Meta)
- Mission: Maximize autonomous agent capability across all projects while maintaining epistemic integrity
- Primary metric: Ratio of autonomous-to-supervised work across sub-projects
- Strategy: Session forensics → hook engineering → observability → research → cross-project propagation

## INTEL CONSTITUTION
> Maximize the rate at which the system corrects its own errors about the world, measured by market feedback.

Key principles: adversarial stance, source grading (Admiralty), quantify before narrating, fast feedback over slow, the join is the moat, falsify before recommending, fractional Kelly sizing.

## INTEL GOALS
- Primary: asymmetric alpha from public data, $500M-$5B small/mid-cap
- 5 alpha strategies: FDA FAERS, CFPB complaints, government contracts, governance signals, insider filings
- Success metrics: alpha vs IWM, Sortino >1.5, calibration curves

---

## WHAT'S BEING REVIEWED

Claude (Opus 4.6) analyzed the evo project and proposed infrastructure transfers to intel. The analysis identified 10 patterns from evo and ranked them by leverage. Review the analysis for:
- Missed opportunities (patterns in evo that weren't identified)
- Wrong priorities (recommendations that don't match intel's actual bottlenecks)
- Scale mismatch (evo patterns that don't translate to intel's domain)
- Constitutional alignment (do recommendations serve intel's error-correction principle?)

## THE ANALYSIS BEING REVIEWED

### High Leverage — Direct Transfers

#### 1. Task Runner with Discoverable Commands
Evo has `bb.edn` with 40+ organized commands. Intel has 152 scripts in `tools/` invoked ad-hoc.
Proposal: A `bb.edn` or `Makefile` or `tasks.py` for intel cataloging common operations.

#### 2. Architecture Analysis Scripts
Evo has `arch:summary`, `arch:complexity`, `arch:call-graph`, `arch:data-flow`, and `arch:lens`.
Intel has zero introspection tooling for its 152 scripts + 295 views.
Proposal: A `tools/arch/` suite mapping script dependencies, view dependencies, dead code, complexity hotspots.

#### 3. Spec-as-Database Pattern
Evo's `resources/specs.edn` — 44 FRs as structured data with executable scenarios.
Proposal: `resources/dataset_specs.edn` defining schema, freshness, row count bounds, entity graph constraints. `bb validate` runs specs against live DB.

#### 4. Failure Modes as Structured Data
Evo has `resources/failure_modes.edn`. Intel has lessons scattered across CLAUDE.md `<gotchas>`, `memory/analytical_reasoning.md`, `docs/download_agent_lessons.md`.
Proposal: Consolidate into one structured, queryable file.

### Medium Leverage — Architectural Ideas

#### 5. Multi-Tier Testing with Speed Expectations
Evo: unit (<1s), integration (<5s), property (<10s), E2E smoke (5s), E2E full (5min).
Intel: `tools/tests/` exists but no tier structure or smoke test.
Proposal: `bb test:quick` (view syntax, <10s), `bb test:integrity` (entity graph, <60s), `bb test:backtest` (regression, minutes).

#### 6. Event Sourcing / Append-Only Ledger
Evo: immutable operation log with replay. Intel: entity graph has no changelog.
Proposal: `data_events.jsonl` recording every data change. Already partially in progress (recent "data infra tier 3" commits).

#### 7. Dry-Run / Simulation for Pipelines
Evo: `transaction/dry-run` simulates without committing.
Proposal: `setup_duckdb.py --diff`, `build_entity_tables.py --preview`.

### Lower Leverage

#### 8. Documentation Landing Page (DX_INDEX.md equivalent)
#### 9. Three-Primitive Kernel (constrained operations)
#### 10. REPL-First Development (iPython with DuckDB loaded)

---

## EVO PROJECT — Full Architecture (for pattern mining)

### Tech Stack
- ClojureScript, shadow-cljs, Replicant UI framework, Babashka task runner
- Event sourcing: all state changes as immutable EDN operations
- Three primitives: create-node, place, update-node
- Transaction pipeline: Normalize → Validate → Apply → Derive Indexes
- Intent → Operations → DB pattern (components dispatch intents, plugins calculate ops)
- Script pattern for multi-step operations (step N depends on step N-1)
- Spec-as-Database: 44 FRs in specs.edn with executable scenarios
- Failure modes as structured data (failure_modes.edn)
- Multi-tier testing: unit, view, integration, property-based, spec scenarios, E2E
- Architecture analysis scripts: namespace overview, complexity, call-graph, data-flow, combined lens
- Pre-commit hooks validate syntax, prevent shadowed vars, check FR citations
- REPL-first development workflow

### Babashka Tasks (bb.edn) — 40+ commands organized by category:
- Quality gates: lint, check, format:check, format:fix
- Tests: test, test:view, test:int, test:specs, test-watch variants
- FR coverage: fr-audit, fr-matrix, lint:fr-tests, lint:specs, lint:intents
- Architecture: arch:summary, arch:complexity, arch:abstractions, arch:data-flow, arch:call-graph, arch:lens
- E2E: e2e, e2e:watch, e2e:debug, e2e:headed, test:e2e, e2e:report
- Cache/index: clean, index
- REPL: repl-health
- Agent: context:file, scaffold:view-test

### Key Design Decisions
- No block references (explicit duplication > hidden coupling)
- Simple plugin system (functions, not framework)
- Separate session atom from persistent DB
- Protocols only at edges
- No async in core

## INTEL PROJECT — Current Infrastructure

### Data Layer
- 525 GB across ~610 datasets, 295 DuckDB views + 18 materialized tables
- Intelligence MCP: entity resolution, search, dossier, connections, anomaly flagging
- 739K entities, 1.35M crosswalk entries, 275K edges, FTS index
- Pre-exported graph CSVs: 24M edges

### Scripts & Tooling (152 .py files in tools/)
- Build/setup: setup_duckdb.py, build_entity_tables.py, build_issuer_xwalk.py
- Analysis: brooklyn_detrend.py, benford_check.py, cfpb_velocity.py, cluster_graph.py
- Backtesting: backtest.py (109K!), governance_backtest.py, leie_backtest.py
- Download: cms_data_download.py and 40+ domain-specific downloaders
- Intelligence: intelligence_mcp.py, unified_lookup.py (630 lines)
- Testing: tools/tests/ (conftest.py, test_*.py), tools/evals/

### Hooks
- Data protection (blocks writes to datasets/, .parquet, intel.duckdb)
- Secrets guard, bash rm guard, backtest guard
- Source-check on research files, stop-research-gate
- Large file read advisory

### Skills
- competing-hypotheses, thesis-check (432 lines), multi-model-review
- dataset-discoverer, entity-refresher, investment-reviewer, sql-reviewer agents

### Memory
- analytical_reasoning.md (11K), mechanisms.md (36K), priors.md (17K)
- entity_graph_schema.md, sf_data_sources.md, tooling.md

### Documentation
- DATA_INVENTORY.md, TOOLS_REFERENCE.md, ANALYSIS_INDEX.md, VIEWS_CATALOG.md
- 10 domain rules in .claude/rules/
