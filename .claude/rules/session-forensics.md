# Session Forensics

<!-- Gov-ID: rule:session-forensics
goal: where session logs and dbs live
verifier: null
blast_radius: local
-->

- Chat histories: `~/.claude/projects/-Users-alien-Projects-*/UUID.jsonl`
- Compaction log: `~/.claude/compact-log.jsonl`
- Session receipts: `~/.claude/session-receipts.jsonl`
- Session/run/tool-call DB: `~/.claude/agentlogs.db` (cross-vendor: Claude+Codex+Gemini+Kimi)
- Session/run CLI: `uv run agentlogs recent|search|stats|query <name>` — the live tool
- Session search: `uv run python3 scripts/sessions.py search <query>` (FTS5, faster than bash/grep)
- Run `just hook-telemetry` for current error sources

> NOTE: `runlogs.db` / `runlog.py` / `meta/runlog.md` are **dead** — runlogs.db has been
> 0 bytes since 2026-04 and runlog.py no longer exists; the live store is `agentlogs.db`.
> A few scripts (`reasoning-audit.py`, `ops.py`, `token-baseline.py`, `agent_surface.py`)
> still read the dead `runlogs.db` and silently produce nothing — they need a schema-aware
> repoint to `agentlogs.db` or retirement (scoped task; don't blind-repoint, the schemas differ).
