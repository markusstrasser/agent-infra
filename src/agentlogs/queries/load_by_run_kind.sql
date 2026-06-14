-- Tool-call load split by MAIN thread vs SUBAGENT runs, per project.
--
-- Answers "what is loading the main agent?" WITHOUT the lumping bug: every tool call
-- is attributed to v_run_kind, so subagent activity is never counted as main-thread.
-- Use this before proposing any subagent-offload / context-shield / cost work.
--
-- Params (all optional; omit = no filter):
--   vendor   e.g. 'claude'
--   project  e.g. 'genomics'  (sessions.project_slug)
--   since    ISO date lower bound, e.g. '2026-05-24' (sessions.start_ts >=)
SELECT
    s.project_slug,
    k.run_kind,
    tc.tool_name,
    COUNT(*) AS calls,
    SUM(CASE WHEN tc.status = 'error' OR (tc.exit_code IS NOT NULL AND tc.exit_code <> 0)
             THEN 1 ELSE 0 END) AS fails
FROM tool_calls tc
JOIN v_run_kind k ON k.run_id = tc.run_id
JOIN sessions s ON s.session_pk = k.session_pk
WHERE (:vendor IS NULL OR s.vendor = :vendor)
  AND (:project IS NULL OR s.project_slug = :project)
  AND (:since IS NULL OR s.start_ts >= :since)
GROUP BY s.project_slug, k.run_kind, tc.tool_name
ORDER BY s.project_slug, calls DESC;
