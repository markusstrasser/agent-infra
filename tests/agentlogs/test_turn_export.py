from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path


SCRIPT = Path(__file__).parents[2] / "scripts" / "export_session_turns_for_emb.py"
SPEC = importlib.util.spec_from_file_location("turn_export", SCRIPT)
assert SPEC and SPEC.loader
turn_export = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(turn_export)


def fixture_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE sessions (
          session_pk INTEGER PRIMARY KEY, session_uuid TEXT, vendor_session_id TEXT,
          vendor TEXT, project_slug TEXT, start_ts TEXT, transcript_lines INTEGER,
          session_role TEXT
        );
        CREATE TABLE runs (run_id TEXT PRIMARY KEY, session_pk INTEGER);
        CREATE TABLE run_edges (src_run_id TEXT, dst_run_id TEXT, edge_type TEXT);
        CREATE TABLE events (
          event_id TEXT PRIMARY KEY, run_id TEXT, seq INTEGER, role TEXT,
          vendor_kind TEXT, text TEXT
        );
        INSERT INTO sessions VALUES
          (1, 'codex:s1', 's1', 'codex', 'agent-infra', '2026-07-16T10:00:00Z', 100, 'operator'),
          (2, 'codex:s2', 's2', 'codex', 'agent-infra', '2026-07-16T11:00:00Z', 100, 'subagent'),
          (3, 'codex:s3', 's3', 'codex', 'agent-infra', '2026-07-16T12:00:00Z', 100, 'dispatch'),
          (4, 'claude:s4', 's4', 'claude', 'agent-infra', '2026-07-16T13:00:00Z', 100, 'operator');
        INSERT INTO runs VALUES ('r1', 1), ('r2', 2), ('r3', 3), ('r4', 4), ('r4-agent', 4);
        INSERT INTO run_edges VALUES ('r4', 'r4-agent', 'spawned_by');
        INSERT INTO events VALUES
          ('e1', 'r1', 1, 'user', 'message', 'Should we keep the turn index?'),
          ('e2', 'r1', 2, 'user', 'message', '# AGENTS.md instructions for /tmp/x'),
          ('e3', 'r1', 3, 'assistant', 'message', 'Keep turns; drop whole-session blobs.'),
          ('e4', 'r1', 4, 'assistant', 'tool_result', 'noisy tool output'),
          ('e5', 'r1', 5, 'user', 'compacted', 'summary replay'),
          ('e6', 'r2', 1, 'assistant', 'assistant', 'subagent answer'),
          ('e7', 'r3', 1, 'user', 'message', 'Watch tick: read loop/WATCH.md'),
          ('e8', 'r4', 1, 'user', 'user', 'Why did the backfill skip these rows?'),
          ('e9', 'r4-agent', 1, 'user', 'user', 'Brief: trace the backfill query'),
          ('e10', 'r4-agent', 2, 'assistant', 'assistant', 'The join drops NULL paths.');
        """
    )
    return con


def test_turn_export_filters_injected_and_non_message_events() -> None:
    con = fixture_db()
    records = list(turn_export.iter_turn_records(con, vendor="codex"))
    assert [record["id"] for record in records] == ["codex:s1:e1", "codex:s1:e3"]
    assert records[0]["metadata"]["parent_id"] == "codex:s1"
    assert records[1]["metadata"]["event_id"] == "e3"
    assert records[1]["text"] == "Keep turns; drop whole-session blobs."


def test_turn_export_keeps_operator_sessions_and_their_main_runs() -> None:
    """Dispatch and subagent sessions are out; so is a subagent run inside an operator
    session (a Claude subagent transcript shares its parent's session row)."""
    con = fixture_db()
    ids = [record["id"] for record in turn_export.iter_turn_records(con)]
    assert ids == ["claude:s4:e8", "codex:s1:e1", "codex:s1:e3"]


def test_turn_export_can_include_subagents_and_writes_atomically(tmp_path: Path) -> None:
    con = fixture_db()
    output = tmp_path / "turns.jsonl"
    count, sessions = turn_export.write_jsonl_atomic(
        output, turn_export.iter_turn_records(con, operator_only=False)
    )
    assert (count, sessions) == (7, 4)
    assert output.read_text().count("\n") == 7
    assert not list(tmp_path.glob("*.tmp"))
