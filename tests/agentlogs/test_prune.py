"""Prune paths: heavy (sessions over retention) vs light (no-op week).

The light path exists because a zero-delete weekly run otherwise pays the
full trigger-drop + FTS-rebuild + VACUUM transaction — measured >1h on a
10.5GB DB under launchd low-priority I/O (2026-07-14).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import agentlogs
from agentlogs import prune as pr


def _seed_session(db, pk: int, start_ts: str, n_events: int = 3) -> None:
    db.execute(
        "INSERT INTO sessions (session_pk, vendor, client, synthetic_session_key, start_ts) "
        "VALUES (?, 'claude', 'claude-code', ?, ?)",
        (pk, f"key-{pk}", start_ts))
    run_id = f"run-{pk}"
    db.execute(
        "INSERT INTO runs (run_id, session_pk, vendor, client, started_at) "
        "VALUES (?, ?, 'claude', 'claude-code', ?)",
        (run_id, pk, start_ts))
    for i in range(n_events):
        db.execute(
            "INSERT INTO events (event_id, run_id, seq, kind, text) "
            "VALUES (?, ?, ?, 'user_message', ?)",
            (f"ev-{pk}-{i}", run_id, i, f"text {pk} {i}"))
    db.commit()


def test_heavy_path_deletes_old_sessions(tmp_path):
    db = agentlogs.connect(tmp_path / "t.db")
    _seed_session(db, 1, "2020-01-01T00:00:00Z")
    _seed_session(db, 2, "2999-01-01T00:00:00Z")

    plan = pr.apply_prune(db, keep_days=30)

    assert plan.sessions == 1
    assert plan.runs == 1
    assert plan.events == 3
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 3
    # FTS stayed in sync (rebuild ran): surviving text still searchable.
    hit = db.execute(
        "SELECT COUNT(*) FROM events_fts WHERE events_fts MATCH '\"text 2 0\"'"
    ).fetchone()[0]
    assert hit == 1
    db.close()


def test_light_path_when_nothing_over_retention(tmp_path):
    db = agentlogs.connect(tmp_path / "t.db")
    _seed_session(db, 1, "2999-01-01T00:00:00Z")

    plan = pr.apply_prune(db, keep_days=30)

    assert (plan.sessions, plan.runs, plan.events) == (0, 0, 0)
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    # Light path must not touch the FTS triggers: an insert after prune
    # still auto-syncs into events_fts.
    db.execute(
        "INSERT INTO events (event_id, run_id, seq, kind, text) "
        "VALUES ('ev-post', 'run-1', 99, 'user_message', 'sentinel after light prune')")
    db.commit()
    hit = db.execute(
        "SELECT COUNT(*) FROM events_fts WHERE events_fts MATCH 'sentinel'"
    ).fetchone()[0]
    assert hit == 1
    db.close()


def test_light_path_still_cleans_orphaned_record_refs(tmp_path):
    db = agentlogs.connect(tmp_path / "t.db")
    _seed_session(db, 1, "2999-01-01T00:00:00Z")
    db.execute(
        "INSERT INTO sources (source_id, vendor, source_kind, path, sha256, discovered_at) "
        "VALUES (7, 'claude', 'jsonl', '/x.jsonl', 'abc', '2026-01-01')")
    db.execute(
        "INSERT INTO imports (import_id, source_id, source_sha256, parser_name, "
        "parser_version, schema_version, imported_at, success) "
        "VALUES (7, 7, 'abc', 'p', '1', 1, '2026-01-01', 1)")
    db.execute(
        "INSERT INTO record_refs (record_ref_id, source_id, import_id, raw_record_hash, "
        "raw_record_key, line_no) VALUES (1, 7, 7, 'h', 'k', 1)")
    db.commit()

    plan = pr.apply_prune(db, keep_days=30)

    assert plan.record_refs == 1
    assert db.execute("SELECT COUNT(*) FROM record_refs").fetchone()[0] == 0
    db.close()
