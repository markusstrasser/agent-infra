# Leverage Survey: Packages, Languages, and Tools Beyond Python

**Date:** 2026-03-19
**Tier:** Standard | **Question:** What could we leverage across any ecosystem?
**Prior art:** package-landscape.md, cross-project-infra-factoring.md, tooling-leverage.md, agent-economics-decision-frameworks.md, scientific-computing-for-agent-telemetry.md

## Ground Truth: What We Already Know

Prior research (5 documents, 3 model reviews) evaluated and rejected: sqlite-utils, click/typer, DuckDB (as Python dep), Rich, pydantic/msgspec, gitpython, R SPC packages, GitPython, LanceDB, Polars migration, OpenBB, dbt-sqlite, shared cross-project library. Reasons uniformly maintenance-burden-based per constitutional principle 8.

Already adopted: just, DuckDB CLI, Harlequin, VisiData, sqlite-utils CLI.

Stdlib audit found the codebase is mature — `concurrent.futures`, `tomllib`, `pathlib`, `argparse` all correctly used. Main underuse: `functools.cache` for singletons, `difflib.SequenceMatcher` not yet applied to session similarity.

## What's Genuinely Worth Adopting

### Tier 1: Negative maintenance cost (adopt)

**1. Datasette — instant web UI over SQLite**
- **What:** Simon Willison's tool. Point it at any SQLite DB, get browsable/queryable web UI + JSON API.
- **Replaces:** Ad-hoc `runlog.py query`, `sessions.py list`, manual `sqlite3` CLI exploration. Human exploration shifts to Datasette; automated scripts stay.
- **Dep weight:** `pip install datasette` or `uvx datasette`. Single binary via `pipx`. Zero config.
- **Maintenance:** NEGATIVE. Willison ships weekly. Plugin ecosystem handles charting, export, faceted browse. We stop maintaining text-mode query formatting for human use.
- **Concrete use:** `datasette ~/.claude/runlogs.db ~/.claude/orchestrator.db ~/.claude/sessions.db`
- **Risk:** Long-running process (needs `launchd` or on-demand invocation). Doesn't replace automated scripts.
- [SOURCE: datasette.io, 9.8K GitHub stars, last release March 2026]

**2. DuckDB as Python library (not just CLI)**
- **What:** `import duckdb; duckdb.sql("SELECT * FROM read_json('receipts.jsonl')")` — native JSONL + SQLite querying.
- **Replaces:** Manual `for line in f: json.loads(line)` loops, cross-DB joins, aggregation pipelines. Every script that loads JSONL + filters + aggregates is a DuckDB one-liner.
- **Dep weight:** `pip install duckdb` (~25MB). Pure Python wheel, no C compilation.
- **Maintenance:** NEGATIVE. Absorbs edge cases we handle manually (malformed lines, timestamp parsing, nested JSON). Well-funded (MotherDuck).
- **Concrete use:** `dashboard.py` cost rollups, `propose-work.py` recent-receipt queries, `hook-roi.py` trigger aggregation — all become SQL.
- **Risk:** OLAP only. Keep SQLite for transactional writes (orchestrator queue, sessions index).
- **Previous decision:** Rejected as dep in complexity-reduction plan. But that plan was about the `common/` extraction scope. The constitutional gate is maintenance burden, and DuckDB reduces it for read-heavy analytics scripts.
- [SOURCE: duckdb.org, 28K GitHub stars]

**3. Polars `scan_ndjson` for lazy JSONL processing**
- **What:** `pl.scan_ndjson("file.jsonl").filter(pl.col("cost") > 0.5).collect()` — lazy eval with predicate pushdown.
- **Replaces:** Manual JSONL load-filter-aggregate. Complementary to DuckDB (Polars for DataFrame ops, DuckDB for SQL).
- **Dep weight:** `pip install polars` (~30MB). Rust-backed, fast.
- **Maintenance:** SLIGHTLY NEGATIVE. Stable API, active development.
- **Risk:** ~200ms import overhead. For small files (<1MB), marginal over manual parsing. Use for new code, don't rewrite working scripts.
- [SOURCE: pola.rs, 32K GitHub stars]

