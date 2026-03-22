---
title: Cross-Project Infrastructure Factoring (v3)
date: 2026-03-06
---

# Cross-Project Infrastructure Factoring (v3)

**Date:** 2026-03-06
**Scope:** intel, research, genomics, selve, meta, research-mcp, emb

---

## 0. Architectural Assessment: Are There More `emb`-Level Extractions?

**Answer: No.** After deep architectural analysis of all major subsystems, the projects are more different than similar at the system level. `emb` worked because embeddings are a **pure, domain-agnostic capability** with a clean interface (text in → vector out). No other cross-project pattern meets that bar.

### Why each candidate fails

| Candidate system | Projects | Why it doesn't extract |
|-----------------|----------|----------------------|
| **Dataset ingestion pipeline** (manifest → download → validate → catalog → DuckDB views) | intel (full), genomics (simple) | Intel's value is in domain-specific parts: per-source rate limits (SEC 0.1s, LDA 2.5s), UA spoofing by domain, healthcare/SEC/nonprofit domain categories, 50+ dataset-specific views. The generic kernel (manifest-driven download with validation) is ~200 lines — too thin for a project, and the domain config IS the system. |
| **Pipeline DAG executor** (stage specs → async execution → QC gates → checkpointing) | genomics (full DAG), meta (task queue), intel (bash script) | Fundamentally different systems. Genomics: data pipeline producing files on Modal NFS, async subprocess executor, content-addressable caching via StageSignature. Meta: agent task queue with approval gates, Claude SDK engine, SQLite state, cost caps. Intel: sequential bash with criticality tiers. The overlap (dependency tracking, state) is thin; the differences (execution model, state storage, scheduling) dominate. |
| **Agent telemetry / observability** | meta, intel, genomics | It's JSONL append with timestamps. ~30 lines of code. A standalone project for 30 lines is absurd. Belongs in shared-lib as a module, not a project. |
| **MCP server framework** | meta, research-mcp, intel | FastMCP IS the framework. The shared pattern (lifespan + SQLite WAL init + tool registration) is a cookiecutter template for scaffolding new servers, not runtime-importable code. |
| **Content-addressable caching** | genomics (StageSignature) | Only genomics uses it. Strongest future extraction candidate — if meta's orchestrator or intel's daily pipeline ever needs "skip if inputs unchanged" logic, extract then. Not today. |
| **Health check / preflight** | meta (doctor.py), genomics (preflight.py) | Same concept (accumulate checks, report), completely different check registries. The Check class is ~20 lines; the value is in what gets checked, which is 100% project-specific. |

### What this means

~~The right extraction is a shared utility library — not a new standalone project.~~

**Decision (2026-03-06): Shared library plan killed.** After model review and user assessment, the shared-lib approach was abandoned. Key reasoning:
1. AI agents write trivial utility functions (parse_ts, safe_float, load_jsonl) fine — deduplication ROI is near-zero when agents generate code.
2. The only high-value shared problem is **web scraping infrastructure** (SSL fallback chains, Cloudflare bypass, HTML trap detection) — ~1000 lines of brittle code across intel and research.
3. **Solution: paid APIs replace shared code.** Scrapfly ($0-30/month) for government data downloads + Browserbase (free tier) for auth-gated sites. An API key replaces a library.

See execution plan: `.claude/plans/65730c3c-shared-lib.md` (web scraping infrastructure).

**Future triggers for new extractions:**
- If a 3rd project needs content-addressable caching → extract `sigcache` from genomics StageSignature
- If we build 2+ more MCP servers → extract a cookiecutter template (not a library)
- If intel's dataset pipeline patterns show up in genomics data downloads → extract `datapipe` manifest system

---

## 1. Duplication Inventory

### Tier A: Identical code copy-pasted (same function, 2+ places)

