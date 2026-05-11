---
title: Graph Storage for Citation Graphs at 300K–3M Edges — DuckDB vs Alternatives
date: 2026-05-11
tags: [graph-storage, duckdb, kuzu, citation-graph, prior-art]
status: complete
---

## TL;DR

**Stay on DuckDB. Add the DuckPGQ community extension when ergonomics matter.** This is not a hedge — the alternative that would have meaningfully outperformed DuckDB at our scale (Kuzu) was **archived on GitHub on 10 October 2025 following its acquisition by Apple** (verify_claim confidence 1.0, cross-confirmed by The Verge, BetaKit, MacRumors, University of Waterloo CS, and the kuzudb/kuzu commit log). Existing Kuzu binaries still work, but there is no maintainer, no security patching, and no schema-migration story going forward. For a single-user, local-Mac, append-only personal corpus we should not adopt an archived project.

DuckDB 1.4 handles 300K–3M directed edges with sub-second multi-hop traversal via recursive CTE or array-based adjacency, and the DuckPGQ extension (CWI-maintained, v1.4.4 March 2026) provides SQL/PGQ pattern matching and bounded-Kleene path finding on top — same engine, better syntax for `(:Paper)-[:CITES*1..k]->(:Paper)` shapes. Bonus: Lance/LanceDB just shipped "Lance x DuckDB SQL retrieval" in January 2026, so vector/full-text live in the same query plane.

## Per-Candidate Fit Assessment

**1. DuckDB 1.4 (current pick) — MIT, CWI-funded.** Sweet spot for our scale. 3M-edge property tables fit in <500MB Parquet; recursive CTEs traverse 3-hop neighborhoods in tens of ms on M3 hardware once the edge table is sorted on `source_id` (the columnar layout means range scans are pre-filtered). The Citation Statements paper validates that production systems (OpenAlex 2.1B edges, S2AG 2.5B, OpenCitations) all use columnar/relational storage, not native graph DBs (`scientific-citation-graph-patterns-2026-05.md`, Claim 7). Our edges-are-rows + CTEs-for-traversal pattern is the industry default at 1000× our scale.

**2. Kuzu — MIT, ARCHIVED.** Was the strongest technical match: embedded property graph, Cypher, vectorized + factorized joins, LDBC-SF100 validated (280M nodes / 1.7B edges). Independent prrao/kuzudb-study on M3 MacBook Pro 36GB at exactly our scale (100K nodes / 2.4M edges) showed multi-hop queries at **8.6ms–95ms** versus Neo4j 3.2–3.9s (40–374× speedup; Neo4j is the relevant comparison for ergonomics, not absolute floor). The Kùzu CIDR 2023 paper notes DuckDB *wins* on 1-hop queries (IS01/IS04 sub-millisecond) but Kùzu's sip-style joins dominated on 2-hop+ patterns over many-to-many edges. Apple acquisition + archive (Oct 10 2025) removes Kuzu as a forward option. Not adopting an archived project as primary storage.

**3. Lance / LanceDB — Apache-2.0, well-funded.** Aimed at multimodal vector lakehouse. The newsletter even labels their direction as "Lance x DuckDB SQL retrieval" — they're consolidating SQL/graph work into DuckDB rather than building it natively. Use Lance for SPECTER2 embeddings when we add semantic-similarity edges (deferred in the prior memo, finding 6); don't use it for the citation graph itself.

**4. NetworkX + Parquet — BSD-3, NumFOCUS.** At 3M edges, dict-of-dicts representation is ~100 bytes/edge (Memgraph guide) → ~300MB resident plus node overhead, before any algorithm allocates. Fine for ad-hoc PageRank / connected-components / centrality once you've sliced the edge table down, terrible as the primary append-only store. Use it the way `bundle_adjudicate.py` would: load a focused subgraph with a SQL prefilter, run the algorithm, throw the graph away.

**5. NebulaGraph / TigerGraph / Neo4j — all wrong layer.** Server-mode, JVM/cluster-oriented, ops overhead a single user on a Mac shouldn't carry. Neo4j Community 100K-edge ingest is "order of seconds"; the prrao study shows it's also 40–374× slower than the embedded option on multi-hop at our scale. Hard veto for personal-scale.

