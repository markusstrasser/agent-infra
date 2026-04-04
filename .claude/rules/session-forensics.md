# Session Forensics

- Chat histories: `~/.claude/projects/-Users-alien-Projects-*/UUID.jsonl`
- Compaction log: `~/.claude/compact-log.jsonl`
- Session receipts: `~/.claude/session-receipts.jsonl`
- Runlog DB: `~/.claude/runlogs.db`
- Runlog docs: `meta/runlog.md`
- Runlog CLI: `uv run python3 scripts/runlog.py stats|import|query|recent`
- Run `just hook-telemetry` for current error sources
- Session search: `uv run python3 scripts/sessions.py search <query>` (FTS5, faster than bash/grep)
