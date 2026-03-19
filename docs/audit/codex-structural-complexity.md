Wrote the audit to [codex-structural-complexity.md](/Users/alien/Projects/meta/docs/audit/codex-structural-complexity.md).

The report includes per-script metrics, the top 5 longest functions with line ranges, lists of all functions over 50 lines, god-function callouts, and concrete module split recommendations for each target script.

**Summary**
- `scripts/orchestrator.py` is the main structural problem: highest overall complexity, duplicated task-execution paths, and duplicated pipeline materialization.
- `scripts/sessions.py` is the next best split target: transcript parsing, indexing, search, and dispatch are all in one CLI file.
- `scripts/autoresearch.py` is dominated by `run_experiment_loop`, which should be broken into smaller experiment-step functions and provider adapters.
- `scripts/runlog.py` is healthier than the others, but `command_import` still does too much in one transaction body.
- `scripts/pushback-index.py` is smaller but still structurally overloaded because `main` combines CLI parsing, traversal, analysis, reporting, metrics logging, and embedded test fixtures.

No tests were run; this was a static audit and documentation pass.