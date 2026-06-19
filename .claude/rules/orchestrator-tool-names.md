# Orchestrator-model tooling — canonical names + LLM contracts

Multi-syllable names. **Just recipes = kebab-case.** **Scripts = snake_case.**

| LLM | Recipe | layer | role |
|-----|--------|-------|------|
| **none** | `operator-status-briefing` | session | operator-tool |
| **none** | `baseline-since-last-green` | session | orchestrator-tool |
| **none** | `audit-findings-consolidation` | session | orchestrator-tool |
| **none** | `commit-slice-planning` | session | orchestrator-tool |
| **optional** | `commit-slice-planning` | session | orchestrator-tool |
| **none** | `verification-gate-runner` | session | orchestrator-tool |
| **none** | `session-automation-telemetry` | infra | orchestrator-tool |
| **optional** | `sensor-integration-ranking` | infra | orchestrator-tool |
| **required** | `adversarial-debug-scout` | session | orchestrator-tool |
| **none** | `rsi-loop-funnel` | gov | orchestrator-tool |

Every run prints `llm: none|optional|required` on stderr. Vocabulary: `config/system-kinds.json`.

## Gate status contract (baseline + verification-gate-runner)

`GREEN` | `RED` | `UNKNOWN` | `SKIPPED` — autonomous paths treat UNKNOWN like RED.

## Roles

- **Operator** → `operator-status-briefing`
- **Orchestrator model** → baseline, consolidation, commit-slice-planning, adversarial-debug-scout, verification-gate-runner
- **Infra / launchd** → sensor-integration-ranking (no `--synthesis`), rsi-loop-funnel

Legacy aliases until 2026-07-19: `audit-delta`, `commit-plan`, `scout-triage`, `debug`, `integrate-rank`, …
