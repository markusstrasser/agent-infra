-- agentlogs migration 011 — sessions.session_role replaces sessions.is_subagent.
--
-- is_subagent (008) was the only operator/non-operator surface, and consumers read
-- is_subagent = 0 as "the operator's session". Measured 2026-09-27 over 4,183 sessions,
-- it was wrong both ways:
--   * scripted runs passed as operator sessions: 1,138 `codex exec` and 602 Codex
--     subagent threads (the codex adapter never set the flag), 624 of 653 Cursor
--     sessions (`cursor-agent -p`), and 762 of the 819 Claude sessions whose transcript
--     is still on disk (`claude -p`: launchd watch and portfolio ticks, reviewers);
--   * every Claude operator session that used the Agent tool was flagged a subagent
--     (65 of 65): a transcript under <session>/subagents/ carries its parent's session
--     id, and the sticky-true upsert flipped the parent.
--
-- session_role: 'operator' (a person typed the first prompt), 'dispatch' (a program
-- did), 'subagent' (an agent spawned the session), NULL (no origin evidence). Adapters
-- set it from each vendor's own stamp. This migration keeps only what is_subagent got
-- right: sessions that have no main run of their own (Codex, Kimi and Gemini subagent
-- threads, legacy top-level Claude agent-*.jsonl transcripts). Everything else starts
-- NULL; `agentlogs session-roles --yes` fills it from the adapters' own rules, and rows
-- whose raw files are gone stay NULL (undetermined, never guessed as operator).

ALTER TABLE sessions ADD COLUMN session_role TEXT
    CHECK (session_role IN ('operator', 'dispatch', 'subagent'));

UPDATE sessions SET session_role = 'subagent'
WHERE is_subagent = 1
  AND (vendor != 'claude' OR vendor_session_id LIKE 'agent-%');

-- Operator exports now drop a subagent run inside an operator session by its
-- spawned_by edge, and the indexer lost the edge when a Claude subagent transcript
-- was imported before its parent (1 of 815 on 2026-09-27; the adapter now emits it
-- from both sides). Restore the missing ones: any other run in a Claude session
-- belongs to a transcript under that session's subagents/ directory.
INSERT OR IGNORE INTO run_edges (src_run_id, dst_run_id, edge_type, inference_method, confidence)
SELECT 'claude:' || s.vendor_session_id, r.run_id, 'spawned_by', 'subagent_path', 0.75
FROM runs r JOIN sessions s ON s.session_pk = r.session_pk
WHERE r.vendor = 'claude'
  AND r.run_id != 'claude:' || s.vendor_session_id
  AND EXISTS (SELECT 1 FROM runs p WHERE p.run_id = 'claude:' || s.vendor_session_id)
  AND NOT EXISTS (SELECT 1 FROM run_edges e
                  WHERE e.dst_run_id = r.run_id AND e.edge_type = 'spawned_by');

DROP VIEW IF EXISTS v_session_role;
DROP INDEX IF EXISTS idx_sessions_is_subagent;
ALTER TABLE sessions DROP COLUMN is_subagent;
CREATE INDEX IF NOT EXISTS idx_sessions_role ON sessions(session_role, vendor);

PRAGMA user_version = 11;
