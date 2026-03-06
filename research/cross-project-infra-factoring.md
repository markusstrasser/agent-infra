# Cross-Project Infrastructure Factoring

**Date:** 2026-03-06
**Scope:** intel, research, genomics, selve, meta, papers-mcp

---

## 1. Duplication Inventory

### Tier A: Identical code copy-pasted across projects

| Pattern | Intel | Research | Genomics | Meta | Papers-MCP | Copies | Total LOC |
|---------|-------|----------|----------|------|------------|--------|-----------|
| `load_jsonl()` | — | — | — | dashboard.py, agent_receipts.py, compaction-nuance.py | — | 3 | ~45 |
| `parse_ts()` (timestamp parsing) | — | — | — | dashboard.py, agent_receipts.py, hook-roi.py, compaction-nuance.py | — | 4 | ~80 |
| `weighted_mean()` | — | 10 files (nlscya, eclsk, pisa, nels, els, hsls, nlsy79, nlsy97, early_school) | — | — | — | 10 | ~40 |
| `weighted_var()` | — | 9 files (same as above) | — | — | — | 9 | ~36 |
| `weighted_standardize()` | — | 5 files (early_school_*, hsls, nels, els, nlsy97_behavior) | — | — | — | 5 | ~50 |
| `pooled_weighted_sd()` | — | nlsy97_stats, nlsy79_stats (+ 3 callers) | — | — | — | 2 | ~36 |
| Weighted Cohen's d | timss_common `weighted_effect` | 8 files (inline pattern) | — | — | — | 9 | ~180 |

### Tier B: Same pattern, different implementations

| Pattern | Intel | Research | Genomics | Meta | Papers-MCP | Impls | Total LOC |
|---------|-------|----------|----------|------|------------|-------|-----------|
| HTTP retry + backoff | `tools/lib/http.py` (195) | `download_nces_*.py` (~15) | `query_mastermind.py` (~35) | — | `discovery.py` + `openalex.py` (~50) | 4 | ~295 |
| SQLite WAL + schema init | — | — | — | orchestrator.py (25), runlog.py (25) | db.py (25) | 3 | ~75 |
| JSONL telemetry/logging | `tools/lib/telemetry.py` (124) | — | `pipeline_log.py` (110) | `config.py` (50) | — | 3 | ~284 |
| DuckDB connection mgmt | `tools/lib/db.py` (167) | (inline) | `variant_lakehouse.py` (304) | — | — | 2 | ~471 |
| File schema introspection | `tools/lib/schema.py` (62) | — | `lakehouse_materialize.py` (partial) | — | — | 2 | ~100 |
| Subprocess w/ timeout | — | — | `modal_utils.py` `run_cmd` (40) | `doctor.py` `run` (10) | — | 2 | ~50 |
| Content-addressable hash | — | — | `modal_utils.py` `StageSignature` (100) | `runlog_adapters/common.py` `stable_id` (30) | — | 2 | ~130 |
| Health check framework | — | — | `preflight.py` (279) | `doctor.py` (200) | — | 2 | ~479 |
| Checkpoint / file validation | `fetch_url.py` (partial) | — | `modal_utils.py` (40) | — | — | 2 | ~60 |

### Tier C: Single-project utilities that other projects would use

| Pattern | Location | LOC | Would benefit |
|---------|----------|-----|---------------|
| `DuckDBLock` (flock) | intel `tools/lib/db.py:99-167` | 68 | genomics (DuckDB lakehouse), research (future) |
| `normalize_name()` | intel `tools/lib/normalize.py` | 156 | research (entity matching), selve |
| `timed_run()` context manager | intel `tools/lib/telemetry.py:96-124` | 28 | genomics, meta |
| Admiralty source grading | intel `tools/lib/admiralty.py` | 178 | research (evidence quality) |
| `load_sav_from_zip()` | research `timss_common.py:29-39` | 11 | any survey data project |
| Jackknife variance | research `timss_common.py:83-117` | 35 | any replicate-weight survey |
| Plausible value MI + JK | research `timss_common.py:120-165` | 45 | any ILSAs (TIMSS, PISA, PIRLS) |

