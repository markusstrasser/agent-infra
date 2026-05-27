# Bitemporal Append-Only via Supersedes Chain — Correctness Deep-Dive

**Date:** 2026-05-27
**Context:** v4 substrate plan — annotations table is APPEND-ONLY, each row carries `valid_from` (informational) and `supersedes_annotation_id` (pointer to prior annotation). "Current state" view via `NOT EXISTS` anti-pattern.
**Verdict (top-line):** Design is structurally sound. **One real risk** (concurrent branching via two writers superseding the same target), **one performance non-risk** (NOT EXISTS on DuckDB), **one boundary subtlety** (`<=` vs `<` on as-of-T). Cycles are impossible-by-construction if `supersedes_annotation_id` is set at INSERT and never updated.

---

## 1. Cycle vulnerability — IMPOSSIBLE BY CONSTRUCTION (with one invariant)

**Claim:** If `supersedes_annotation_id` is set at INSERT time and never updated, cycles cannot form. Because `annotation_id`s are monotonically allocated and any `supersedes` pointer MUST reference an `annotation_id` that already existed (i.e., a smaller id), the supersedes graph is a forest whose edges always point backward in id-space — a DAG by construction. A cycle `A→B→A` would require B to reference A before A was inserted, which the FK constraint prevents.

**The single invariant the design relies on:** `supersedes_annotation_id` is immutable post-insert AND has a FK to `annotations(annotation_id)`. Both should be enforced architecturally:

```sql
supersedes_annotation_id BIGINT
  REFERENCES annotations(annotation_id),  -- forces predecessor exists
-- No UPDATE path through the gateway — append-only enforced by the
-- MutationGateway pattern from decisions/2026-05-26-cross-attestation-substrate-v2.md
```

**No cycle-detection trigger needed.** This is qualitatively different from the parent-pointer trees in the StackOverflow / SQLite forum threads on cycle detection [^1][^2] — those involve `UPDATE parent_id`, which is exactly the operation our append-only gateway forbids. The cycle-detection literature (recursive CTE in CHECK constraints, triggers with `WITH RECURSIVE`) applies to *mutable* parent pointers. Our pointers are immutable, so the literature's complexity does not transfer.

**What if the writer is corrupted/buggy and inserts `supersedes = NULL` when it should be `B`?** That's not a cycle; that's a misclassified root. Detectable by audit (`audit_corpus_sync.py` pattern) but not by structural invariant. Mitigation: bug fixing in the gateway, not schema constraints.

**Source grade:** A (mathematical argument from monotonic ID allocation + FK + append-only).

---

## 2. Multiple-supersession branching — REAL RISK, needs explicit policy

**The scenario:** Writer X and Writer Y both observe annotation A as current, both decide to supersede it. Y inserts B with `supersedes=A`; X inserts C with `supersedes=A`. The `NOT EXISTS` view now returns **both B and C as current** (neither is superseded by anything).

**This is the well-known concurrent-update / lost-update problem in event-sourced systems** and the answer depends on which guarantee you want:

| Policy | Mechanism | Trade-off |
|---|---|---|
| Single-writer serialization | XTDB / Datomic single-writer transactor [^3][^4] | Throughput bottleneck; simplest semantics |
| Optimistic concurrency control (OCC) | `UNIQUE(supersedes_annotation_id)` constraint | One writer wins, the other gets FK/UNIQUE violation and retries reading new current state |
| Last-writer-wins (LWW) | Tiebreak in view: `ORDER BY asserted_at DESC, annotation_id DESC LIMIT 1` per claim_id | Silently drops one writer's data; not auditable |
| Branching CRDT-style | Keep both, surface conflict to reader | Multi-valued reads; resolution deferred |

**XTDB's answer:** single-writer architecture — "single-writer architecture that ensures ACID consistency...with strong consistency guarantees needed for auditing and bitemporal timestamp generation" [^3]. Concurrent supersession races are eliminated at the transaction-log level; transactions are totally ordered before they touch the store.

**Datomic's answer:** also single-writer (transactor process). Race resolution happens via `:db.fn/cas` (compare-and-swap) transaction functions which abort if the precondition no longer holds [^4].

