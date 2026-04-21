WITH latencies AS (
    SELECT
        runs.vendor,
        tool_calls.tool_name,
        (julianday(tool_calls.ts_end) - julianday(tool_calls.ts_start)) * 86400.0 AS latency_seconds
    FROM tool_calls
    JOIN runs ON runs.run_id = tool_calls.run_id
    WHERE tool_calls.ts_start IS NOT NULL
      AND tool_calls.ts_end IS NOT NULL
      AND (:vendor IS NULL OR runs.vendor = :vendor)
      AND (:tool_name IS NULL OR tool_calls.tool_name = :tool_name)
),
ranked AS (
    SELECT
        vendor,
        tool_name,
        latency_seconds,
        ROW_NUMBER() OVER (PARTITION BY vendor, tool_name ORDER BY latency_seconds) AS rn,
        COUNT(*) OVER (PARTITION BY vendor, tool_name) AS cnt
    FROM latencies
)
SELECT
    vendor,
    tool_name,
    ROUND(AVG(latency_seconds), 4) AS median_latency_seconds,
    COUNT(*) AS contributing_rows
FROM ranked
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
GROUP BY vendor, tool_name
ORDER BY median_latency_seconds DESC, tool_name;
