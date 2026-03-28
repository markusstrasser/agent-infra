---
description: Auto-generated file map with cross-file relationships. Updated daily.
---
# Codebase Map
# 71 Python files — generated 2026-03-28
# Navigation: repo_callgraph(target="name") finds callers across files

## scripts/

  agent_receipts.py             Normalize Codex/OpenAI runs into a common re…  → common
  autoresearch.py               Autoresearch — evolutionary code search with LLM-as-mut
  best-sync.py                  Daily git fetch for key OSS reference repos in ~/Projec
  calibration-canary.py         Run canary set for answer-confidence calibra…  → config
  claims-reader.py              Claims Table Reader — extract structured epi…  → config
  code-review-schedule.py       Submit code-review-sweep pipeline with rotating project
  code-review-scout.py          Continuous code review scout — dispatches code chunks t
  codebase-map.py               Generate a compact codebase map for agent context.
  codex_dispatch.py             Codex dispatch wrapper — lifecycle management for paral
  compaction-canary.py          Compaction canary benchmark — measur…  → common, config
  compaction-nuance.py          Summarize pre-compaction nuance sign…  → common, config
  config.py                     Shared config for epistemic meas…  → common  ← 46 files
  dashboard.py                  Agent ops dashboard.  → agent_receipts, common, config
  doctor.py                     Claude Code infrastructure health ch…  → common, config
  epistemic-lint.py             Epistemic Lint — static analysis for unsourc…  → config
  extract_user_tags.py          Extract #f feedback from user messag…  → common, config
  fail_open.py                  Fail-open decorator for epistemic measurement functions
  finding-triage.py             Finding auto-triage — SQLite staging…  → common, config
  fix-verify.py                 Fix verification — closed-loop valid…  → common, config
  fold-detector.py              Fold detector: measures behavioral s…  → common, config
  gen-skill-docs.py             Generate SKILL.md from .tmpl templates with …  → common
  generate-indexes.py           Generate and validate index files across meta project.
  hook-outcome-correlator.py    Hook outcome correlator — join hook triggers…  → common
  hook-roi.py                   Hook ROI telemetry — analyze hook trigger pa…  → common
  hook-telemetry-report.py      Hook telemetry report — reads ~/.claude/hook…  → common
  knowledge-balance-check.py      → config
  mcp_middleware.py             Shared MCP telemetry middleware for meta pro…  → common
  meta_infra_mcp.py             In-process MCP server exposing meta infrastr…  → common
  model-review.py               Model-review dispatch — context assembly + parallel llm
  orchestrator.py               Orchestrator: cron-driven task runner for Ag…  → common
  overview-trigger-analysis.py  Analyze overview trigger logs across project…  → config
  overview-usage.py             Overview usage tracker — measure ove…  → common, config
  pattern-maintenance.py          → common
  plan-status.py                Plan status tracker — scans .claude/plans/ across proje
  postwrite-knowledge-index.py
  prompt-archaeology.py         Prompt Archaeology — feed entire instruction…  → common
  propagate-correction.py         → common, config
  propose-work.py               Propose ranked work items from cross-project…  → common
  pushback-index.py             Pushback Index — cheapest sycophancy…  → common, config
  repo-changes.py               Recent changes grouped by area — what changed and where
  repo-deps.py                  Show project dependencies with descriptions.
  repo-imports.py               Cross-file import graph for Python projects.
  repo-outline.py               Lightweight code structure tools for agent navigation.
  repo-summary.py               Generate or update per-file one-line summaries using a
  repo_tools_mcp.py             MCP server exposing repo navigation tools to AI agents.
  researcher-postmortem.py      Researcher postmortem — classify silent suba…  → common
  runlog.py                     Cross-vendor local run stor…  → common, runlog_adapters
  safe-lite-eval.py             SAFE-lite Eval — factual precision m…  → common, config
  selve-frontmatter-backfill.py
  session-features.py           Extract structured epistemic feature…  → common, config
  session-shape.py              Session shape detector — zero-LLM-co…  → common, config
  sessions.py                   Session search & dispatch infrastruc…  → common, config
  skill-validator.py            Skill Validator — static checks for ~/Projec…  → common
  steering-signals.py             → common
  subagent-analysis.py          Analyze subagent usage from ~/.claude/subage…  → common
  supervision-kpi.py            Supervision KPI — measure human supe…  → common, config
  thesis-challenge.py           Thesis Challenge Metric — measures w…  → common, config
  tool-trajectory.py            Tool-opportunity utilization model —…  → common, config
  trace-faithfulness.py         Tool-Trace Faithfulness — detect mis…  → common, config
  vendor-versions.py            Check latest versions of AI vendor tools and SDKs.
  verify-audit.py

## scripts/common/

  __init__.py Shared utilities for meta scripts.  ← 149 files
  db.py       SQLite connection policy defaults.
  io.py       JSONL file helpers.
  paths.py    Env-aware path constants for ~/.claude resources.

## scripts/runlog_adapters/

  __init__.py   ← 3 files
  claude.py     → common
  codex.py      → common
  common.py
  gemini.py     → common
  kimi.py       → common
