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
            mcp_server TEXT,
            status TEXT,
            ts_start TEXT,
            ts_end TEXT,
            args_json TEXT
        );
        CREATE TABLE file_touches (
            touch_id INTEGER PRIMARY KEY,
            run_id TEXT,
            tool_call_id TEXT,
            path TEXT,
            op TEXT
        );
        INSERT INTO sessions VALUES (1, 'test-session-abc', 'cursor', 50, '2026-06-17');
        INSERT INTO runs VALUES ('run1', 1, 'cursor', 'default', '2026-06-17', 'ok');
        INSERT INTO events VALUES ('e1', 'run1', 1, 'user_message', 'user', 'hello', NULL, NULL);
        INSERT INTO events VALUES ('e2', 'run1', 2, 'assistant_message', 'assistant', 'hi', NULL, NULL);
        INSERT INTO tool_calls VALUES ('tc1', 'run1', 'Read', NULL, 'ok', '2026-06-17T01', '2026-06-17', '{"file_path":"/x/a.py"}');
        INSERT INTO tool_calls VALUES ('tc2', 'run1', 'Write', NULL, 'ok', '2026-06-17T02', '2026-06-17', '{"file_path":"/x/b.py"}');
        INSERT INTO tool_calls VALUES ('tc3', 'run1', 'Read', NULL, 'ok', '2026-06-17T03', '2026-06-17', '{"file_path":"/x/b.py"}');
        INSERT INTO tool_calls VALUES ('tc4', 'run1', 'web_search_exa', 'exa', 'ok', '2026-06-17T04', '2026-06-17', '{"query":"q"}');
        INSERT INTO file_touches VALUES (1, 'run1', 'tc1', '/x/a.py', 'read');
        INSERT INTO file_touches VALUES (2, 'run1', 'tc2', '/x/b.py', 'write');
        INSERT INTO file_touches VALUES (3, 'run1', 'tc3', '/x/b.py', 'read');
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


# --- F1: typed trace IR ---

def test_effect_kind_file_op_authoritative():
    # file_touches.op overrides tool_name classification
    assert st._effect_kind("Bash", None, {"write"}) == "mutate"
    assert st._effect_kind("Bash", None, {"read"}) == "read"
    assert st._effect_kind("Bash", None, set()) == "exec"


def test_effect_kind_tool_and_mcp_fallback():
    assert st._effect_kind("Edit", None, set()) == "mutate"
    assert st._effect_kind("Read", None, set()) == "read"
    assert st._effect_kind("Agent", None, set()) == "spawn"
    assert st._effect_kind("web_search_exa", "exa", set()) == "network"
    assert st._effect_kind("some_inspect", "genomics", set()) == "read"
    assert st._effect_kind("totally_unknown", None, set()) == "other"


def test_to_typed_ir_steps_and_histogram():
    td = _fixture_db()
    con = sqlite3.connect(td.name)
    ir = st.to_typed_ir(con, 1)
    assert ir["step_count"] == 4
    assert ir["effect_histogram"]["read"] == 2      # tc1, tc3
    assert ir["effect_histogram"]["mutate"] == 1     # tc2
    assert ir["effect_histogram"]["network"] == 1    # tc4 (exa)
    # resource_ref resolves from file_touches path, then args
    step1 = next(s for s in ir["steps"] if s["id"] == "tc1")
    assert step1["resource_ref"] == "/x/a.py"
    td.close()


def test_to_typed_ir_inferred_provenance_edge():
    td = _fixture_db()
    con = sqlite3.connect(td.name)
    ir = st.to_typed_ir(con, 1)
    # tc2 writes /x/b.py, tc3 reads it -> one inferred data_flow edge
    assert len(ir["provenance_edges"]) == 1
    edge = ir["provenance_edges"][0]
    assert edge["from"] == "tc2" and edge["to"] == "tc3"
    assert edge["via_resource"] == "/x/b.py"
    assert edge["inferred"] is True
    assert ir["edges_all_inferred"] is True
    td.close()
