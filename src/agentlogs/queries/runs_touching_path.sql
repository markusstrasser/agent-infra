SELECT
    file_touches.path,
    file_touches.op,
    runs.run_id,
    runs.vendor,
    runs.started_at,
    tool_calls.tool_name
FROM file_touches
JOIN runs ON runs.run_id = file_touches.run_id
LEFT JOIN tool_calls ON tool_calls.tool_call_id = file_touches.tool_call_id
WHERE (:path IS NULL OR file_touches.path = :path)
  AND (:path_like IS NULL OR file_touches.path LIKE :path_like)
  AND (:vendor IS NULL OR runs.vendor = :vendor)
ORDER BY runs.started_at DESC, file_touches.path;
