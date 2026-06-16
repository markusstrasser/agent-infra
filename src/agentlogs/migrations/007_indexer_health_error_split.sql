-- Split the indexer health error metric so crash-recovery noise stops masquerading
-- as vendor parse failures.
--
-- Problem (2026-06-16): `agentlogs stats` showed codex errors_7d=94, last_index_error
-- TODAY — read as "the codex indexer is broken". Investigation: ALL 94 were
-- error_class='OrphanedRun', sources_failed=0. OrphanedRun is written by
-- reap_orphaned_runs() when a prior run hit the --max-run-seconds SIGALRM hard-deadline
-- (_os._exit(75)) and left its indexer_runs row status='running'; the next startup
-- finalizes it as an error. On a 3.8 GB DB with WatchPaths re-firing every ~60s during
-- an active session, this happens ~15-24x/day and is pure operational crash-recovery,
-- NOT a parse/vendor failure. Counting it in errors_7d trains the reader to ignore the
-- one metric that should flag a real broken adapter.
--
-- Fix: the view now distinguishes:
--   parse_errors_7d  — genuine errors (sources_failed>0 OR a non-OrphanedRun error_class)
--   orphaned_7d      — reaped crash rows (error_class='OrphanedRun')
--   error_7d         — KEPT for back-compat (= parse_errors_7d + orphaned_7d); existing
--                      callers (health.py) read this, but the stats table now surfaces
--                      the split so the codex "94" reads as "0 real + 94 reaped".
DROP VIEW IF EXISTS v_indexer_health;
CREATE VIEW v_indexer_health AS
SELECT
    vendor,
    MAX(started_at) FILTER (WHERE status='success') AS last_success_at,
    MAX(started_at) FILTER (WHERE status='error')   AS last_error_at,
    -- last_error_at restricted to GENUINE errors (the one operators should act on)
    MAX(started_at) FILTER (
        WHERE status='error'
        AND (sources_failed > 0 OR COALESCE(error_class,'') <> 'OrphanedRun')
    ) AS last_parse_error_at,
    COUNT(*) FILTER (WHERE status='success')        AS success_count_total,
    COUNT(*) FILTER (WHERE status='error')          AS error_count_total,
    COUNT(*) FILTER (WHERE status='success'
                     AND started_at > datetime('now', '-7 days')) AS success_7d,
    COUNT(*) FILTER (WHERE status='error'
                     AND started_at > datetime('now', '-7 days')) AS error_7d,
    -- genuine parse/vendor failures in the last 7d
    COUNT(*) FILTER (
        WHERE status='error'
        AND started_at > datetime('now', '-7 days')
        AND (sources_failed > 0 OR COALESCE(error_class,'') <> 'OrphanedRun')
    ) AS parse_errors_7d,
    -- reaped crash rows (operational noise, not a broken adapter)
    COUNT(*) FILTER (
        WHERE status='error'
        AND started_at > datetime('now', '-7 days')
        AND COALESCE(error_class,'') = 'OrphanedRun'
        AND sources_failed = 0
    ) AS orphaned_7d
FROM indexer_runs
WHERE vendor IS NOT NULL
GROUP BY vendor;

PRAGMA user_version = 7;
