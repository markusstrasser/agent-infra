---
description: Weekly cleanup — stale plans, worktrees, unused skills
schedule_candidate: "0 17 * * 5"
---

Delete .claude/plans older than 14 days, list stale worktrees, and archive any skill with 0 invocations in 30 days to skills/archive/. Do not prune branches. Retry transient failures up to 3 times with exponential backoff.
