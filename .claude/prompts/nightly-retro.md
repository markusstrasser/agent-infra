---
description: End-of-day session retrospective — findings to improvement-log
schedule_candidate: "0 22 * * *"
---

Run /retro on today's sessions. Write findings to improvement-log. Retry transient failures up to 3 times with exponential backoff (1m, 5m, 15m). Only auto-commit docs/config safety classes; escalate any .py/.sh change.

Then run the learning-loop deep pass: `just reflect-classify` (deterministic, $0, self-guarding — it only classifies clusters of ≥3 signals across ≥2 sessions and defers the rest). It auto-records evidence to existing FM dossiers and quarantines any new-FM mints or enforcer proposals. If `just reflect-review` shows pending items, summarize them in the retro for the human — do NOT promote or apply them (auto-record-never-auto-apply; enforcers stay report-only until the human flips them active).