| Pattern | Where | Copies | LOC each |
|---------|-------|--------|----------|
| `load_jsonl(path) -> list[dict]` | meta: dashboard.py, agent_receipts.py, compaction-nuance.py | 3 | 13 |
| `parse_ts(value) -> datetime` | meta: dashboard.py, agent_receipts.py, hook-roi.py, compaction-nuance.py | 4 | 15-20 |
| `safe_float(value) -> float\|None` | genomics: variant_evidence_core.py, modal_annotsv_manta.py, generate_review_packets.py (x2), modal_local_ancestry.py, modal_ancestry_admixture.py | 5 | 8-12 |
| `weighted_mean(values, weights)` | research: 10 files (nlscya, eclsk, eclsk2011, pisa, nels, els, hsls×2, nlsy79, nlsy97_transcript) | 10 | 3-4 |
| `weighted_var(values, weights)` | research: same 9 files | 9 | 3-4 |
| `weighted_standardize(values, weights)` | research: 5 files (early_school×2, hsls_wedge, nels, els, nlsy97_behavior) | 5 | 6-8 |

### Tier B: Same problem, different implementations (pattern duplication)

| Pattern | Implementations | Projects |
|---------|----------------|----------|
| **Atomic file write** (.tmp + rename) | intel http.py:161-174, intel download_manifest.py:63-68, intel paper_ledger.py:289-291, intel prediction_tracker.py:124-126, intel download_datasets.py:2188+2223, genomics modal_utils.py (log_stage_state) | intel, genomics |
| **fcntl file locking** | intel db.py:99-145 (DuckDBLock class), intel download_manifest.py:65-67, meta orchestrator.py:108-114, selve agent_coord.py:125-148 | intel, meta, selve |
| **HTML trap detection** (downloaded file is actually an error page) | intel fetch_url.py:28 `is_html_trap`, intel download.py:166 `_is_html_trap`, intel setup_duckdb.py:135 `_is_csv_content`, intel setup_duckdb.py:150 `_is_real_file` | intel (4× internal) |
| **SQLite WAL + schema init** | meta orchestrator.py:71-76, meta runlog.py:43-50, research-mcp db.py:48-56 | meta, research-mcp |
| **SQLite column migration** (ALTER TABLE ... ADD COLUMN, catch OperationalError) | meta orchestrator.py:82-92, research-mcp db.py:58-63 | meta, research-mcp |
| **JSONL append with timestamp** (telemetry/metrics) | intel telemetry.py:34-71 `log_run`, genomics pipeline_log.py:61-65 `_write`, meta config.py:21-25 `log_metric` | intel, genomics, meta |
| **Timed operation context manager** | intel telemetry.py:96-124 `timed_run`, genomics modal_utils.py `init_stage/finalize_stage` | intel, genomics |
| **HTTP retry + exponential backoff** (requests-based) | intel http.py:81-127 `fetch_with_retry`, genomics query_mastermind.py:99-132 `_api_get` | intel, genomics |
| **Streaming file download** (chunked + validate) | intel http.py:130-190 `fetch_streaming`, research download_nces.py `stream_download` | intel, research |
| **DuckDB schema introspection** | intel schema.py:24-46 `_fetch_schema`, genomics variant_lakehouse.py `create_connection` | intel, genomics |
| **Health check accumulation** (collect errors, report at end) | meta doctor.py (Check class), genomics preflight.py (279 lines), genomics pipeline_qc_gates.py | meta, genomics |
| **Config file discovery** (try multiple candidate paths) | genomics variant_evidence_core.py:13-26 `resolve_threshold_config` | genomics (but universal problem) |
| **Content-addressable hashing** | genomics modal_utils.py:273-375 StageSignature, meta runlog_adapters/common.py:157-170 stable_id | meta, genomics |
| **MCP server lifespan** (FastMCP + async context + shared clients) | research-mcp server.py:27-70, meta meta_mcp.py | meta, research-mcp |

### Tier C: Within-project duplication worth noting

| Pattern | Where | Count | LOC each |
|---------|-------|-------|----------|
| CSV DictWriter boilerplate | intel: 46 scripts use identical 4-line write pattern | 46 | 4 |
| Hardcoded PROJECT_ROOT / DATASETS | intel: 61 scripts ignore existing `lib/paths.py` | 61 | 3-5 |
| `_is_csv_content` / `_is_html_trap` | intel: fetch_url.py, download.py, setup_duckdb.py | 4 | 10-15 |

