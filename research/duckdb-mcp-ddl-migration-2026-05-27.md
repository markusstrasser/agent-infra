# DuckDB Writer-Lock Semantics + Safe DDL Migration for Long-Running MCP Servers

**Date:** 2026-05-27
**Scope:** Validate planned "SIGTERM MCP → ALTER TABLE → restart MCP" protocol for `graph.duckdb`
**TL;DR (≤200 words):** The plan's core assumption is **wrong but the conclusion is right**. DuckDB does NOT support RO + RW across processes — having ANY connection (even read-only from the MCP) prevents any other process from opening RW. So the MCP must be shut down regardless of whether it's reading or writing; this is a hard architectural constraint, not a courtesy. `pgrep -f corpus_mcp.py` is insufficient — use `lsof graph.duckdb` (which reports the actual `fcntl` lock holder PID + user) as the canonical detector, with launchctl as a secondary check for daemonized invocations. The "wait, ALTER, restart" sequence is the right protocol — no online schema-change mode exists in DuckDB ≤1.5. Quack (v1.5.3, May 2026) IS now a core extension and DOES solve multi-writer, but is explicitly beta until v2.0 (Sept 2026) with breaking-change warnings — don't adopt for infra migrations yet. Schema-versioning + self-restart-on-bump is a valid alternative pattern (expand/contract) and worth building if migrations recur; for a one-shot G0 it's over-engineering. For Phase I cross-DB: pre-resolved crosswalk is sufficient ONLY IF intel never opens `graph.duckdb` directly — verify via `git grep -l "graph.duckdb" intel/`.

---

## Q1: Writer-lock vs reader-lock across processes

**Finding (D1, source-grade):** DuckDB does NOT distinguish reader-lock from writer-lock across processes. The locking model is:

