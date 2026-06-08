"""Schema + migration runner tests."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import agentlogs
from agentlogs import index as ix


def test_fresh_db_reaches_head_version(tmp_path: Path) -> None:
    db = agentlogs.connect(tmp_path / "new.db")
    assert agentlogs.current_version(db) == 4
    db.close()


def test_schema_has_expected_surface(tmp_path: Path) -> None:
    db = agentlogs.connect(tmp_path / "new.db")
    tables = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}
    assert {
        "sources", "imports", "record_refs", "sessions", "runs", "events",
        "tool_calls", "file_touches", "run_edges", "run_configs",
        "git_commits", "git_commit_files", "indexer_runs",
        "trace_index",
    }.issubset(tables)
    db.close()


def test_tool_calls_has_no_result_json(tmp_path: Path) -> None:
    """Phase 0 refinement: result_json dropped (duplicated by tool_result event)."""
    db = agentlogs.connect(tmp_path / "new.db")
    cols = {r[1] for r in db.execute("PRAGMA table_info(tool_calls)")}
    assert "result_json" not in cols
    assert "args_json" in cols
    db.close()


def test_runs_has_token_columns(tmp_path: Path) -> None:
    """Phase 0 refinement: token counts promoted to structured columns."""
    db = agentlogs.connect(tmp_path / "new.db")
    cols = {r[1] for r in db.execute("PRAGMA table_info(runs)")}
    assert {
        "input_tokens", "cached_tokens", "output_tokens",
        "reasoning_tokens", "total_tokens",
    }.issubset(cols)
    db.close()


def test_events_fts_trigger_maintains_index(tmp_path: Path) -> None:
    db = agentlogs.connect(tmp_path / "new.db")
    db.execute(
        "INSERT INTO sessions (vendor, client, vendor_session_id, session_uuid) "
        "VALUES ('claude', 'cc', 's1', 's1')"
    )
    pk = db.execute("SELECT session_pk FROM sessions").fetchone()[0]
    db.execute(
        "INSERT INTO runs (run_id, session_pk, vendor, client) "
        "VALUES ('r1', ?, 'claude', 'cc')", (pk,),
    )
    db.execute(
        "INSERT INTO events (event_id, run_id, seq, kind, role, text) "
        "VALUES ('e1', 'r1', 1, 'user_message', 'user', 'find subject_id aliases')"
    )
    hits = db.execute(
        "SELECT COUNT(*) FROM events_fts WHERE events_fts MATCH 'subject_id'"
    ).fetchone()[0]
    assert hits == 1

    db.execute("DELETE FROM events WHERE event_id='e1'")
    hits2 = db.execute(
        "SELECT COUNT(*) FROM events_fts WHERE events_fts MATCH 'subject_id'"
    ).fetchone()[0]
    assert hits2 == 0
    db.close()


def test_migrations_idempotent_on_reopen(tmp_path: Path) -> None:
    path = tmp_path / "new.db"
    db1 = agentlogs.connect(path)
    db1.close()
    db2 = agentlogs.connect(path)
    assert agentlogs.current_version(db2) == 4
    db2.close()


def test_token_aggregation_gemini_style() -> None:
    """Gemini token dicts sit at top level without a wrapper key."""
    from agentlogs.index import aggregate_tokens

    class FakeEvent:
        def __init__(self, payload):
            self.payload = payload

    events = [
        FakeEvent({"cached": 0, "input": 100, "output": 50, "thoughts": 20, "total": 170}),
        FakeEvent({"cached": 10, "input": 200, "output": 80, "thoughts": 0, "total": 290}),
    ]
    totals = aggregate_tokens(events)
    assert totals["input_tokens"] == 300
    assert totals["cached_tokens"] == 10
    assert totals["output_tokens"] == 130
    assert totals["reasoning_tokens"] == 20
    assert totals["total_tokens"] == 460


def test_token_aggregation_claude_style() -> None:
    """Claude token dicts are nested under 'usage'."""
    from agentlogs.index import aggregate_tokens

    class FakeEvent:
        def __init__(self, payload):
            self.payload = payload

    events = [
        FakeEvent({"usage": {"input_tokens": 100, "output_tokens": 50}}),
        FakeEvent({"message": {"usage": {"input_tokens": 200, "output_tokens": 80}}}),
    ]
    totals = aggregate_tokens(events)
    assert totals["input_tokens"] == 300
    assert totals["output_tokens"] == 130


def test_ingest_minimal_real_data(tmp_path: Path) -> None:
    """End-to-end: ingest 2 Gemini sources, verify events + tokens + FTS."""
    db = agentlogs.connect(tmp_path / "e2e.db")
    stats = ix.index_vendor(db, "gemini", limit_sources=2)
    assert stats.sources_imported >= 1
    assert stats.events_written > 0

    # FTS5 populated
    any_hit = db.execute("SELECT COUNT(*) FROM events_fts").fetchone()[0]
    assert any_hit == stats.events_written

    # indexer_runs has a success row
    ir = db.execute(
        "SELECT status, vendor, sources_imported FROM indexer_runs ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    assert ir["status"] == "success"
    assert ir["vendor"] == "gemini"
    assert ir["sources_imported"] == stats.sources_imported

    # import_id FK set on events
    unlinked = db.execute(
        "SELECT COUNT(*) FROM events WHERE import_id IS NULL"
    ).fetchone()[0]
    assert unlinked == 0
    db.close()