---

## 2. Extraction Plan

### Module 1: `shared.io` — JSONL, timestamps, atomic writes, safe coercion

**Purpose:** The most-copied functions across all projects.

**What moves (source of truth in parens):**
- `load_jsonl(path) -> list[dict]` — (meta agent_receipts.py:63-76)
- `write_jsonl(path, rows)` — (meta agent_receipts.py:79+)
- `append_jsonl(path, entry)` — consolidate from config.py:21-25, telemetry.py:70-71
- `parse_ts(value) -> datetime | None` — (meta agent_receipts.py:35-54, handles str/int/float/None, UTC normalization)
- `stable_id(prefix, *parts) -> str` — (meta runlog_adapters/common.py:157-170)
- `sha256_file(path) -> str` — (meta runlog.py:35-40)
- `atomic_write(path, content_fn, *, suffix=".tmp")` — consolidate from 6+ intel atomic-write sites
- `safe_float(value) -> float | None` — (genomics variant_evidence_core.py:51-62, handles "", ".", "NA", "nan", "None")
- `is_html_trap(content_type, first_bytes) -> bool` — (intel fetch_url.py:28-45, consolidate 4 intel variants)

**Dependencies:** stdlib only

**Migration risk:** LOW. Pure functions. Biggest win is within-meta (7 copies) and within-genomics (5 copies of safe_float).

**Consumers:** meta (7 scripts), genomics (5 scripts), intel (4+ scripts for HTML trap + atomic write)

---

### Module 2: `shared.files` — File locking + validated downloads

**Purpose:** Consolidate the 4 different fcntl locking implementations and the download-validation pattern.

**What moves:**
- `FileLock(path, *, exclusive=False, timeout=30)` — generalize from intel DuckDBLock (db.py:99-145). Same context-manager API, parameterized path instead of hardcoded DB_PATH. Includes `_find_holders()` diagnostics via lsof.
- `atomic_download(session, url, dest, *, chunk_size=8192, timeout=1800, max_retries=3, validate=True) -> bool` — merge intel http.py:130-190 `fetch_streaming` + fetch_url.py:28 `is_html_trap`. Downloads to .tmp, validates not HTML error page, atomic rename.
- `verify_file(path, *, min_bytes=None, not_html=True) -> tuple[bool, str]` — merge intel setup_duckdb.py `_is_csv_content`/`_is_real_file` + genomics modal_utils.py `validate_file`

**What stays:**
- intel `DuckDBLock` becomes a thin wrapper: `FileLock(DB_PATH.parent / ".duckdb.lock", exclusive=exclusive, timeout=timeout)`
- selve `agent_coord.py` — keep as-is (different purpose: agent coordination, not file safety)
- genomics `checkpoint_exists()` — stays (it does vol.reload() which is Modal-specific)

**Dependencies:** stdlib (fcntl, os, pathlib, time, subprocess)

**Migration risk:** LOW. The intel DuckDBLock API is preserved exactly. Other locking sites simplify.

**Consumers:** intel (DuckDB lock + download verification), meta (orchestrator lock), genomics (file validation)

---

### Module 3: `shared.db` — SQLite init + DuckDB helpers

**Purpose:** Three identical SQLite init patterns; DuckDB schema introspection useful in 2+ projects.

**What moves:**
```python
# SQLite
def get_db(path, schema_sql=None, *, wal=True, busy_timeout=5000,
           foreign_keys=False, row_factory=True) -> sqlite3.Connection

def migrate_columns(db, migrations: list[str])
# tries each ALTER TABLE, catches OperationalError (column exists)

# DuckDB
def describe_file(file_path) -> list[tuple[str, str]]  # (col_name, col_type)
def get_columns(file_path) -> list[str]
def validate_columns(file_path, required) -> list[str]  # returns missing
```

