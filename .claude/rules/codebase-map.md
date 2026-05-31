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

# 84 Python files — generated 2026-05-11
# Navigation: repo_callgraph(target="name") finds callers across files

## scripts/

  agent_infra_mcp.py              → common
  agent_maintainability.py
  agent_receipts.py             Normalize Codex/OpenAI runs into a common re…  → common
  agent_surface.py                → common
  archived_orchestrator.py        → agent_infra_mcp, common
  audit-research-memo.py          → common, config
  autoresearch.py               Autoresearch — evolutionary code search with LLM-as-mut
  best-sync.py                  Daily git fetch for key OSS reference repos in ~/Projec
  calibration-canary.py         Run canary set for answer-confidence calibra…  → config
  claim-vulnerabilities.py        → common, config
  claims-reader.py              Claims Table Reader — extract structured epi…  → config
  code-review-schedule.py       Submit code-review-sweep pipeline with rotating project
  code-review-scout.py          Continuous code review scout — dispatches code chunks t
  codebase-map.py               Generate a compact codebase map for agent context.
  codex_dispatch.py
  compaction-canary.py          Compaction canary benchmark — measur…  → common, config
  compaction-nuance.py          Summarize pre-compaction nuance sign…  → common, config
  compress-research-index.py
  config.py                     Shared config for epistemic meas…  → common  ← 52 files
  context-budget.py               → common
  cross-project-drift.py
  dashboard.py                  Agent ops dashboard.  → agent_receipts, common, config
  doctor.py                     Claude Code infrastructure health ch…  → common, config
  epistemic-lint.py             Epistemic Lint — static analysis for unsourc…  → config
  extract-citation-ids.py         → common, config
  fail_open.py                  Fail-open decorator for epistemic measurement functions
  finding-triage.py             Finding auto-triage — SQLite staging…  → common, config
  fix-verify.py                 Fix verification — closed-loop valid…  → common, config
  fold-detector.py              Fold detector: measures behavioral s…  → common, config
  gen-skill-docs.py             Generate SKILL.md from .tmpl templates with …  → common
  generate-indexes.py           Generate and validate index files across meta project.
  hook-outcome-correlator.py    Hook outcome correlator — join hook triggers…  → common
  hook-roi.py                   Hook ROI telemetry — analyze hook trigger pa…  → common
  hook-telemetry-report.py      Hook telemetry report — reads ~/.claude/hook…  → common
  improvement_cycle.py
  knowledge-balance-check.py      → config
  mcp-audit.py                    → common
  mcp_middleware.py             Shared MCP telemetry middleware for meta pro…  → common
  ops.py                          → common, session_store
  overview-trigger-analysis.py  Analyze overview trigger logs across project…  → config
  overview-usage.py             Overview usage tracker — measure ove…  → common, config
  parallel_mcp.py
  parallel_search.py
  pattern-maintenance.py          → common
  plan-staleness.py
  plan-status.py                Plan status tracker — scans .claude/plans/ a…  → common
  posttool-paper-quality.py
  postwrite-knowledge-index.py
  prompt-archaeology.py         Prompt Archaeology — feed entire instruction…  → common
  propagate-correction.py         → common, config
  propose-work.py               Propose ranked work items from cross-project…  → common
  pushback-index.py             Pushback Index — cheapest sycophancy…  → common, config
  reasoning-audit.py              → common
  repo-changes.py               Recent changes grouped by area — what changed and where
  repo-deps.py                  Show project dependencies with descriptions.
  repo-imports.py               Cross-file import graph for Python projects.
  repo-outline.py               Lightweight code structure tools for agent navigation.
  repo-summary.py               Generate or update per-file one-line summaries using a
  repo_tools_mcp.py             MCP server exposing repo navigation tools to AI agents.
  research_verifier.py
  researcher-postmortem.py      Researcher postmortem — classify silent suba…  → common
  safe-lite-eval.py             SAFE-lite Eval — factual precision m…  → common, config
  selve-frontmatter-backfill.py
  session-features.py           Extract structured epistemic feature…  → common, config
  session_store.py                → common
  skill-routing.py
  skill-validator.py            Skill Validator — static checks for ~/Projec…  → common
  subagent-analysis.py          Analyze subagent usage from ~/.claude/subage…  → common
  supervision-kpi.py            Supervision KPI — measure human supe…  → common, config
  thesis-challenge.py           Thesis Challenge Metric — measures w…  → common, config
  token-baseline.py
  tool-trajectory.py            Tool-opportunity utilization model —…  → common, config
  trace-faithfulness.py         Tool-Trace Faithfulness — detect mis…  → common, config
  verify-audit.py

## scripts/common/

  __init__.py    ← 71 files
  console.py
  db.py
  event_log.py
  io.py
  paths.py

## scripts/tests/

  conftest.py
  test_harness_infra.py
  test_skill_consolidation.py
