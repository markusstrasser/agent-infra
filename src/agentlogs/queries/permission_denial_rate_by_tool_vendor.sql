WITH tool_base AS (
    SELECT
        runs.vendor,
        tool_calls.tool_name,
        COUNT(*) AS total_calls
    FROM tool_calls
    JOIN runs ON runs.run_id = tool_calls.run_id
    WHERE (:vendor IS NULL OR runs.vendor = :vendor)
      AND (:tool_name IS NULL OR tool_calls.tool_name = :tool_name)
    GROUP BY runs.vendor, tool_calls.tool_name
),
denials AS (
    SELECT
        runs.vendor,
        tool_calls.tool_name,
        COUNT(*) AS denied_calls
    FROM tool_calls
    JOIN runs ON runs.run_id = tool_calls.run_id
    JOIN events ON events.tool_call_id = tool_calls.tool_call_id
    WHERE events.kind = 'permission_denied'
      AND (:vendor IS NULL OR runs.vendor = :vendor)
      AND (:tool_name IS NULL OR tool_calls.tool_name = :tool_name)
    GROUP BY runs.vendor, tool_calls.tool_name
)
SELECT
    tool_base.vendor,
    tool_base.tool_name,
    COALESCE(denials.denied_calls, 0) AS denied_calls,
    tool_base.total_calls,
    CASE
        WHEN tool_base.total_calls = 0 THEN NULL
        ELSE ROUND(1.0 * COALESCE(denials.denied_calls, 0) / tool_base.total_calls, 4)
    END AS denial_rate
FROM tool_base
LEFT JOIN denials USING (vendor, tool_name)
ORDER BY denial_rate DESC, denied_calls DESC, tool_base.tool_name;
