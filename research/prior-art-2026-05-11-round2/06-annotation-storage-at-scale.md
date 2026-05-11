---
title: Annotation Storage at 100K-1M Scale — JSONL vs Columnar Alternatives
date: 2026-05-11
tags: [storage, jsonl, parquet, lance, ducklake, iceberg, annotations]
status: complete
scope: round-2 prior-art sweep, decision on canonical storage format
---

# Annotation Storage at 100K-1M Records

## TL;DR — recommendation

**Keep per-source `annotations.jsonl` as canonical, swap derived DuckDB projection for `DuckLake` if the projection grows past ~1M rows or you outgrow single-file DuckDB.** Until then, today's setup is right.

Do NOT:
- Migrate canonical to Parquet — appends require rewrite or external table-format ACID layer (Iceberg/Delta/Hudi). The ergonomics tax (compaction, manifests, catalog) is not worth it at this scale.
- Migrate canonical to Lance — append-friendly columnar, but the ecosystem (DuckDB scan, jq, grep, `cat`) doesn't read it directly. You'd lose human-grokkability for compression gains that don't matter at <10 GB total.
- Migrate canonical to SQLite — atomic, but per-source `*.db` files are opaque, hostile to grep/`cat`/diff, and create binary lock files that break filesystem replication patterns (Time Machine, rclone, git-annex).

Do:
- **Keep JSONL canonical.** O_APPEND on Linux is atomic for writes ≤PIPE_BUF (4KB); annotation records are routinely under 1KB. Concurrent appenders from 3-5 agents are safe on local filesystems (ext4, APFS, ZFS) without a lock manager.
- **Keep DuckDB as the derived projection.** `read_ndjson_auto` over the JSONL tree is "nearly instant" up to a few million records; the projection table is for compound queries (joins across sources, aggregations), not for replacing the log.
- **Add a compaction recipe** — `annotations.jsonl` per source compacted to `annotations.YYYY-MM.jsonl.zst` after each month, deletion-blocked. Keeps directory size bounded and replication friendly.
- **Document the migration trigger** — single source >500K records OR aggregate projection >5M rows → switch projection layer to DuckLake (not Iceberg).

## Format comparison

