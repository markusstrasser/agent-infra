-- Vendor / project session throughput over a rolling window (stop raw sqlite reinvent).
-- Params: :days
SELECT
    s.vendor,
    COALESCE(s.project_slug, '(none)') AS project_slug,
    COUNT(DISTINCT s.session_pk) AS sessions,
    COUNT(tc.tool_call_id) AS tool_calls,
    ROUND(AVG(COALESCE(s.duration_min, 0)), 1) AS avg_duration_min
FROM sessions s
LEFT JOIN runs r ON r.session_pk = s.session_pk
LEFT JOIN tool_calls tc ON tc.run_id = r.run_id
WHERE s.start_ts >= datetime('now', printf('-%d days', CAST(:days AS INTEGER)))
GROUP BY s.vendor, COALESCE(s.project_slug, '(none)')
ORDER BY sessions DESC, s.vendor, project_slug;