> "Multiple processes connecting to the same database file is only possible if they are all read-only connections. It is not possible to have a read-write connection and a read-only connection connected to the same database file across multiple processes." — Mytherin (DuckDB maintainer), [discussion #5946](https://github.com/duckdb/duckdb/discussions/5946)

Mechanism: DuckDB uses `fcntl F_SETLK` directly on the database file (not a separate `.lock` file). Locks are exclusive at the file level for any RW connection. The RO/RW split is asymmetric:

| Process A | Process B | Allowed? |
|-----------|-----------|----------|
| RO        | RO        | Yes (multi-reader) |
| RW        | (none)    | Yes |
| RW        | RO        | **NO** — B fails with "Could not set lock" |
| RO        | RW        | **NO** — B fails with "Could not set lock" |
| RW        | RW        | **NO** |

**Implication for your plan:** If the MCP holds a long-running RO connection to `graph.duckdb`, a separate process attempting `ALTER TABLE` (which requires RW) **will fail to even open the database**. So "the MCP only reads" doesn't help — it still must be shut down.

**Note on intra-process:** Within a single Python process, multiple connections can coexist freely (MVCC handles them). The cross-process lock is a separate concern. ([concurrency docs](https://duckdb.org/docs/current/connect/concurrency))

---

## Q2: "Could not set lock" failure mode

**Trigger:** Any second process trying to open the DB file when another process holds a lock (RO or RW). Error format ([issue #17158](https://github.com/duckdb/duckdb/issues/17158)):

```
IO Error: Could not set lock on file: Conflicting lock is held in
/path/to/db.duckdb (PID 46912) by user jonas
```

The error includes PID + user. This is the canonical detection signal — more authoritative than `pgrep`.

**Recovery:**
1. Identify holder via the error message PID, OR `lsof graph.duckdb` (queries kernel fcntl table directly).
2. SIGTERM the holder. If the holder crashed without releasing (rare with fcntl — kernel releases on process death), the lock self-clears.
3. NFS/network FS: locks may persist after process death; manual `fuser -k` or restart of the host nfsd. Not your situation (local FS) but worth noting.

**Cross-connection same process:** Does NOT happen — DuckDB shares state across in-process connections via MVCC.

---

## Q3: Best-practice DDL migration with live server

**Finding (D1):** DuckDB has NO online schema change mode in v1.5. The recommended pattern from DuckDB docs is exactly your plan:

> "Stop the cron job, apply a migration in a separate DuckDB session (ALTER TABLE), and then restart the pipeline." — [DuckDB docs](https://duckdb.org/docs/current/connect/concurrency)

**Confirmed pitfall:** Even within a single transaction, `ALTER TABLE` followed by `INSERT` raises `Transaction conflict: adding entries to a table that has been altered!` ([issue #618](https://github.com/duckdb/duckdb/issues/618), [issue #20570](https://github.com/duckdb/duckdb/issues/20570), latest report Jan 2026 — still broken in 1.3+). Implication: every ALTER must commit before any reader/writer touches the table. Bundle DDL in a separate connection from DML.

**Quack (alternative, not yet viable):** [Quack remote protocol](https://duckdb.org/quack/) shipped as core extension in v1.5.3 (May 2026). Solves multi-writer via HTTP client-server. But: **beta**, breaking changes expected, stable in v2.0 (Sept 2026). FAQ explicitly: "you can use Quack for prototyping but it is still in development." Do NOT adopt for infrastructure migrations now. Flag for revisit Q4 2026.

**MotherDuck:** Hosted variant uses per-user "Ducklings" with isolated engines and transactional storage. Not relevant unless you're moving to hosted.

**Cloudflare DuckDB Workers / D1:** No published DDL migration guidance — D1 is SQLite, not DuckDB. The `cloudflare-duckdb` repo (tobilg) uses ephemeral containers, no live-migration story.

**Verdict:** Your "SIGTERM → ALTER → restart" is the right protocol for DuckDB 1.5. No gentler alternative exists in-tree.

---

## Q4: Detection problem

**`pgrep -f corpus_mcp.py` is insufficient.** Failure modes:
- Different user (e.g., `_corpus` daemon user) — pgrep filters by current user by default; needs `-a` and root.
- Renamed entrypoint (`python -m corpus.mcp` instead of `corpus_mcp.py`).
- Container (Docker namespace isolation — pgrep on host won't see it).
- launchd-managed daemon — visible to pgrep but the label is more authoritative.

**Better detector (composable, robust):**

```bash
# Primary: query the actual fcntl lock holder
LOCK_HOLDER=$(lsof -t /path/to/graph.duckdb 2>/dev/null | head -1)

# Secondary: launchd label probe
LAUNCHD_PID=$(launchctl list | awk '$3 == "com.agent-infra.corpus-mcp" {print $1}')

# Tertiary fallback: pgrep
PGREP_PID=$(pgrep -fa corpus_mcp | awk '{print $1}' | head -1)
```

`lsof` is authoritative because DuckDB locks via `fcntl F_SETLK` on the file itself — the kernel tracks the holder. If `lsof` returns empty, the file is genuinely unlocked and you can ALTER. If non-empty, that PID is your shutdown target regardless of what binary it's running.

**PID files:** [ProcessManagement wiki](https://mywiki.wooledge.org/ProcessManagement) — PID files are unreliable (PID reuse, stale files, daemon death without cleanup). Use only as a hint; verify with `lsof`.

---

## Q5: Idempotency of shutdown-DDL-restart

| Branch | Failure | Recovery |
|--------|---------|----------|
| SIGTERM ignored | MCP hung in C extension | `kill -KILL` after 10s timeout (SIGKILL is unblockable). Re-check `lsof`. |
| ALTER fails partway | Transaction conflict mid-DDL | DuckDB DDL is per-statement transactional. Each `ALTER` either commits or rolls back atomically. NO partial-state risk unless you wrap multiple ALTERs in a BEGIN/COMMIT block — don't. |
| ALTER fails entirely | Schema mismatch detected | Abort, restart MCP with old schema. State unchanged. |
| Restart fails | launchctl error, missing deps | MCP down — clients get connection refused. Log to systemd/launchctl error log. Manual debug. |
| Race: another writer between TERM and ALTER | Rare but possible | Wrap in advisory lock: `lsof` immediately before ALTER; if non-empty, retry. |

**Idempotency-safe recipe:**
```bash
set -e
LOCK_HOLDER=$(lsof -t graph.duckdb 2>/dev/null || true)
if [ -n "$LOCK_HOLDER" ]; then
  kill -TERM "$LOCK_HOLDER"
  for i in {1..10}; do
    sleep 1
    lsof -t graph.duckdb >/dev/null 2>&1 || break
  done
  lsof -t graph.duckdb >/dev/null 2>&1 && kill -KILL "$LOCK_HOLDER"
fi
# Re-check before ALTER
[ -z "$(lsof -t graph.duckdb 2>/dev/null)" ] || { echo "lock still held"; exit 1; }
duckdb graph.duckdb < migration.sql
# Restart
launchctl kickstart -k system/com.agent-infra.corpus-mcp
```

---

## Q6: Schema versioning as soft contract — alternative to shutdown

**Pattern:** The MCP server reads a `schema_meta(version INTEGER)` row on connect. If `version > expected`, the MCP triggers self-restart (SIGTERM itself, let launchd respawn it with new code path). Migration tool bumps version + does ALTER atomically.

**Problem:** This DOESN'T solve the lock conflict. The MCP must still release its connection before the migrator can ALTER. The "soft contract" pattern works in Postgres/MySQL because they support online DDL with reader-compatible locks. **DuckDB's exclusive-file-lock model makes self-restart equivalent to external shutdown — just self-initiated.**

Where it DOES help:
- Reduces RTO: MCP detects mismatch on next request, gracefully drains in-flight requests, releases lock, restarts. Migrator's wait window shrinks.
- Code organization: migrator doesn't need to know about MCP; MCP knows about its own schema dependency.

**Literature:** The "expand/contract" pattern ([HN thread](https://news.ycombinator.com/item?id=45776138), [Defacto](https://www.getdefacto.com/article/database-schema-migrations)) is the canonical soft-contract approach. It requires backward-compatible schema changes (add nullable columns, never drop in same deploy). Works in DuckDB IF you can avoid the lock window by using only ADD COLUMN (which still needs RW, but is fast).

**Recommendation:** For G0 one-shot, the shutdown protocol is fine. If migrations recur (>monthly), build schema_meta + preflight + self-restart-on-bump. It's not strictly better at the lock layer but reduces operator load.

---

## Q7: Cross-DB lock dependencies (Phase I)

**Plan:** Intel writes `theses.duckdb`, corpus writes `graph.duckdb`, pre-resolved crosswalk prevents intel from touching graph during writer lock.

**Verification needed:** Run these probes before Phase I:

```bash
# 1. Does intel ever open graph.duckdb?
git -C ~/Projects/intel grep -l "graph.duckdb" -- scripts/ src/

# 2. Does intel ATTACH graph.duckdb?
git -C ~/Projects/intel grep -E "ATTACH.*graph" -- scripts/ src/

# 3. Does the crosswalk pre-resolution actually materialize into theses.duckdb?
git -C ~/Projects/intel grep -l "crosswalk" -- scripts/
```

**Hidden coupling risks:**
- DuckDB `ATTACH` of `graph.duckdb` from intel's connection → acquires lock on graph too. Even read-only ATTACH requires the cross-process RO rules from Q1.
- Shared parquet exports — if intel reads `graph_exports/*.parquet` written by corpus, no lock issue.
- Symlinks: `ls -la ~/Projects/intel/data/` for any symlink to graph dir.

If grep is clean → pre-resolved crosswalk is sufficient. If any ATTACH or direct open exists → that's an additional shutdown coordination point.

---

## Sources

- [DuckDB Concurrency docs](https://duckdb.org/docs/current/connect/concurrency) — D1, official
- [Discussion #5946: Multi-process connections](https://github.com/duckdb/duckdb/discussions/5946) — D1, Mytherin (maintainer)
- [Issue #17158: Could not set lock on read_only](https://github.com/duckdb/duckdb/issues/17158) — D1, GitHub issue
- [Issue #618: ALTER transaction conflict](https://github.com/duckdb/duckdb/issues/618) — D1, GitHub issue
- [Issue #20570: UPDATE+DROP in transaction](https://github.com/duckdb/duckdb/issues/20570) — D1, Jan 2026
- [Issue #6477: Remove lock on DuckDB file](https://github.com/duckdb/duckdb/issues/6477) — D1, fcntl mechanism
- [Quack FAQ](https://duckdb.org/quack/faq) — D1, official, beta status
- [Analytics-Optimized Concurrent Transactions](https://duckdb.org/2024/10/30/analytics-optimized-concurrent-transactions) — D1, MVCC details
- [Quack v1.5.3 announcement](https://duckdb.org/2026/05/20/announcing-duckdb-153) — D1, core extension promotion
- [ProcessManagement wiki](https://mywiki.wooledge.org/ProcessManagement) — D2, PID-file unreliability
- [Expand/contract HN discussion](https://news.ycombinator.com/item?id=45776138) — D3, pattern context
- [Defacto schema migration article](https://www.getdefacto.com/article/database-schema-migrations) — D3, expand/contract practice

## Negative findings (no evidence found, worth flagging)

- No published guidance on DuckDB schema migrations from MotherDuck, Cloudflare, or Definite specifically addressing live-server DDL coordination.
- No DuckDB advisory-lock primitive (Postgres has `pg_advisory_lock`; DuckDB does not).
- No "online schema change" mode in DuckDB 1.5 docs. None planned for 2.0 per current roadmap.
- Quack lock semantics under multi-writer — FAQ doesn't address what happens when one client ALTERs while another reads. Untested; defer.

<!-- knowledge-index
generated: 2026-05-27T11:22:30Z
hash: 2632de87d289


end-knowledge-index -->