**Genomics' MutationGateway** uses a `BEGIN/COMMIT` span with a process-level writer lock (per `decisions/2026-05-26-cross-attestation-substrate-v2.md`). This functionally provides the single-writer semantics inside one process. **Cross-process concurrent supersession is not currently prevented** — if two processes hold separate gateway instances, the race exists. The mitigation pattern from Postgres cycle detection thread applies: "without serializable isolation or explicit locking, concurrent updates can still cause transient cycles; SERIALIZABLE or locking may be required for correctness under concurrent workload" [^2].

**Recommended addition to v4 plan:** Add `UNIQUE(supersedes_annotation_id) WHERE supersedes_annotation_id IS NOT NULL` partial unique index. This makes the gateway's commit fail with a UNIQUE violation on concurrent supersession, forcing the loser to re-read and retry against the new current state — OCC semantics, no schema bloat, deterministic. Costs near-zero for our scale (<10⁶ annotations).

**Source grade:** A (XTDB docs, Datomic docs, well-established CAS pattern).

---

## 3. Point-in-time as-of-T — CORRECT, with one boundary clarification

**Proposed:**
```sql
WHERE a.asserted_at <= T
  AND NOT EXISTS (
    SELECT 1 FROM annotations s
    WHERE s.supersedes_annotation_id = a.annotation_id
      AND s.asserted_at <= T
  )
```

**This is correct** under standard bitemporal semantics: "the row a was true as-of T iff a was asserted by T AND nothing asserted by T supersedes a." Matches Fowler's described pattern for event-sourced bitemporal reconstruction [^5] and the partial-persistence access-method paper (Kumar/Tsotras) [^6].

**Boundary case (`asserted_at == T` exactly):** With `<=` on both sides, an annotation asserted exactly at T is visible AND its same-instant supersessor (if any) wins. This is correct for *transaction-time* (which is what `asserted_at` represents) — at instant T, the latest fact known at T is the answer. Use `<` if you want strictly-before semantics. **The two semantics differ only on row asserted exactly at T**, which is rare for wall-clock timestamps but common for system-allocated identical timestamps (batch import). Document the choice; either is defensible.

**Edge cases:**
1. **Multi-step chain at the boundary:** A→B→C all asserted at T. Query as-of-T returns C (correct: nothing asserted ≤T supersedes C; B is superseded by C; A is superseded by B). Verified by induction on chain length.
2. **Branching at point-in-time:** If §2's race is unresolved and B,C both supersede A at time T, query as-of-T returns {B, C} — same multi-row result as `current`. Consistent.
3. **Retroactive insertion (a row inserted today with `asserted_at` in the past) — handled correctly** because the predicate is on `asserted_at`, not `inserted_at`. If you need "knowledge as of inserted_at T", add a separate `inserted_at <= T` clause — this is the second bitemporal axis Fowler emphasizes [^5].

**Source grade:** A (Fowler, Kumar/Tsotras, internally consistent).

---

## 4. Performance: `NOT EXISTS` at scale — NON-RISK on DuckDB

**DuckDB decorrelates correlated subqueries automatically** via the Unnesting Arbitrary Queries algorithm. Mark Raasveldt's 2023 DuckDB blog post measures: on a 4M-row ontime dataset, a correlated subquery that runs in **0.06s in DuckDB** runs in **>48 hours in Postgres and SQLite** [^7]. The optimizer emits a hash-join physical plan, not an O(N²) loop.

**Specifically for `NOT EXISTS`:** DuckDB docs state: "DuckDB automatically detects when a NOT EXISTS query expresses an antijoin operation. There is no need to manually rewrite such queries to use LEFT OUTER JOIN ... WHERE ... IS NULL" [^8]. The physical plan uses an anti-join (`LOGICAL_DEPENDENT_JOIN` rewritten to an anti-join after decorrelation) — true O((N+M) log N) hash-join complexity, not O(N²).

