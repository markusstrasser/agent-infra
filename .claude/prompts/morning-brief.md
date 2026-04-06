---
description: Morning status — open items, git activity, schedule health
schedule_candidate: "0 7 * * *"
---

Generate morning brief: read open items and schedule health from runlogs.db and rendered views, check git log --since=yesterday across meta/selve/genomics, list any schedule failures from yesterday, and write artifacts/morning-brief.md. Retry transient failures up to 3 times with exponential backoff.
