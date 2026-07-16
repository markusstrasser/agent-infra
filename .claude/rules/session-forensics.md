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
- agentlogs labels harness-injected user lines at ingest (Claude adapter): `events.vendor_kind` = `compact_summary` (isCompactSummary) / `meta_injected` (isMeta) vs `user`. Label-never-drop — forensics sees everything; signal miners filter on the label. Raw-JSONL miners load `scripts/common/transcript_text.py` instead of re-implementing the predicate (drift-tested vs the skills-repo copy)
- Session/run/tool-call DB: `~/.claude/agentlogs.db` (cross-vendor; 5 adapters wired: Claude, Codex, Cursor, Gemini, Kimi — but only Claude+Codex+Cursor have live data; Gemini/Kimi data is pre-21d-retention so it was indexed then pruned, and the import-ledger blocks re-import of those old files — new Gemini/Kimi sessions would index normally)
- Session/run CLI: `uv run agentlogs recent|search|stats|query <name>` — the live tool
- agentlogs ships INSIDE the agent-infra wheel (hatch force-include; no own dist, non-editable install) — after editing `src/agentlogs/`, `uv sync --reinstall-package agent-infra`; `--reinstall-package agentlogs` is a silent no-op
- Session search: `uv run python3 scripts/sessions.py search <query>` (FTS5, faster than bash/grep)
- **Embed-once semantic layer** (angle-agnostic; query any NEW angle for free, no per-angle LLM re-read — validated 2026-06-17, `research/2026-06-17-embed-once-validated-recurring-mistakes.md`): `scripts/export_sessions_for_emb.py --out s.jsonl` → `emb embed s.jsonl -o idx/ --chunk` → `emb search idx/ "angle"` (free) / `emb read idx/ "angle" --top-k 200` (cheap LLM-on-hits). For recurring-pattern clustering: embed the signal texts + `emb pairs idx/ --threshold 0.80`. NOTE: bulk LLM passes use subscription/`--flex`, never metered Composer.
- **Turn-level prior context** (answer retrieval, not corpus mining): `scripts/prior-context-index build` exports real user/assistant turns into an atomic cached `emb` generation; `scripts/prior-context-index search "what decision did we make?" --project <slug>` returns session-deduplicated `agentlogs show …` handles. Manual/advisory only until the 2026-07-10 rediscovery-control window closes on 2026-07-24; do not wire the shared UserPromptSubmit hook earlier.
- Run `just hook-telemetry` for current error sources

> NOTE: `runlogs.db` / `runlog.py` / `meta/runlog.md` are **dead** — runlogs.db has been
> 0 bytes since 2026-04 and runlog.py no longer exists; the live store is `agentlogs.db`.
> `reasoning-audit.py`, `ops.py` (+ its `session_store.py`), and `token-baseline.py` were
> deleted 2026-06-13 (no live callers). No live script still reads the dead DB:
> `agent_surface.py` was already repointed to `agentlogs.db` (tool_calls/runs/sessions
> schema) — the old "reads runlogs.db" note was stale.