### Tier 2: New capabilities (probe first)

**4. ruptures — changepoint detection**
- **What:** PELT/Binseg algorithms detect "when did a metric shift?" Non-trivial to hand-roll (~100 lines).
- **Replaces:** Nothing currently — NEW CAPABILITY. Could detect: "pushback index dropped after March 5," "session costs shifted regime on March 12."
- **Dep weight:** Only depends on numpy. ~2MB.
- **Maintenance:** Low. Academic backing (published in JMLR). Stable API.
- **Concrete use:** Feed any time-series metric (daily cost, SLI, fold rate) and get structural breakpoints.
- **Gate:** Defer until any metric has 60+ observations. Currently too sparse for robust detection.
- [SOURCE: centre-borelli.github.io/ruptures-docs, 1.7K stars]

**5. `difflib.SequenceMatcher` for session similarity (stdlib, zero dep)**
- **What:** Sequence alignment on tool-call event streams. Extract tool sequences from sessions, find similar/anomalous patterns.
- **Replaces:** Nothing currently — NEW CAPABILITY. Could answer: "which sessions look like this failure?" and "what's the normal tool-call pattern for intel sessions?"
- **Dep weight:** Zero. stdlib.
- **Concrete use:** Extract `[Read, Grep, Edit, Bash, ...]` sequences from transcripts, compute pairwise similarity, cluster sessions.
- **Gate:** Build a 20-line probe first. If session similarity proves useful, consider STUMPY matrix profiles for scaling.

**6. scipy.stats for pre/post comparisons**
- **What:** Mann-Whitney U, Kolmogorov-Smirnov for "did this hook actually change behavior?"
- **Replaces:** Current manual before/after eyeballing. Proper statistical tests for "did SLI improve after deploying hook X?"
- **Dep weight:** scipy is heavy (~150MB) but already available via uv.
- **Gate:** Needs 500+ session pairs to have statistical power. We're approaching this threshold.

### Tier 3: Creative cross-domain ideas (extract pattern, not tool)

**7. FastQC adaptive thresholds (genomics pattern)**
- **What:** Instead of hardcoded warn/fail thresholds, derive them from historical percentiles (p5/p25/p75/p95).
- **Replaces:** Hardcoded thresholds in `dashboard.py`, `session-shape.py`.
- **Dep weight:** Zero. ~20 lines of Python. The PATTERN from genomics QC, not the tool.
- **Concrete use:** `session-shape.py` currently uses z-scores with magic numbers. Adaptive percentile thresholds are more robust to regime changes.

**8. IQR-based outlier bounds (statistics pattern)**
- **What:** `Q1 - 1.5*IQR` to `Q3 + 1.5*IQR` instead of mean ± N*stdev. Robust to outliers.
- **Replaces:** Z-score anomaly detection in `session-shape.py`.
- **Dep weight:** Zero. One line change.

**9. Calibration curves (sklearn pattern, inline)**
- **What:** Bin predictions by decile, compute per-bin accuracy. Reveals systematic over/under-confidence.
- **Replaces:** Simple Brier score in `calibration-canary.py`. Adds diagnostic power.
- **Dep weight:** ~15 lines inline. Don't import sklearn for this.

## What's NOT Worth Adopting (with reasons)

### Other languages

| Language/Tool | Considered for | Verdict | Why |
|---|---|---|---|
| **R (forecast, qcc, mvMonitoring)** | SPC, time series anomaly | SKIP | Adds entire language runtime. Python `statsmodels` covers 90%. Western Electric rules are ~50 lines. |
| **Scala (Akka)** | Orchestrator concurrency | SKIP | JVM startup, build system, two-language maintenance. Our SQLite queue + `anyio` is simpler and works. |
| **Nushell** | JSONL pipeline one-liners | SKIP | DuckDB CLI gives same structured-data querying without learning new shell syntax. |
| **Observable Framework** | Interactive dashboard | SKIP | Adds Node.js/npm toolchain to Python-only repo. Datasette plugins give 80% of the value. |

### Rust/Go CLIs

