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

# 122 Python files — generated 2026-06-13
# Edge annotations: → imports  ← imported-by-N-files

## scripts/

  _detector_patterns.py             Vendored regex pattern banks for deterministic session-
  acqui_hire_scan.py                Acqui-hire / acquisition cluster detector (Live Data pa
  agent_infra_mcp.py                In-process MCP server exposing meta infrastr…  → common
  agent_maintainability.py          Maintainability metrics for conservatively agent-attrib
  agent_receipts.py                 Normalize Codex/OpenAI runs into a common re…  → common
  agent_surface.py                  Agent surface analyzer.  → common
  audit_corpus_sync.py              audit_corpus_sync — verdicts ↔ corpus-annotations drift
  autoresearch.py                   Autoresearch — evolutionary code search with LLM-as-mut
  best-sync.py                      Daily git fetch for key OSS reference repos in ~/Projec
  binary_skills_extract.py          Extract embedded skill/workflow prompts from the Claude
  buildthenundo.py                  Build-then-undo detector — REPORT-ONLY git-h…  → common
  calibration-canary.py             Run canary set for answer-confidence calibra…  → config
  claims-reader.py                  Claims Table Reader — extract structured epi…  → config
  code-review-schedule.py           Submit code-review-sweep pipeline with rotating project
  code-review-scout.py              Continuous code review scout — dispatches code chunks t
  codebase-map.py                   Generate a compact codebase map for agent context.
  codex_dispatch.py                 Codex dispatch wrapper — lifecycle management for paral
  codex_hook_compat.py              Codex hook compatibility checker.  → common  ← 5 files
  codex_hook_shim.py                codex_hook_shim.py — normalize Claude-dialect hook outp
  codex_mcp_smoke.py                Smoke-test project-scoped Codex stdio MCP de…  → common
  codex_parity_sync.py              codex_parity_sync.py — mirror per-repo Claud…  → common
  compaction-nuance.py              Summarize pre-compaction nuance sign…  → common, config
  compress-research-index.py        Compress research-index.md from fat 3-col table to thin
  config.py                         Shared config for epistemic meas…  → common  ← 29 files
  context-budget.py                 Context budget analyzer.  → common
  corpus_ingest_gwern.py            Ingest Gwern.net essays into the shared corpus.
  corpus_ingest_lesswrong.py        Ingest LessWrong high-karma posts into the shared corpu
  corpus_marker_modal.py            Marker on Modal — GPU-accelerated PDF → markdown with G
  corpus_mcp.py                     corpus-mcp — dedicated MCP server for the local corpus
  corpus_reference_search.py        Full-text reference search over LessWrong + Gwern sourc
  critique_health.py                Critique-axis health — report-only quality m…  → common
  dashboard.py                      Agent ops dashboard.  → agent_receipts, common, config
  dispatch-with-stub.py             Write a stub output file BEFORE dispatching a subagent.
  doctor.py                         Claude Code infrastruc…  → common, config, orphan_check
  epistemic-lint.py                 Epistemic Lint — static analysis for unsourc…  → config
  export_public_skills.py           Allowlisted public export for shared skills.  → common
  extract_intel_entity_citations.py Intel entity citation extraction (manual corpus annotat
  fable_speedup_probe.py            fable_speedup_probe.py — throttle detector with STRUCTU
  fable_throttle_probe.py           fable_throttle_probe.py — tell when Claude Fable 5 is b
  fail_open.py                      Fail-open decorator for epistemic measurement functions
  fm.py                             fm.py — machine-addressable spine for the failure-mode
  fold-detector.py                  Fold detector: measures behavioral s…  → common, config
  gen-skill-docs.py                 Generate SKILL.md from .tmpl templates with …  → common
  generate-indexes.py               Generate and validate index files across meta project.
  gov.py                            gov.py — governance self-revision orchestrator (report-  → buildthenundo, common, gov_intake, gov_invariants, risky_diff_review_shadow
  gov_intake.py                     Feedback intake — UserPromptSubmit hook.
  gov_invariants.py                 Curated contradiction-invariant registry.
  guard_doctor.py                   guard_doctor.py — is tool-agnostic commit-time protecti
  hook-outcome-correlator.py        Hook outcome correlator — join hook triggers…  → common
  hook-roi.py                       Hook ROI telemetry — analyze hook trigger pa…  → common
  hook-telemetry-report.py          Hook telemetry report — reads ~/.claude/hook…  → common
  hooks_smoke.py                    Claude hook smoke — catch…  → codex_hook_compat, common
  lint_no_bare_annotations_read.py  Caller-migration lint — Phase A.
  mcp_contract_smoke.py             $0 in-process contract …  → agent_infra_mcp, corpus_mcp
  mcp_middleware.py                 Shared MCP telemetry middleware for meta pro…  → common
  migrate_skills.py                 Dry-run skill migration planner from manifes…  → common
  orphan_check.py                   orphan_check.py — the orphaned-generator ratchet (repor
  parallel_mcp.py                   Parallel Task API — MCP server for deep web research.
  parallel_search.py                Parallel Task API — CLI wrapper for deep web research.
  plan-status.py                    Plan status tracker — scans .claude/plans/ a…  → common
  posttool-paper-quality.py         PostToolUse advisory for research paper quality cards.
  postwrite-knowledge-index.py      PostToolUse hook: extract knowledge index from written/
  propose-work.py                   Propose ranked work items from cross-project…  → common
  pushback-index.py                 Pushback Index — cheapest sycophancy…  → common, config
  reclassify_improvement_log.py     Reclassify improvement-log open `[ ]` statuses into the
  reflect.py                        reflect.py — the deep pass of the recursive lear…  → fm
  reflect_capture.py                reflect_capture.py — zero-LLM session-end capture for t
  reflect_eval.py                   reflect_eval.py — grade the learning loop a…  → reflect
  repo-changes.py                   Recent changes grouped by area — what changed and where
  repo-imports.py                   Cross-file import graph for Python projects.
  repo-outline.py                   Lightweight code structure tools for agent navigation.
  repo-summary.py                   Generate or update per-file one-line summaries using a
  research_verifier.py              Generate a companion verification artifact for claim-he
  researcher-postmortem.py          Researcher postmortem — classify silent suba…  → common
  risky_diff_review_shadow.py       Risky-diff-review SHADOW detector — REPORT-ONLY git-his
  safe-lite-eval.py                 SAFE-lite Eval — factual precision m…  → common, config
  selve-frontmatter-backfill.py     Backfill YAML frontmatter on selve research memos that
  session-features.py               Extract structure…  → common, config, session_detectors
  session_detectors.py              Deterministic session-quality de…  → _detector_patterns
  skill-routing.py                  Analyze skill usage and run deterministic sk…  → common
  skill-validator.py                Skill Validator — static checks for ~/Projec…  → common
  skill_description_budget.py       Report always-loaded skill description budge…  → common
  skill_graph.py                    Emit a workflow -> module/lens graph from sk…  → common
  skill_loader_probe.py             Probe skill-loader filesystem assumptions.  → common
  skill_manifest.py                 Generate and validate cross-project skill ma…  → common
  skill_reference_validator.py      Validate skill reference closure across hook…  → common
  skill_usage_watch.py              skill-usage-watch collector — deterministic half of the
  supervision-kpi.py                Supervision KPI — measure human supe…  → common, config
  talent_flow_livedata.py           Talent-flow measurement via Live Data Technologies work
  talent_flow_probe.py              Talent-flow tracker (Exa prototype) — dated A→B job tra
  test_health.py                    Test-health sentinel — watch whether each repo's test s
  thesis-challenge.py               Thesis Challenge Metric — measures w…  → common, config
  tool-trajectory.py                Tool-opportunity utilization model —…  → common, config
  tool_hallucination_probe.py       One-time characterization of tool-hallucination events
  trace-faithfulness.py             Tool-Trace Faithfulness — detect mis…  → common, config
  ts-replace.py                     TS/JS-aware string replacement for fix scripts.
  usage-check.py                    Session cost meter — reads ~/.claude/llmx-usage.jsonl a
  validate_probe_tasks.py           validate_probe_tasks.py — prov…  → fable_throttle_probe
  verify-audit.py                   Audit Haiku orchestrator verification accura…  → common
  verify-subagent-claims.py         Random-sample re-verifier for subagent verdict files.

## scripts/common/

  __init__.py         Shared utilities for meta scripts.  ← 91 files
  console.py          Minimal console output utilities — colors, progress, ta
  db.py               SQLite connection policy defaults.
  event_log.py        Operational event-log helpers.
  hookmeta.py         Hook metadata helpers — git-derived deploy dates for ho
  io.py               JSONL file helpers.
  paths.py            Env-aware path constants for ~/.claude resources.
  project_registry.py Shared project registries for cross-repo agent-infra ch
  skill_objects.py    Shared skill-object inventory and manifest h…  → common

## scripts/tests/

  conftest.py                      Shared test fixtures for agent-infra scripts.
  test_autoresearch.py               → autoresearch
  test_buildthenundo.py            Tests for the build-then-undo detecto…  → buildthenundo
  test_codex_hook_shim.py          Tests for codex_hook_shim.py — Claude-dialect hook outp
  test_gov.py                      Regression tests for gov.py + gov_i…  → gov, gov_intake
  test_gov_intake.py               Tests for the feedback intake hook (scripts/gov_intake.
  test_harness_infra.py            Tests for agent-infra harness infrastructure — trace in
  test_hooks_smoke.py              Negative controls for hooks_smoke.py — prove the detect
  test_lint_no_bare_annotations.py Phase A — Caller-migr…  → lint_no_bare_annotations_read
  test_propose_work.py
  test_risky_diff_review_shadow.py Tests for the risky-diff-r…  → risky_diff_review_shadow
  test_skill_consolidation.py      Skill mode-telemetry contract (the pretool-skill-log ho
  test_test_health.py              Contract tests for the test-health sent…  → test_health
