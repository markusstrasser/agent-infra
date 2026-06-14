-- Run lineage as a queryable per-run column.
--
-- The "is this run the main thread or a subagent dispatch?" signal already exists
-- in run_edges (edge_type='spawned_by': dst_run_id = the subagent, src_run_id = its
-- parent), but there was no queryable per-run surface for it. Consequence (2026-06-14):
-- a load analysis joined tool_calls -> runs -> sessions and SILENTLY lumped subagent
-- tool calls in with the main thread, overstating main-thread load until re-segmented
-- by hand. This view makes the split a one-join primitive so no future analysis repeats it.
--
-- run_kind = 'subagent' iff the run is the dst of a 'spawned_by' edge; else 'main'.
-- parent_run_id = the spawning run (NULL for main-thread runs).
DROP VIEW IF EXISTS v_run_kind;
CREATE VIEW v_run_kind AS
SELECT
    r.run_id,
    r.session_pk,
    r.vendor,
    CASE WHEN p.parent_run_id IS NOT NULL THEN 'subagent' ELSE 'main' END AS run_kind,
    p.parent_run_id
FROM runs r
LEFT JOIN (
    -- one parent per run (MIN is deterministic if both inference methods ever
    -- emit an edge for the same dst; currently 1:1)
    SELECT dst_run_id, MIN(src_run_id) AS parent_run_id
    FROM run_edges
    WHERE edge_type = 'spawned_by'
    GROUP BY dst_run_id
) p ON p.dst_run_id = r.run_id;

PRAGMA user_version = 6;
