SELECT
    run_edges.edge_type,
    runs.vendor,
    strftime('%Y-%W', runs.started_at) AS week,
    COUNT(*) AS edge_count
FROM run_edges
JOIN runs ON runs.run_id = run_edges.dst_run_id
WHERE (:vendor IS NULL OR runs.vendor = :vendor)
GROUP BY run_edges.edge_type, runs.vendor, strftime('%Y-%W', runs.started_at)
ORDER BY week DESC, runs.vendor, run_edges.edge_type;
