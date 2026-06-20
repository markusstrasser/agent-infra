"""Tests for over_ask_telemetry_grader.py — L2 faithful act/ask instrument."""

import sqlite3
import tempfile

import over_ask_telemetry_grader as g


def test_ended_with_question_intent_vs_rhetorical():
    assert g.ended_with_question("Here's the result.\n\nWant me to ship it?") is True
    assert g.ended_with_question("Should I proceed with option A?") is True
    # rhetorical / embedded ? mid-text with a decisive close is NOT an ask
    assert g.ended_with_question("Why not just do it? I went ahead and shipped it.") is False
    assert g.ended_with_question("Done. Tests green.") is False
    assert g.ended_with_question("") is False


def _fixture_db():
    td = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    con = sqlite3.connect(td.name)
    con.executescript("""
        CREATE TABLE sessions (session_pk INTEGER PRIMARY KEY, session_uuid TEXT,
            vendor TEXT, transcript_lines INTEGER, start_ts TEXT);
        CREATE TABLE runs (run_id TEXT PRIMARY KEY, session_pk INTEGER, vendor TEXT,
            approval_mode TEXT, started_at TEXT, status TEXT);
        CREATE TABLE events (event_id TEXT PRIMARY KEY, run_id TEXT, seq INTEGER, kind TEXT,
            role TEXT, text TEXT, tool_call_id TEXT, parent_event_id TEXT);
        CREATE TABLE tool_calls (tool_call_id TEXT PRIMARY KEY, run_id TEXT, tool_name TEXT,
            mcp_server TEXT, status TEXT, ts_start TEXT, ts_end TEXT, args_json TEXT);
        CREATE TABLE file_touches (touch_id INTEGER PRIMARY KEY, run_id TEXT,
            tool_call_id TEXT, path TEXT, op TEXT);
    """)
    return td, con


def test_grade_session_ask():
    # final turn: only a Read (non-acting) then a closing question -> ASK
    td, con = _fixture_db()
    con.executescript("""
        INSERT INTO sessions VALUES (1, 'ask-sess', 'claude', 10, '2026-06-17');
        INSERT INTO runs VALUES ('r1', 1, 'claude', 'default', '2026-06-17', 'ok');
        INSERT INTO tool_calls VALUES ('t1','r1','Read',NULL,'ok','1','1','{}');
        INSERT INTO file_touches VALUES (1,'r1','t1','/x/a.py','read');
        INSERT INTO events VALUES ('e1','r1',9,'assistant_message','assistant',
            'I looked at the file. Want me to refactor it?',NULL,NULL);
    """)
    con.commit()
    res = g.grade_session(con, "ask-sess")
    assert res["verdict"] == "ASK", res
    assert res["acting_tool_calls"] == 0
    td.close()


def test_grade_session_act_with_edits():
    # final turn made an Edit (acting) -> ACT even if text has a trailing question
    td, con = _fixture_db()
    con.executescript("""
        INSERT INTO sessions VALUES (1, 'act-sess', 'claude', 10, '2026-06-17');
        INSERT INTO runs VALUES ('r1', 1, 'claude', 'default', '2026-06-17', 'ok');
        INSERT INTO tool_calls VALUES ('t1','r1','Edit',NULL,'ok','1','1','{}');
        INSERT INTO file_touches VALUES (1,'r1','t1','/x/a.py','edit');
        INSERT INTO events VALUES ('e1','r1',9,'assistant_message','assistant',
            'Shipped the fix. Anything else?',NULL,NULL);
    """)
    con.commit()
    res = g.grade_session(con, "act-sess")
    assert res["verdict"] == "ACT", res
    assert res["acting_tool_calls"] == 1
    assert "mutate" in res["acting_effects"]
    td.close()


def test_grade_session_act_decisive_no_question():
    # zero tool calls but no question (a decisive statement) -> ACT, not ASK
    td, con = _fixture_db()
    con.executescript("""
        INSERT INTO sessions VALUES (1, 'dec-sess', 'claude', 10, '2026-06-17');
        INSERT INTO runs VALUES ('r1', 1, 'claude', 'default', '2026-06-17', 'ok');
        INSERT INTO events VALUES ('e1','r1',9,'assistant_message','assistant',
            'Done. All tests pass.',NULL,NULL);
    """)
    con.commit()
    res = g.grade_session(con, "dec-sess")
    assert res["verdict"] == "ACT", res
    td.close()


def test_grade_session_unknown():
    td, con = _fixture_db()
    res = g.grade_session(con, "nope")
    assert res["verdict"] == "UNKNOWN"
    td.close()
