"""CLI + search + query + lock tests."""
from __future__ import annotations

import multiprocessing
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest

import agentlogs
from agentlogs import index as ix
from agentlogs import search as se
from agentlogs.cli import main as cli_main
from agentlogs.locks import IndexerLockBusy, indexer_lock


def _seeded_db(tmp_path: Path) -> Path:
    """A small DB with one Gemini session ingested."""
    db_path = tmp_path / "seed.db"
    db = agentlogs.connect(db_path)
    ix.index_vendor(db, "gemini", limit_sources=2)
    db.close()
    return db_path


def test_cli_stats(tmp_path, capsys):
    db_path = _seeded_db(tmp_path)
    rc = cli_main(["--db", str(db_path), "stats"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "vendor" in out and "gemini" in out


def test_cli_recent(tmp_path, capsys):
    db_path = _seeded_db(tmp_path)
    rc = cli_main(["--db", str(db_path), "recent", "-n", "5"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "session_uuid" in out


def test_cli_search_session_mode(tmp_path, capsys):
    db_path = _seeded_db(tmp_path)
    rc = cli_main(["--db", str(db_path), "search", "the", "--limit", "3"])
    # May or may not have hits — just verify no crash
    assert rc == 0


def test_cli_search_event_mode(tmp_path, capsys):
    db_path = _seeded_db(tmp_path)
    rc = cli_main(["--db", str(db_path), "search", "the", "--mode", "event", "--limit", "3"])
    assert rc == 0


def test_search_treats_paths_and_hyphens_as_literals(tmp_path) -> None:
    db = agentlogs.connect(tmp_path / "fts-literals.db")
    db.execute(
        """
        INSERT INTO sessions
          (session_pk, vendor, client, session_uuid, project_slug, is_subagent)
        VALUES (1, 'claude', 'claude-code', 's-1', 'genomics', 0)
        """
    )
    db.execute(
        """
        INSERT INTO runs (run_id, session_pk, vendor, client)
        VALUES ('r-1', 1, 'claude', 'claude-code')
        """
    )
    db.execute(
        """
        INSERT INTO events (event_id, run_id, seq, kind, text)
        VALUES (
          'e-1',
          'r-1',
          1,
          'tool_result',
          'dispatch launch failed: [Errno 17] File exists: data/wgs; sample-state followup'
        )
        """
    )

    hits = se.search_sessions(
        db,
        "data/wgs File exists sample-state",
        project="genomics",
    )

    assert len(hits) == 1
    assert hits[0].session_uuid == "s-1"


def test_cli_query_list(tmp_path, capsys):
    db_path = _seeded_db(tmp_path)
    rc = cli_main(["--db", str(db_path), "query"])
    assert rc == 0
    out = capsys.readouterr().out
    # Just spot-check one known named query
    assert "tool_failure_rate_by_tool" in out


def test_session_role_derivation_and_filter(tmp_path):
    """is_subagent is derived from the claude subagent path marker, persisted on the
    session, and exposed by recent_sessions(role=...) — migration 008."""
    import json
    from agentlogs import search as se

    projects = tmp_path / "projects" / "-proj"
    sub_dir = projects / "subagents"
    sub_dir.mkdir(parents=True)

    def _line(role, text, ts):
        return json.dumps({
            "type": role, "timestamp": ts, "cwd": "/proj", "gitBranch": "main",
            "isSidechain": role == "user", "uuid": f"{role}-{ts}",
            "message": {"role": role, "content": [{"type": "text", "text": text}]},
        }) + "\n"

    # Operator (top-level) transcript.
    op = projects / "11111111-1111-1111-1111-111111111111.jsonl"
    op.write_text(_line("user", "operator turn", "2026-06-16T10:00:00Z")
                  + _line("assistant", "ok", "2026-06-16T10:00:01Z"))
    # Subagent transcript (subagents/ dir + agent- stem => is_subagent).
    sa = sub_dir / "agent-22222222222222222.jsonl"
    sa.write_text(_line("user", "subagent turn", "2026-06-16T10:05:00Z")
                  + _line("assistant", "done", "2026-06-16T10:05:01Z"))

    db = agentlogs.connect(tmp_path / "roles.db")
    ix.index_vendor(db, "claude", source_paths=[op, sa])

    roles = {
        r["vendor_session_id"]: r["is_subagent"]
        for r in db.execute("SELECT vendor_session_id, is_subagent FROM sessions WHERE vendor='claude'")
    }
    assert any(v == 1 for v in roles.values()), "subagent session not flagged"
    assert any(v == 0 for v in roles.values()), "operator session mis-flagged"

    op_rows = se.recent_sessions(db, role="operator")
    sa_rows = se.recent_sessions(db, role="subagent")
    assert all(r["role"] == "operator" for r in op_rows)
    assert all(r["role"] == "subagent" for r in sa_rows)
    assert len(op_rows) >= 1 and len(sa_rows) >= 1
    db.close()


def test_query_signatures():
    params = agentlogs.list_queries()
    assert "tool_failure_rate_by_tool" in params
    assert "build_then_retire" in params


def test_query_missing_param_raises(tmp_path):
    db = agentlogs.connect(tmp_path / "new.db")
    try:
        with pytest.raises(ValueError, match="requires parameters"):
            agentlogs.run_query(db, "tool_failure_rate_by_tool")
    finally:
        db.close()


def test_indexer_lock_serializes(tmp_path):
    lock_path = tmp_path / "test.lock"
    enter_times: list[tuple[int, float]] = []
    exit_times: list[tuple[int, float]] = []

    def worker(idx: int):
        with indexer_lock(lock_path, timeout_s=10.0):
            enter_times.append((idx, time.monotonic()))
            time.sleep(0.2)
            exit_times.append((idx, time.monotonic()))

    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # The two critical sections must not overlap (serialized by flock).
    # Order: first exits before second enters (or vice versa).
    e1, e2 = sorted(enter_times, key=lambda t: t[1])
    x_first = next(t for t in exit_times if t[0] == e1[0])
    assert x_first[1] <= e2[1] + 0.05


def _lock_holder(lock_path_str: str, hold_s: float) -> None:
    """Subprocess helper: acquire indexer_lock and hold it for hold_s seconds.

    fcntl.flock is a process-level lock; threads in the same process share
    it. Testing timeout semantics requires a separate process.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from agentlogs.locks import indexer_lock as _lock

    with _lock(Path(lock_path_str), timeout_s=10.0):
        time.sleep(hold_s)


def test_indexer_lock_timeout_raises(tmp_path):
    lock_path = tmp_path / "hot.lock"
    ctx = multiprocessing.get_context("fork")
    holder = ctx.Process(target=_lock_holder, args=(str(lock_path), 1.0))
    holder.start()
    try:
        time.sleep(0.2)  # give subprocess time to acquire
        with pytest.raises(IndexerLockBusy):
            with indexer_lock(lock_path, timeout_s=0.3):
                pass
    finally:
        holder.join(timeout=5.0)
