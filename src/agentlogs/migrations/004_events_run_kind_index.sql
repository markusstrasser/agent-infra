-- agentlogs migration 004 — composite (run_id, kind, seq) index on events.
--
-- _refresh_session_denorm's first_message subquery —
--   SELECT … FROM events e JOIN runs r ON r.run_id = e.run_id
--   WHERE r.session_pk = ? AND e.kind = 'user_message'
--   ORDER BY r.started_at, e.seq LIMIT 1
-- had no index supporting the (run_id, kind) seek, so the planner drove from
-- idx_events_kind and SCANNED every kind='user_message' event in the table
-- (45,995 rows / a TEMP B-TREE sort) for EVERY session's denorm. On the 2.76M-row
-- / 11GB store this cost ~3.2s per source (74% of _write_parsed) and was the real
-- root of both the slow backfill and the original multi-hour indexer "hang"
-- (the FTS triggers were only an amplifier). Profiled session 4d40085a:
-- _write_parsed 5.36s → 0.94s, _refresh_session_denorm 3.22s → 0.002s.
--
-- ANALYZE is required: without table stats the planner over-trusts idx_events_kind
-- and ignores the new index even after it exists.

CREATE INDEX IF NOT EXISTS idx_events_run_kind ON events(run_id, kind, seq);

ANALYZE events;
ANALYZE runs;

PRAGMA user_version = 4;
