---
date: 2026-04-20
title: Unified agent logs — agentlogs replaces sessions.py + runlog.py
status: implemented
concept: session-telemetry
affects: [agent-infra, skills/observe, skills/hooks]
---

# Unified agent logs — agentlogs replaces sessions.py + runlog.py

## Context

Two parallel local stores of session telemetry grew in isolation:

- `~/.claude/sessions.db` (16 MB, 1,110 Claude sessions) — FTS5 on aggregated transcript text, indexed by `scripts/sessions.py` (1,266 lines).
- `~/.claude/runlogs.db` (4.3 GB, 917 Codex runs / 579K events / 111K tool_calls) — structured `events`/`tool_calls`/`git_commits` tables and 16 named analytical queries, indexed by `scripts/runlog.py` (916 lines). The schema had a `vendor` column but only Codex was ever ingested despite adapters for Claude and Gemini existing.

Consequence: cross-vendor analytics (e.g. `tool_failure_rate` per vendor, Claude vs Codex supervision ratios) required ad-hoc transcript extraction. `/observe` sessions skill was shipping 1–3 MB of raw transcripts to Gemini every run because the DB couldn't answer questions the schema was designed for. No session-level FTS on Codex; no structured analytics on Claude.

## Decision

Replace both with a single `agentlogs` package (`src/agentlogs/`) backed by one database `~/.claude/agentlogs.db` and one CLI binary (`agentlogs`).

### What it is

- **One schema** (PRAGMA user_version versioned, migrations in `src/agentlogs/migrations/`). Ports runlogs schema with Phase 0 refinements: no `content_text` denorm on sessions (FTS5 external-content over `events.text`), no `tool_calls.result_json` column (duplicated by `tool_result` events), token counts promoted from `events.payload_json` JSON-extract into structured columns on `runs`, `import_id` FK on events/tool_calls/file_touches so parser-version re-imports can scoped-delete instead of colliding.
- **One CLI** — `agentlogs` (installed as a pyproject console_script). Subcommands: `index`, `search`, `show`, `recent`, `query`, `stats`, `dispatch`.
- **One Python library** — `from agentlogs import connect, search_sessions, get_session, run_query`. Consumed by `agent_infra_mcp.py`, `observe/session-shape.py`, and any future tooling.
- **Launchd WatchPaths** indexer — event-driven rather than polling. Watches `~/.claude/projects/`, `~/.codex/sessions/`, `~/.gemini/tmp/` with 60s throttle + 2h safety interval. Near-real-time freshness, no idle polling cycles.
- **Daily backup plist** — `sqlite3 .backup` at 04:00 with 14-day rolling retention.
- **fcntl single-writer lock** on `~/.claude/agentlogs.db.indexlock` — serializes launchd + manual indexer invocations.

### What got deleted

- `scripts/sessions.py` (1,266 lines)
- `scripts/runlog.py` (916 lines)
- `scripts/runlog_adapters/` (ported into `src/agentlogs/adapters/`)
- `scripts/runlog_queries/` (ported into `src/agentlogs/queries/`)
- `tests/test_runlog.py`
- `SESSIONS_DB` + `RUNLOGS_DB` constants from `scripts/common/paths.py`

### What got archived

- `~/.claude/sessions.db` → `~/.claude/archive/sessions_pre_unification.db` (small, kept)
- `~/.claude/runlogs.db` → initially moved to archive then **deleted** once the agentlogs ingest was confirmed building from the raw JSONLs (the old DB was a parsed cache of files that remain on disk). This differs from the plan's "30-day retention" — the raw sources are the durability guarantee.

## Alternatives considered (pre-decision divergence)

1. **Unified DB + unified CLI** (chosen). Max coherence; full migration.
2. Unified DB, two CLIs kept. Rejected — preserves the semantic split that is the actual pain.
3. Two DBs, federated query layer. Rejected — adds a third thing to maintain; doesn't fix schema drift.
4. Move everything into `sessions.db` (FTS-first), lose structured tables or re-encode as JSON. Rejected — abandons 16 analytical queries.
5. DuckDB / Parquet + FTS sidecar. Rejected at current scale (<20 GB). Revisit if DB > 50 GB.

## Cross-model review

Cross-model review (Gemini 3.1 Pro arch + GPT-5.4 formal) returned 18 findings. 16 cosigned and applied before execution:

- Don't store transcript text on `sessions` table (FTS5 external-content is the right shape).
- FTS5 maintained by triggers, not periodic rebuild.
- Archive old DBs, don't immediate-delete (later relaxed once raw-JSONL durability was confirmed).
- Concurrency: fcntl lock + 30s busy_timeout + explicit pragmas.
- Indexer health surface via `indexer_runs` table + `v_indexer_health` view + `agentlogs stats`.
- Import lineage: `import_id` FK on materialized facts.
- `PRAGMA user_version` + numbered migrations.
- `session_uuid` as canonical cross-vendor key.
- Drop `tool_calls.result_json` (Phase 0 refinement).

Disposition: `.model-review/2026-04-20-unified-agent-logs-plan-a08692/disposition.md`.

## Rejected

- Compatibility shims of any kind. No symlinks pointing agentlogs.db at the old paths, no `SESSIONS_DB = RUNLOGS_DB = AGENTLOGS_DB` aliasing in common.paths, no "temporary" dual-reads. Called sites were migrated in the same commits that dropped the old symbols.
- Gemini reviewer's extension of "drop content_text" to also drop `first_message`. Rejected: conflates transcript-text bloat (content_text) with a 200-char list-view denorm (first_message). Different classes of field.
- Kimi adapter. `codebase-map.md` referenced `scripts/runlog_adapters/kimi.py` but the file did not exist on disk. Dropped from scope — can be added later if needed.
- Keeping the archived 4.3 GB `runlogs_pre_unification.db` for 30 days. Deleted once the launchd indexer was running and raw JSONL source files were confirmed intact.

## Evidence

- Plan: `.claude/plans/8799d138-unified-agent-logs.md` (rev 2, post cross-model review)
- Phase 0 adapter fitness report: `artifacts/agentlogs-phase0.md`
- Model review artifacts: `.model-review/2026-04-20-unified-agent-logs-plan-a08692/`
- Test suite: `tests/agentlogs/test_schema.py` (9) + `tests/agentlogs/test_cli.py` (9). 18 tests, all passing.
- Commits: `6d0ec6e`, `3853dd8` (Phase 3a/b); this commit (Phase 4).
