"""Env-aware path constants for ~/.claude resources."""

import os
from pathlib import Path

# Env-aware: CLAUDE_DIR=/tmp/test redirects everything (for tests/worktrees)
CLAUDE_DIR = Path(os.environ.get("CLAUDE_DIR", str(Path.home() / ".claude")))
PROJECTS_DIR = CLAUDE_DIR / "projects"

# Common JSONL files
RECEIPTS_PATH = CLAUDE_DIR / "session-receipts.jsonl"
COMPACT_LOG = CLAUDE_DIR / "compact-log.jsonl"
TRIGGERS_FILE = CLAUDE_DIR / "hook-triggers.jsonl"

# Databases
ORCHESTRATOR_DB = CLAUDE_DIR / "orchestrator.db"
SESSIONS_DB = CLAUDE_DIR / "sessions.db"
RUNLOGS_DB = CLAUDE_DIR / "runlogs.db"
FINDINGS_DB = CLAUDE_DIR / "findings.db"
