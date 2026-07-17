-- Exploratory low-use tool screen (NOT a delete recommendation list).
-- Call-count alone conflates new/rare/unused — rank by session spread first.
-- Params: days, max_calls, limit (just tool-trim-audit supplies defaults).
SELECT
    tool_calls.tool_name,
    COUNT(*) AS calls,
    COUNT(DISTINCT tool_calls.run_id) AS distinct_runs,
    COUNT(DISTINCT runs.session_pk) AS distinct_sessions
FROM tool_calls
JOIN runs ON runs.run_id = tool_calls.run_id
WHERE tool_calls.ts_start IS NOT NULL
  AND julianday('now') - julianday(tool_calls.ts_start) <= CAST(:days AS REAL)
GROUP BY tool_calls.tool_name
HAVING calls < CAST(:max_calls AS INTEGER)
ORDER BY distinct_sessions ASC, calls ASC, tool_calls.tool_name
LIMIT CAST(:limit AS INTEGER);
