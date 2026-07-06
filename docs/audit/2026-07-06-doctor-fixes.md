# Doctor Health Fixes — 2026-07-06

PROBE IN PROGRESS

Fixing three doctor health flags:
1. test-health:agent-infra
2. test-health:phenome
3. hook:PreToolUse:pretool-bash-secret-guard.py

Findings appended incrementally below.

## 2. test-health:phenome — FIXED (dc909042)
Root cause: peer commit 70b9efaf ("drop claimcore dep — suite green") retired the
claim-KG stack but MISSED the `mcp/` subpackage. `mcp/pyproject.toml` still declared
`claimcore` + editable path `../../substrate/packages/claimcore`, whose pyproject.toml
was removed by substrate f61c9b6 (2026-07-06 15:39). `phenome-mcp-self-check` /
`runtime-check` run the mcp in an ISOLATED env → uv fails to resolve the dead editable
path → collection_error (since 07-03). claimcore has zero live imports in mcp/src (claims_tools
unwired 2026-07-06), so the dep is dead. Fix: removed from dependencies + [tool.uv.sources].
Verify: `cd ~/Projects/phenome && uv run python3 -m pytest tests/ -m "not slow" -q`
→ 310 passed, 2 skipped (was 2 failed). Direct: `cd mcp && uv run phenome-mcp-self-check` → ok.

## 1. test-health:agent-infra — INVESTIGATING
Doctor flag "regressed 4→5" reads the 03:30 test-health.jsonl tick. Live suite
`uv run python3 -m pytest tests/ scripts/tests/ -m "not slow"` → 595 passed, 0 failed.
The 5 failures are gone in the current tree. Verifying determinism + whether refresh clears it.
