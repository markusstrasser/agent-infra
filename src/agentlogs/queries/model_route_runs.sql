SELECT
    run_id,
    vendor,
    provider_name,
    transport,
    model_requested,
    model_resolved,
    started_at,
    status
FROM runs
WHERE (:vendor IS NULL OR vendor = :vendor)
  AND (:provider_name IS NULL OR provider_name = :provider_name)
  AND (:transport IS NULL OR transport = :transport)
  AND (:model_requested IS NULL OR model_requested = :model_requested)
  AND (:model_resolved IS NULL OR model_resolved = :model_resolved)
ORDER BY started_at DESC;
