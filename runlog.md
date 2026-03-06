# Runlog — Cross-Vendor Local Run Store

`runlog` is the local forensic store for agent runs across Claude Code, Codex CLI, Gemini CLI, and Kimi CLI.

It imports raw local artifacts into a vendor-aware SQLite sidecar at `~/.claude/runlogs.db`. The goal is not a universal chat transcript format. The goal is a durable run/event store that preserves:

- what happened: messages, tool calls, tool results, file touches
- when it happened: ordered events and timestamps
- how it happened: vendor, model route, approval mode, sandbox mode, MCP/tool metadata
- why it matters operationally: supervision events, run lineage, config/provenance

## When To Use It

Use `runlog` when you need:

- cross-vendor session forensics
- tool-use analysis across Claude, Codex, Gemini, and Kimi
- parent/child run lineage
- supervision and permission-rate analysis
- path-level file-touch history
- a stable local store for SQL queries

Do not use `runlog` for the lightweight cockpit view. That remains the job of `agent_receipts.py` and `dashboard.py`.

## Raw Sources

The raw logs stay the source of truth. `runlog` is a derived store.

- Claude: `~/.claude/projects/-Users-*/UUID.jsonl`
- Codex: `~/.codex/sessions/**/*.jsonl`
- Gemini: `~/.gemini/tmp/*/chats/session-*.json`, fallback `logs.json`
- Kimi: `~/.kimi/sessions/**/*.jsonl`, `context*.jsonl`, `wire.jsonl`

## Data Model

Core tables:

- `sources`: one row per discovered raw artifact
- `imports`: one row per import attempt, keyed by source hash + parser version + schema version
- `record_refs`: byte/line provenance back to source records
- `sessions`: long-lived vendor session grouping
- `runs`: canonical analytic run units
- `run_edges`: parent/child or spawn lineage
- `events`: normalized event stream
- `tool_calls`: first-class tool lifecycle projection
- `file_touches`: file-side effects extracted from tool usage
- `run_configs`: model/tool/config snapshots per run

This is intentionally vendor-aware. Normalized fields exist where they are stable across vendors. Vendor-native detail stays in payload JSON.

## CLI

Initialize the DB:

```bash
uv run python3 scripts/runlog.py init-db
```

Import everything:

```bash
uv run python3 scripts/runlog.py import --vendor claude --vendor codex --vendor gemini --vendor kimi
```

Import a single file:

```bash
uv run python3 scripts/runlog.py import --vendor codex --source ~/.codex/sessions/2026/03/05/example.jsonl
```

Re-import even when the source hash is unchanged:

```bash
uv run python3 scripts/runlog.py import --vendor claude --force
```

Show corpus counts:

```bash
uv run python3 scripts/runlog.py stats
```

Run a named SQL query:

```bash
uv run python3 scripts/runlog.py query supervision_ratio_by_vendor_week --format json
```

Use a temporary DB for testing:

```bash
uv run python3 scripts/runlog.py --db /tmp/runlogs.db import --fixtures
```

## Named Queries

Named queries live in `scripts/runlog_queries/`.

- `supervision_ratio_by_vendor_week`
- `permission_denial_rate_by_tool_vendor`
- `tool_failure_rate_by_tool`
- `median_tool_latency_by_tool_vendor`
- `top_error_classes_by_vendor`
- `run_edges_over_time`
- `tool_usage_by_mcp_server`
- `model_route_runs`
- `runs_touching_path`
- `runs_by_config_hash`

Examples:

```bash
uv run python3 scripts/runlog.py query runs_touching_path --param path_like=%schema% --format json
uv run python3 scripts/runlog.py query tool_usage_by_mcp_server --param vendor=codex --format json
uv run python3 scripts/runlog.py query run_edges_over_time --param vendor=claude --format json
```

## Import Semantics

- Imports are idempotent for unchanged sources.
- Import history is preserved in `imports`; latest success is what matters operationally.
- `cleanup_source_data()` is source-scoped, so reparsing one file only replaces rows derived from that file.
- `completeness` marks whether a run is full or partial.
- Gemini fallback imports can be partial when only sparse logs are available.

## Vendor Notes

- Claude: imports main transcripts plus subagent transcripts and infers run edges from `subagents/`.
- Codex: imports `session_meta`, `turn_context`, `response_item`, `event_msg`, and uses `session_meta.source` for subagent lineage when available.
- Kimi: merges context logs and wire logs into one run when they share the same token; approvals come from wire data.
- Gemini: prefers rich `chats/session-*.json` exports and falls back to sparse `logs.json` only when needed.

## Relationship To Other Meta Tools

- `scripts/sessions.py`: Claude-only session index/search. Good for transcript recall.
- `scripts/agent_receipts.py`: receipt normalization for dashboard/cost/status views.
- `scripts/dashboard.py`: operator-facing cockpit summary.
- `scripts/runlog.py`: deep cross-vendor forensic store and query surface.

## Standards Stance

The canonical store is local SQLite, not OpenTelemetry.

OTel / OpenInference is used as a vocabulary source and later export target where useful, but not as the authoritative storage model. The compatibility note is in `research/runlog-otel-compatibility.md`.
