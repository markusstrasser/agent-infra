# Dispatch Research Audit — 2026-03-25

## Scope

Bounded audit-to-fix pass over current meta infrastructure drift, focused on:

1. Scheduler wording and launchd/manual-tick drift
2. `model-review.py` handling of Gemini Pro transient failures

## Verified Findings

### Confirmed

1. **Scheduler wording drift**
   - `CLAUDE.md` described the orchestrator as "cron-driven" and also said launchd agents were removed, while the repo still checked in `launchd` plist templates.
   - `.claude/overviews/tooling-overview.md` described several workflows as plist-driven without distinguishing checked-in templates from installed jobs.
   - `scripts/orchestrator.py` still self-described as "cron-driven".

2. **Missing Gemini session-level failover in `model-review.py`**
   - Repo guidance says Gemini 503/rate-limit events should trigger session-level fallback instead of repeated retries.
   - `scripts/model-review.py` launched llmx jobs, collected stderr, and returned failures, but had no built-in fallback path.

### Corrected During Verification

1. **Installed vs checked-in scheduler state**
   - The repo still contains plist files.
- On this machine, `launchctl list` showed no loaded `com.agent-infra.*` jobs at audit time.
   - Correct interpretation: docs should distinguish checked-in plist templates from currently installed scheduling.

### Rejected

1. **CLI example drift in orchestrator docs**
   - Rejected. The `CLAUDE.md` command examples still match the current argparse surface.

## Implemented

1. **`scripts/model-review.py`**
   - Added explicit Gemini Pro transient-failure detection.
   - Added one-shot fallback to Gemini Flash for Gemini Pro axes after the first rate-limit signal in a dispatch session.
   - Recorded fallback metadata in the JSON result (`requested_model`, `fallback_from`, `fallback_reason`, initial failure details).

2. **Docs / wording**
   - Updated `CLAUDE.md` and `.claude/overviews/tooling-overview.md` to describe manual ticking as the default and plist files as local templates/reference.
   - Updated `scripts/orchestrator.py` help/docstrings to remove the stale "cron-driven" wording.

3. **Tests**
   - Added `tests/test_model_review.py` to verify the Gemini Pro -> Gemini Flash fallback path.

## Verification

Passed:

```bash
uv run python3 -m unittest tests.test_model_review tests.test_runlog
```
