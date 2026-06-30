# Native Tool Patterns

<!-- Gov-ID: rule:native-patterns
goal: prefer native tools (just/sqlite/launchd/git) over new scripts
verifier: evals/graders/governance/native_first.py
blast_radius: local
-->

Before building a new Python script, check if a native tool already handles the need.
This table is the default — deviate with a `Native-First:` commit trailer explaining why.

| Problem Class | Default Native Tool | Don't Build |
|---|---|---|
| History/provenance annotation | git trailers, notes, blame | custom session tracker DB |
| Mutable local state | SQLite (views, triggers) | ad-hoc JSON in /tmp |
| Queryable operational state | SQLite views (`scripts/views.sql`) | Python CLI wrappers |
| Event trigger | launchd WatchPaths, git hooks | Python file watchers |
| Scheduled execution | launchd plist | Python cron loops |
| Cross-repo search | `git grep` / `rg` / agent-infra MCP | custom search scripts |
| Artifact staging | filesystem path conventions | routing registries |
| Task orchestration | justfile recipes / orchestrator.py | one-off shell scripts |
| Process supervision | launchd KeepAlive + TimeOut | Python stall detection |
| Pre-run guardrail / pre-flight check | `just` recipe-dependency of the mutating recipe (fires *on invocation*) | standing launchd/cron daemon — unless genuinely-unattended overnight progress is required |

## Decision Flow

1. **Can a `just` recipe + shell compose this from existing tools?** → Do that.
2. **Can a SQLite view or trigger handle the query?** → Add to `scripts/views.sql`.
3. **Does an MCP tool or skill already cover this?** → Use it.
4. **None of the above?** → Write the script, but add `Native-First:` trailer to the commit.

## Examples

- "I need to check orchestrator status" → `sqlite3 ~/.claude/orchestrator.db "SELECT * FROM v_queue"`
- "I need to run something daily" → launchd plist, not a Python scheduler
- "A watcher should guard every mutating run" → make it a `just` recipe-**dependency**, not a
  daemon. Genomics: `pipeline-run *ARGS: _ensure-control-plane ensure-crash-loop-watch`
  (`justfile:1848`) — the watcher fires when you invoke work, then ends with it. Genomics
  retired its cron-daemons this way (`justfile:224` "Replaces the cron-daemon pattern;
  user-invoked"). Keep a daemon only where progress must happen unattended (hutter's overnight
  search; anim's `$0`-idle hourly outer-loop). Anchor: `decisions/2026-06-30-cross-repo-loop-transfers.md` (T3).
