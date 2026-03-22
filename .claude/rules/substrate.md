---
paths:
  - "substrate/**"
---

# Knowledge Substrate

Per-project SQLite DB at `~/.claude/knowledge/{project}.db`. The substrate MCP is configured in intel, selve, and genomics (not meta).

**Current state (2026-03-21):** Write path works (60 MCP writes). Read path is weak (4 MCP reads). For genomics, the substrate functions as a write-only audit log — classification is deterministic and surveillance handles evidence drift. Stale objects are surfaced at session start via `session-init.sh` Phase 8.

Cross-project propagation is dormant (1 ref total). Script kept but not scheduled.

```bash
uv run python3 substrate/stress_test.py                                # 27 tests
uv run python3 substrate/propagate_cross_project.py                    # cross-project (dormant)
```

See `substrate/` directory and `decisions/2026-03-17-shared-knowledge-substrate.md` for architecture.

## Adding Substrate to a New Project

Add to the project's `.mcp.json`:
```json
"knowledge-substrate": {
  "command": "uv",
  "args": ["run", "--directory", "/Users/alien/Projects/meta",
           "python3", "substrate/mcp_server.py", "--project", "PROJECT_NAME"]
}
```
Then create `.claude/rules/substrate.md` with project-specific registration guidance. DB is auto-created at `~/.claude/knowledge/PROJECT_NAME.db`.
