# Intel — Pattern Extraction (2026-05-11)

Source: `/Users/alien/Projects/intel` at HEAD `0ea2f5e`. Investigation budget: ~50% of turns; stopped after `spinning-detector` blocked further exploration.

## What Intel Does (and maturity level)

**Mature, not a sketch.** Intel is an "adversarial intelligence service" for public-market investing, built around a 2.0 GB DuckDB warehouse (`intel.duckdb`: 658 tables, 672 views) joined across ~610 datasets covering CMS Medicaid, NPPES, LEIE, SEC EDGAR (10-K/10-Q/8-K/Form 4/13D-G), FAERS, ClinicalTrials.gov, FDA Orange Book / 483 inspections, OSHA, EPA ECHO, BLS, USAspending, OpenSanctions, UK Companies House, FINRA SI, IRS 990s, lobbying disclosures, EIA generators, and X/social media. Constitution sits inline in `CLAUDE.md` ("error correction per market feedback"). 397 scripts in `tools/`, 343 entity files in `analysis/entities/`, 21 themes in `analysis/themes/`, predicate-graph DB (`intel/indexed/theses.duckdb`) with its own MCP server (`intel-theses`). Git log shows daily-cadence commits over many months; conviction templates, hook-gauntlet sections, FSM entry gates — operational discipline well beyond prototype.

Maturity verdict: **the most architecturally complete of the three repos**. It has its own MCP servers (`intel-theses`, plus shared `duckdb`, `fmp`, `exa`, `research`, `parallel`, `agent-infra`, `context7`), a tested rebuild pipeline (`tools/rebuild_all.sh`), and a self-imposed "constitution + governance" layer that constrains the agent.

## Domain Entities

The unit-of-analysis is the **tradeable security**, expressed as a markdown file at `analysis/entities/{TICKER}.md` (e.g. `ARWR.md`, `NTLA.md`, `BEAM.md`, `2337.TW.md`, `BANB.SW.md`). 343 entity files; 270 are US tickers, rest are TW/JP/KR/HK/EU/UK listings. Frontmatter is canonical (`ticker`, `sector`, `ai_relationship.{tag,mechanism,falsifier}`, `conviction`, `trade_stance`, `sizing_pct`, `last_reviewed`); markdown body holds the thesis, falsifiers, evidence with `[A1]`-`[F6]` NATO Admiralty source grades and `[DATA]` for own-DuckDB analysis.

Secondary entities: **themes** (`analysis/themes/*.md` — bottleneck-level investment narratives like `genetic_medicine_modality_stack`, `china_biotech_supply_glut`, `ai_power_buildout`, `hbm_supply_chain`), **predictions** (JSONL append-only), **assertions** in the theses graph (33 predicates / 9 families, 18 slot vocabulary — see `tools/theses/predicates.py`, `tools/theses/slot_vocab.py`). Also tracked: **social-media accounts** (`memory/social_account_track_record.md`), **enforcement cases** (73 across 17 mechanisms in `analysis/case_library/`), **NPIs/providers** for fraud detection.

## Scripts/Tools Inventory

`tools/` has 397 files. Functional buckets:

- **DuckDB build/maintenance:** `setup_duckdb.py`, `rebuild_all.sh`, `_rebuild_sec_financial_views.py`, `_build_sec_xbrl_parquet.py`, `auto_view.py`
- **Entity & graph:** `build_entity_file.py`, `build_entity_tables.py`, `entity.py`, `unified_lookup.py`, `cluster_graph.py`, `sf_entity_resolution.py`, `splink_medicaid.py`, `splink_phmsa_operators.py`, `splink_usaspending_recipients.py`
- **Scanners (continuous signal mining):** `scan_insider_clusters.py`, `scan_13d_mandate.py`, `scan_clinicaltrials.py`, `scan_capex_pause_signal.py`, `scan_interconnection_queue.py`, `scan_edgar_rss.py`, `scan_congress.py`, `scan_political_money.py`, `scan_permitting_delays.py`, `scan_value_candidates.py`, `scan_theme_readthrough.py`
- **Backtests:** `backtest_signals.py`, `backtest_operational_risk_signals.py`, `backtest_signal_forward_returns.py`, `asymmetric_payoff_backtest.py`, `replay_big_winner_catchability.py`, `retroactive_oos.py`
- **Theses-graph subsystem:** `tools/theses/` — `extract_frontmatter.py`, `rebuild.py`, `predicates.py`, `slot_vocab.py`, `schema.sql`, `closure/` (12-axis entry FSM), `upstream_daemon.py`. MCP server: `theses_mcp.py`.
- **External-feed pulls:** `pull_990s.py`, `pull_citrini_comments.py`, `refresh_iso_queues.py`, `refresh_eia_860m.py`, `cms_data_download.py`, `asia_press_monitor.py`, `x_cashtag_sweep.py`
- **Calibration & meta:** `calibrate_scanners.py`, `prediction_tracker.py`, `reconcile_predictions.py`, `resolve_predictions.py`, `triage.py`, `telemetry_report.py`
- **Skills (15):** `.claude/skills/` — `thesis-check`, `entity-management`, `idea-generation`, `trace-influence`, `earnings-preview`, `resolve-predictions`, `social-thread`, `new-dataset`, plus 6 vendored finance-modeling skills (`3-statement-model`, `dcf-model`, `comps-analysis`, `xlsx-author`, `audit-xls`, `model-update`).

