WITH tool_totals AS (
    SELECT
        runs.vendor,
        strftime('%Y-%W', runs.started_at) AS week,
        COUNT(tool_calls.tool_call_id) AS total_tool_calls
    FROM runs
    LEFT JOIN tool_calls ON tool_calls.run_id = runs.run_id
    WHERE (:vendor IS NULL OR runs.vendor = :vendor)
    GROUP BY runs.vendor, strftime('%Y-%W', runs.started_at)
),
permission_events AS (
    SELECT
        runs.vendor,
        strftime('%Y-%W', runs.started_at) AS week,
        SUM(CASE WHEN events.kind = 'permission_requested' THEN 1 ELSE 0 END) AS permission_requests
    FROM runs
    LEFT JOIN events ON events.run_id = runs.run_id
    WHERE (:vendor IS NULL OR runs.vendor = :vendor)
    GROUP BY runs.vendor, strftime('%Y-%W', runs.started_at)
)
SELECT
    tool_totals.vendor,
    tool_totals.week,
    permission_events.permission_requests,
    tool_totals.total_tool_calls,
    CASE
        WHEN tool_totals.total_tool_calls = 0 THEN NULL
        ELSE ROUND(1.0 * permission_events.permission_requests / tool_totals.total_tool_calls, 4)
    END AS supervision_ratio
FROM tool_totals
JOIN permission_events USING (vendor, week)
ORDER BY tool_totals.week DESC, tool_totals.vendor;
