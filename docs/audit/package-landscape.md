# Python Package Landscape for Meta Scripts

**Date:** 2026-03-19
**Scope:** 54 scripts in `scripts/`, evaluated against 7 consolidation axes
**Goal:** Identify packages that reduce duplication without adding maintenance burden

---

## Current State (measured)

| Pattern | Count | Detail |
|---------|-------|--------|
| argparse scripts | 28 | 168 `add_argument` calls |
| Subparser scripts | 9 | orchestrator, runlog, sessions, etc. |
| `--days` arg | 25 scripts | Common: default 7 or 30 |
| `--project` arg | 17 scripts | |
| `--verbose` arg | 12 scripts | |
| `--format` arg | 3 scripts | text/json/markdown |
| JSONL load patterns | 27 | `json.loads` per-line |
| `sqlite3.connect` | 10 scripts | Duplicated WAL/row_factory setup |
| `subprocess` + git | 13 scripts | `git log`, `git diff`, `git show` |

---

## 1. CLI Framework: click vs typer vs cyclopts

### Verdict: **Stay with argparse. Extract a shared `cli_common.py` module.**

| Package | Stars | Last Release | License | Deps |
|---------|-------|-------------|---------|------|
| **click** | 17.3K | 8.3.1 (2025-11-15) | BSD-3 | None (markupsafe only) |
| **typer** | 19.1K | 0.24.1 (2026-02-21) | MIT | click, rich, shellingham |
| **cyclopts** | 1.1K | 4.10.0 (2026-03-14) | Apache-2.0 | attrs, docstring-parser, rich |

**Analysis:**

- **click** is the most mature and battle-tested (Pallets project, Flask ecosystem). Shared arguments work via `@click.pass_context` and decorator composition, but the pattern is verbose — you stack decorators for every shared option.
- **typer** wraps click with type hints, reducing boilerplate. But it's still pre-1.0 (0.24.x), and shared arguments between commands is an open issue (fastapi/typer#153) with no clean native solution — the workaround is a callback on a parent command.
- **cyclopts** is the cleanest for type-hint-driven CLIs and explicitly addresses typer's pain points (better Union support, docstring parsing, no click dependency). But 1.1K stars means small community, single maintainer (BrianPugh), and any non-trivial issue is your problem.

**Why argparse is fine here:**

1. **No shared arguments problem in argparse.** A function that takes a parser and adds common args is 5 lines. Click/typer solve this less cleanly (decorator stacking, `@click.pass_context`, or parent callbacks).
2. **28 scripts is a lot of migration surface** for marginal gain. The duplication isn't in the framework choice — it's in the repeated `--days`, `--project`, `--verbose` boilerplate.
3. **Zero new dependencies.** argparse is stdlib. Every package above adds at least 1-3 transitive deps.
4. **Agent readability.** Agents read and write argparse fluently — it's the most common pattern in training data.

**What to build instead:**

```python
# scripts/cli_common.py
def add_days_arg(parser, default=7):
    parser.add_argument("--days", "-d", type=int, default=default,
                        help=f"Lookback window in days (default: {default})")

def add_project_arg(parser):
    parser.add_argument("--project", "-p",
                        help="Project name filter")

def add_verbose_arg(parser):
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")

def add_output_format(parser, default="text"):
    parser.add_argument("--format", "-f", choices=["text", "json", "markdown"],
                        default=default, help=f"Output format (default: {default})")
```

This eliminates the 168-call duplication without adding a single dependency. Migrate incrementally — `from scripts.cli_common import add_days_arg` in each script.

**If you were starting fresh:** cyclopts. It's the only one where shared argument patterns are native (via `App` inheritance and `Annotated` types). But migrating 28 existing scripts to it has negative ROI.

