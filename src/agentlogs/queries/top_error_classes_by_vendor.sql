SELECT
    runs.vendor,
    COALESCE(events.vendor_kind, 'unknown') AS error_class,
    COUNT(*) AS error_count
FROM events
JOIN runs ON runs.run_id = events.run_id
WHERE events.kind = 'error'
  AND (:vendor IS NULL OR runs.vendor = :vendor)
GROUP BY runs.vendor, COALESCE(events.vendor_kind, 'unknown')
ORDER BY error_count DESC, runs.vendor, error_class;
