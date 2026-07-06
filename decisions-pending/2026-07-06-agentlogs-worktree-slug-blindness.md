# agentlogs: worktree sessions invisible to project queries + ingest lag

**Found:** 2026-07-06, arc-agi operator-input week audit
(`arc-agi/research/2026-07-06-operator-input-week-audit.md` §C1).

## Symptom [DATA]

`project_slug = 'arc-agi'` queries returned 313 of ~928 actual user-role messages for the
week. Two causes:

1. **Worktree sessions get their own slug.** Sessions launched via `claude --worktree` write
   transcripts under e.g. `-Users-alien-Projects-arc-agi--claude-worktrees-sorted-jumping-parnas`,
   which the indexer slugs as a DIFFERENT project. With worktree-per-peer now the recommended
   multi-session pattern (SessionStart peer warning), a growing share of each repo's sessions
   is invisible to `--project <repo>` queries — silently, a false-zero of the rg-gitignore class.
2. **Ingest lag on active sessions:** messages typed hours earlier (a 12:40 #g) were absent at
   22:30 despite the indexer running; recent/open sessions lag behind `agentlogs recent`
   freshness expectations.

## Why it matters

`agentlogs search --project X` is the canonical "what did we discuss" tool (global CLAUDE.md
toolbelt). Rescue-rate / operator-intervention audits (HINDSIGHT Mode 3) read operator
messages; under-reads corrupt the RSI metric. Any negative-evidence claim ("operator never
said X") from agentlogs is currently unsound.

## Proposed fix

- Indexer canonicalizes project roots: resolve `<repo>--claude-worktrees-<name>` (and git
  worktree paths generally — `git rev-parse --git-common-dir` equivalent) to the main repo
  slug; keep the worktree name as a session attribute, not a slug fork.
- Add a drift test: a synthetic worktree transcript must land under the parent slug.
- Freshness: surface per-vendor max-ingested-ts in `agentlogs stats` (it may already);
  document that open sessions lag, so auditors fall back to disk transcripts.
- Interim workaround (already in use, arc-agi): direct disk-transcript extraction —
  `arc-agi/loop/rescue_rate.py` globs `-Users-alien-Projects-arc-agi*` dirs.
