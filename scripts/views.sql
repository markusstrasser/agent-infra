-- Orchestrator convenience views
-- Apply: sqlite3 ~/.claude/orchestrator.db < scripts/views.sql
-- Test:  just db-smoke

-- Tasks running >30 min (potential stalls)
CREATE VIEW IF NOT EXISTS v_stalled AS
SELECT id, pipeline, project, prompt, started_at,
       ROUND((julianday('now','localtime') - julianday(started_at)) * 1440, 1) AS minutes_running
FROM tasks WHERE status = 'running'
  AND julianday('now','localtime') - julianday(started_at) > 0.0208;

-- Today's cost and status by pipeline
CREATE VIEW IF NOT EXISTS v_daily_cost AS
SELECT pipeline, COUNT(*) AS tasks,
       ROUND(SUM(COALESCE(cost_usd, 0)), 2) AS cost,
       SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done,
       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
FROM tasks WHERE DATE(created_at) = DATE('now', 'localtime')
GROUP BY pipeline;

-- Recent failures
CREATE VIEW IF NOT EXISTS v_failures AS
SELECT id, pipeline, project, error, finished_at
FROM tasks WHERE status IN ('failed', 'done_with_denials')
ORDER BY finished_at DESC LIMIT 20;

-- Pipeline health summary (all time)
CREATE VIEW IF NOT EXISTS v_pipeline_health AS
SELECT pipeline,
       COUNT(*) AS total,
       ROUND(AVG(CASE WHEN status = 'done' THEN 1.0 ELSE 0.0 END) * 100, 0) AS success_pct,
       ROUND(AVG(COALESCE(cost_usd, 0)), 2) AS avg_cost,
       MAX(finished_at) AS last_run
FROM tasks GROUP BY pipeline;

-- Queue status counts
CREATE VIEW IF NOT EXISTS v_queue AS
SELECT status, COUNT(*) AS n FROM tasks GROUP BY status;

-- Actionable proposals: failed tasks, pending approvals, stalled runs
CREATE VIEW IF NOT EXISTS v_proposals AS
SELECT 'failed_task' AS type, id AS ref,
       pipeline || ': ' || SUBSTR(COALESCE(error, '(no error)'), 1, 80) AS detail
FROM tasks WHERE status = 'failed'
  AND DATE(finished_at) > DATE('now', '-3 days', 'localtime')
UNION ALL
SELECT 'needs_approval', id,
       pipeline || COALESCE(' step ' || step, '')
FROM tasks WHERE status = 'paused' AND requires_approval = 1
UNION ALL
SELECT 'stalled', id,
       pipeline || ' running ' || CAST(ROUND((julianday('now','localtime') - julianday(started_at)) * 1440) AS INT) || 'min'
FROM tasks WHERE status = 'running'
  AND julianday('now','localtime') - julianday(started_at) > 0.0208;