**Source of truth:**
- SQLite: meta runlog.py:43-50 (most complete — WAL + foreign_keys + row_factory)
- DuckDB schema: intel schema.py (62 lines, cleanly factored)
- Migration: research-mcp db.py:58-63

**Dependencies:** sqlite3 (stdlib), duckdb (optional extra)

**Migration risk:** LOW. Drop-in replacements.

**Consumers:** meta (orchestrator, runlog), research-mcp, intel, genomics

---

### Module 4: `shared.telemetry` — Operation logging + timing

**Purpose:** Three projects write timestamped JSONL telemetry with identical schemas.

**What moves:**
- `log_event(event_name, *, log_path, **fields)` — consolidate config.py:log_metric, config.py:log_hook_event. One function that appends `{ts, event, **fields}` to JSONL.
- `timed_run(job_name, *, log_path, inputs=None)` — from intel telemetry.py:96-124. Context manager that auto-logs duration, status, error.

**What stays:**
- genomics `PipelineLogger` — keeps Modal volume.commit() integration. Could internally use `shared.telemetry.log_event` for the JSONL writing, but the class stays in genomics.
- intel `telemetry.py` — becomes thin wrapper importing from shared

**Dependencies:** stdlib only

**Migration risk:** LOW.

---

### Module 5: `shared.http` — Session + retry (requests-based)

**Purpose:** Intel's http.py is already project-agnostic. Publishing it as shared lets genomics use it instead of reimplementing.

**What moves:** Intel `tools/lib/http.py` as-is (195 lines). Zero changes needed — it's already generic.
- `get_session(user_agent, max_retries, backoff_factor, status_forcelist, timeout)`
- `fetch_with_retry(session, url, *, max_retries, timeout, sleep_base, raise_on_failure)`
- `rate_limit_sleep(seconds)`

**Note:** `fetch_streaming` moves to `shared.files.atomic_download` (Module 2) since it's really a file operation with HTTP as transport.

**What doesn't move:** research-mcp stays on httpx+tenacity (different ecosystem, no benefit to unifying).

**Dependencies:** requests, urllib3

**Migration risk:** TRIVIAL. Literally moving a file.

**Consumers:** intel (already using it), genomics (replace query_mastermind._api_get)

---

### Module 6: `shared.env` — API keys + project root discovery + config file resolution

**Purpose:** Standardize the 3 different approaches to finding config/env files.

**What moves:**
- `get_key(name, *, env_file=".env.local")` — from intel env.py (34 lines)
- `find_project_root(markers=("pyproject.toml", ".git"))` — new, replaces 61+ hardcoded `Path(__file__).parent.parent.parent` in intel
- `resolve_config(filename, candidates=None)` — from genomics variant_evidence_core.py:13-26 pattern. Tries multiple candidate directories, raises FileNotFoundError listing all candidates tried.

**Dependencies:** stdlib only

**Migration risk:** TRIVIAL.

---

## 3. Proposed Project Structure

```
~/Projects/lib/
├── pyproject.toml
├── src/
│   └── shared/
│       ├── __init__.py
│       ├── io.py           # JSONL, timestamps, hashing, safe_float, html_trap (~120 lines)
│       ├── files.py         # FileLock, atomic_download, verify_file (~120 lines)
│       ├── http.py          # Session, retry — intel http.py verbatim (~200 lines)
│       ├── env.py           # API keys, project root, config resolution (~60 lines)
│       ├── telemetry.py     # log_event, timed_run (~80 lines)
│       └── db.py            # get_db (SQLite), describe_file (DuckDB) (~100 lines)
└── tests/
    ├── test_io.py
    ├── test_files.py
    ├── test_db.py
    └── test_telemetry.py
```

**~680 lines total.** No `stats/` module — use numpy/scipy/pingouin.

```toml
[project]
name = "shared-lib"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []  # everything optional

[project.optional-dependencies]
http = ["requests>=2.31"]
duckdb = ["duckdb>=1.0"]
all = ["shared-lib[http,duckdb]"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/shared"]
```