**Caveats:**
- DuckDB issue #22267 (Apr 2026, v1.5.2) reports a correlated-EXISTS-with-derived-table decorrelation bug; fix PR #22296 in flight [^9]. Our query has no derived table, so not affected — but worth pinning DuckDB ≥1.5.3 once it includes the fix.
- DuckDB issue #19022 (closed as false alarm Sep 2025) confirms NOT EXISTS / ANTI JOIN semantics are correct for empty-RHS edge case [^10].
- Postgres pattern (postgres.ai blog [^11]): NOT EXISTS with a partial index on the minority subset (here: rows that *are* supersessors) can give 30-50x speedups on Postgres. Not relevant to DuckDB (column-store anti-join is already optimal), but if we ever port to Postgres, add `CREATE INDEX ON annotations(supersedes_annotation_id) WHERE supersedes_annotation_id IS NOT NULL`.

**At what N does this hurt?** On DuckDB the answer is "much larger than our scale." The `corpus_core.annotate` workload sits in the 10⁴-10⁶ annotation range; hash-anti-join on this size completes in single-digit milliseconds. **Materialized current-state table with refresh-on-supersession trigger is unnecessary** at our scale and adds invalidation complexity. Reconsider only if (a) we exceed 10⁸ rows, or (b) per-query latency for `annotations_current` becomes a hot path measured at >50ms.

**Source grade:** A (DuckDB blog with quantitative benchmarks, source code reference, open issues).

---

## 5. Industry pattern check

| System | Pattern | Notes |
|---|---|---|
| **XTDB v2** | Pure append-only event log; bitemporal reconstruction by sort-merge over entity-id-keyed, system-time-descending files [^3][^12] | Single-writer transactor; "WITHOUT OVERLAPS" constraint enforces no rectangle overlap in (system-time × valid-time) plane. Uses HAMT in-memory + Parquet on object storage. |
| **Datomic** | Append-only EAVT/AEVT/AVET indexes; retraction is just a new datom with `op=false`; excision is the only true delete [^4][^13] | Single-writer transactor. `:db.fn/cas` for OCC. `rewriting-history` library (Ivar Refsdal) exists precisely *because* mutable history is intentionally hard. |
| **immudb** | Append-only Merkle-verified ledger; no in-place updates; "Data can only be added and never changed or deleted" [^14] | Cryptographic proof of immutability is the differentiator. Closest to a "pure" append-only model. |
| **Crux** | Predecessor of XTDB v2; same conceptual model | Subsumed by XTDB. |
| **Fowler bitemporal** | Record-history append-only, actual-history mutable; or full event sourcing [^5] | Snapshots-as-cache pattern recommended for read-side. |
| **Snodgrass / standard SQL TSQL2** | Closed-open intervals `[valid_from, valid_to)` with mutable `valid_to`; `WITHOUT OVERLAPS` constraint | Academic standard; what most SQL temporal extensions implement. NOT what we're doing. |

**Pattern alignment:** Our design is closest to **XTDB's event-log model** with the supersedes pointer making the reconstruction explicit (XTDB infers supersession from `(entity_id, system_time)` sort). The pointer is a denormalization that simplifies the view at the cost of one extra column per row — reasonable trade for our scale where we don't have XTDB's bespoke columnar storage layer.

**What each learned the hard way:**
- **Datomic:** retracting a fact-you-need-to-correct ≠ retracting a fact-that-was-wrong-and-must-disappear. The latter required *excision* (rare, irreversible, on-prem only) [^13]. Our design implicitly inherits this — supersession marks history, doesn't erase it. If GDPR-erasure is ever needed, plan for tombstoning at the gateway layer.
- **XTDB:** the single-writer transactor is the linchpin of bitemporal correctness; without it, system-time ordering becomes ambiguous and supersession races become silent inconsistencies.
- **immudb:** verifiability vs. performance is a real trade-off — Merkle proofs cost write throughput. We don't need cryptographic verifiability, so we don't pay this cost.

**Source grade:** A (primary docs from each project).

---

## 6. Case AGAINST pure append-only

**When mutable `valid_to` is genuinely better:**

