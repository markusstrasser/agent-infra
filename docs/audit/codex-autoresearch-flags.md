**Report**

Saved the audit to [codex-autoresearch-flags.md](/Users/alien/Projects/meta/docs/audit/codex-autoresearch-flags.md).

**Markdown Summary**

- `BUG`: `_run_mutator_codex()` uses `--dangerously-bypass-approvals-and-sandbox` at [autoresearch.py](/Users/alien/Projects/meta/scripts/autoresearch.py#L448). That is not the right default here. Headless `codex exec` already defaults approvals to `never`, and the safer path is explicit `--sandbox workspace-write` for this workload, or `--sandbox danger-full-access` only if you truly need it. `--full-auto --sandbox danger-full-access` is not a good replacement because `--full-auto` wins and forces workspace-write in exec mode.
- `BUG`: Codex env cleaning is wrong. The function strips Claude vars, not Codex vars. Relevant Codex env includes `OPENAI_API_KEY`, `CODEX_API_KEY`, `CODEX_THREAD_ID`, `CODEX_INTERNAL_ORIGINATOR_OVERRIDE`, `CODEX_HOME`, and `CODEX_SQLITE_HOME`; the current code does not handle that intentionally.
- `BUG`: stdout parsing is not robust. Current code takes the last line of stdout as the description, but Codex’s default contract is “entire final message on stdout” and `--json` gives structured JSONL events. The “last line” heuristic is unreliable.
- `BUG`: the comment says “take first line as description” but the code actually takes the last line in [autoresearch.py](/Users/alien/Projects/meta/scripts/autoresearch.py#L481).
- `HANDLED_CORRECTLY`: `codex exec --json` is a real structured channel and is much better for this mutator. `--output-schema` is also real and suitable for a machine-readable final summary.
- `IMPROVEMENT`: the best rewrite is `codex exec --json --sandbox workspace-write --output-schema <schema> --output-last-message <file>`, then parse JSONL and/or the final-message file instead of scraping stdout.
- `HANDLED_CORRECTLY`: only one runnable experiment config exists right now, [toy-scorer config.json](/Users/alien/Projects/meta/experiments/toy-scorer/config.json#L1). It does not set `engine`, so it uses the default Claude mutator path. `proposal-ranker` exists as a directory but has no runnable config.
- `IMPROVEMENT`: among the three mutators as currently written, `llmx` is the most fail-closed, `claude` would be strongest after adding a missing returncode check, and `codex` is the least robust by a wide margin.

**Verification**

- Ran `codex exec --help` against installed `codex-cli 0.115.0`.
- Probed `codex exec --json`; it emitted JSONL on stdout (`thread.started`) before hitting an environment-specific panic on stderr, which reinforces that stdout/stderr should be treated separately.