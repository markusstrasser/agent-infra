# Knowledge Substrate

Per-project SQLite DB at `~/.claude/knowledge/meta.db`. The substrate MCP is configured in intel, selve, and genomics (not meta), but meta's DB exists for cross-project propagation.

When cross-project substrate work is needed (propagation, schema changes, stress tests):
```bash
uv run python3 substrate/propagate_cross_project.py   # cross-project propagation
uv run python3 substrate/stress_test.py                # 27 tests
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
