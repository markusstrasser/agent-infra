Audit written to [docs/audit/codex-dependency-audit.md](/Users/alien/Projects/meta/docs/audit/codex-dependency-audit.md).

Key points:
- All four declared runtime dependencies in `pyproject.toml` are actually used by the audited scripts.
- The real third-party footprint is slightly larger than declared: `orchestrator.py` imports `anyio`, `skill-validator.py` imports `yaml` (`PyYAML`), and `repo-deps.py` still carries a removable `tomli` fallback despite `requires-python >=3.11`.
- The CLI surface is large: 28 `argparse` scripts with 168 `add_argument(...)` calls, split into 9 subparser CLIs and 19 simple parsers, plus 21 more scripts that still hand-parse `sys.argv`.
- `subprocess` use is concentrated and mostly justified: 16 scripts use it, 6 invoke git, 0 invoke the `sqlite3` CLI, and most non-git calls are wrappers around external tools like `llmx`, `codex`, `claude`, `emb`, `pgrep`, and `osascript`.
- The best simplification target is local shared infrastructure, not more dependencies: JSONL IO, recurring CLI flags, command execution, and `.claude` path helpers.
- If you want a library-led cleanup, the doc recommends `typer` and `rich` first, with `pydantic` and `duckdb` only for selective use.

No tests were run; this was a documentation-only audit.