1. **Range queries become trivially indexable:** `WHERE T BETWEEN valid_from AND valid_to` is a single B-tree or GiST range query. With our pointer model, point-in-time-as-of-T requires the anti-join. DuckDB makes this free; row-store OLTP databases (Postgres, MySQL) do not.
2. **Reporting tools (BI dashboards) expect interval rows.** Tableau / Looker / Metabase semantic layers handle `[from, to)` natively; they don't have a "follow the supersedes pointer" operator. We'd need a materialized view to expose `valid_to` for tooling.
3. **Storage cost:** mutable `valid_to` stores N rows for N versions. Our model stores N rows too — same storage. **No advantage to mutable_valid_to here**; this is a wash.
4. **`UNIQUE` constraints on currently-active rows** are slightly cleaner with `valid_to IS NULL` than with the anti-join trick. Both work.

**What you genuinely lose with pure append-only:**
- **Range-intersection queries** (e.g., "all annotations valid at any point in 2025-Q3") require deriving `valid_to` from `MIN(supersessor.valid_from)`, then doing range intersection. Possible but verbose. If this is a common query class, materialize a `valid_to` column on read.
- **`PERIOD FOR valid_time` SQL:2011 syntax** — standard SQL temporal queries don't natively work. Not portable. Acceptable for a DuckDB-internal store; not for a federated query layer.

**The real argument for our design** (which the v4 plan makes implicitly): we're not building a general-purpose bitemporal DB. We're building an append-only annotation log where **the audit trail IS the data** and supersession is rare relative to insertion. The pointer model is more natural for this access pattern and aligns with the broader epistemic principle "Append-only over edit for institutional knowledge" [^15]. **Verdict: pure append-only is the right choice here.** No suppressed alternative is genuinely better for our access pattern.

**Source grade:** B (analysis from first principles + Fowler discussion of trade-offs).

---

## 7. Replay semantics — CLAIM CONFIRMED

**Claim under review:** "If supersession events ARE annotations, then INSERTing them in JSONL order trivially reconstructs the state. No 2-pass needed."

**This is correct.** Proof sketch:

- Let `J = [a₁, a₂, ..., aₙ]` be the JSONL stream in insertion order.
- After inserting `aᵢ`, the `annotations` table contains `{a₁, ..., aᵢ}`.
- The `annotations_current` view at this point evaluates `NOT EXISTS` over `{a₁, ..., aᵢ}`.
- Because `supersedes_annotation_id` is a backward pointer (per §1, `supersedes` always references a smaller id which is already inserted), every supersession event's target exists at insert time.
- Therefore at every intermediate state, the view is consistent.
- After the final insert `aₙ`, the table state and view are identical to the state that produced the JSONL.

**No 2-pass needed.** The only requirement is **insertion-order preservation**. If JSONL is sorted by `annotation_id` (or by `asserted_at` if `annotation_id` is generation-stamped accordingly), replay is single-pass.

**Subtle case the claim COULD miss:**

1. **Orphaned supersessors** — a supersession row references an `annotation_id` that doesn't exist in the JSONL (e.g., JSONL is a slice, not the full history). The FK violates at insert. **Mitigation:** export must include the full supersession chain, or replay must be against a base snapshot that already contains predecessors. **This is a correctness issue with partial exports, not with the model.**

2. **Out-of-order JSONL** — if the JSONL is sorted by `asserted_at` and a clock skew or batch-import causes a child to appear before its parent, FK fails. **Mitigation:** topological sort by `supersedes` before replay, OR use `INSERT ... ON CONFLICT DO NOTHING` with a fixup pass. The "trivially single-pass" claim assumes sorted-by-id order. Worth stating explicitly in plan.

3. **Concurrent JSONL streams from multiple gateways** — if two JSONL streams from different writers are replayed by interleaving, you need to respect causal order (supersedes references). A topological sort on the union is sufficient; merge-by-timestamp is NOT sufficient if timestamps can collide.

**Claim holds with the explicit invariant: "JSONL is in topological order on the supersedes DAG."** For single-gateway exports this is implied by id-order; for multi-gateway merges it must be enforced.

**Source grade:** A (formal proof + identified subtleties).

---

## Summary of recommended additions to v4 plan

