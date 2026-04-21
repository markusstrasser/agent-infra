"""Env-aware path constants for agentlogs."""

from __future__ import annotations

import os
from pathlib import Path


CLAUDE_DIR = Path(os.environ.get("CLAUDE_DIR", str(Path.home() / ".claude")))
PROJECTS_DIR = CLAUDE_DIR / "projects"
CODEX_DIR = Path.home() / ".codex"
GEMINI_DIR = Path.home() / ".gemini"

AGENTLOGS_DB = Path(os.environ.get("AGENTLOGS_DB", str(CLAUDE_DIR / "agentlogs.db")))
AGENTLOGS_LOCK = CLAUDE_DIR / "agentlogs.db.indexlock"
AGENTLOGS_BACKUPS = CLAUDE_DIR / "backups"
AGENTLOGS_ARCHIVE = CLAUDE_DIR / "archive"