| Format | Read perf | Write perf | Concurrent append safety | Human-readable | Schema evolution | Maturity 2026 |
|---|---|---|---|---|---|---|
| JSONL (current) | Good via DuckDB `read_ndjson` (parallel, near-instant <few M rows); linear via `jq`/`grep` | Fastest. `open(O_APPEND)`+write atomic ≤4KB | Yes — POSIX `O_APPEND` atomic on Linux 3.14+ for sub-PIPE_BUF writes; ext4/APFS/ZFS honor | Yes (`cat`, `jq`, `grep`, `tail -f`) | Trivial — add field, old readers ignore. No coordination needed | Native everywhere |
| Parquet (one file/source) | Excellent (column pruning, predicate pushdown) | Bad for append — must rewrite file or split into chunks → small-files problem | No native append. Concurrent writers corrupt unless table-format layer used | No (`parquet-tools head` or DuckDB to read) | Per-file evolution OK; cross-file requires manifest | Mature for batch analytics; bad fit for event-log append |
| Parquet partitioned (Hive `year=/month=`) | Excellent. DuckDB `read_parquet('**/*.parquet', hive_partitioning=true)` | Append by writing new file per partition. `COPY ... PARTITION_BY ... APPEND` (DuckDB) regenerates UUIDs to avoid clash | Safe at file granularity; not at intra-file | No | Per-partition; mixed schemas tolerated by readers | Mature; recommended partition size 100 MB+ — our 1M annotations × 1KB = 1 GB total, fits 1 partition |
| Arrow Feather/IPC stream | Fast (zero-copy memmap) | Stream format is append-only by design BUT no concurrent writer story | Not designed for multi-writer | No | Schema fixed per stream | Stable but niche; ecosystem favors Parquet |
| Lance | Excellent for random access + scans; `lance` reads in DuckDB/Polars | True append-friendly via versioned transaction log (like Delta but lighter) | Yes — versioned writes | No (`lance` CLI, Python only) | First-class; column add is metadata-only | v2 stable (2025), ecosystem still growing. BI tools don't read it |
| Apache Iceberg + DuckDB | Excellent | DuckDB-Iceberg writes available since v1.4.2 (Nov 2025) | Yes — ACID via manifests | No | Schema evolution **broken in DuckDB-Iceberg today** — column-add against old files crashes (issue #805) | DuckDB writer maturing; partitioned/sorted tables can't take updates yet. Too new |
| Delta Lake + DuckDB | Good (read via `delta` extension) | DuckDB write support partial | Yes — ACID | No | First-class | Mature in Spark/Databricks; DuckDB integration thinner than Iceberg |
| **DuckLake** | Excellent (native DuckDB) | Native | Yes — SQL catalog replaces file-manifest soup; inlined small writes avoid the small-files problem by design | No (catalog is SQLite/Postgres/DuckDB; data in Parquet) | First-class, SQL-driven | **1.0 GA April 2026.** Designed for exactly our scale (50GB-2TB, small writes). Reads/writes Iceberg too |
| SQLite per source | Good (FTS5, indexes) | Good (WAL mode 2× rollback journal) | Yes (single-writer per file; one file per source = no contention) | No (sqlite3 CLI) | ALTER TABLE works; ad-hoc field add awkward | Mature; per-directory `.db` adds opacity and lock-file clutter |
| DuckDB single-file | Excellent | Good with WAL | Single-writer process at a time (file lock) | No | ALTER TABLE | Mature; bottleneck if multiple agents need concurrent write |

## Concrete pick for our 100K-1M target

**At 100K total: today's setup (JSONL canonical + DuckDB projection) is correct.** The projection table is essential for compound queries (join across source, filter by agent, aggregate by month). The canonical JSONL is essential for:
- 3-5 agents writing concurrently without coordination
- Audit/grep/diff workflows
- Append-only invariant enforced by filesystem semantics, not a service
- Schema evolution by adding fields (drop-in, no migration)

**Will JSONL hold at 1M?** Yes for storage (1M × ~1KB ≈ 1 GB; trivial). For queries via DuckDB `read_ndjson` over a hive-laid directory tree, parallel scan keeps p99 under a few seconds for cold reads on M3. The projection table is what handles repeated analytical queries — that's what it's for. Don't fight the architecture by querying canonical for every question.

**Why not just put everything in the projection table?** Three concrete reasons:
1. **Concurrent writers.** DuckDB single-file holds an exclusive process lock during writes. Multiple agents need a coordinator (queue, lock service) or per-process file. JSONL via `O_APPEND` needs nothing.
2. **Rebuild safety.** If the projection schema changes (v1 → v2 of the annotation contract), you rebuild from canonical with one SQL statement. If canonical IS DuckDB, you've lost the source of truth.
3. **Forensic legibility.** A junior agent, future-you, or an external auditor can read `tail -10 annotations.jsonl` and understand the record. Nobody opens DuckDB blobs without tooling.

**Why not Lance?** Genuinely append-friendly columnar — closest "best of both worlds" candidate. But: not human-readable, not in BI tooling, ecosystem still vector-database-flavored. The cost in opacity outweighs the compression benefit at <10 GB. Revisit if you ever store embeddings alongside annotations.

**Why not DuckLake instead of DuckDB-file projection?** Plausible *upgrade* path, not current recommendation. DuckLake 1.0 (April 2026) is brand new — wait 6 months for stability and tooling. Today's single-file DuckDB projection is simpler and adequate to ~5M projected rows.

## Migration story if we ever outgrow current

Trigger conditions for moving the **projection** off single-file DuckDB:
- Single source's `annotations.jsonl` exceeds 500K records (slow cold scan)
- Aggregate projection table exceeds ~5M rows (DuckDB file >1 GB, ALTER becomes painful)
- More than one writer process needs to mutate the projection concurrently

Migration path (projection only; canonical stays JSONL):

1. **Compact JSONL.** Add monthly compaction recipe: `gzip` or `zstd` immutable months. `annotations.2026-05.jsonl.zst`. Hive layout: `corpus/{source}/annotations/year=2026/month=05/...`. DuckDB reads `.zst` natively.
2. **Switch projection to DuckLake.** SQL catalog (SQLite is fine for single user) + Parquet data files. DuckDB reads/writes natively. Small-write inlining handles per-source updates. Migration is `CREATE TABLE ... AS SELECT * FROM read_ndjson_auto(...)`; one statement.
3. **Optional: replace JSONL projection table in DuckDB with hive-partitioned Parquet** if the projection is read 100× more than written. Use `COPY ... TO 'projection/' PARTITION_BY (source, year) APPEND`. DuckLake handles this transparently.

Trigger conditions for moving the **canonical** off JSONL (less likely, included for completeness):
- Need cross-machine consistency without filesystem replication
- Need ACID across multiple source-files in a single transaction
- Hit O_APPEND atomicity limit (record size >4KB consistently) — this would only happen if you start embedding large blobs inline (don't; reference by hash to a content-addressed store).

If forced: DuckLake becomes both canonical and projection. Costs: lose `tail -f` on the log, lose drop-in field addition, gain ACID across sources. Reversible: `COPY annotations TO 'export.jsonl' (FORMAT json, ARRAY false)`.

**Schema v1 → v2 evolution while staying on JSONL:** add new fields, ignore on old records (`COALESCE(field, default)` in projection SQL). The `conformsTo` field per record (recommended in 02-provenance-attestation-patterns) makes this explicit. Renames: write the rename rule into the projection SQL, never rewrite canonical. The git log of the projection SQL becomes the schema-evolution audit trail.

**What mem0/Cognee/DVC actually do:** Cognee uses SQLite + LanceDB + Kuzu (per-record memory ledger in SQLite, vectors in LanceDB, knowledge graph in Kuzu). Mem0 is similar — SQLite + FTS5 + vector index. DVC stores lineage in git + per-file `.dvc` YAML pointers, with optional Parquet for tabular outputs. None of them use JSONL as canonical event log — but none of them have our use case either (single-user, append-only, schema-evolving, multi-agent). The pattern most similar to ours is **event-sourcing with SQLite read cache** (paperclip RFC #801) which converges on the same shape: append-only log canonical, indexed cache derived.

## Sources

- [DuckDB JSON reads](https://duckdb.org/docs/current/guides/file_formats/json_import) — `read_ndjson` parallelizes; near-instant up to a few M rows.
- [Roland Bouman: DuckDB JSON tricks](https://rpbouman.blogspot.com/2024/12/duckdb-bag-of-tricks-reading-json-data.html) — shred stable fields into columns, then Parquet for hot paths.
- [DuckDB Iceberg writes (Nov 2025)](https://duckdb.org/2025/11/28/iceberg-writes-in-duckdb) — supports insert/update/delete on v2 tables; partitioned/sorted updates not yet supported.
- [DuckDB-Iceberg issue #805](https://github.com/duckdb/duckdb-iceberg/issues/805) — schema evolution (column add) crashes when querying old data files. Reason to wait.
- [DuckLake 1.0 release](https://ducklake.select/2026/04/13/ducklake-10/) — production ready April 2026; data inlining solves small-files problem.
- [DuckLake business case](https://www.definite.app/blog/duckdb-ducklake-business-case) — designed for 50GB-2TB, 5-20 person teams (single-user envelope subset).
- [Iceberg vs DuckLake summary](https://selectstarfrom.substack.com/p/iceberg-vs-ducklake-summary-of-a) — DuckLake stores manifests in SQL DB vs Iceberg in files.
- [Lance v2 columnar](https://blog.lancedb.com/lance-v2/) — append via versioned transaction log; Arrow-native zero-copy in DuckDB/Polars; ecosystem still vector-flavored.
- [Materialized View: Nimble and Lance](https://materializedview.io/p/nimble-and-lance-parquet-killers) — Lance is append-optimized, Parquet is batch-optimized; both have a home.
- [Dipankar Mazumdar: Parquet vs newer formats](https://dipankar-tnt.medium.com/apache-parquet-vs-newer-file-formats-btrblocks-fastlanes-lance-vortex-cdf02130182c) — Parquet's append weakness is the central problem newer formats address.
- [DuckDB Hive Partitioning](https://duckdb.org/docs/current/data/partitioning/hive_partitioning) — read by directory pattern with partition pushdown.
- [DuckDB Partitioned Writes APPEND](https://duckdb.org/docs/lts/data/partitioning/partitioned_writes) — `APPEND` option regenerates UUID on clash; safe per-file.
- [Apache Arrow IPC](https://arrow.apache.org/docs/python/ipc.html) — stream format append-only by design; not designed for multi-writer.
- [Datobra: small Parquet files become a big problem](https://www.datobra.com/when-small-parquet-files-become-a-big-problem-and-how-i-ended-up-writing-a-compactor-in-pyarrow/) — confirms compaction is the cost of append-via-new-file.
- [Hudi file sizing](https://hudi.apache.org/docs/next/file_sizing/) — recommended 128-512 MB per file; our 1M × 1KB = 1 GB fits one.
- [Cognee storage stack](https://lumadock.com/tutorials/openclaw-advanced-memory-management) — SQLite + LanceDB + Kuzu local-first.
- [Mem0 vs Cognee comparison](https://vectorize.io/articles/mem0-vs-cognee) — Mem0 SQLite+FTS5, Cognee event ledger via SQLite.
- [paperclip RFC #801: event-sourced file log + SQLite cache](https://github.com/paperclipai/paperclip/issues/801) — convergent architecture to ours; JSONL canonical + indexed read cache.
- [SQLite WAL mode](https://sqlite.org/wal.html) — 2× write throughput, sequential append-friendly; option if we ever want one .db per source.
- [Null Program: appending from multiple processes](https://nullprogram.com/blog/2016/08/03/) — O_APPEND atomicity on Linux for sub-PIPE_BUF writes; the 4KB ceiling is why annotation records must stay small (reference large blobs by hash, don't inline).
- [POSIX write() atomicity, Chris Siebenmann](https://utcc.utoronto.ca/~cks/space/blog/unix/WriteNotVeryAtomic) — caveat that POSIX-the-spec guarantees less than Linux-the-implementation; in practice, Linux 3.14+ gives us what we need.

<!-- knowledge-index
generated: 2026-05-11T07:46:33Z
hash: bef02ffaa690

title: Annotation Storage at 100K-1M Scale — JSONL vs Columnar Alternatives
status: complete
tags: storage, jsonl, parquet, lance, ducklake, iceberg, annotations

end-knowledge-index -->
