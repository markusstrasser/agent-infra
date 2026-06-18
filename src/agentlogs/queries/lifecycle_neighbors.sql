-- RSI-lifecycle neighborhood of :node — every edge where :node is the subject or
-- target. `direction` shows which side :node sits on (out = :node->other along the
-- canonical relation; in = other->:node). `traversable` is 0 for relates_to /
-- provenance / vocab-gap edges (association only, excluded from bundling), 1 for
-- lifecycle edges. `dangling`=1 means `other` resolves to no known node.
-- Ordered traversable-first (lifecycle edges before weak), then by type/other.
SELECT
    lifecycle_edges.type        AS type,
    CASE WHEN lifecycle_edges.subject = :node THEN 'out' ELSE 'in' END AS direction,
    CASE WHEN lifecycle_edges.subject = :node
         THEN lifecycle_edges.target ELSE lifecycle_edges.subject END  AS other,
    lifecycle_edges.traversable AS traversable,
    lifecycle_edges.dangling    AS dangling,
    lifecycle_edges.raw_type    AS raw_type,
    lifecycle_edges.source      AS source
FROM lifecycle_edges
WHERE lifecycle_edges.subject = :node
   OR lifecycle_edges.target = :node
ORDER BY lifecycle_edges.traversable DESC, lifecycle_edges.type, other;
