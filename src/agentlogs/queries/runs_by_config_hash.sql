SELECT
    run_id,
    vendor,
    started_at,
    instruction_hash,
    config_hash,
    mcp_set_hash,
    model_requested,
    model_resolved
FROM runs
WHERE (:vendor IS NULL OR vendor = :vendor)
  AND (:instruction_hash IS NULL OR instruction_hash = :instruction_hash)
  AND (:config_hash IS NULL OR config_hash = :config_hash)
  AND (:mcp_set_hash IS NULL OR mcp_set_hash = :mcp_set_hash)
ORDER BY started_at DESC;
