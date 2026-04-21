"""agentlogs — unified local store for Claude Code, Codex, and Gemini sessions.

Single SQLite DB, single CLI, single Python library. Replaces scripts/sessions.py
and scripts/runlog.py.

Public API:
    from agentlogs import connect, search, get_session, query

See .claude/plans/8799d138-unified-agent-logs.md for architecture.
"""

from __future__ import annotations

from .db import DEFAULT_DB_PATH, connect, current_version

__all__ = ["DEFAULT_DB_PATH", "connect", "current_version"]
__version__ = "0.1.0"
