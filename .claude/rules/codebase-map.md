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
# Navigation: repo_callgraph(target="name") finds callers across files

## scripts/

  _detector_patterns.py
  agent_infra_mcp.py                  → common
  agent_maintainability.py
  agent_receipts.py                 Normalize Codex/OpenAI runs into a common re…  → common
  agent_surface.py                    → common
  archived_orchestrator.py            → agent_infra_mcp, common
  audit-research-memo.py              → common, config
  audit_corpus_sync.py
  autoresearch.py                   Autoresearch — evolutionary code search with LLM-as-mut
  best-sync.py                      Daily git fetch for key OSS reference repos in ~/Projec
  buildthenundo.py                    → common
  calibration-canary.py             Run canary set for answer-confidence calibra…  → config
  claim-vulnerabilities.py            → common, config
  claims-reader.py                  Claims Table Reader — extract structured epi…  → config
  code-review-schedule.py           Submit code-review-sweep pipeline with rotating project
  code-review-scout.py              Continuous code review scout — dispatches code chunks t
  codebase-map.py                   Generate a compact codebase map for agent context.
  codex_dispatch.py
  codex_parity_sync.py                → common
  compaction-canary.py              Compaction canary benchmark — measur…  → common, config
  compaction-nuance.py              Summarize pre-compaction nuance sign…  → common, config
  compress-research-index.py
  config.py                         Shared config for epistemic meas…  → common  ← 44 files
  context-budget.py                   → common
  corpus_ingest_gwern.py
  corpus_ingest_lesswrong.py
  corpus_marker_modal.py
  corpus_mcp.py
  corpus_reference_search.py
  critique_health.py                  → common
  cross-project-drift.py
  dashboard.py                      Agent ops dashboard.  → agent_receipts, common, config
  dispatch-with-stub.py
  doctor.py                         Claude Code infrastructure health ch…  → common, config
  epistemic-lint.py                 Epistemic Lint — static analysis for unsourc…  → config
  extract-citation-ids.py             → common, config
  extract_intel_entity_citations.py
  fail_open.py                      Fail-open decorator for epistemic measurement functions
  fix-verify.py                     Fix verification — closed-loop valid…  → common, config
  fm.py
  fold-detector.py                  Fold detector: measures behavioral s…  → common, config
  gen-skill-docs.py                 Generate SKILL.md from .tmpl templates with …  → common
  generate-indexes.py               Generate and validate index files across meta project.
  gov.py                              → buildthenundo, common, gov_intake, gov_invariants
  gov_intake.py
  gov_invariants.py
  hook-outcome-correlator.py        Hook outcome correlator — join hook triggers…  → common
  hook-roi.py                       Hook ROI telemetry — analyze hook trigger pa…  → common
  hook-telemetry-report.py          Hook telemetry report — reads ~/.claude/hook…  → common
  improvement_cycle.py
  lint_no_bare_annotations_read.py
  mcp-audit.py                        → common
  mcp_contract_smoke.py               → agent_infra_mcp, corpus_mcp
  mcp_middleware.py                 Shared MCP telemetry middleware for meta pro…  → common
  ops.py                              → common, session_store
  overview-trigger-analysis.py      Analyze overview trigger logs across project…  → config
  overview-usage.py                 Overview usage tracker — measure ove…  → common, config
  parallel_mcp.py
  parallel_search.py
  pattern-maintenance.py              → common
  plan-staleness.py
  plan-status.py                    Plan status tracker — scans .claude/plans/ a…  → common
  posttool-paper-quality.py
  postwrite-knowledge-index.py
  prompt-archaeology.py             Prompt Archaeology — feed entire instruction…  → common
  propose-work.py                   Propose ranked work items from cross-project…  → common
  pushback-index.py                 Pushback Index — cheapest sycophancy…  → common, config
  reasoning-audit.py                  → common
  reflect.py                          → fm
  reflect_capture.py
  reflect_eval.py                     → reflect
  repo-changes.py                   Recent changes grouped by area — what changed and where
  repo-deps.py                      Show project dependencies with descriptions.
  repo-imports.py                   Cross-file import graph for Python projects.
  repo-outline.py                   Lightweight code structure tools for agent navigation.
  repo-summary.py                   Generate or update per-file one-line summaries using a
  research_verifier.py
  researcher-postmortem.py          Researcher postmortem — classify silent suba…  → common
  safe-lite-eval.py                 SAFE-lite Eval — factual precision m…  → common, config
  selve-frontmatter-backfill.py
  session-features.py               Extract structure…  → common, config, session_detectors
  session_detectors.py                → _detector_patterns
  session_store.py                    → common
  skill-routing.py
  skill-validator.py                Skill Validator — static checks for ~/Projec…  → common
  subagent-analysis.py              Analyze subagent usage from ~/.claude/subage…  → common
  supervision-kpi.py                Supervision KPI — measure human supe…  → common, config
  test_health.py
  thesis-challenge.py               Thesis Challenge Metric — measures w…  → common, config
  token-baseline.py                   → token_baseline_helpers
  token_baseline_helpers.py
  tool-trajectory.py                Tool-opportunity utilization model —…  → common, config
  trace-faithfulness.py             Tool-Trace Faithfulness — detect mis…  → common, config
  ts-replace.py
  usage-check.py
  verify-audit.py                     → common
  verify-subagent-claims.py

## scripts/common/

  __init__.py    ← 75 files
  console.py
  db.py
  event_log.py
  hookmeta.py
  io.py
  paths.py

## scripts/corpus/packages/corpus-core/corpus_core/

  __init__.py
  annotate.py
  annotate_cli.py
  batch.py
  canonical.py
  cli.py
  extract_citances.py
  figure_extract.py
  graph_cli.py
  identity.py
  identity_crosswalk.py
  index.py
  ingest.py
  lookup.py
  maintain.py
  outbox.py
  parse_health.py
  replay.py
  resolve_references.py
  schema_version.py
  store.py
  sync.py
  uri.py

## scripts/corpus/packages/corpus-core/corpus_core/extract/

  __init__.py
  _common.py
  html_trafilatura.py
  pdf_lightweight.py
  pdf_liteparse.py
  pdf_llm.py
  pdf_marker.py
  pdf_marker_modal.py
  pdf_mineru.py

## scripts/corpus/packages/corpus-core/corpus_core/util/

  __init__.py
  stdio_guard.py

## scripts/corpus/packages/corpus-core/tests/

  conftest.py
  test_annotate.py
  test_annotations_index.py
  test_bitemporal.py
  test_canonical.py
  test_claim_relations.py
  test_extract.py
  test_figure_extract.py
  test_graph_rebuild_idempotent.py
  test_identity.py
  test_identity_crosswalk.py
  test_ingest_idempotent.py
  test_outbox.py
  test_paper_id_derivation.py
  test_papers_cli_smoke.py
  test_parse_health.py
  test_read_loop.py
  test_register_revision.py
  test_replay.py
  test_resolve_references.py
  test_schema_version.py

## scripts/corpus/packages/corpus-testing/corpus_testing/

  __init__.py
  annotation_fixtures.py
  conftest_template.py
  corpus_fixtures.py
  mcp_fixtures.py

## scripts/corpus/packages/corpus-testing/tests/

  test_fixtures_smoke.py

## scripts/tests/

  conftest.py
  test_buildthenundo.py              → buildthenundo
  test_gov.py                        → gov, gov_intake
  test_gov_intake.py
  test_harness_infra.py
  test_lint_no_bare_annotations.py   → lint_no_bare_annotations_read
  test_skill_consolidation.py
  test_test_health.py                → test_health
