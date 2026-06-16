# agentlogs Foundation Fix — COMPLETE

Date: 2026-06-16 | Worktree: agent-a78ed6915c1f3f109
Live DB: ~/.claude/agentlogs.db (3.84 GB) — at PRAGMA user_version=8 after this work.

ENV NOTE: the worktree's `uv run` was broken (editable dep `../substrate/packages/
corpus-core` resolves to a nonexistent `worktrees/substrate`). Fixed with a worktree-local
symlink `worktrees/substrate -> ~/Projects/substrate` (outside the git tree, not committed;
auto-removed when the worktree is torn down). All verification ran from the worktree venv
against the shared live DB.

MERGE DEPENDENCY: the launchd indexer (`com.agent-infra.agentlogs-index`) runs the MAIN
checkout's installed code. Migrations 007/008 are already baked into the live DB and the
OLD main-checkout code reads them fine (verified: no regression). BUT the starvation fix
and going-forward is_subagent population only take effect once these 4 worktree commits
land on main. Until then the backlog won't keep draining and new claude subagent sessions
won't get is_subagent=1 at index time (they'd still be caught by the run_edges backfill
path if re-derived). Merge the worktree to activate.

============================================================================
## TASK 1 — Codex "94 errors/7d" — FIXED (commit 5c4afa2)
============================================================================
ROOT CAUSE (not a parse bug): all 94 codex errors were error_class='OrphanedRun',
sources_failed=0. OrphanedRun is written by reap_orphaned_runs() when a prior run hit the
--max-run-seconds 600 SIGALRM hard-deadline (_os._exit(75)) and left its indexer_runs row
status='running'; the next startup finalizes it as an error. The launchd job has WatchPaths
on the session dirs, so during an active session it re-fires every ~60s; on a 3.84 GB DB,
WAL contention occasionally pushes a cycle past 660s and whatever vendor's row is open gets
reaped. Codex is over-represented by vendor ordering. Evidence: run 23963 held the lock
20:58:45->21:10:08 (11.4 min > 600s), then was reaped. Codex indexing itself is HEALTHY
(discovered=40 imported=0 skipped=40 every cycle = fully caught up).

FIX: migration 007 recreates v_indexer_health splitting error_7d into parse_errors_7d
(genuine: sources_failed>0 OR non-OrphanedRun class) and orphaned_7d (reaped crash rows),
plus last_parse_error_at. `agentlogs stats` now shows the split + a footnote. Kept
success_7d/last_success_at (doctor.py + skill_usage_watch.py consumers unchanged).

VERIFIED LIVE: codex now reads parse_errors_7d=0 / orphaned_7d=94-95. claude
parse_errors_7d=1 (one real FileNotFoundError 06-11). The scary "94" is now correctly
labelled crash-recovery noise.

============================================================================
## TASK 2 — Gemini/Kimi drift — FIXED (docs, commit c81f435)
============================================================================
DETERMINATION: WIRED + FUNCTIONAL, not aspirational, not broken code. Both adapters
(gemini.py, kimi.py) exist, are registered, run every cycle, and parse correctly in
isolation (gemini 30/30 state_json + log_json -> sessions; kimi 20/20 -> sessions).
gemini has 428 sources + 96 historical imports; kimi 94 sources + 96 imports — ALL
marked success=1 in the imports table. But sessions/runs/events = 0 for both.

WHY 0 SESSIONS: the gemini/kimi data is OLD (Aug-Nov 2025). `reclaim rotate` runs prune.py
daily with keep_days=21, which DELETEs sessions/runs/events by start_ts<cutoff but
DELIBERATELY KEEPS sources/imports rows as skip-markers (prune.py:27-28). So the data was
imported, then correctly pruned, and _successful_import_exists now blocks re-import. The
launchd --since-days 60 discovery filter also excludes most old files. This is WORKING AS
DESIGNED — new gemini/kimi sessions inside the 21d window WOULD index normally.

FIX: corrected CLAUDE.md ("Claude+Codex+Cursor+Gemini") and session-forensics.md
("Claude+Codex+Gemini+Kimi") — both were misleading. Now states: 5 adapters wired, only
claude/codex/cursor have live data, gemini/kimi data is pre-retention.

NO CODE CHANGE — the pipeline is correct. (Did NOT --force-reimport the old data: it's
>21d old and would just be re-pruned next night; pure churn.)

============================================================================
## TASK 3 — Cursor headless coverage — REAL BUG FOUND + FIXED (commit d465296)
============================================================================
COVERAGE: all cursor sessions are client=cursor-agent (the HEADLESS CLI). The probe/
tmp/var-folders project dirs ARE the CI/script Composer dispatches — headless IS captured
by the path glob ~/.cursor/projects/*/agent-transcripts/*/*.jsonl. (In-editor IDE Cursor
writes elsewhere and is out of scope.)

BUG: 711 in-window cursor transcripts on disk, only 347 registered (49% coverage). Root
cause is a GENERAL starvation bug affecting ALL vendors >40 in-window sources:
index_vendor did `sources[:limit_sources]` (sorted BY PATH) BEFORE the per-source
skip-check. So it only ever examined the first `limit` paths; once those imported, every
run skipped all of them and NEVER advanced to files limit+1..N. The 364 later-sorted
cursor files were permanently starved. (Also explains why claude — 11k sources — never
fully catches up.)

FIX: (1) sort sources mtime-desc so the current session is always reachable and a backlog
drains from the recent end; (2) count the limit against ACTUAL IMPORTS not the iteration
window, so each run advances `limit` NEW sources; (3) cheap mtime-based pre-skip (one
indexed query/pass) so the caught-up case stays O(1)/file instead of sha-ing all sources.

VERIFIED LIVE: cursor 347 -> 466 sources over 3 manual cycles (40 new/cycle; skipped rising
48->100->138 via cheap skip; caught-up re-run imports 0). The remaining ~245 cursor backlog
+ claude's backlog will drain over subsequent launchd cycles ONCE MERGED to main.

============================================================================
## TASK 4 — Operator vs subagent — DERIVABLE + IMPLEMENTED (commit 204e5ba)
============================================================================
DERIVABLE: YES, cleanly, from two existing markers:
  1. claude: run_configs.metadata_json.is_subagent (adapter sets it from the raw path:
     agent-*.jsonl / subagents/ dir == isSidechain:true; 2743 such transcripts on disk).
  2. codex/all: run_edges(edge_type='spawned_by') dst runs (codex thread_spawn). The
     pre-existing v_run_kind view already exposes this per-run.

IMPLEMENTED (additive): migration 008 ADD COLUMN sessions.is_subagent (default 0=operator),
backfilled from BOTH markers (session is subagent if ANY of its runs is flagged by either),
+ idx_sessions_is_subagent + v_session_role view. Going forward the indexer populates it at
write time (SessionRow.is_subagent set by the claude adapter; sticky-true on re-import).
`agentlogs recent --role operator|subagent` filters; rows carry a 'role' column.

VERIFIED LIVE: backfill = claude 1087 op / 629 sub, codex 185 / 211, cursor 464 / 0
(matches independent run_configs=629 and v_run_kind=211 counts). Totals: 1736 operator /
840 subagent. --role filter + v_session_role view both correct. New test
test_session_role_derivation_and_filter added; full suite 39 passed.

============================================================================
## GUARDRAILS HONORED
============================================================================
- All DB changes ADDITIVE/IDEMPOTENT: 2 migrations (ADD COLUMN, CREATE VIEW/INDEX IF NOT
  EXISTS), re-index (idempotent). NO DROP/DELETE of data, no destructive rewrite.
- The only DROP statements are `DROP VIEW IF EXISTS` (recreating views) — standard, safe.
- Migrations numbered 007/008 following convention; each bumps PRAGMA user_version.
- Live DB verified after every fix.
- launchd indexer was unloaded to apply migrations under lock contention, then RELOADED
  (confirmed `launchctl list | grep agentlogs-index` present).

## NOTHING NEEDS HUMAN SIGN-OFF
No destructive migration was required. The only follow-up is mechanical: merge the 4
worktree commits to main so the launchd job picks up the starvation fix + is_subagent
population. (Optional future: the OrphanedRun frequency itself could be reduced by giving
each vendor its own SIGALRM-safe finalize, but it's now correctly labelled and benign.)

## COMMITS
- 5c4afa2  [agentlogs] Split indexer health errors — OrphanedRun is crash-recovery
- c81f435  [docs] Correct agentlogs vendor coverage — 5 adapters wired, 3 with live data
- d465296  [agentlogs] Fix limit-sources starvation — apply limit to imports, newest-first
- 204e5ba  [agentlogs] Add session is_subagent — operator vs subagent split