---

## 2. Extraction Plan

### Module 1: `shared.io` — JSONL, timestamps, hashing

**Purpose:** Eliminate the most-copied utility functions across meta scripts.

**Source of truth:** `meta/scripts/agent_receipts.py` (most robust `parse_ts`), `meta/scripts/dashboard.py` (`load_jsonl`)

**What moves:**
- `load_jsonl(path: Path) -> list[dict]` — from `agent_receipts.py:63-76`
- `write_jsonl(path: Path, rows: list[dict])` — from `agent_receipts.py:79+`
- `append_jsonl(path: Path, entry: dict)` — consolidate from `config.py:21-25`, `telemetry.py:70-71`
- `parse_ts(value) -> datetime | None` — from `agent_receipts.py:35-54` (handles str, int, float, None)
- `stable_id(prefix: str, *parts) -> str` — from `runlog_adapters/common.py:157-170`
- `sha256_file(path: Path) -> str` — from `runlog.py:35-40`

**What stays:** Project-specific callers unchanged — just `from shared.io import load_jsonl, parse_ts`

**Dependencies:** stdlib only (json, datetime, hashlib, pathlib)

**Migration risk:** LOW. Pure functions, no state, no side effects.

---

### Module 2: `shared.http` — Session, retry, streaming downloads

**Purpose:** One HTTP retry implementation instead of four.

**Source of truth:** `intel/tools/lib/http.py` — most complete (195 lines, covers session setup, manual backoff, atomic streaming, rate limiting)

**What moves:**
- `get_session(user_agent, max_retries, backoff_factor, status_forcelist, timeout)` — http.py:35-78
- `fetch_with_retry(session, url, *, max_retries, timeout, sleep_base, raise_on_failure)` — http.py:81-127
- `fetch_streaming(session, url, dest, *, chunk_size, timeout, max_retries, sleep_base)` — http.py:130-190
- `rate_limit_sleep(seconds)` — http.py:193-195
- Move `USER_AGENTS` dict but make it extensible (projects can register their own)

**What stays:**
- `intel/tools/fetch_url.py` — stays as intel CLI tool, imports shared HTTP
- `papers-mcp/discovery.py` — keeps httpx+tenacity (different HTTP library); no change
- `genomics/query_mastermind.py` — refactor to use shared.http.get_session

**Dependencies:** `requests`, `urllib3`

**Migration risk:** LOW. Intel's `http.py` already has zero intel-specific code. Genomics uses `requests` too. Papers-MCP uses `httpx` — leave it alone.

---

### Module 3: `shared.stats` — Weighted statistics and effect sizes

**Purpose:** Eliminate 10+ copies of `weighted_mean`/`weighted_var`/`weighted_standardize` in research, and provide a shared effect-size toolkit.

**Source of truth:** Research `timss_common.py` for survey stats; intel `scoring.py` for Bayesian stats. These serve different purposes and should be separate submodules.

**What moves into `shared.stats.weighted`:**
- `weighted_mean(values, weights)` — consolidate from 10 research files
- `weighted_var(values, weights)` — consolidate from 9 research files
- `weighted_standardize(values, weights)` — consolidate from 5 research files
- `pooled_weighted_sd(values, weights, group_mask)` — from `nlsy97_stats_pipeline.py:101-119`
- `cohens_d_weighted(values, weights, group_mask, min_n=30)` — from `timss_common.py:49-80`

**What moves into `shared.stats.survey`:**
- `jackknife_variance(values, weights, group_mask, jkzone, jkrep)` — from `timss_common.py:83-117`
- `plausible_value_summary(estimates, sampling_vars)` — generalize from `timss_common.py:120-165`
- `load_sav_from_zip(zip_path, member, usecols)` — from `timss_common.py:29-39`

