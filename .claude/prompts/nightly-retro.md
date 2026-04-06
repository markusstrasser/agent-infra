---
description: End-of-day session retrospective — findings to improvement-log
schedule_candidate: "0 22 * * *"
---

Run /retro on today's sessions. Write findings to improvement-log. Retry transient failures up to 3 times with exponential backoff (1m, 5m, 15m). Only auto-commit docs/config safety classes; escalate any .py/.sh change.
