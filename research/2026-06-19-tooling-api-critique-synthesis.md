---
title: Tooling API — critique synthesis + implementation
date: 2026-06-19
tags: [critique, tools, orchestrator]
status: implemented
review: .model-review/2026-06-19-tooling-api-design-8e3ddf/
---

# Critique → ship

**Cross2 review:** 42 findings. Key accepts incorporated in implementation.

## Accepted from critique

| Finding | Fix shipped |
|---------|-------------|
| Fake GREEN in suggest-only | `gate_status: SKIPPED`; JSON notes UNKNOWN contagious |
| No baseline → always trigger | No trigger without baseline unless `--allow-no-baseline` |
| scout-triage ignores fix-backlog | `audit-findings-consolidation` parses P0 table rows |
| commit-plan artifacts pollution | `is_excluded_path()` + artifact prefixes |
| Placeholder apply | Refuse apply if message contains `<one-line` |
| HEAD drift on apply | Plan stamps `head_sha`; apply compares |
| `--no-llm` + `ORCHESTRATOR_TOOLS_NO_LLM` | `tool_contract.py` |
| Legacy alias confusion | Deprecation stderr + just aliases 30d |
| kebab vs snake | just kebab / script snake documented |
| integrate-rank LLM on cron | `sensor-integration-ranking` default deterministic; `--synthesis` opt-in |

## Partial / deferred

- Process-level network deny for deterministic tools — document-only for now
- Markdown AST parser — regex + parse error accounting v1
- fix-prep, review-queue — P2

## Canonical API

See `.claude/rules/orchestrator-tool-names.md`

## Verify

```bash
just operator-status-briefing --repo ~/Projects/genomics
just audit-findings-consolidation ~/Projects/genomics/docs/audit --repo ~/Projects/genomics
just baseline-since-last-green --repo ~/Projects/genomics --suggest-only
uv run python3 scripts/tests/test_orchestrator_tools.py
```