**What stays:**
- `intel/tools/lib/scoring.py` — stays in intel. Its LLR/EB/Bayes functions are intel-specific calibration tools. The generic statistics it contains (Welch t, Stouffer, BH FDR) could move eventually but aren't duplicated elsewhere yet.
- Research scripts keep their domain logic, just `from shared.stats.weighted import weighted_mean, cohens_d_weighted`

**Dependencies:** `numpy`, `pandas` (optional, for Series overloads), `pyreadstat` (optional, for `load_sav_from_zip`)

**Migration risk:** MEDIUM. The 10 research files that define `weighted_mean` need import changes. But each is self-contained — change one at a time, run the script, verify output matches.

---

### Module 4: `shared.db` — SQLite and DuckDB helpers

**Purpose:** Consolidate 3 identical SQLite init patterns and the DuckDB file-locking pattern.

**What moves into `shared.db.sqlite`:**
- `get_sqlite_db(path, schema_sql, *, wal=True, busy_timeout=5000, foreign_keys=False)` — consolidate from:
  - `meta/orchestrator.py:71-76`
  - `meta/runlog.py:43-50`
  - `papers-mcp/db.py:48-56`
- `migrate_columns(db, table, migrations: list[str])` — from `papers-mcp/db.py:58-63`

**What moves into `shared.db.duckdb`:**
- `DuckDBLock(lock_path, exclusive, timeout)` — from `intel/tools/lib/db.py:99-167`, parameterize lock path
- `view_exists(con, name)` — from `intel/tools/lib/db.py:76-82`
- `get_memory_connection()` — from `intel/tools/lib/db.py:85-89`
- `describe_file(file_path)` — from `intel/tools/lib/schema.py:24-46`
- `get_columns(file_path)` — from `intel/tools/lib/schema.py:49-51`
- `validate_columns(file_path, required)` — from `intel/tools/lib/schema.py:59-62`

**What stays:**
- `intel/tools/lib/db.py` — keep `get_connection()`, `get_state_connection()`, `check_stale_paths()` (project-specific paths). Import `DuckDBLock` from shared.
- `papers-mcp/db.py` — keep `PaperDB` class (domain-specific). Init uses `shared.db.sqlite.get_sqlite_db()`.
- `genomics/variant_lakehouse.py` — keep as-is (its DuckDB-over-Parquet pattern is more specialized)

**Dependencies:** `sqlite3` (stdlib), `duckdb` (optional), `fcntl` (stdlib, macOS/Linux)

**Migration risk:** LOW for SQLite (drop-in replacement). LOW for DuckDB lock (parameterize path, same API).

---

### Module 5: `shared.telemetry` — Structured operation logging

**Purpose:** One JSONL telemetry pattern instead of three.

**Source of truth:** `intel/tools/lib/telemetry.py` — best API design (log_run + timed_run context manager)

**What moves:**
- `log_run(job_name, *, log_path, inputs, outputs, duration_ms, status, error, row_counts)` — from `telemetry.py:34-71`, add `log_path` parameter
- `timed_run(job_name, *, log_path, inputs)` — from `telemetry.py:96-124`
- `_RunContext` class — from `telemetry.py:74-93`
- `log_event(event_name, *, log_path, **fields)` — consolidate `config.py:log_metric` and `config.py:log_hook_event`

**What stays:**
- `genomics/pipeline_log.py` `PipelineLogger` — keeps Modal volume commit integration (Modal-specific). Could optionally wrap `shared.telemetry.log_run` for the JSONL part.
- `meta/config.py` — replace `log_metric`/`log_hook_event` with `shared.telemetry.log_event`

**Dependencies:** stdlib only (json, os, socket, time, datetime, pathlib, contextlib)

**Migration risk:** LOW. All three implementations write to JSONL with the same schema shape.

---

### Module 6: `shared.env` — Environment and API key helpers

**Purpose:** Standardize .env.local loading and project root discovery.

