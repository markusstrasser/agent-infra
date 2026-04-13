"""Runlogs-backed session metadata helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from common.db import open_db

RUNLOG_SCHEMA_PATH = Path(__file__).with_name("runlog_schema.sql")
SESSIONS_BOOTSTRAP_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_pk INTEGER PRIMARY KEY,
    vendor TEXT NOT NULL,
    client TEXT NOT NULL,
    vendor_session_id TEXT,
    synthetic_session_key TEXT,
    project_root TEXT,
    project_slug TEXT,
    slug TEXT,
    project_dir TEXT,
    jsonl_path TEXT,
    started_at TEXT,
    ended_at TEXT,
    model TEXT,
    duration_min REAL,
    cost_usd REAL,
    context_pct INTEGER,
    first_message TEXT,
    files_touched TEXT,
    tools_used TEXT,
    commits TEXT,
    lines_added INTEGER,
    lines_removed INTEGER,
    subagent_count INTEGER,
    transcript_lines INTEGER,
    has_receipt INTEGER DEFAULT 0,
    indexed_at TEXT,
    file_mtime REAL,
    session_kind TEXT DEFAULT 'unclassified'
);
"""

SESSION_COLUMNS: dict[str, str] = {
    "slug": "TEXT",
    "project_dir": "TEXT",
    "jsonl_path": "TEXT",
    "started_at": "TEXT",
    "ended_at": "TEXT",
    "model": "TEXT",
    "duration_min": "REAL",
    "cost_usd": "REAL",
    "context_pct": "INTEGER",
    "first_message": "TEXT",
    "files_touched": "TEXT",
    "tools_used": "TEXT",
    "commits": "TEXT",
    "lines_added": "INTEGER",
    "lines_removed": "INTEGER",
    "subagent_count": "INTEGER",
    "transcript_lines": "INTEGER",
    "has_receipt": "INTEGER DEFAULT 0",
    "indexed_at": "TEXT",
    "file_mtime": "REAL",
    "session_kind": "TEXT DEFAULT 'unclassified'",
}


def open_session_store(db_path: Path | str) -> sqlite3.Connection:
    db = open_db(db_path, foreign_keys=True)
    db.executescript(SESSIONS_BOOTSTRAP_SQL)
    for column, column_type in SESSION_COLUMNS.items():
        try:
            db.execute(f"ALTER TABLE sessions ADD COLUMN {column} {column_type}")
        except sqlite3.OperationalError:
            pass
    db.executescript(RUNLOG_SCHEMA_PATH.read_text())
    return db


def classify_session_kind(first_message: str | None) -> str:
    text = (first_message or "").lower()
    if not text:
        return "unclassified"
    if any(token in text for token in (
        "hook", "fix", "broken", "stale", "cleanup", "debug", "error",
        "fail", "doctor", "health", "config", "settings", "update claude",
        "update memory", "orchestrator", "launchd", "plist",
    )):
        return "maintenance"
    if any(token in text for token in (
        "research", "paper", "literature", "evidence", "investigate",
        "search for", "what do we know",
    )):
        return "research"
    if any(token in text for token in (
        "review", "retro", "session-analyst", "design-review",
        "model-review", "audit",
    )):
        return "review"
    if any(token in text for token in (
        "build", "implement", "add", "create", "write", "new skill", "new hook",
    )):
        return "feature"
    if any(token in text for token in (
        "plan", "propose", "strategy", "architecture", "refactor",
    )):
        return "planning"
    return "other"


def ensure_session_pk(
    db: sqlite3.Connection,
    *,
    uuid: str,
    project_root: str | None,
    project_slug: str | None,
    vendor: str = "claude",
    client: str = "claude-code",
) -> int:
    row = db.execute(
        """
        SELECT session_pk
        FROM sessions
        WHERE vendor = ? AND client = ? AND vendor_session_id = ?
        """,
        (vendor, client, uuid),
    ).fetchone()
    if row is not None:
        db.execute(
            """
            UPDATE sessions
            SET project_root = COALESCE(?, project_root),
                project_slug = COALESCE(?, project_slug)
            WHERE session_pk = ?
            """,
            (project_root, project_slug, row["session_pk"]),
        )
        return int(row["session_pk"])

    cursor = db.execute(
        """
        INSERT INTO sessions (vendor, client, vendor_session_id, project_root, project_slug)
        VALUES (?, ?, ?, ?, ?)
        """,
        (vendor, client, uuid, project_root, project_slug),
    )
    return int(cursor.lastrowid)


def upsert_session_metadata(db: sqlite3.Connection, row: dict) -> None:
    session_pk = row["session_pk"]
    current = db.execute(
        "SELECT first_message FROM sessions WHERE session_pk = ?",
        [session_pk],
    ).fetchone()
    columns = [key for key in row.keys() if key != "session_pk"]
    assignments = ", ".join(f"{column} = ?" for column in columns)
    db.execute(
        f"UPDATE sessions SET {assignments} WHERE session_pk = ?",
        [row[column] for column in columns] + [session_pk],
    )
    if current and current["first_message"] and current["first_message"] != row["first_message"]:
        db.execute(
            "INSERT INTO sessions_fts(sessions_fts, rowid, first_message) VALUES('delete', ?, ?)",
            [session_pk, current["first_message"]],
        )
        if row["first_message"]:
            db.execute(
                "INSERT INTO sessions_fts(rowid, first_message) VALUES(?, ?)",
                [session_pk, row["first_message"]],
            )
