# Doctor Health Fixes — 2026-07-06

All three doctor health flags FIXED. `doctor.py` now: 405 pass, 22 warn, **0 fail**
(was 6 fail: 3 targets + 3 sibling genomics hooks swept as one class).

## 1. test-health:agent-infra — FIXED (peer 14:00 commits; sentinel refreshed)
Doctor flag "regressed 4→5" read the stale 03:30 test-health.jsonl tick. The 5 failures
were already root-caused + fixed by the maintain-tick loop at ~14:00 today:
`bfa00b6` (timeout-scaler test born red at 80MB), `7c7c5f7` (maintainability dates
hardcoded, aged out of days=120), `9f3ee1b` (approval-tiers manifest missing 2 guards);
logged in `8c9f7d9`. Live suite is green — nothing left to fix at the root.
My action: refreshed the sentinel (`test_health.py --repo agent-infra`) so doctor reads current state.
Verify: `uv run python3 -m pytest tests/ scripts/tests/ -m "not slow"` → 595 passed, 0 failed.

## 2. test-health:phenome — FIXED (dc909042, phenome)
Root cause: peer commit `70b9efaf` ("drop claimcore dep — suite green") retired the
claim-KG stack but MISSED the `mcp/` subpackage. `mcp/pyproject.toml` still declared
`claimcore` + editable path `../../substrate/packages/claimcore`, whose pyproject.toml
was removed by substrate `f61c9b6` (2026-07-06 15:39). `phenome-mcp-self-check` /
`runtime-check` build the mcp in an ISOLATED env → uv can't resolve the dead editable
path → exit 2 → test-health collection_error (since 07-03). claimcore has zero live
imports in `mcp/src` (claims_tools unwired 2026-07-06). Fix: removed from `dependencies`
+ `[tool.uv.sources]`. NOT shared, working tree was clean — pure completion of an
incomplete migration.
Verify: `cd ~/Projects/phenome && uv run python3 -m pytest tests/ -m "not slow"` →
310 passed, 2 skipped (was 2 failed). Direct: `cd mcp && uv run phenome-mcp-self-check` → ok.

## 3. hook:PreToolUse:pretool-bash-secret-guard.py — FIXED (13aca8d8f, genomics)
Root cause: 4 genomics-local PreToolUse hooks were committed 100644 (no +x) on Jun 30;
`doctor.py:141` checks `os.access(script, os.X_OK)` and flagged "Not executable".
Swept the whole class (rule #21): secret-guard + process-kill-guard + pytest-scope-guard
+ sample-diagnostic-router, all four 100644. NOT a shared hook (not in skills/hooks or
any other repo; genomics-only, invoked via `python3 X.py` so no blocking-behavior change)
— safe to ship, no human gate. Durable root fix: `git update-index --chmod=+x` persists
the bit in git (100644→100755) so a fresh checkout stays green. Fail-loud guard already
exists: doctor.py:141 is the standing detector that caught it. No catalog entry — the
genomics `docs/ops/*failure-pattern-catalog*` is scoped to biology-pipeline/Modal run
failures, not harness config; a hook-+x note there would be off-altitude noise.
Verify: `git ls-files -s .claude/hooks/pretool-bash-*.py` → all 100755;
`uv run python3 scripts/doctor.py` → all 4 hooks ✓.

## Final verification
`uv run python3 scripts/doctor.py` → 405 pass, 22 warn, 0 fail. All three targets ✓.