**Source of truth:** `intel/tools/lib/env.py` (34 lines)

**What moves:**
- `get_key(name, *, env_file=".env.local")` — from `env.py`, parameterize env file path
- `find_project_root(marker_files=("pyproject.toml", ".git"))` — new utility to replace hardcoded `Path(__file__).parent.parent.parent` patterns

**Dependencies:** stdlib only

**Migration risk:** TRIVIAL.

---

## 3. Proposed Project Structure

```
~/Projects/lib/
├── pyproject.toml          # name = "shared-lib", no heavy deps by default
├── src/
│   └── shared/
│       ├── __init__.py
│       ├── io.py           # JSONL, timestamps, hashing (~80 lines)
│       ├── http.py          # Session, retry, streaming (~200 lines)
│       ├── env.py           # API keys, project root (~40 lines)
│       ├── telemetry.py     # Structured JSONL logging (~130 lines)
│       ├── db/
│       │   ├── __init__.py
│       │   ├── sqlite.py    # WAL init, migrations (~50 lines)
│       │   └── duckdb.py    # Lock, schema introspection (~150 lines)
│       └── stats/
│           ├── __init__.py
│           ├── weighted.py  # weighted_mean/var/sd, Cohen's d (~100 lines)
│           └── survey.py    # JK variance, MI, SPSS loader (~100 lines)
└── tests/
    ├── test_io.py
    ├── test_http.py
    ├── test_stats.py
    └── test_db.py
```

**pyproject.toml:**
```toml
[project]
name = "shared-lib"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []  # zero required deps — everything optional

[project.optional-dependencies]
http = ["requests>=2.31"]
duckdb = ["duckdb>=1.0"]
stats = ["numpy>=1.24"]
survey = ["numpy>=1.24", "pandas>=2.0", "pyreadstat>=1.2"]
all = ["shared-lib[http,duckdb,stats,survey]"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/shared"]
```

**Consumer projects add as path dependency:**
```toml
# In intel/pyproject.toml
dependencies = [
    "shared-lib[http,duckdb] @ file:///${PROJECT_ROOT}/../lib",
    ...
]

# Or via uv sources:
[tool.uv.sources]
shared-lib = { path = "../lib" }
```

---

## 4. Migration Order

Each step is independently committable and testable.

### Step 1: `shared.io` (JSONL + timestamps)
**Value:** HIGH (eliminates 3 copies of `load_jsonl`, 4 copies of `parse_ts` within meta alone)
**Risk:** TRIVIAL (pure functions, stdlib only, no external deps)
**Verify:** Run `uv run python3 scripts/dashboard.py` and `uv run python3 scripts/agent_receipts.py sync-codex` — output identical

### Step 2: `shared.stats.weighted` (weighted statistics)
**Value:** HIGH (eliminates 10+ copies of `weighted_mean` in research)
**Risk:** LOW (pure functions, but need to update 10 files)
**Verify:** For each research script, run before/after and diff the TSV output