## Knowledge Artifacts

- `analysis/entities/*.md` (343) — durable conviction files, the canonical thesis surface
- `analysis/themes/*.md` (21) — bottleneck-level theme library; precomputed cross-domain probe templates
- `analysis/research/*.md` — ad-hoc research memos (~dozens)
- `analysis/case_library/` — enforcement-action library (73 cases)
- `analysis/investments/feature_pit_registry.csv` — PIT-safety classification for views
- `analysis/_logs/*.jsonl` — append-only event streams (predictions, portfolio, upstream observations)
- `memory/mechanisms.md`, `memory/priors.md`, `memory/analytical_reasoning.md`, `memory/short_report_registry.md`, `memory/social_account_track_record.md`
- `intel.duckdb` — derived; `intel/indexed/theses.duckdb` — derived (markdown frontmatter is canonical, DB is rebuildable)
- `.claude/rules/conviction-template.md` + `adversarial-review.md` + `ai-relationship-tag.md` — the operative writing contracts after the 2026-05-10 "hard strip"

## Overlap with Phenome/Genomics (where the bridge would exist)

Intel **already touches biology heavily** but through different surfaces than phenome/genomics. Concrete overlap surfaces:

1. **Clinical-trial / FDA / pharma data in `intel.duckdb`.** `clinical_trials_active`, `clinical_trials_halted`, `faers_drug` (15.5M rows), `fda_orange_book_products` (48K rows), `fda_orange_book_patents`, `fda_purple_book`, `fda_drug_enforcement`, `fda_483_fy2021..2025`, `pmda_approved_drugs`, `openfda_drug_events_monthly`, `cms_partd_prescriber_drug` (26.8M rows), `medicaid_drug_util`. These are commercial-signal extracts; phenome likely has deeper, modality-aware indexing of the same source data.

2. **Biotech entity files cite peer-reviewed literature inline.** `NTLA.md` cites NEJM DOI `10.1056/NEJMoa2405734` and `10.1056/NEJMoa2107454`; `ARWR.md` enumerates RNAi mechanism, SHASTA-3/4/5 readouts, partnership details with `[A1]` 10-K accession provenance. The biotech basket (NTLA/BEAM/CRSP/ARWR/BCRX/COAG/HG/BBOT/ABSI/ALKS/MRNA + theme files `genetic_medicine_modality_stack`, `china_biotech_supply_glut`, `anthropic_life_sciences`) IS the bridge target.

3. **How intel currently sources literature: out-of-band, not via research-mcp.** Although `research-mcp` IS registered in `intel/.mcp.json`, search across `analysis/` finds essentially **zero** invocations of `search_papers`, `ask_papers`, `prepare_evidence`, or `verify_claim`. Citations are pasted in from one-off Exa/Perplexity/scite calls or model training data. The biotech themes mostly cite Twitter/Substack threads (`Nuzhna`) + press releases + 10-Ks, not the primary literature corpus that phenome/genomics presumably curate.

4. **Variant-level / gene-level evidence is absent.** Intel reasons at the drug + indication + sponsor + clinical-phase level. It does NOT carry a CRISPR-guide library, a perturbation atlas, a PGx variant ledger, or a target-gene index — exactly the spaces phenome and genomics own. A bridge query like "what does literature say about ANGPTL3 as a cardiometabolic siRNA target" is currently answered by ad-hoc Exa/scite in-session, not by routing to phenome.

