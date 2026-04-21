SELECT
    tool_calls.tool_name,
    runs.vendor,
    SUM(CASE WHEN tool_calls.status = 'error' OR tool_calls.exit_code IS NOT NULL AND tool_calls.exit_code <> 0 THEN 1 ELSE 0 END) AS failed_calls,
    COUNT(*) AS total_calls,
    ROUND(
        1.0 * SUM(CASE WHEN tool_calls.status = 'error' OR tool_calls.exit_code IS NOT NULL AND tool_calls.exit_code <> 0 THEN 1 ELSE 0 END)
        / COUNT(*),
        4
    ) AS failure_rate
FROM tool_calls
JOIN runs ON runs.run_id = tool_calls.run_id
WHERE (:vendor IS NULL OR runs.vendor = :vendor)
  AND (:tool_name IS NULL OR tool_calls.tool_name = :tool_name)
GROUP BY tool_calls.tool_name, runs.vendor
ORDER BY failure_rate DESC, failed_calls DESC, tool_calls.tool_name;
