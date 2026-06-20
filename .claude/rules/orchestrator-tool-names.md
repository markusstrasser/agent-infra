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

## When to fire (orchestrator-model decides — NOT a hook)

These are central hub recipes that take a repo as an **argument** — they run on any
repo regardless of its local justfile. The orchestrator model reaches for them by
judgment; deciding "is this a major-enough plan finish?" is a semantic call, so it is
NOT auto-fired by a hook. Cursor scouts are cheap — fan out freely.

| Trigger the orchestrator watches for | Reach for | Dispatch |
|---|---|---|
| Major plan / `/decide` / refactor just landed | `adversarial-debug-scout <repo>` then `audit-findings-consolidation` | **background**: `just -f ~/Projects/agent-infra/justfile adversarial-debug-scout <repo> recent &` → triage `docs/audit/` later |
| Pre-commit / pre-ship gate | `verification-gate-runner <repo>` | foreground (fast) |
| "what changed since green?" | `baseline-since-last-green <repo>` | foreground |

Fire-and-forget convention: append `&` (or `run_in_background`) for scout/loop recipes
(~minutes); they write to `<repo>/docs/audit/` and the orchestrator triages on return.

## Gate status contract (baseline + verification-gate-runner)

`GREEN` | `RED` | `UNKNOWN` | `SKIPPED` — autonomous paths treat UNKNOWN like RED.

## Roles

- **Operator** → `operator-status-briefing`
- **Orchestrator model** → baseline, consolidation, commit-slice-planning, adversarial-debug-scout, verification-gate-runner
- **Infra / launchd** → sensor-integration-ranking (no `--synthesis`), rsi-loop-funnel

Legacy aliases until 2026-07-19: `audit-delta`, `commit-plan`, `scout-triage`, `debug`, `integrate-rank`, …
