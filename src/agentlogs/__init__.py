"""agentlogs — unified local store for Claude Code, Codex, and Gemini sessions.

Single SQLite DB, single CLI, single Python library. Replaces scripts/sessions.py
and scripts/runlog.py.

Public API::

    from agentlogs import connect, search_sessions, search_events, get_session, recent_sessions, run_query

    with connect() as db:
        hits = search_sessions(db, "subject_id aliases", vendor="claude")
        for h in hits:
            print(h.session_uuid, h.matching_events)

See .claude/plans/8799d138-unified-agent-logs.md for architecture.
"""

from __future__ import annotations

from .db import DEFAULT_DB_PATH, connect, current_version
from .paths import AGENTLOGS_ARCHIVE, AGENTLOGS_BACKUPS, AGENTLOGS_DB, AGENTLOGS_LOCK
from .query import list_queries, run_query
from .search import (
    EventHit,
    SessionHit,
    get_session,
    recent_sessions,
    search_events,
    search_sessions,
)

__all__ = [
    # DB
    "AGENTLOGS_ARCHIVE",
    "AGENTLOGS_BACKUPS",
    "AGENTLOGS_DB",
    "AGENTLOGS_LOCK",
    "DEFAULT_DB_PATH",
    "connect",
    "current_version",
    # Search
    "EventHit",
    "SessionHit",
    "get_session",
    "recent_sessions",
    "search_events",
    "search_sessions",
    # Query
    "list_queries",
    "run_query",
]

__version__ = "0.1.0"