**Consumer projects:**
```toml
# uv sources (preferred)
[tool.uv.sources]
shared-lib = { path = "../lib" }
```

Precedent: `emb` library already works this way (selve depends on `../emb`).

---

## 4. Migration Order

### Step 1: `shared.io` — JSONL + timestamps + safe_float + html_trap
**Value:** HIGHEST. Eliminates 7 copies within meta, 5 copies of safe_float in genomics, 4 copies of html_trap in intel.
**Risk:** TRIVIAL (pure functions, stdlib only)
**Verify:** `uv run python3 scripts/dashboard.py`, `uv run python3 scripts/agent_receipts.py sync-codex`

### Step 2: `shared.files` — FileLock + atomic_download + verify_file
**Value:** HIGH. The DuckDBLock pattern is non-trivial (68 lines, with lsof diagnostics and timeout). Used in 4 places across 3 projects. Atomic-write pattern in 6+ places.
**Risk:** LOW (context manager API preserved exactly)
**Verify:** `intel/tools/setup_duckdb.py` with concurrent readers, orchestrator tick under lock

### Step 3: `shared.db` — SQLite init + DuckDB schema
**Value:** MEDIUM. 3 SQLite init copies, 2 DuckDB schema introspection copies.
**Risk:** LOW
**Verify:** `orchestrator.py status`, `runlog.py stats`, research-mcp server start

### Step 4: `shared.http` — Session + retry
**Value:** MEDIUM. Intel's http.py is already the extraction — just publish it.
**Risk:** TRIVIAL (literally moving a file)
**Verify:** Any intel download script

### Step 5: `shared.telemetry` — log_event + timed_run
**Value:** MEDIUM. 3 implementations.
**Risk:** LOW
**Verify:** Check JSONL output format

### Step 6: `shared.env` — API keys + config resolution
**Value:** LOW-MEDIUM. Small functions but standardizes a pattern.
**Risk:** TRIVIAL

---

## 5. What I Decided NOT to Extract and Why

### Use existing libraries instead

| Candidate | Use this instead |
|-----------|-----------------|
| `weighted_mean()` (10 copies in research) | `np.average(values, weights=weights)` — built into numpy |
| `weighted_var()` (9 copies) | `np.average((values - np.average(values, weights=weights))**2, weights=weights)` |
| `pooled_weighted_sd()`, Cohen's d | `pingouin.compute_effsize` or inline with numpy (3 lines) |
| `weighted_standardize()` (5 copies) | `(values - np.average(values, w=w)) / np.sqrt(weighted_var)` — 2 lines |
| Jackknife variance | Stay in `timss_common.py` — too specialized for a library, but the research project should deduplicate internally by importing from timss_common instead of copy-pasting |
| Meta-analysis (DerSimonian-Laird) | `statsmodels.stats.meta_analysis` or the `meta-analysis` PyPI package |

**Action for research:** Don't extract — just make the 10 files import from one local `research/sources/iq-sex-diff/stats_common.py` that calls numpy. Internal refactor, not a shared library.

### Too few consumers (single project, no realistic second user)

| Candidate | Why not |
|-----------|---------|
| intel `scoring.py` (799 lines: LLR, EB, Bayes) | Only intel. Move when a second project needs Bayesian scoring. |
| intel `normalize.py` (entity name normalization) | Only intel does entity matching. |
| intel `watchlist.py`, `xwalk.py`, `sentinels.py`, `signal_schema.py` | Intel-domain. |
| intel `claim_extraction.py`, `falsification.py`, `ach_scorer.py` | Intel-domain. ACH is already a skill. |
| intel `admiralty.py` (source grading) | Already exists as a skill. Grade tables are intel-specific. |
| genomics `PipelineLogger` | Coupled to Modal volume commits. |
| genomics `StageSignature` (content-addressable caching) | Only genomics has multi-stage pipelines. Extract if orchestrator needs it. |
| genomics `preflight.py` | Overlaps with meta doctor.py conceptually, but check registries are completely different. |
| genomics `Sample` dataclass (path management) | Genomics-specific path conventions. |
| genomics `pipeline_stages.py` (stage DAG) | Genomics pipeline-specific. |
| research-mcp `PaperDB`, `SemanticScholar`, `OpenAlex` | Domain-specific API clients. |
| research-mcp CAG (Gemini 1M context) | Specialized to research-mcp. |
| selve `search.py` (2100+ lines) | Massive, selve-specific. emb already extracted as shared lib. |
| selve connector/parser pattern | Architectural pattern, not a library. |
| meta `orchestrator.py` task state machine | Meta-specific. |
| meta `doctor.py` Check class | Only meta uses it. Genomics has preflight.py with different structure. Would extract if a third project needed health checks. |
| meta `runlog_adapters/*` | Specific to vendor-specific session parsing. |