| Tool | What it does | Verdict | Why |
|---|---|---|---|
| **jq/jaq** | JSON processing | ALREADY HAVE | DuckDB SQL is more powerful for our aggregation patterns. |
| **watchexec** | File watching | SKIP | We use launchd WatchPaths (native-patterns.md). |
| **xsv/qsv** | CSV processing | SKIP | We don't process CSV. JSONL + SQLite are our formats. |
| **fd** | File finding | MARGINAL | `glob` and `rg` already cover our needs. |

### Python packages

| Package | What it does | Verdict | Why |
|---|---|---|---|
| **Rich** | Terminal formatting | SKIP | Agents parse output as text. Formatting adds parsing noise. |
| **click/typer** | CLI framework | SKIP | 28 scripts to port. argparse is self-documenting. |
| **pydantic** | Validation | SKIP | No untrusted-input boundary. stdlib dataclasses suffice. |
| **sqlite-utils (as lib)** | SQLite helpers | SKIP | `open_db()` covers our needs. sqlite-utils adds API surface. |
| **Great Expectations** | Data validation | SKIP | Config ceremony larger than entire measurement codebase. |
| **PyMC/ArviZ** | Bayesian calibration | SKIP | ~200MB for 75 data points. Massively overfit. |
| **STUMPY** | Matrix profiles | SKIP (for now) | Needs 1000+ point dense series. Our data is sparse (5-20 sessions/day). |
| **instructor** | Structured LLM output | DEFER | Interesting but no current consumer. Revisit when we need structured agent output parsing. |

## Rust/Go CLI Tools (single-binary, zero-config)

### Tier 1: Strong fits

**1. `jaq` — Rust jq clone, JSONL native** (3.4K stars, v3.0.0 March 2026)
- 30x faster than jq. JSONL native. NLnet security-audited.
- Replaces: every `for line in f: json.loads(line)` + field extraction in `just` recipes or ad-hoc exploration.
- Example: `jaq -s '[.[] | select(.ts > "2026-03-01")] | length' ~/.claude/session-receipts.jsonl`
- NOT a Python dep replacement — a shell-level complement. The Python scripts stay; `jaq` replaces ad-hoc `python3 -c` one-liners.
- Install: `brew install jaq`
- [SOURCE: github.com/01mf02/jaq]

**2. `hl` — structured log viewer** (~3K stars, v0.36.0 Feb 2026)
- Parses JSONL at 2 GiB/s. Field filtering (`-f pipeline=session-retro`), level filtering (`-l error`), time range (`--since -3h`), follow mode (`-F`).
- Replaces: manual JSONL exploration via `cat | jq` or Python scripts.
- Example: `hl -l error --since yesterday ~/.claude/orchestrator-log.jsonl`
- Install: `brew install pamburus/tap/hl`
- [SOURCE: github.com/pamburus/hl]

**3. `git-cliff` — structured git log analysis** (11.6K stars, active March 2026)
- Regex-powered commit parsing with Tera templates. Outputs structured JSON via `--context`.
- Replaces: `repo-changes.py` git log parsing, could auto-generate improvement-log structure.
- Our `[scope] Verb thing` commit format is directly parseable.
- Install: `brew install git-cliff`
- [SOURCE: github.com/orhun/git-cliff]

### Tier 2: Dev convenience

| Tool | Stars | What | Verdict |
|---|---|---|---|
| `watchexec` | 6.8K | File watcher, dev iteration | We use launchd for production. Useful for dev only. |
| `miller` (mlr) | 9.8K | "awk for structured data" | Overlaps with jaq for JSONL. Unique for format conversion (JSONL↔CSV). |
| `SuperDB` (ex-zq) | 1.5K | Heterogeneous data query engine | Architecturally interesting but immature. Watch. |

### Excluded

| Tool | Why |
|---|---|
| `dsq` | Dead (Sept 2023), author recommends DuckDB |
| `xsv` | Archived, recommends `qsv`. We don't do CSV. |

## Python 3.14 Stdlib Wins (zero-dep, zero-risk)

**Immediate adoption — costs nothing:**

