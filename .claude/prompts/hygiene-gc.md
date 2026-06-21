---
description: Weekly cleanup — stale plans, worktrees, unused skills
schedule_candidate: "0 17 * * 5"
---

Delete .claude/plans older than 14 days, run `just worktree-gc apply --all-projects` (audit first if unsure; use `--force-stale` only when ahead==0 worktrees show deletion-drift dirt), and archive any skill with 0 invocations in 30 days to skills/archive/. Do not `--prune-branches` unless operator confirms. Retry transient failures up to 3 times with exponential backoff.