### Step 3: `shared.http` (HTTP retry)
**Value:** MEDIUM (intel already has it factored; mainly benefits genomics)
**Risk:** LOW (intel's existing implementation is battle-tested)
**Verify:** Run one intel download script and one genomics script that uses HTTP

### Step 4: `shared.db.sqlite` (SQLite init)
**Value:** MEDIUM (3 implementations, but they're small)
**Risk:** LOW (drop-in replacement)
**Verify:** `orchestrator.py status`, `runlog.py stats`, papers-mcp server start

### Step 5: `shared.db.duckdb` (DuckDB lock + schema)
**Value:** MEDIUM (DuckDBLock is high-quality; schema introspection prevents column-guessing bugs)
**Risk:** LOW (intel's implementation is production-proven)
**Verify:** `intel/tools/setup_duckdb.py` with concurrent readers

### Step 6: `shared.telemetry` (operation logging)
**Value:** LOW-MEDIUM (3 implementations but not heavily duplicated)
**Risk:** LOW
**Verify:** Check JSONL output format matches expectations

### Step 7: `shared.stats.survey` (JK/MI/SPSS)
**Value:** LOW (only used in research, but prevents future duplication)
**Risk:** LOW (timss_common.py is well-tested)
**Verify:** Run TIMSS analysis scripts, compare output

### Step 8: `shared.env` (API keys)
**Value:** LOW (small utility, but standardizes a pattern)
**Risk:** TRIVIAL
**Verify:** Any script that calls `get_key()`

---

## 5. What I Decided NOT to Extract and Why

| Candidate | Why not |
|-----------|---------|
| **intel `scoring.py`** (799 lines: LLR, EB shrinkage, evidence fusion) | Only used in intel. Despite being generic statistics, there's no second consumer. The weighted stats overlap (Cohen's d) is extracted separately. Move scoring.py when a second project needs Bayesian LLR. |
| **intel `normalize.py`** (entity name normalization, 156 lines) | Only intel does entity name matching. Generic, but single user. |
| **intel `admiralty.py`** (source grading, 178 lines) | The architecture is generic but the grade tables are intel-specific. Already exists as a skill (`source-grading`). |
| **intel `watchlist.py`**, `xwalk.py`, `signal_schema.py`, `sentinels.py` | Domain-specific to investment research. |
| **intel `claim_extraction.py`**, `falsification.py`**, `ach_scorer.py` | Intel-specific methodology. ACH is already a skill. |
| **genomics `PipelineLogger`** | Tightly coupled to Modal volume commits. Pattern overlaps with `shared.telemetry` but the Modal integration makes it genomics-specific. |
| **genomics `StageSignature`** (content-addressable caching) | Excellent pattern but only genomics has multi-stage pipelines. Would extract when orchestrator or another project needs input-hash-based cache invalidation. |
| **genomics `preflight.py`** | Overlaps conceptually with `meta/doctor.py` but the check registries are completely different. Extract only if a third project needs preflight checks. |
| **genomics `run_cmd()`** (subprocess wrapper) | 40 lines. Not enough duplication to justify a shared module. `subprocess.run()` with `capture_output=True, timeout=N` is already pretty clean. |
| **papers-mcp `PaperDB`** | Domain-specific (papers schema). The SQLite init pattern moves to shared, but the rest stays. |
| **papers-mcp httpx+tenacity retry** | Different HTTP library (httpx vs requests). Not worth unifying — let projects pick their HTTP client. |
| **research `stage0_config.py`** | Excellent config pattern (314 lines) but entirely dataset-specific. The pattern is "use a Python module as config" — that's a convention, not a library. |
| **research `timss_common.py` domain functions** | `member_country_code()`, `plausible_value_summary()` with TIMSS-specific column names (ITSEX, TOTWGT, JKZONE) — stays in research. Only the generic statistical functions move. |
| **selve `search.py`** (2100+ lines) | Massive semantic search system. Only selve uses it. Papers-MCP uses a completely different search approach (API clients). |
| **meta `orchestrator.py`** | Task queue is meta-specific. The Agent SDK wrapper pattern is interesting but too coupled to orchestrator's status machine. |
| **Skills** | Already in `~/Projects/skills/`. Not a library concern. |
| **Hooks** | Already in `~/Projects/skills/hooks/`. Not a library concern. |

---

## Impact Summary

| Metric | Before | After |
|--------|--------|-------|
| Copies of `weighted_mean` | 10 | 1 |
| Copies of `load_jsonl` | 3 | 1 |
| Copies of `parse_ts` | 4 | 1 |
| SQLite init patterns | 3 | 1 |
| HTTP retry implementations | 4 | 2 (shared + papers-mcp httpx) |
| JSONL telemetry patterns | 3 | 1 (+ genomics Modal-specific) |
| Total duplicated LOC eliminated | ~900 | — |
| New shared library LOC | — | ~850 |
| Projects consuming shared lib | — | intel, research, meta, genomics |