| Feature | What | Where |
|---|---|---|
| `argparse(suggest_on_error=True)` | Typo suggestions on bad flags | All 20+ argparse scripts |
| `argparse(color=True)` | Colored help output | All 20+ argparse scripts |
| `argparse(deprecated=True)` | Deprecation warnings per flag | Any flag we want to sunset |
| `pathlib.Path.copy()` / `.move()` | Replaces `shutil.copy`/`shutil.move` | Cross-project |

**Not applicable (but worth noting):**
- `InterpreterPoolExecutor` — true parallelism without subprocess. But our ThreadPoolExecutor use is I/O-bound (git, HTTP), so no benefit.
- `dbm.sqlite3` — stdlib key-value on SQLite. Not applicable (our schemas are relational).
- `compression.zstd` — no compression in codebase.

## Missing Pattern: `common/migrate.py`

Three scripts do ad-hoc `ALTER TABLE ADD COLUMN` with try/except (`finding-triage.py:107`, `sessions.py:130`, `orchestrator.py:90`). The eskerda pattern (numbered `.sql` files + `PRAGMA user_version`) is ~20 lines of stdlib Python and would standardize these. A pattern to adopt, not a library to install.

## Dev Tools (not dependencies)

| Tool | What | Install |
|---|---|---|
| `litecli` | Auto-completing SQLite CLI with syntax highlighting | `uvx litecli ~/.claude/orchestrator.db` |
| `datasette` | Web UI over SQLite DBs | `uvx datasette ~/.claude/runlogs.db` |

## Implementation Priority

| # | What | Type | Dep weight | Impact |
|---|---|---|---|---|
| 1 | `argparse(suggest_on_error=True, color=True)` | Stdlib upgrade | 0 | Free UX improvement across 20+ scripts |
| 2 | Datasette for exploration | Dev tool install | 0 (uvx) | Replaces ad-hoc query workflows |
| 3 | `jaq` + `hl` for shell-level JSONL | Brew install | 0 (CLI tools) | Replaces ad-hoc `python3 -c` one-liners |
| 4 | `common/migrate.py` (eskerda pattern) | ~20 lines stdlib | 0 | Standardize 3 ad-hoc schema migrations |
| 5 | DuckDB Python for analytics scripts | 1 pip pkg | 2-3 scripts rewritten | Replaces JSONL parsing boilerplate |
| 6 | IQR bounds + adaptive thresholds | Inline changes | 0 | More robust anomaly detection |
| 7 | `git-cliff` for commit analysis | Brew install | 0 (CLI tool) | Could simplify repo-changes.py |
| 8 | `difflib.SequenceMatcher` probe | stdlib | 0 | Session similarity detection |
| 9 | Polars for new JSONL code | 1 pip pkg | New code only | Cleaner JSONL processing |
| 10 | ruptures changepoint | 1 pip pkg | Defer to 60+ obs | Regime-shift detection |

## The Meta-Pattern

The highest-leverage items share a property: they're **tools that absorb edge cases** rather than tools that add new API surface. Datasette absorbs query formatting. DuckDB absorbs JSONL parsing. IQR bounds absorb outlier sensitivity. The worst candidates are tools that add ceremony (dbt, Great Expectations, Pydantic) or language runtimes (R, Scala, Node.js).

Three distinct leverage layers emerged:
1. **Stdlib upgrades** (Python 3.14 argparse) — zero cost, zero risk, adopt immediately
2. **CLI tools** (jaq, hl, git-cliff, datasette) — zero Python deps, complement existing scripts
3. **Python libraries** (DuckDB, Polars, ruptures) — real deps, adopt selectively where maintenance is NEGATIVE

The scientific computing angle is mostly a dead end at our data density — we have 5-20 sessions/day, not 5000. Statistical sophistication is blocked by sample size, not tooling. The one exception is `ruptures` for changepoint detection, which becomes viable once metrics accumulate 60+ observations.

The bioinformatics crossover that actually works is methodological, not tooling: FastQC's adaptive-threshold pattern and `difflib.SequenceMatcher` for sequence alignment on tool-call streams. Extract the pattern, not the tool.

<!-- knowledge-index
generated: 2026-03-22T00:13:52Z
hash: 6d70cd1d18ce


end-knowledge-index -->
