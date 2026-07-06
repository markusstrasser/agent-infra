# Worktree GC Sweep — 2026-07-06

PROBE IN PROGRESS

## Scope reconciliation

Control-plane `--check` now reports **6 LAND / 2 INSPECT / 1 REAP**, but 4 of those
are **live arc-agi peer sessions** committing seconds/minutes ago — EXCLUDED (task:
never touch live peer work). The task's intended stale set (3 LAND / 1 INSPECT "pub" /
1 REAP) maps to:

| Disp | Repo/branch | ahead | age | status |
|------|-------------|-------|-----|--------|
| LAND | substrate/worktree-agent-a1a05d9f236aac59a | 2 | 8d | pending |
| LAND | substrate/worktree-agent-a9d90b0c2c159a0f9 | 2 | 8d | pending |
| LAND | substrate/worktree-agent-ade0fd3e6f3d2b12e | 2 | 8d | pending |
| INSPECT | publishing/worktree-agent-a50704d3c6939405b | 13 | 7wk | pending |
| REAP | genomics/worktree-agent-aab883543a1e2fd6b | 1 (DUP) | 2h | pending |

EXCLUDED (live arc-agi peers): a36c381 (INSPECT, 9min, dirty), a770d7fe (82s),
ab45524 (2min), ad8f0c25 (2min).

## Per-branch findings (appended as confirmed)
