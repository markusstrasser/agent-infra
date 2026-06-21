"""Tests for agentlogs compact (status_update payload reclaim)."""
from __future__ import annotations

import sqlite3

from agentlogs.compact import apply_compact_status_payloads, plan_compact_status_payloads


def test_compact_status_update_payloads(tmp_path):
    db = sqlite3.connect(tmp_path / "t.db")
    db.executescript("""
        CREATE TABLE events (
            event_id INTEGER PRIMARY KEY,
            kind TEXT,
            payload_json TEXT
        );
        INSERT INTO events VALUES (1, 'status_update', '{"spin": "x"}');
        INSERT INTO events VALUES (2, 'tool_call', '{"x": 1}');
        INSERT INTO events VALUES (3, 'status_update', NULL);
    """)
    plan = plan_compact_status_payloads(db)
    assert plan.rows == 1
    assert plan.payload_bytes > 0
    out = apply_compact_status_payloads(db)
    assert out.rows == 1
    left = db.execute(
        "SELECT COUNT(*) FROM events WHERE kind='status_update' AND payload_json IS NOT NULL"
    ).fetchone()[0]
    assert left == 0
    still = db.execute(
        "SELECT payload_json FROM events WHERE kind='tool_call'"
    ).fetchone()[0]
    assert still is not None
