-- Operator vs subagent session split as a queryable column.
--
-- "Is this an operator (top-level interactive) session or a subagent dispatch
-- (Task/Agent tool spawn)?" is cleanly derivable from existing raw data but had no
-- session-level surface, so `agentlogs recent`/stats lumped them together — a load
-- or supervision analysis silently counted subagent sessions as operator sessions.
--
-- Two independent markers already in the DB (verified 2026-06-16):
--   1. claude: the adapter sets run_configs.metadata_json.is_subagent from the raw
--      transcript path (agent-*.jsonl / subagents/ dir == isSidechain:true; 2743
--      such transcripts on disk). 2135 claude runs flagged -> 629 sessions.
--   2. codex/all: run_edges(edge_type='spawned_by') — the dst run is a spawned
--      subagent thread (codex thread_spawn). v_run_kind already exposes this per-run.
--
-- This migration adds sessions.is_subagent (default 0 = operator) and backfills from
-- BOTH markers (a session is a subagent if ANY of its runs is flagged by either).
-- Going forward the indexer populates it at write time (SessionRow.is_subagent +
-- sticky-true on re-import). Additive + idempotent: ADD COLUMN, UPDATE, CREATE VIEW.

ALTER TABLE sessions ADD COLUMN is_subagent INTEGER NOT NULL DEFAULT 0;

-- Backfill marker 1: claude path-based flag in run_configs.metadata_json.
UPDATE sessions SET is_subagent = 1
WHERE session_pk IN (
    SELECT DISTINCT r.session_pk
    FROM runs r JOIN run_configs rc ON rc.run_id = r.run_id
    WHERE json_extract(rc.metadata_json, '$.is_subagent') = 1
);

-- Backfill marker 2: any vendor — the session owns a run that is the dst of a
-- 'spawned_by' edge (codex thread_spawn, claude path-inferred subagent edges).
UPDATE sessions SET is_subagent = 1
WHERE session_pk IN (
    SELECT DISTINCT r.session_pk
    FROM runs r JOIN run_edges e ON e.dst_run_id = r.run_id
    WHERE e.edge_type = 'spawned_by'
);

CREATE INDEX IF NOT EXISTS idx_sessions_is_subagent ON sessions(is_subagent, vendor);

-- Convenience view: operator vs subagent as a labelled role for `recent`/stats.
DROP VIEW IF EXISTS v_session_role;
CREATE VIEW v_session_role AS
SELECT
    session_pk,
    vendor,
    client,
    vendor_session_id,
    session_uuid,
    project_slug,
    start_ts,
    CASE WHEN is_subagent = 1 THEN 'subagent' ELSE 'operator' END AS session_role
FROM sessions;

PRAGMA user_version = 8;
