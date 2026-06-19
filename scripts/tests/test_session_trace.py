"""Tests for session_trace.py — Eve-shaped replay from agentlogs."""

import json
import sqlite3
import tempfile
from pathlib import Path

import session_trace as st


def _fixture_db() -> tempfile.NamedTemporaryFile:
    td = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    con = sqlite3.connect(td.name)
    con.executescript("""
        CREATE TABLE sessions (
            session_pk INTEGER PRIMARY KEY,
            session_uuid TEXT,
            vendor TEXT,
            transcript_lines INTEGER,
            start_ts TEXT
        );
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY,
            session_pk INTEGER,
            vendor TEXT,
            approval_mode TEXT,
            started_at TEXT,
            status TEXT
        );
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            run_id TEXT,
            seq INTEGER,
            kind TEXT,
            role TEXT,
            text TEXT,
            tool_call_id TEXT,
            parent_event_id TEXT
        );
        CREATE TABLE tool_calls (
            tool_call_id TEXT PRIMARY KEY,
            run_id TEXT,
            tool_name TEXT,
            status TEXT,
            ts_start TEXT,
            ts_end TEXT,
            args_json TEXT
        );
        INSERT INTO sessions VALUES (1, 'test-session-abc', 'cursor', 50, '2026-06-17');
        INSERT INTO runs VALUES ('run1', 1, 'cursor', 'default', '2026-06-17', 'ok');
        INSERT INTO events VALUES ('e1', 'run1', 1, 'user_message', 'user', 'hello', NULL, NULL);
        INSERT INTO events VALUES ('e2', 'run1', 2, 'assistant_message', 'assistant', 'hi', NULL, NULL);
        INSERT INTO tool_calls VALUES ('tc1', 'run1', 'Read', 'ok', '2026-06-17', '2026-06-17', '{}');
    """)
    con.commit()
    con.close()
    return td


def test_resolve_session_by_prefix():
    td = _fixture_db()
    con = sqlite3.connect(td.name)
    con.row_factory = sqlite3.Row
    row = st.resolve_session(con, "test-session")
    assert row is not None
    assert row["session_uuid"] == "test-session-abc"
    td.close()


def test_trace_session_shape():
    td = _fixture_db()
    con = sqlite3.connect(td.name)
    trace = st.trace_session(con, 1)
    assert trace["turn_count"] == 1
    turn = trace["turns"][0]
    assert turn["approval_mode"] == "default"
    assert len(turn["events"]) == 2
    assert turn["tool_calls"][0]["name"] == "Read"
    td.close()


def test_render_text_includes_session():
    session = {"session_uuid": "x", "vendor": "cursor", "transcript_lines": 50}
    trace = {"turn_count": 1, "turns": [{"run_id": "run1", "approval_mode": None, "events": [], "tool_calls": []}]}
    out = st.render_text(session, trace)
    assert "session x" in out
