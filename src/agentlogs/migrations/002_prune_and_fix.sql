-- agentlogs migration 002 — prune dead columns, fix v_session_commits join.
--
-- /critique close residue cleanup:
--   - Drop sessions columns that no writer populates and no consumer reads.
--     cost_usd would need model-pricing lookup tables; reintroduce only
--     when a consumer actually needs dollars (can compute at query time
--     via a pricing CTE).
--   - subagent_count is kept and populated by _refresh_session_denorm
--     (cheap: count of Agent/Task/spawn_agent tool calls per session).
--   - v_session_commits extended to join on synthetic_session_key as well,
--     so Gemini (path-derived key) sessions surface git attribution once
--     `agentlogs git-import` has run.

-- SQLite supports DROP COLUMN as of 3.35 (macOS ships 3.43+). Safe here.
-- cost_usd requires model-pricing lookup tables to compute from token counts;
-- dropped until a consumer actually needs dollars (can join with a pricing
-- CTE at query time instead of storing).
ALTER TABLE sessions DROP COLUMN cost_usd;
ALTER TABLE sessions DROP COLUMN context_pct;
ALTER TABLE sessions DROP COLUMN lines_added;
ALTER TABLE sessions DROP COLUMN lines_removed;
ALTER TABLE sessions DROP COLUMN harness_hash;

DROP VIEW IF EXISTS v_session_commits;
CREATE VIEW v_session_commits AS
SELECT
    s.vendor_session_id,
    s.synthetic_session_key,
    s.session_uuid,
    s.project_slug,
    gc.hash,
    gc.project,
    gc.authored_at,
    gc.subject,
    gc.scope,
    gc.commit_type,
    gc.files_changed,
    gc.insertions,
    gc.deletions
FROM git_commits gc
JOIN sessions s
  ON  gc.session_id IS NOT NULL
  AND (
        gc.session_id = s.vendor_session_id
     OR gc.session_id = s.synthetic_session_key
  )
ORDER BY gc.authored_at;

PRAGMA user_version = 2;
