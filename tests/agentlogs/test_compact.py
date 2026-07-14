"""Tests for agentlogs compact (write-only payload reclaim: status_update + text-backed)."""
from __future__ import annotations

import sqlite3

from agentlogs.compact import (
    apply_compact_status_payloads,
    plan_compact_status_payloads,
    plan_compact_text_backed_payloads,
)
from agentlogs.index import TEXT_BACKED_PAYLOADLESS_KINDS, trim_payload


def _db(tmp_path) -> sqlite3.Connection:
    db = sqlite3.connect(tmp_path / "t.db")
    db.executescript("""
        CREATE TABLE events (
            event_id INTEGER PRIMARY KEY,
            kind TEXT,
            text TEXT,
            payload_json TEXT
        );
        INSERT INTO events VALUES (1, 'status_update', NULL, '{"spin": "x"}');
        INSERT INTO events VALUES (2, 'tool_call', 'Bash(ls)', '{"args": 1}');
        INSERT INTO events VALUES (3, 'status_update', NULL, NULL);
        INSERT INTO events VALUES (4, 'tool_result', 'stdout here', '{"stdout": "stdout here"}');
        INSERT INTO events VALUES (5, 'tool_result', '', '{"isImage": true}');
        INSERT INTO events VALUES (6, 'reasoning', '[reasoning]', '{"encrypted_content": "gAAA"}');
        INSERT INTO events VALUES (7, 'token_usage', NULL, '{"in": 5, "out": 9}');
        INSERT INTO events VALUES (8, 'error', 'traceback...', '{"call_id": "c1"}');
    """)
    return db


def test_compact_both_passes(tmp_path):
    db = _db(tmp_path)

    status = plan_compact_status_payloads(db)
    assert status.rows == 1

    text_backed = plan_compact_text_backed_payloads(db)
    # rows 2 (tool_call), 4 (tool_result), 6 (reasoning), 8 (error) — NOT row 5
    assert text_backed.rows == 4

    out = apply_compact_status_payloads(db)
    assert out.rows == 5  # aggregate of both passes

    nulled = {r[0] for r in db.execute(
        "SELECT event_id FROM events WHERE payload_json IS NULL").fetchall()}
    assert nulled == {1, 2, 3, 4, 6, 8}


def test_sole_copy_and_unlisted_kinds_survive(tmp_path):
    """Empty-text tool_result keeps its payload (sole DB copy); token_usage is
    not in the kind set and is untouched."""
    db = _db(tmp_path)
    apply_compact_status_payloads(db)

    image_result = db.execute(
        "SELECT payload_json FROM events WHERE event_id = 5").fetchone()[0]
    assert image_result is not None, "text-empty tool_result payload is the sole DB copy"

    usage = db.execute(
        "SELECT payload_json FROM events WHERE event_id = 7").fetchone()[0]
    assert usage is not None, "token_usage is outside the text-backed kind set"


def test_apply_is_idempotent(tmp_path):
    db = _db(tmp_path)
    first = apply_compact_status_payloads(db)
    second = apply_compact_status_payloads(db)
    assert first.rows == 5
    assert second.rows == 0


def test_ingest_predicate_matches_backfill():
    """The crux invariant: trim_payload's text-backed drop (ingest) and the
    compact WHERE clause (backfill) must name the same rows — both load
    TEXT_BACKED_PAYLOADLESS_KINDS from index.py."""
    for kind in TEXT_BACKED_PAYLOADLESS_KINDS:
        # text present → ingest drops the payload entirely
        assert trim_payload({"stdout": "x"}, kind, "some text") is None
        # text empty/None → ingest keeps it (sole copy), matching the backfill guard
        assert trim_payload({"isImage": True}, kind, "") is not None
        assert trim_payload({"isImage": True}, kind, None) is not None
    # unlisted kind with text → key-level trim only, payload survives
    assert trim_payload({"in": 5}, "token_usage", "t") is not None
