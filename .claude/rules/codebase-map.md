---
description: Auto-generated file map with cross-file relationships. Updated daily.
paths:
  - "scripts/**"
---
# Codebase Map

<!-- Gov-ID: rule:codebase-map
goal: compact code map for agent navigation (generated)
verifier: null
blast_radius: style
-->

# 173 Python files — generated 2026-06-04
# Edge annotations: → imports  ← imported-by-N-files

## scripts/

  _detector_patterns.py             Vendored regex pattern banks for deterministic session-
  agent_infra_mcp.py                In-process MCP server exposing meta infrastr…  → common
  agent_maintainability.py          Maintainability metrics for conservatively agent-attrib
  agent_receipts.py                 Normalize Codex/OpenAI runs into a common re…  → common
  agent_surface.py                  Agent surface analyzer.  → common
  archived_orchestrator.py          Orchestrator: queue-backed …  → agent_infra_mcp, common
  audit-research-memo.py            Audit whether research memos follow …  → common, config
  audit_corpus_sync.py              audit_corpus_sync — verdicts ↔ corpus-annotations drift
  autoresearch.py                   Autoresearch — evolutionary code search with LLM-as-mut
  best-sync.py                      Daily git fetch for key OSS reference repos in ~/Projec
  buildthenundo.py                  Build-then-undo detector — REPORT-ONLY git-h…  → common
  calibration-canary.py             Run canary set for answer-confidence calibra…  → config
  claim-vulnerabilities.py          Claim vulnerability detection across…  → common, config
  claims-reader.py                  Claims Table Reader — extract structured epi…  → config
  code-review-schedule.py           Submit code-review-sweep pipeline with rotating project
  code-review-scout.py              Continuous code review scout — dispatches code chunks t
  codebase-map.py                   Generate a compact codebase map for agent context.
  codex_dispatch.py                 Codex dispatch wrapper — lifecycle management for paral
  codex_parity_sync.py              codex_parity_sync.py — mirror per-repo Claud…  → common
  compaction-canary.py              Compaction canary benchmark — measur…  → common, config
  compaction-nuance.py              Summarize pre-compaction nuance sign…  → common, config
  compress-research-index.py        Compress research-index.md from fat 3-col table to thin
  config.py                         Shared config for epistemic meas…  → common  ← 44 files
  context-budget.py                 Context budget analyzer.  → common
  corpus_ingest_gwern.py            Ingest Gwern.net essays into the shared corpus.
  corpus_ingest_lesswrong.py        Ingest LessWrong high-karma posts into the shared corpu
  corpus_marker_modal.py            Marker on Modal — GPU-accelerated PDF → markdown with G
  corpus_mcp.py                     corpus-mcp — dedicated MCP server for the local corpus
  corpus_reference_search.py        Full-text reference search over LessWrong + Gwern sourc
  critique_health.py                Critique-axis health — report-only quality m…  → common
  cross-project-drift.py            Cross-project drift detection — find divergences in hoo
  dashboard.py                      Agent ops dashboard.  → agent_receipts, common, config
  dispatch-with-stub.py             Write a stub output file BEFORE dispatching a subagent.
  doctor.py                         Claude Code infrastructure health ch…  → common, config
  epistemic-lint.py                 Epistemic Lint — static analysis for unsourc…  → config
  extract-citation-ids.py           Extract citation identifiers (DOI / …  → common, config
  extract_intel_entity_citations.py Intel entity citation extraction (manual corpus annotat
  fail_open.py                      Fail-open decorator for epistemic measurement functions
  fix-verify.py                     Fix verification — closed-loop valid…  → common, config
  fm.py                             fm.py — machine-addressable spine for the failure-mode
  fold-detector.py                  Fold detector: measures behavioral s…  → common, config
  gen-skill-docs.py                 Generate SKILL.md from .tmpl templates with …  → common
  generate-indexes.py               Generate and validate index files across meta project.
  gov.py                            gov.py — governance self-revision orchestrator (report-  → buildthenundo, common, gov_intake, gov_invariants
  gov_intake.py                     Governance correction intake — UserPromptSubmit hook.
  gov_invariants.py                 Curated contradiction-invariant registry.
  hook-outcome-correlator.py        Hook outcome correlator — join hook triggers…  → common
  hook-roi.py                       Hook ROI telemetry — analyze hook trigger pa…  → common
  hook-telemetry-report.py          Hook telemetry report — reads ~/.claude/hook…  → common
  improvement_cycle.py              Improvement-log cycle time — measures self-improvement
  lint_no_bare_annotations_read.py  Caller-migration lint — Phase A.
  mcp-audit.py                      MCP tool loading overhead audit across proje…  → common
  mcp_contract_smoke.py             $0 in-process contract …  → agent_infra_mcp, corpus_mcp
  mcp_middleware.py                 Shared MCP telemetry middleware for meta pro…  → common
  ops.py                            Operational state CLI over ru…  → common, session_store
  overview-trigger-analysis.py      Analyze overview trigger logs across project…  → config
  overview-usage.py                 Overview usage tracker — measure ove…  → common, config
  parallel_mcp.py                   Parallel Task API — MCP server for deep web research.
  parallel_search.py                Parallel Task API — CLI wrapper for deep web research.
  pattern-maintenance.py            Maintenance for design-review patterns.jsonl…  → common
  plan-staleness.py                 Plan staleness scanner — find stale .claude/plans/ acro
  plan-status.py                    Plan status tracker — scans .claude/plans/ a…  → common
  posttool-paper-quality.py         PostToolUse advisory for research paper quality cards.
  postwrite-knowledge-index.py      PostToolUse hook: extract knowledge index from written/
  prompt-archaeology.py             Prompt Archaeology — feed entire instruction…  → common
  propose-work.py                   Propose ranked work items from cross-project…  → common
  pushback-index.py                 Pushback Index — cheapest sycophancy…  → common, config
  reasoning-audit.py                Reasoning audit — identify expensive session…  → common
  reflect.py                        reflect.py — the deep pass of the recursive lear…  → fm
  reflect_capture.py                reflect_capture.py — zero-LLM session-end capture for t
  reflect_eval.py                   reflect_eval.py — grade the learning loop a…  → reflect
  repo-changes.py                   Recent changes grouped by area — what changed and where
  repo-deps.py                      Show project dependencies with descriptions.
  repo-imports.py                   Cross-file import graph for Python projects.
  repo-outline.py                   Lightweight code structure tools for agent navigation.
  repo-summary.py                   Generate or update per-file one-line summaries using a
  research_verifier.py              Generate a companion verification artifact for claim-he
  researcher-postmortem.py          Researcher postmortem — classify silent suba…  → common
  safe-lite-eval.py                 SAFE-lite Eval — factual precision m…  → common, config
  selve-frontmatter-backfill.py     Backfill YAML frontmatter on selve research memos that
  session-features.py               Extract structure…  → common, config, session_detectors
  session_detectors.py              Deterministic session-quality de…  → _detector_patterns
  session_store.py                  Runlogs-backed session metadata helpers.  → common
  skill-routing.py                  Classify Skill tool invocations as user-slash vs model-
  skill-validator.py                Skill Validator — static checks for ~/Projec…  → common
  subagent-analysis.py              Analyze subagent usage from ~/.claude/subage…  → common
  supervision-kpi.py                Supervision KPI — measure human supe…  → common, config
  test_health.py                    Test-health sentinel — watch whether each repo's test s
  thesis-challenge.py               Thesis Challenge Metric — measures w…  → common, config
  token-baseline.py                 Token baseline measurements …  → token_baseline_helpers
  token_baseline_helpers.py         Pure, importable helpers for token-baseline.py.
  tool-trajectory.py                Tool-opportunity utilization model —…  → common, config
  trace-faithfulness.py             Tool-Trace Faithfulness — detect mis…  → common, config
  ts-replace.py                     TS/JS-aware string replacement for fix scripts.
  usage-check.py                    Session cost meter — reads ~/.claude/llmx-usage.jsonl a
  verify-audit.py                   Audit Haiku orchestrator verification accura…  → common
  verify-subagent-claims.py         Random-sample re-verifier for subagent verdict files.

## scripts/common/

  __init__.py  Shared utilities for meta scripts.  ← 75 files
  console.py   Minimal console output utilities — colors, progress, ta
  db.py        SQLite connection policy defaults.
  event_log.py Operational event-log helpers.
  hookmeta.py  Hook metadata helpers — git-derived deploy dates for ho
  io.py        JSONL file helpers.
  paths.py     Env-aware path constants for ~/.claude resources.

## scripts/corpus/packages/corpus-core/corpus_core/

  __init__.py           Canonical corpus store — single cross-repo cache of sou
  annotate.py           Sole writer for ``<corpus-root>/<source_id>/annotations
  annotate_cli.py       `corpus annotate ...` subcommand wiring.
  batch.py              Batch-ingest PDFs in parallel — fan out to Modal extrac
  canonical.py          Versioned canonical JSON for the corpus substrate.
  cli.py                `corpus` console script entry point.
  extract_citances.py   Phase C of the graph layer — extract normalized citance
  figure_extract.py     On-demand figure-DATA extraction → `figure_extraction`
  graph_cli.py          Graph query CLI — `corpus cites|cited-by|ego|path|simil
  identity.py           Content-addressed identity primitives for the corpus.
  identity_crosswalk.py Cross-repo source identity crosswalk.
  index.py              Derived `annotations` table in graph.duckdb.
  ingest.py             Ingest a source (PDF, HTML/URL) into the canonical stor
  lookup.py             Read-side helpers: source records, annotations.
  maintain.py           Store maintenance — stats, verify, rebuild indexes/cita
  outbox.py             Cross-repo outbox primitive for the substrate-v2 cross-
  parse_health.py       Parse-state derivation + an empty-parse health flag ove
  replay.py             Replay verifier: rebuild graph.duckdb from annotations.
  resolve_references.py Phase B of the graph layer — resolve reference-section
  schema_version.py     DB-resident schema version + preflight for the corpus s
  store.py              Canonical corpus store helper module.
  sync.py               Best-effort bootstrap from upstream — NOT a backup mech
  uri.py                Portable URIs for cross-repo references.

## scripts/corpus/packages/corpus-core/corpus_core/extract/

  __init__.py         Extractor dispatch for the corpus.
  _common.py          Shared helpers for extractors.
  html_trafilatura.py trafilatura — HTML → markdown.
  pdf_lightweight.py  pymupdf4llm — fast native-text PDF extraction.
  pdf_liteparse.py    liteparse — fast, model-free PDF/office/image text extr
  pdf_llm.py          LLM-fallback PDF extraction via Gemini Flash-Lite.
  pdf_marker.py       Marker — LLM-enhanced PDF extraction (opt-in, GPL-licen
  pdf_marker_modal.py Marker-on-Modal extractor — calls the deployed corpus-m
  pdf_mineru.py       MinerU 3.x — high-fidelity scientific-PDF parser.

## scripts/corpus/packages/corpus-core/corpus_core/util/

  __init__.py
  stdio_guard.py Reject stray stdout writes when running as a stdio MCP.

## scripts/corpus/packages/corpus-core/tests/

  conftest.py                      Test fixtures — every test gets an explicit temp Corpus
  test_annotate.py                 Annotation writer: schema validation, idempotency, atom
  test_annotations_index.py        Phase 2: annotations table in graph.duckdb — projection
  test_bitemporal.py               Phase A — bitemporal valid_from + chain-aware annotatio
  test_canonical.py                Phase F — versioned canonical JSON.
  test_claim_relations.py          Epistemic core: inline claim_relation annotations + the
  test_extract.py                  Extractor dispatch + per-tool smoke tests.
  test_figure_extract.py           Figure-extraction tests. The live vision call is valida
  test_graph_rebuild_idempotent.py Rebuilding the graph twice produces the same edge set.
  test_identity.py                 Identity primitives: byte-stable canonical_json + sha25
  test_identity_crosswalk.py       Phase B — source identity crosswalk.
  test_ingest_idempotent.py        Ingest is a no-op on re-run with same PDF + parser.
  test_outbox.py                   Cross-repo outbox primitive — schema, lifecycle migrati
  test_paper_id_derivation.py      DOI > PMID > SHA precedence, slug normalization, collis
  test_papers_cli_smoke.py         `corpus stats` works on an empty store + after one inge
  test_parse_health.py             Parse-state (C0) + empty-parse health seed tests.
  test_read_loop.py                Read-loop: `active_annotations_for_source` surfaces ver
  test_register_revision.py        Revision flow archives prior PDF + active parse, update
  test_replay.py                   Phase F — replay verifier.
  test_resolve_references.py       Reference-section + entry extraction against marker's r
  test_schema_version.py           Phase G0 — DB-resident schema version + preflight.

## scripts/corpus/packages/corpus-testing/corpus_testing/

  __init__.py            Test utilities for downstream consumers of corpus-core.
  annotation_fixtures.py Sample annotation factories for tests.
  conftest_template.py   Drop-in conftest.py template for downstream consumers.
  corpus_fixtures.py     Pytest fixtures providing an isolated corpus root per t
  mcp_fixtures.py        FastMCP-native test fixtures.

## scripts/corpus/packages/corpus-testing/tests/

  test_fixtures_smoke.py Smoke test: corpus-testing fixtures actually work end-t

## scripts/tests/

  conftest.py                      Shared test fixtures for agent-infra scripts.
  test_buildthenundo.py            Tests for the build-then-undo detecto…  → buildthenundo
  test_gov.py                      Regression tests for gov.py + gov_i…  → gov, gov_intake
  test_gov_intake.py               Tests for the governance correction intake hook (script
  test_harness_infra.py            Tests for agent-infra harness infrastructure — trace in
  test_lint_no_bare_annotations.py Phase A — Caller-migr…  → lint_no_bare_annotations_read
  test_skill_consolidation.py      Skill mode-telemetry contract (the pretool-skill-log ho
  test_test_health.py              Contract tests for the test-health sent…  → test_health
