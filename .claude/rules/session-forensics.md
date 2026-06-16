# Session Forensics

<!-- Gov-ID: rule:session-forensics
goal: where session logs and dbs live
verifier: null
blast_radius: local
-->

- Clean-room repro: `claude --safe-mode` (or `CLAUDE_CODE_SAFE_MODE=1`, ≥2.1.169) disables ALL CLAUDE.md/plugins/skills/hooks/MCP — first move for "is the harness causing this?"; pairs with single-variable harness commits
- Codex hook ground truth: `~/.codex/log/hook_shim_invocations.jsonl` (one JSONL line per shim-wrapped hook fire; codex#25875-class no-fire regressions become a grep)
- Chat histories: `~/.claude/projects/-Users-alien-Projects-*/UUID.jsonl`
- Compaction log: `~/.claude/compact-log.jsonl`
- Session receipts: `~/.claude/session-receipts.jsonl`
- Session/run/tool-call DB: `~/.claude/agentlogs.db` (cross-vendor; 5 adapters wired: Claude, Codex, Cursor, Gemini, Kimi — but only Claude+Codex+Cursor have live data; Gemini/Kimi data is pre-21d-retention so it was indexed then pruned, and the import-ledger blocks re-import of those old files — new Gemini/Kimi sessions would index normally)
- Session/run CLI: `uv run agentlogs recent|search|stats|query <name>` — the live tool
- agentlogs ships INSIDE the agent-infra wheel (hatch force-include; no own dist, non-editable install) — after editing `src/agentlogs/`, `uv sync --reinstall-package agent-infra`; `--reinstall-package agentlogs` is a silent no-op
- Session search: `uv run python3 scripts/sessions.py search <query>` (FTS5, faster than bash/grep)
- Run `just hook-telemetry` for current error sources

> NOTE: `runlogs.db` / `runlog.py` / `meta/runlog.md` are **dead** — runlogs.db has been
> 0 bytes since 2026-04 and runlog.py no longer exists; the live store is `agentlogs.db`.
> `reasoning-audit.py`, `ops.py` (+ its `session_store.py`), and `token-baseline.py` were
> deleted 2026-06-13 (no live callers). No live script still reads the dead DB:
> `agent_surface.py` was already repointed to `agentlogs.db` (tool_calls/runs/sessions
> schema) — the old "reads runlogs.db" note was stale.
