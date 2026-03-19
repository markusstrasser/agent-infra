Wrote the audit to [docs/audit/codex-duplicated-patterns.md](/Users/alien/Projects/meta/docs/audit/codex-duplicated-patterns.md).

`scripts/config.py` currently centralizes metrics/project config plus `extract_project_name()` and `jsonl_log()`, but it does not provide shared `.claude` path constants, session iterators, SQLite helpers, argparse helpers, or JSONL readers/bulk writers. The report includes the exact `rg -n` evidence, file:line inventories, config cross-reference, and extraction recommendations.

## Summary

| Pattern | Scripts | Occurrences | In `config.py`? | Recommendation |
|---|---:|---:|---|---|
| JSONL helpers (`load_jsonl` / `write_jsonl`) | 4 | 5 | Partial (`jsonl_log` only) | Extract |
| SQLite connection boilerplate | 10 | 26 | No | Extract |
| Session directory traversal | 9 raw hits | 15 | Partial (`extract_project_name` only) | Extract |
| Argparse boilerplate | 28 | 52 | No | Leave as-is for now |
| `.claude` path constants / `CLAUDE_DIR` | 33 | 65 | Partial | Extract |

## Findings

- Highest-value extraction target is shared `.claude` path handling. It appears in 33 scripts and should move to a dedicated shared paths module.
- SQLite setup is duplicated enough to justify a shared `connect_sqlite(...)` helper, but schema/migration logic should stay local.
- Session traversal is duplicated across Claude transcript consumers and should be unified with shared iterators; one hit is a docstring false positive and one is a Codex-session variant.
- JSONL helpers are repeated in four scripts. `config.py` only covers append-only writes, not reads or bulk writes.
- Argparse repetition is real, but most parser shapes diverge. Only the recurring `--days` / `--project` flags look worth extracting later.

No tests were needed for this task.