[SOURCE: https://github.com/BrianPugh/cyclopts (GitHub)]
[SOURCE: https://cyclopts.readthedocs.io/en/latest/vs_typer/README.html]
[SOURCE: https://github.com/fastapi/typer/issues/153]

---

## 2. JSONL Read/Write

### Verdict: **10-line shared util is the right call. No package needed.**

There is no well-known standalone JSONL package that's worth a dependency. The pattern is trivial:

```python
# scripts/cli_common.py (add to the same module)
import json
from pathlib import Path

def load_jsonl(path: str | Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]

def append_jsonl(path: str | Path, record: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

def iter_jsonl(path: str | Path):
    """Memory-efficient iterator for large JSONL files."""
    with open(path) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)
```

27 scripts with JSONL patterns can import from one place. The `default=str` in `append_jsonl` handles datetime and Path serialization, which is the most common source of per-script variation.

**DuckDB as JSONL reader** — see Section 3 below. For analytics queries, `SELECT * FROM 'file.jsonl'` in DuckDB eliminates the load entirely. But for simple "read records, filter, process" patterns, the shared util is lighter.

**What NOT to do:** Don't install `jsonlines` (1.1K stars, last release 2023, adds a context manager wrapper around the exact same pattern above). The stdlib version is equally readable and has zero risk.

---

## 3. SQLite Helpers

### Verdict: **sqlite-utils for CLI/exploration. DuckDB for analytics. Shared `db_common.py` for scripts.**

| Package | Stars | Last Release | License | Use Case |
|---------|-------|-------------|---------|----------|
| **sqlite-utils** | 2.0K | 3.39 (2025-11-24) | Apache-2.0 | CLI + Python lib for SQLite manipulation |
| **DuckDB** | 36.8K | 1.5.0 (2026-03-09) | MIT | Analytics engine, reads SQLite/JSONL/CSV directly |

### sqlite-utils (Simon Willison)

Mature, well-maintained by a prolific single developer (Willison). Two modes:
- **CLI:** `sqlite-utils query db.sqlite "SELECT ..." --json` — eliminates many one-off Python scripts
- **Python library:** `db = Database("file.db"); db["table"].insert_all(records)` — cleaner than raw sqlite3

**Battle-tested:** Used by Datasette (9.7K stars), which is built on top of it. Willison maintains both actively. The CLI alone could replace several scripts that exist only to query SQLite and format output.

**Limitation:** Not a connection pool. Not an ORM. It's a helper library, which is exactly the right weight for 10 scripts.

### DuckDB

The strongest candidate for eliminating entire scripts. DuckDB can:
- Query JSONL files directly: `SELECT * FROM 'receipts.jsonl' WHERE date > '2026-03-01'`
- Query SQLite databases directly: `SELECT * FROM sqlite_scan('orchestrator.db', 'tasks')`
- Join across formats: `SELECT * FROM 'file.jsonl' j JOIN sqlite_scan('db.sqlite', 't') s ON j.id = s.id`
- Replace pandas-style analytics without pandas overhead

**For the orchestrator analytics** (efficiency, cost rollup, daily summary): DuckDB queries over the SQLite DB would be significantly cleaner than the current Python string-building. A single `duckdb.sql(...)` call replaces 50+ lines of cursor management.

**Concern:** DuckDB is 48MB+ installed (C++ engine). It's not lightweight. But it's a `uv add` away and the analytical power justifies it for a repo that exists to analyze agent sessions.

### Shared DB helper (for the 10 scripts with sqlite3.connect)

```python
# scripts/db_common.py
import sqlite3
from pathlib import Path

def connect(db_path: str | Path, wal: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    if wal:
        conn.execute("PRAGMA journal_mode=WAL")
    return conn
```

This eliminates the duplicated WAL/row_factory boilerplate across 10 scripts, without adding any dependency.

### litestream / litefs

**Not relevant.** These are replication tools for multi-server SQLite. Single-user local system has no use case.

[SOURCE: https://github.com/simonw/sqlite-utils (GitHub)]
[SOURCE: https://github.com/duckdb/duckdb (GitHub)]
[SOURCE: Verified: DuckDB reads JSONL directly (duckdb.org/2023/03/03/json.html)]

---

## 4. Subprocess/Git

### Verdict: **Keep subprocess. It's actually the best option.**

| Package | Stars | Last Release | License | Approach |
|---------|-------|-------------|---------|----------|
| **GitPython** | 5.1K | 3.1.46 (2026-01-01) | BSD-3 | Wraps git CLI + some native |
| **dulwich** | 2.2K | 1.1.0 (2026-02-17) | GPL-2+/Apache-2.0 | Pure Python git implementation |
| **pygit2** | 1.7K | (2026-03-19) | GPL-2 w/ linking exception | libgit2 bindings (C) |

**Why subprocess wins:**

1. **GitPython has known security issues.** Its `Git` object shells out to git anyway, but with insufficient input sanitization historically (CVE-2024-22190, CVE-2023-40590). The maintainers have flagged that [GitPython is not designed for safe use with untrusted input](https://github.com/gitpython-developers/GitPython/issues/1515). For a personal repo, this is less critical, but the abstraction adds complexity without removing the subprocess dependency.

2. **dulwich is pure Python** — no git binary needed. Good for environments without git. Irrelevant here (git is always available). Its API is low-level and non-obvious for common operations. GPL-2 license is a concern for any future extraction.

3. **pygit2 requires libgit2 C library** compiled and linked. Fragile on macOS with system updates. GPL-2 with linking exception.

4. **subprocess.run(["git", ...])** is:
   - Zero dependencies
   - Trivially debuggable (same command works in terminal)
   - Handles all 13 script use cases (log, diff, show, blame, rev-parse)
   - Agent-friendly (agents know git CLI flags)

**What's worth extracting:**

```python
# scripts/cli_common.py
import subprocess

def git(*args, cwd=None) -> str:
    """Run git command, return stdout. Raises on failure."""
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=cwd
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()
```

13 scripts can replace `subprocess.run(["git", "log", ...], capture_output=True, text=True)` with `git("log", ...)`. Same approach, less boilerplate, zero deps.

[SOURCE: https://github.com/gitpython-developers/GitPython (GitHub)]
[SOURCE: CVE-2024-22190 — GitPython arbitrary code execution]

---

## 5. Rich for Output

### Verdict: **Yes, but only for interactive output. Not for structured/piped output.**

| Package | Stars | Last Release | License | Deps |
|---------|-------|-------------|---------|------|
| **rich** | 55.8K | (2026-02-26) | MIT | markdown-it-py, pygments |

Rich is the most-starred Python library in this entire audit. Will McGugan (Textualize) maintains it actively. It's a dependency of typer, textual, and many major projects.

**Where it helps (interactive terminal):**
- Tables: `rich.table.Table` replaces manual column alignment
- Progress bars: long-running operations (session analysis, bulk imports)
- Syntax highlighting: displaying code/JSON diffs
- Panels/trees: hierarchical data (dependency trees, pipeline status)

**Where it hurts (piped/scripted output):**
- Rich auto-detects TTY and falls back to plain text, but the fallback isn't always clean
- Scripts that output JSON/CSV for other scripts should NOT use rich
- The `--format json` paths should stay as `json.dumps`

**Recommendation:** Add rich as a dependency. Use it in dashboard.py, orchestrator status, doctor.py, and any interactive-only output. Keep structured output paths (JSON, markdown) as-is. Import pattern:

```python
try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = None  # Graceful degradation

def print_table(headers, rows):
    if console and console.is_terminal:
        table = Table(...)
        # rich output
    else:
        # plain text fallback
```

**Not recommended: textual** (TUI framework, same author). The scripts are CLIs, not TUIs. Textual is for interactive applications, which none of these are.

[SOURCE: https://github.com/Textualize/rich (GitHub)]

---

## 6. Dataclass Serialization

### Verdict: **stdlib `dataclasses` + `dataclasses.asdict()` + `json.dumps()`. No new package.**

| Package | Stars | Last Release | License | Speed | Deps |
|---------|-------|-------------|---------|-------|------|
| **pydantic** | 27.2K | (2026-03-18) | MIT | Baseline | pydantic-core (Rust) |
| **msgspec** | 3.7K | 0.20.0 (2025-11-24) | BSD-3 | 2-5x pydantic | None (C ext) |
| **cattrs** | 1.0K | 26.1.0 (2026-02-18) | MIT | ~pydantic | attrs |
| **dataclasses-json** | 1.5K | (2024-08-08) | MIT | Slow | marshmallow |
| **attrs** | 5.7K | (2026-03-19) | MIT | Faster than dataclasses | None |

**Why no new package:**

The scripts use ad-hoc dict construction because they're producing output records — session receipts, task status, metrics. This is a `dict -> json.dumps` pipeline, not a validation boundary.

- **pydantic** solves the wrong problem. These scripts don't receive untrusted input. Pydantic's validation overhead (5-15x slower than dataclasses) is waste. It also pulls in pydantic-core (Rust compiled extension), adding build complexity.
- **msgspec** is genuinely fast (2-5x faster than pydantic) but has a niche API (`msgspec.Struct` instead of `@dataclass`). Pre-1.0 (0.20.0). Last release Nov 2025. Good for high-throughput APIs, overkill for CLI scripts that run once and exit.
- **cattrs** specializes in `attrs <-> dict` structuring/unstructuring. Clean API, but adds attrs as a dependency for something stdlib already does.
- **dataclasses-json** is effectively abandoned (last push Aug 2024). Depends on marshmallow. Do not adopt.

**What to do:**

For the scripts that construct dicts ad-hoc, define dataclasses and use the stdlib:

```python
from dataclasses import dataclass, asdict
import json

@dataclass
class TaskResult:
    task_id: str
    status: str
    duration_s: float
    error: str | None = None

result = TaskResult(task_id="abc", status="done", duration_s=1.2)
json.dumps(asdict(result), default=str)
```

This is zero dependencies, type-checked by mypy/pyright, and gives you named fields instead of `d["task_id"]`. The round-trip is `dataclass -> asdict -> json.dumps` (serialize) and `TaskResult(**d)` (deserialize). No package needed.

**If you later need validation** (e.g., for MCP tool inputs or API boundaries): pydantic, at those boundaries only. Don't use it for internal data flow.

[SOURCE: https://hrekov.com/blog/msgspec-vs-pydantic-v2-benchmark]
[SOURCE: https://github.com/jcrist/msgspec (GitHub)]

---

## 7. Task/Pipeline Orchestration

### Verdict: **Keep the hand-rolled SQLite orchestrator. It's the right weight.**

| Package | Stars | Last Release | License | Weight |
|---------|-------|-------------|---------|--------|
| **APScheduler** | 7.4K | (2026-03-01) | MIT | Medium — scheduler, not task queue |
| **huey** | 5.9K | 2.6.0 (2026-01-06) | MIT | Light — Redis/SQLite task queue |
| **rq** | 10.6K | (2026-03-18) | BSD | Medium — Redis required |
| **Prefect** | 21.9K | (2026-03-19) | Apache-2.0 | Heavy — full platform |
| **Temporal** | — | — | MIT | Heavy — requires server |

**Why the hand-rolled orchestrator is correct:**

1. **APScheduler** is a scheduler, not a task queue. It fires callbacks on a cron schedule. The orchestrator already does this via launchd + `tick()`. APScheduler would replace the launchd plists but add a Python daemon that needs supervision — strictly worse for a system that's already supervised by launchd.

2. **huey** is the closest fit — it has a SQLite backend (`SqliteHuey`), supports scheduled tasks, retries, and result storage. But it's designed for web app background tasks (Django/Flask integration), not for launching `claude -p` subprocesses. The orchestrator's dual-engine design (LLM tasks via `claude -p` + deterministic tasks via subprocess) doesn't map to huey's worker model.

3. **rq** requires Redis. Adding a Redis server for a single-user local system is absurd.

4. **Prefect/Temporal** are production workflow engines designed for teams. They have servers, UIs, cloud offerings, and 100+ MB install footprints. Using them for a personal cron runner is orders of magnitude overengineered.

**What the orchestrator actually does that none of these handle:**

- Dual-engine dispatch: `claude -p` for LLM tasks, `subprocess` for scripts
- Pipeline templates with variable substitution and approval gates
- `done_with_denials` as a distinct terminal state (permission model)
- Constitutional hard limits ($25/day cost cap, cross-project approval)
- `fcntl.flock` single-writer guarantee
- `anyio.fail_after(600s)` stall detection for hung LLM tasks

These are domain-specific behaviors that no generic task queue provides. Wrapping a generic queue to support these would be more code than the current 1809-line orchestrator.

**What IS worth extracting from the orchestrator:**

The SQLite task queue pattern (submit, claim, complete, retry) is 200 lines that could be a reusable `TaskQueue` class. If other projects need similar patterns, extract that — not the whole orchestrator.

---

## Summary: What to Actually Do

| Action | LOC | Deps Added | Scripts Affected |
|--------|-----|-----------|-----------------|
| Create `scripts/cli_common.py` with shared args + git helper + JSONL utils | ~60 | 0 | 28 (argparse) + 27 (JSONL) + 13 (git) |
| Create `scripts/db_common.py` with connect helper | ~15 | 0 | 10 (sqlite3) |
| Add `rich` to project deps | 0 | 1 (+2 transitive) | 5-10 (interactive output scripts) |
| Add `duckdb` to project deps for analytics | 0 | 1 | 3-5 (analytics/reporting scripts) |
| Define dataclasses for common output records | ~50 | 0 | 10-15 (ad-hoc dict construction) |
| **Total new dependencies** | | **2** (rich, duckdb) | |

### Priority Order

1. **`cli_common.py`** — highest ROI. Eliminates the most duplication (168 add_argument calls become ~28 import lines). Zero risk.
2. **`db_common.py`** — trivial extraction, high consistency gain.
3. **Dataclass definitions** — type safety improvement, catches bugs at definition time.
4. **DuckDB for analytics** — replace the most complex scripts (dashboard, efficiency, cost rollup) with SQL queries over existing data.
5. **Rich for interactive output** — cosmetic improvement, lower priority.

### What NOT to Do

- **Don't migrate from argparse to click/typer/cyclopts.** The migration cost exceeds the benefit for 28 existing scripts. The shared-args problem is better solved by a 10-line module than by a framework swap.
- **Don't add pydantic.** These scripts don't validate untrusted input. stdlib dataclasses + `asdict` is sufficient.
- **Don't add GitPython.** subprocess is simpler, more debuggable, and avoids GitPython's security history.
- **Don't replace the orchestrator.** No off-the-shelf task queue handles the dual-engine + constitutional model.
- **Don't add msgspec.** It's fast, but performance isn't the bottleneck for scripts that run once and exit.

---

## Package Metadata (verified 2026-03-19)

All star counts and release dates verified via GitHub API (`gh api repos/{owner}/{repo}`).

| Package | Stars | Last Release | Last Push | License | Maintained |
|---------|-------|-------------|-----------|---------|------------|
| click | 17,345 | 8.3.1 (Nov 2025) | Mar 2026 | BSD-3 | Yes (Pallets) |
| typer | 19,056 | 0.24.1 (Feb 2026) | Mar 2026 | MIT | Yes (Tiangolo) |
| cyclopts | 1,091 | 4.10.0 (Mar 2026) | Mar 2026 | Apache-2.0 | Yes (single maintainer) |
| sqlite-utils | 2,018 | 3.39 (Nov 2025) | Jan 2026 | Apache-2.0 | Yes (Willison) |
| DuckDB | 36,791 | 1.5.0 (Mar 2026) | Mar 2026 | MIT | Yes (DuckDB Labs) |
| GitPython | 5,082 | 3.1.46 (Jan 2026) | Mar 2026 | BSD-3 | Yes (but security flags) |
| dulwich | 2,220 | 1.1.0 (Feb 2026) | Mar 2026 | GPL-2+/Apache-2.0 | Yes |
| pygit2 | 1,716 | — | Mar 2026 | GPL-2 | Yes |
| rich | 55,809 | — (Feb 2026) | Feb 2026 | MIT | Yes (Textualize) |
| pydantic | 27,245 | — (Mar 2026) | Mar 2026 | MIT | Yes (Pydantic team) |
| msgspec | 3,653 | 0.20.0 (Nov 2025) | Nov 2025 | BSD-3 | Slower cadence |
| cattrs | 1,015 | 26.1.0 (Feb 2026) | Mar 2026 | MIT | Yes |
| attrs | 5,746 | — | Mar 2026 | MIT | Yes |
| dataclasses-json | 1,482 | — (Aug 2024) | Aug 2024 | MIT | Abandoned |
| APScheduler | 7,378 | — | Mar 2026 | MIT | Yes |
| huey | 5,941 | 2.6.0 (Jan 2026) | Feb 2026 | MIT | Yes (coleifer) |
| rq | 10,608 | — | Mar 2026 | BSD | Yes |
| Prefect | 21,905 | — | Mar 2026 | Apache-2.0 | Yes (VC-funded) |