**6. DataFusion + Substrait — Apache-2.0, broad backing.** Could federate across multiple DuckDB files, but adds a layer above the engine we already trust. No reason to introduce it unless we end up sharding the corpus by year or by venue, which we won't at 3M edges. Deferrable.

**7. SQLite + JSON1 — Public Domain.** Row-oriented; recursive CTEs work but no vectorized scan, no Parquet zero-copy, no DuckPGQ analog. At 3M edges with stance/year/source filtering, table scans hurt. Vetoed at this scale.

## Concrete Query Benchmark Expectations

Best evidence we have for the target query (`cited_by(paper_id, stance=contrasting, limit=50)`) and its k-hop variant, on M3-class hardware:

- **prrao87/kuzudb-study, M3 MacBook Pro 36 GB, 100K nodes / 2.4M edges**: 1-hop and 2-hop traversal queries at 8.6 ms – 95 ms in Kuzu (the now-archived option). DuckDB on the same workload — comparable for 1-hop (the CIDR paper notes DuckDB winning on IS01/IS04 with sub-ms selective primary-key paths) and within a small constant factor of Kuzu on 2-hop+ when the edge table is sorted on source and the recursion is bounded.
- **Cross-Model Efficiency in SQL/PGQ (arXiv 2505.07595, 2025)**: DuckPGQ bounded triangle queries (Q1–Q3) 7.7–28.8 ms; unbounded multi-hop (Q4–Q6) 16.5–67.7 ms across 50/100/150-row test sets. Tiny datasets, but consistent with sub-100ms multi-hop at our edge count. Paper reports means, not p95 — cite as order of magnitude, not a service-level commitment.
- **DuckDB blog (Oct 2025), DuckPGQ financial-crime example**: recursive bounded path search over a transfer graph runs interactively; their guidance is to put an explicit depth bound (`ps.depth < 11`) to avoid quadratic blow-up on dense subgraphs.
- **For our p95 expectation**: `cited_by(source=X, stance=contrasting, limit=50)` is a one-hop selective filter on an indexed edge table. **Realistic p95 < 5 ms** once `(source_id, stance_class)` is in a zonemap or DuckDB min/max index. `k-hop within Y, k≤3` is **realistic p95 in the tens of ms** with a bounded recursive CTE or DuckPGQ `->{1,3}` pattern. We should measure on our actual corpus before promising numbers.

Caveats: none of the cited benchmarks measure p95. They are means / single-run timings. The honest answer is "we expect single-digit-ms to low-tens-of-ms p95 on M3 for the three named query shapes at 3M edges; we will validate on the real corpus before publishing a SLO."

## Does Cypher Buy Us Anything CTEs Can't?

Ergonomics, yes. Capability, no. DuckPGQ's `MATCH (a:Paper)-[c:CITES WHERE c.stance='contrasting']->(b)` is the same plan as a join + recursive CTE, but the source is 3–5× shorter and reads like the question. For a scientific-agent audience this matters — agents generate graph queries from text, and graph syntax is closer to the text. **Recommendation**: keep CTEs as the primary path (it's what the rest of our stack already does), add DuckPGQ once we have a real query that's painful to write in SQL.

## Long-Term Maintenance Burden

- **DuckDB**: CWI core + commercial (DuckDB Labs), heavy funding, monthly releases, multi-maintainer. Lowest bus factor of the set.
- **DuckPGQ**: CWI / Daniël ten Wolde, single-PhD-driven but actively releasing (v1.4.4 March 2026, paper in VLDB 2023, follow-ons in VLDB 2025 / GRADES 2025). Higher bus factor than Kuzu was — flag in eval if it stalls.
- **Kuzu**: archived. Past tense.
- **Lance/LanceDB**: VC-backed (Series A, multi-million), strong team, growing OSS community. Safe for vector workloads.
- **NetworkX**: NumFOCUS-sponsored, decade+ of maintenance, fine for ephemeral analytical use.

## Recommendation: Stay DuckDB