### Pattern, not code (conventions beat libraries)

| Pattern | Why not a library |
|---------|------------------|
| Config-as-Python-module (research stage0_config.py) | Convention: "put your config in a .py module." No code to extract. |
| Frozen dataclass + hash (genomics wgs_config.py) | Convention: "use frozen dataclasses + SHA256 for config versioning." Write it up, don't library-ify it. |
| CSV DictWriter 4-line boilerplate (intel, 46 scripts) | Too thin. The boilerplate IS the pattern. Wrap if you want, but `csv.DictWriter` is already the API. |
| Subprocess with timeout (10-40 lines) | `subprocess.run(cmd, capture_output=True, timeout=N)` is already clean enough. |

---

## 6. Within-Project Cleanup (Not Shared, But Worth Doing)

These aren't cross-project extractions but were found during the scan:

### Intel
- **61 scripts ignore `lib/paths.py`** — hardcode `PROJECT_ROOT = Path(__file__).resolve().parent.parent`. Retrofit imports.
- **4 variants of HTML trap detection** — consolidate into `lib/http.py` or `lib/validation.py`.
- **`download.py` reimplements `lib/http.py`** (has its own rate-limit dict + User-Agent map). Should import from lib/http.py.
- **46 scripts duplicate CSV DictWriter setup** — not worth abstracting, but worth a code review to standardize.

### Research
- **10 files define `weighted_mean`** — import from numpy or create one local `stats_common.py`.
- **3 files define `parse_numeric` with MISSING_CODES** — consolidate into one research-local utility.
- **`meta_analysis.py` reimplements DerSimonian-Laird** — replace with `statsmodels.stats.meta_analysis`.

### Genomics
- **5 files define `_safe_float`** with slightly different signatures — consolidate into `variant_evidence_core.py` (already the best version) and import from there, OR move to shared.io.

### Meta
- **4 files define `parse_ts`** — highest priority for shared.io extraction.
- **3 files define `load_jsonl`** — same.

---

## Impact Summary

| Metric | Before | After |
|--------|--------|-------|
| `load_jsonl` copies | 3 (meta) | 1 (shared.io) |
| `parse_ts` copies | 4 (meta) | 1 (shared.io) |
| `safe_float` copies | 5 (genomics) | 1 (shared.io) |
| HTML trap detection copies | 4 (intel) | 1 (shared.io) |
| Atomic write patterns | 6+ (intel, genomics) | 1 (shared.files) |
| fcntl locking implementations | 4 (intel, meta, selve) | 1 (shared.files.FileLock) |
| SQLite WAL init patterns | 3 (meta, research-mcp) | 1 (shared.db) |
| SQLite migration patterns | 2 (meta, research-mcp) | 1 (shared.db) |
| HTTP retry implementations | 2 requests-based (intel, genomics) | 1 (shared.http) |
| Telemetry JSONL patterns | 3 (intel, genomics, meta) | 1 (shared.telemetry) |
| research `weighted_mean` copies | 10 | 0 (use numpy) |
| New shared library LOC | — | ~680 |
| Projects consuming shared lib | — | intel, meta, genomics, research-mcp |

<!-- knowledge-index
generated: 2026-03-22T00:15:43Z
hash: c879e179b669

title: Cross-Project Infrastructure Factoring (v3)

end-knowledge-index -->
