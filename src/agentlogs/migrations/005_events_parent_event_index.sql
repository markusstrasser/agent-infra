-- agentlogs migration 005 — index the self-referential FK events.parent_event_id.
--
-- The events UPSERT's UPDATE branch reassigns event_id (the parent key of
-- parent_event_id REFERENCES events(event_id)). With PRAGMA foreign_keys=ON
-- and NO index on the child column, every such UPDATE makes SQLite verify the
-- old key is unreferenced via a FULL SCAN of events (567K rows / 2.9 GB).
-- Active sessions re-import on every WatchPaths fire, each prior event takes
-- the conflict-UPDATE path, so one 311-event source cost >10 min of pure
-- sqlite3BtreeNext (sampled 2026-06-12, probe killed at 10 min) — blowing the
-- 180s _SourceWatchdog budget every run since ~06-10 and keeping
-- com.agent-infra.agentlogs-index permanently red ("OperationalError:
-- interrupted", same sources retried each fire).
--
-- Indexing the FK child column turns the parent-key check into a point lookup.

CREATE INDEX IF NOT EXISTS idx_events_parent_event ON events(parent_event_id);

ANALYZE events;

PRAGMA user_version = 5;