5. **Coefficient Bio / Anthropic Life Sciences theme.** `analysis/themes/anthropic_life_sciences.md` and `genetic_medicine_modality_stack.md` are the most-obvious entry points where intel would consume structured outputs from phenome/genomics (perturbation-data quality assessments, modality stack mapping, target validation evidence).

## Build-Then-Undo Signals

Visible in `git log` and the vetoed-decisions/archive layer:

- **Repo-tools MCP** — listed as available in `CLAUDE.md` but globally retired 2026-03-20 per meta `vetoed-decisions.md`. Intel's CLAUDE.md may be stale on this.
- **Knowledge-substrate MCP** — explicitly replaced by `intel-theses` MCP ("Replaces the legacy `knowledge-substrate` MCP").
- **`.claude/rules/_archived/2026-05-10-full-strip/`** — entire prior scoring framework (size formulas, universal edge/asymmetry/convexity scores) stripped a day before this audit. Commit `0ea2f5e` reflects the post-strip rules.
- **Portfolio tracking** — Constitution Principle 9 was amended 2026-05-07 to remove parallel-portfolio tracking after "systematic biases — borrowed conviction from prior allocation."
- **`migrate_2026-05-07_mandate_violators.csv` / `migrate_2026-05-07_trade_stance.csv`** at repo root — recent schema migration on entity frontmatter.
- **`backtest.py` + 5 sibling backtest scripts** — multiple iterations of backtest framing (`asymmetric_payoff_backtest`, `backtest_operational_risk_signals`, `backtest_signal_forward_returns`, `retroactive_oos`) suggesting the "what counts as a calibrated signal" question has been re-answered multiple times.
- **Tooling-decisions archive** in `memory/tooling-decisions.md` and `memory/killed_proposals_2026-05-06.md` — explicit graveyard.

## Candidates for Shared Infrastructure

1. **Research-mcp adoption.** Intel registers it but doesn't use it. Phenome/genomics presumably do. A shared evidence-grading convention — `[A1]` for peer-reviewed primary, NEJM/Nature DOI fetched via research-mcp — would let intel's biotech theses inherit phenome's literature ledger automatically. Highest-ROI bridge.

2. **Predicate / slot vocabulary.** `tools/theses/predicates.py` (33 predicates, 9 families) and `slot_vocab.py` (18 slots) are a generic assertion ontology. Could be reused for variant/gene/trial assertions in phenome.

3. **Closure FSM pattern.** `tools/theses/closure/` runs a 12-axis entry-readiness gate plus 6-axis monitoring against a `ProspectiveState` (DB ∪ proposed delta). The same architecture would work for genomics variant-promotion gates or phenome modality-classification gates.

4. **Source-grade-on-write hook.** `.claude/rules/research-depth.md` plus the unsourced-claim PostToolUse prompt hook. Already cross-applicable.

5. **Append-only canonical-state convention.** Markdown frontmatter canonical, JSONL append-only, DB derivable. This is exactly the pattern meta enforces (`pretool-append-only-guard.sh`); intel's theses subsystem is the most fleshed-out implementation.

6. **Theme-as-bottleneck artifact.** `analysis/themes/*.md` precomputes bottleneck synthesis so social-media prompts land against an existing structure. Phenome could have equivalent "modality stack" themes; genomics could have "variant pathway" themes.

7. **Clinical-trial / FAERS / Orange Book tables** in `intel.duckdb` could be exposed read-only (or replicated) to phenome/genomics to avoid duplicate ingestion of the same source feeds.

**Bridge architecture sketch:** intel posts a "literature query" against research-mcp (or a phenome-owned MCP), receives structured evidence with phenome-grade variant/target/mechanism context, attaches `[A1]` provenance, writes into the entity file. The intel side already has the conviction-template scaffold to receive it; the phenome side just needs to expose `target_evidence(target_symbol, indication)` or similar.

<!-- knowledge-index
generated: 2026-05-11T04:08:12Z
hash: c6cdd39d6dbe

cross_refs: analysis/entities/*.md, analysis/entities/{TICKER}.md, analysis/research/*.md, analysis/themes/*.md, analysis/themes/anthropic_life_sciences.md

end-knowledge-index -->
