"""sessions.session_role: adapter rules, migration 011 and the backfill (2026-09-27)."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest

import agentlogs
from agentlogs import session_roles
from agentlogs.adapters import codex, cursor
from agentlogs.migrations import _migration_files, _read_migration, _split_sql, apply_migrations


THREAD = {"subagent": {"thread_spawn": {"parent_thread_id": "p1", "depth": 1}}}


@pytest.mark.parametrize(
    ("source", "originator", "role"),
    [
        ("vscode", "Codex Desktop", "operator"),
        ("cli", None, "operator"),
        ("exec", "codex_exec", "dispatch"),
        ("exec", "Codex Desktop", "dispatch"),  # a desktop-launched exec run is still a program
        ("mcp", None, "dispatch"),
        (None, "codex_exec", "dispatch"),  # exec runs older than the source field
        (THREAD, "codex_exec", "subagent"),
        ({"subagent": {"other": "guardian"}}, "Codex Desktop", "subagent"),
        ({"subagent": "review"}, None, "subagent"),  # unit kind serializes as a string
        (None, None, None),
    ],
)
def test_codex_role_from_session_meta(source, originator, role) -> None:
    assert codex.session_role(source, originator) == role


def _cursor_transcript(root: Path, session_id: str) -> Path:
    path = root / ".cursor" / "projects" / "Users-x-Projects-p" / "agent-transcripts" / session_id / f"{session_id}.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"role": "user", "message": {"content": [{"type": "text", "text": "hi"}]}}) + "\n")
    return path


def test_cursor_role_is_dispatch_when_the_cli_store_exists(tmp_path: Path) -> None:
    ide = _cursor_transcript(tmp_path, "aaaa-ide")
    cli = _cursor_transcript(tmp_path, "bbbb-cli")
    (tmp_path / ".cursor" / "chats" / "0f3a" / "bbbb-cli").mkdir(parents=True)
    assert cursor.session_role(ide, "aaaa-ide") == "operator"
    assert cursor.session_role(cli, "bbbb-cli") == "dispatch"


def _v10_db(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(path), isolation_level=None)
    for version, filename in _migration_files():
        if version > 10:
            break
        for stmt in _split_sql(_read_migration(filename)):
            db.execute(stmt)
    assert db.execute("PRAGMA user_version").fetchone()[0] == 10
    return db


def test_migration_011_keeps_only_the_subagent_flags_that_were_right(tmp_path: Path) -> None:
    db = _v10_db(tmp_path / "v10.db")
    db.executemany(
        "INSERT INTO sessions (session_pk, vendor, client, vendor_session_id, is_subagent) VALUES (?,?,?,?,?)",
        [
            (1, "claude", "claude-code", "11111111-parent", 1),  # parent flipped by its subagent file
            (2, "claude", "claude-code", "agent-legacy", 1),  # legacy top-level subagent transcript
            (3, "codex", "codex-cli", "thread-1", 1),
            (4, "codex", "codex-cli", "exec-1", 0),
        ],
    )
    # the parent's subagent run lost its spawned_by edge (imported before the parent)
    db.executemany(
        "INSERT INTO runs (run_id, session_pk, vendor, client) VALUES (?, 1, 'claude', 'claude-code')",
        [("claude:11111111-parent",), ("claude:agent-child",)],
    )
    apply_migrations(db)
    assert db.execute(
        "SELECT src_run_id FROM run_edges WHERE dst_run_id = 'claude:agent-child' AND edge_type = 'spawned_by'"
    ).fetchall() == [("claude:11111111-parent",)]
    assert db.execute("PRAGMA user_version").fetchone()[0] == 11
    columns = {r[1] for r in db.execute("PRAGMA table_info(sessions)")}
    assert "is_subagent" not in columns and "session_role" in columns
    assert db.execute("SELECT name FROM sqlite_master WHERE name = 'v_session_role'").fetchone() is None
    roles = dict(db.execute("SELECT session_pk, session_role FROM sessions"))
    assert roles == {1: None, 2: "subagent", 3: "subagent", 4: None}
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE sessions SET session_role = 'human' WHERE session_pk = 4")


def test_backfill_uses_the_adapter_rules_and_leaves_missing_evidence_null(tmp_path: Path, monkeypatch) -> None:
    projects = tmp_path / "claude-projects"
    monkeypatch.setattr(session_roles, "PROJECTS_DIR", projects)
    proj = projects / "-Users-x-Projects-p"
    proj.mkdir(parents=True)
    tick = proj / "tick.jsonl"
    tick.write_text(json.dumps({"type": "user", "entrypoint": "sdk-cli"}) + "\n")
    typed = proj / "typed.jsonl"
    typed.write_text(json.dumps({"type": "user", "entrypoint": "sdk-cli"}) + "\n"
                     + json.dumps({"type": "user", "entrypoint": "cli"}) + "\n")
    cursor_cli = _cursor_transcript(tmp_path, "cccc-cli")
    (tmp_path / ".cursor" / "chats" / "77aa" / "cccc-cli").mkdir(parents=True)
    archive = tmp_path / "archive"
    (archive / "claude" / "-Users-x-Projects-p").mkdir(parents=True)
    (archive / "claude" / "-Users-x-Projects-p" / "archived.jsonl").write_text(
        json.dumps({"type": "user", "entrypoint": "cli"}) + "\n")

    db = agentlogs.connect(tmp_path / "roles.db")
    sessions = [
        (1, "claude", "tick", str(tick), None, None),
        (2, "claude", "typed", str(typed), None, None),
        (3, "claude", "gone", str(proj / "gone.jsonl"), None, None),
        (4, "claude", "archived", str(proj / "archived.jsonl"), None, None),
        (5, "codex", "x1", None, json.dumps({"session_source": "exec", "originator": "codex_exec"}), "exec"),
        (6, "codex", "x2", None, json.dumps({"originator": "Codex Desktop"}), "vscode"),
        (7, "cursor", "cccc-cli", str(cursor_cli), None, None),
    ]
    for pk, vendor, vsid, path, meta, transport in sessions:
        db.execute("INSERT INTO sessions (session_pk, vendor, client, vendor_session_id) VALUES (?,?,?,?)",
                   (pk, vendor, vendor, vsid))
        source_id = None
        if path:
            source_id = db.execute(
                "INSERT INTO sources (vendor, source_kind, path, sha256, discovered_at) "
                "VALUES (?, 'transcript_jsonl', ?, ?, '2026-09-27')",
                (vendor, path, f"sha{pk}"),
            ).lastrowid
        run_id = f"{vendor}:{vsid}" if vendor != "cursor" else f"cursor:proj:{vsid}"
        db.execute("INSERT INTO runs (run_id, session_pk, vendor, client, transport, primary_source_id) "
                   "VALUES (?,?,?,?,?,?)", (run_id, pk, vendor, vendor, transport, source_id))
        if meta:
            db.execute("INSERT INTO run_configs (run_id, metadata_json) VALUES (?, ?)", (run_id, meta))

    plan = session_roles.plan_roles(db)
    assert plan.undetermined[("claude", "transcript gone")] == 2
    session_roles.apply_roles(db, archive_root=archive)
    roles = dict(db.execute("SELECT session_pk, session_role FROM sessions"))
    assert roles == {1: "dispatch", 2: "operator", 3: None, 4: "operator",
                     5: "dispatch", 6: "operator", 7: "dispatch"}
    # idempotent: a second pass finds only the row with no evidence
    again = session_roles.apply_roles(db, archive_root=archive)
    assert sum(again.roles.values()) == 0 and sum(again.undetermined.values()) == 1
    db.close()
