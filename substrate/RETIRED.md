# RETIRED — 2026-03-24

Knowledge substrate MCP retired. 4 reads / 60 writes in 7 days.

Knowledge-index hook (PostToolUse, 100% file coverage) solved the actual pain.
Correction propagation now handled by `scripts/propagate-correction.py`.

> **Update 2026-05-29:** Both pointers above are now superseded. The
> knowledge-index generator hook was unwired and `propagate-correction.py`
> retired with the dormant correction-sweep pipeline (agent-infra@d239543).
> Correction tracing is now `just propagate` / `just scan-corrections`. The
> substrate-MCP retirement itself still stands.

**Decision record:** `decisions/2026-03-17-shared-knowledge-substrate.md` (see Resolution section)
**Model review:** `.model-review/2026-03-24-substrate-retirement-4b8505/`
**DBs archived to:** `~/.claude/knowledge/archive/`