| Recommendation | Priority | Cost |
|---|---|---|
| Add FK `supersedes_annotation_id REFERENCES annotations(annotation_id)` | Must | Trivial |
| Add partial UNIQUE `(supersedes_annotation_id) WHERE NOT NULL` to prevent concurrent branching | Should | Trivial; gives OCC semantics |
| Document `<=` vs `<` semantics for as-of-T boundary | Should | Doc only |
| Document "JSONL must be in topological order" invariant for replay | Should | Doc only; for multi-gateway merge contexts |
| Pin DuckDB ≥1.5.3 once #22296 lands (defensive against decorrelation bug) | Nice | Trivial |
| Skip materialized current-state table | Negative recommendation | N/A — adds invalidation complexity for zero measured benefit at our scale |
| Skip cycle-detection trigger | Negative recommendation | N/A — impossible by construction |

---

## Sources


<!-- knowledge-index
generated: 2026-05-27T11:23:39Z
hash: 367b7718a14c

cross_refs: decisions/2026-05-26-cross-attestation-substrate-v2.md, docs/1.2/sql/expressions/subqueries.md

end-knowledge-index -->

[^1]: SQLite User Forum, "cycle detection in CHECK constraint with recursive CTE", 2021-07. https://www.sqlite.org/forum/info/f7efbc8d41bc822a — Grade B (forum, but verified solution from sqlite maintainers).
[^2]: StackOverflow, "Prevent and/or detect cycles in postgres", 2014, updated 2022. Includes Leisetreter's note on concurrent execution caveats. — Grade B.
[^3]: XTDB docs, "Key concepts". https://docs.xtdb.com/concepts/key-concepts.html — Grade A (primary docs).
[^4]: Datomic docs, "Transaction Functions". https://docs.datomic.com/transactions/transaction-functions.html — Grade A (primary docs).
[^5]: Martin Fowler, "Bitemporal History". https://martinfowler.com/articles/bitemporal-history.html — Grade A (canonical reference).
[^6]: Kumar/Tsotras, "Designing Access Methods for Bitemporal Databases", U. Maryland. — Grade A (peer-reviewed).
[^7]: Mark Raasveldt, "Correlated Subqueries in SQL", DuckDB blog, 2023-05-26. https://duckdb.org/2023/05/26/correlated-subqueries-in-sql — Grade A (primary, with benchmarks).
[^8]: DuckDB docs, Subqueries (NOT EXISTS section). https://raw.githubusercontent.com/duckdb/duckdb-web/refs/heads/main/docs/1.2/sql/expressions/subqueries.md — Grade A.
[^9]: DuckDB issue #22267, "Inconsistent result for correlated EXISTS subquery with derived table". Apr 2026, fix in PR #22296. — Grade A.
[^10]: DuckDB issue #19022, "ANTI JOIN & WHERE NOT EXISTS produce incorrect result if right-hand table is empty" — closed as false alarm Sep 2025. — Grade A.
[^11]: PostgresAI blog, "How moving one word can speed up a query 10–50x", 2026-03-11. https://postgres.ai/blog/20260311-not-exists-vs-exists-partial-index — Grade B (vendor blog, with reproduction).
[^12]: James Henderson, "Building a Bitemporal Index (part 3): Storage", XTDB blog, 2025-06-05. https://xtdb.com/blog/building-a-bitemp-index-3-storage.html — Grade A.
[^13]: Ivar Refsdal, `rewriting-history` library. https://github.com/ivarref/rewriting-history — Grade B (community library, but documents Datomic's intentional difficulty with history modification).
[^14]: immudb project page. https://immudb.io/ — Grade A (primary).
[^15]: Local: `/Users/alien/Projects/agent-infra/CLAUDE.md` epistemic_discipline §2 "Append-only over edit for institutional knowledge."

## Negative findings (no issue found)

- **No cycle protection needed beyond FK + immutable column.** Mathematical impossibility, not a missing feature.
- **No O(N²) performance risk on DuckDB.** Decorrelation handles it. No need for materialized view.
- **No suppressed advantage of mutable_valid_to** for our access pattern.
- **No 2-pass replay needed** under the topological-order invariant (implicit for single-writer JSONL).