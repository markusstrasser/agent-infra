---
description: Auto-generated file map with cross-file relationships. Updated daily.
---
# Codebase Map
# 42 Python files — generated 2026-03-13
# Navigation: repo_callgraph(target="name") finds callers across files

## scripts/

  agent_receipts.py            Normalize Codex/OpenAI runs into a common receipt schem
  autoresearch.py              Autoresearch — evolutionary code search with LLM-as-mut
  best-sync.py                 Daily git fetch for key OSS reference repos in ~/Projec
  calibration-canary.py        Run canary set for answer-confidence calibra…  → config
  claims-reader.py             Claims Table Reader — extract structured epi…  → config
  code-review-schedule.py      Submit code-review-sweep pipeline with rotating project
  code-review-scout.py         Continuous code review scout — dispatches code chunks t
  codebase-map.py
  compaction-nuance.py         Summarize pre-compaction nuance signals from…  → config
  config.py                    Shared config for epistemic measurement sc…  ← 25 files
  dashboard.py                 Agent ops dashboard.  → agent_receipts
  doctor.py                    Claude Code infrastructure health checker.  → config
  epistemic-lint.py            Epistemic Lint — static analysis for unsourc…  → config
  extract_user_tags.py         Extract #f feedback from user messages in Cl…  → config
  fold-detector.py             Fold detector: measures behavioral sycophanc…  → config
  hook-outcome-correlator.py   Hook outcome correlator — join hook triggers with sessi
  hook-roi.py                  Hook ROI telemetry — analyze hook trigger patterns.
  hook-telemetry-report.py     Hook telemetry report — reads ~/.claude/hook-triggers.j
  meta_infra_mcp.py            In-process MCP server exposing meta infrastructure to o
  model-review.py              Model-review dispatch — context assembly + parallel llmx
  orchestrator.py              Orchestrator: cron-driven task runner for Agent SDK and
  overview-trigger-analysis.py Analyze overview trigger logs across project…  → config
  prompt-archaeology.py        Prompt Archaeology — feed entire instruction surface in
  propose-work.py              Propose ranked work items from cross-project signals.
  pushback-index.py            Pushback Index — cheapest sycophancy metric.  → config
  repo-changes.py              Recent changes grouped by area — what changed and where
  repo-deps.py                 Show project dependencies with descriptions.
  repo-imports.py              Cross-file import graph for Python projects.
  repo-outline.py              Lightweight code structure tools for agent navigation.
  repo-summary.py              Generate or update per-file one-line summaries using a
  repo_tools_mcp.py            MCP server exposing repo navigation tools to AI agents.
  runlog.py                    Cross-vendor local run store for Cl…  → runlog_adapters
  safe-lite-eval.py            SAFE-lite Eval — factual precision measureme…  → config
  sessions.py                  Session search & dispatch infrastructure for…  → config
  subagent-analysis.py         Analyze subagent usage from ~/.claude/subagent-log.json
  trace-faithfulness.py        Tool-Trace Faithfulness — detect mismatches …  → config
  vendor-versions.py           Check latest versions of AI vendor tools and SDKs.

## scripts/runlog_adapters/

  __init__.py   ← 3 files
  claude.py
  codex.py
  common.py
  gemini.py
  kimi.py
