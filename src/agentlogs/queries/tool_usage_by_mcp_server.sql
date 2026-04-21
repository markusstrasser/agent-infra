SELECT
    COALESCE(tool_calls.mcp_server, 'non_mcp') AS mcp_server,
    runs.vendor,
    tool_calls.tool_name,
    COUNT(*) AS call_count
FROM tool_calls
JOIN runs ON runs.run_id = tool_calls.run_id
WHERE (:vendor IS NULL OR runs.vendor = :vendor)
GROUP BY COALESCE(tool_calls.mcp_server, 'non_mcp'), runs.vendor, tool_calls.tool_name
ORDER BY call_count DESC, mcp_server, tool_calls.tool_name;