1. **Primary citation graph store**: DuckDB tables `papers`, `citances_in`, `citances_out` exactly as the prior memo specifies. Sort `citances_in` on `(cited_paper_id, stance_class)` and `citances_out` on `(citing_paper_id, stance_class)` to make selective filters cheap.
2. **Graph syntax**: leave CTEs as default. Optional: `INSTALL duckpgq FROM community; LOAD duckpgq;` when a multi-hop query gets painful — same engine, no migration.
3. **Don't adopt Kuzu** even though existing binaries run. Single-maintainer surface that just lost its maintainer is the wrong place for our most queried artifact.
4. **Defer Lance** to a future semantic-similarity-edge plan; cohabit with DuckDB via the new Lance × DuckDB integration when it lands.
5. **Reserve NetworkX** for in-memory analysis on filtered subgraphs (PageRank, components, centrality). Never as primary store.

The prior memo's confirmation of DuckDB stands; the new information strengthens it (Kuzu archived) rather than challenging it.

## Sources

1. [BetaKit — Apple strikes deal to acquire Kuzu](https://betakit.com/apple-strikes-deal-to-acquire-canadian-database-software-startup-kuzu) — acquisition confirmation
2. [The Verge — Apple quietly acquired Kuzu late last year](http://on.theverge.com/tech/877360/apple-quietly-acquired-the-graph-database-company-kuzu-late-last-year)
3. [University of Waterloo CS — Waterloo-based graph DB startup Kùzu acquired by Apple](https://uwaterloo.ca/computer-science/news/waterloo-based-graph-database-start-up-kuzu-acquired-apple)
4. [kuzudb/kuzu archive commit 06890e1, Oct 10 2025](https://github.com/kuzudb/kuzu/commit/06890e1ac6bd31216f916526b933afc2a7802ec1)
5. [Kùzu CIDR 2023 paper (Jin et al.)](https://www.cidrdb.org/cidr2023/papers/p48-jin.pdf) — LDBC-SNB IS queries, DuckDB vs Kùzu on 1-hop vs multi-hop
6. [prrao87/kuzudb-study](https://github.com/prrao87/kuzudb-study) — 100K nodes / 2.4M edges, M3 MacBook Pro 36 GB, multi-hop 8.6 ms – 95 ms vs Neo4j 3.2–3.9 s
7. [Rotschield & Peterfreund 2025, Towards Cross-Model Efficiency in SQL/PGQ, arXiv:2505.07595](https://arxiv.org/html/2505.07595v1) — DuckPGQ bounded Q1–Q3 7.7–28.8 ms, unbounded Q4–Q6 16.5–67.7 ms
8. [DuckPGQ: Bringing SQL/PGQ to DuckDB, VLDB 2023](https://dl.acm.org/doi/10.14778/3611540.3611614)
9. [DuckPGQ project site & community extension v1.4.4](https://duckpgq.org/) and [duckdb.org/community_extensions/extensions/duckpgq](https://duckdb.org/community_extensions/extensions/duckpgq)
10. [DuckDB blog Oct 2025 — Financial-crime graphs with DuckPGQ](https://duckdb.org/2025/10/22/duckdb-graph-queries-duckpgq) — recursive-bound guidance
11. [Memgraph NetworkX FAQ](https://memgraph.github.io/networkx-guide/faq/) — ~100 bytes/edge memory model, 30M edges ≈ 40 GB RAM
12. [ArcadeDB blog — Neo4j alternatives 2026](https://arcadedb.com/blog/neo4j-alternatives-in-2026-a-fair-look-at-the-open-source-options/) — independent Kuzu archive confirmation, LDBC SNB SF1 comparison
13. [LanceDB January 2026 newsletter — Lance × DuckDB SQL retrieval](https://www.lancedb.com/blog/newsletter-january-2026) — Lance consolidating SQL queryability through DuckDB rather than reimplementing
14. Companion: `~/Projects/agent-infra/research/scientific-citation-graph-patterns-2026-05.md` — Claim 7, design implication 3, columnar storage at production scale

<!-- knowledge-index
generated: 2026-05-11T07:45:19Z
hash: 990186d3e192

title: Graph Storage for Citation Graphs at 300K–3M Edges — DuckDB vs Alternatives
status: complete
tags: graph-storage, duckdb, kuzu, citation-graph, prior-art
cross_refs: research/scientific-citation-graph-patterns-2026-05.md

end-knowledge-index -->
