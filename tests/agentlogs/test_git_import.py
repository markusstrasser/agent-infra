"""Tests for agentlogs.git_import and the session-commit view join fix."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import agentlogs
from agentlogs.git_import import (
    _classify_commit,
    _extract_scope,
    _parse_git_log,
    import_git_commits,
)


def _init_repo(path: Path) -> None:
    """Initialize a throwaway git repo for testing."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)


def _commit(repo: Path, msg: str, filename: str = "a.txt", content: str = "x") -> str:
    (repo / filename).write_text(content)
    subprocess.run(["git", "-C", str(repo), "add", filename], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", msg], check=True,
    )
    h = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return h


def test_classify_commit_rules() -> None:
    assert _classify_commit("[api] Fix auth bug", ["src/api.py"]) == "fix"
    assert _classify_commit("[auth] Revert token flow", ["src/auth.py"]) == "revert"
    assert _classify_commit("[rules] Tighten hook", ["CLAUDE.md"]) == "rule"
    assert _classify_commit("[note] Initial research", ["research/x.md"]) == "research"
    assert _classify_commit("[api] Add endpoint", ["src/api.py"]) == "feature"


def test_extract_scope() -> None:
    assert _extract_scope("[infra] Add X") == "infra"
    assert _extract_scope("Plain subject") is None


def test_parse_git_log_end_to_end(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _init_repo(repo)
    _commit(repo, "[infra] Add a thing")
    _commit(repo, "[infra] Fix a thing", content="y")

    commits = _parse_git_log("r", repo, days=1)
    assert len(commits) == 2
    # Newest first
    assert commits[0]["subject"].startswith("[infra] Fix")
    assert commits[0]["commit_type"] == "fix"
    assert commits[0]["scope"] == "infra"
    assert commits[1]["commit_type"] == "feature"


def test_import_populates_git_tables_and_view(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "Projects"
    repo_root.mkdir()
    repo = repo_root / "testproj"
    repo.mkdir()
    _init_repo(repo)

    # Insert Session-ID trailer so v_session_commits can link
    sid = "11111111-2222-3333-4444-555555555555"
    (repo / "a.txt").write_text("x")
    subprocess.run(["git", "-C", str(repo), "add", "a.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q",
         "-m", f"[test] Wire it\n\nSession-ID: {sid}"],
        check=True,
    )

    # Point PROJECTS_ROOT at our fixture
    import agentlogs.git_import as gi
    monkeypatch.setattr(gi, "PROJECTS_ROOT", repo_root)

    db = agentlogs.connect(tmp_path / "e.db")
    # Seed a matching session so the view join can resolve
    db.execute(
        "INSERT INTO sessions (vendor, client, vendor_session_id, session_uuid, project_slug) "
        "VALUES ('claude', 'cc', ?, ?, 'testproj')", (sid, f"claude:{sid}"),
    )

    n = import_git_commits(db, projects=["testproj"], days=1)
    assert n == 1

    # Verify git_commits row
    row = db.execute("SELECT session_id, subject FROM git_commits").fetchone()
    assert row["session_id"] == sid
    assert "Wire it" in row["subject"]

    # v_session_commits should join through vendor_session_id
    view_rows = db.execute(
        "SELECT vendor_session_id, subject FROM v_session_commits"
    ).fetchall()
    assert len(view_rows) == 1
    assert view_rows[0]["vendor_session_id"] == sid
    db.close()


def test_v_session_commits_joins_synthetic_session_key(tmp_path: Path) -> None:
    """Migration 002 extended v_session_commits to join on synthetic_session_key too.

    Pre-fix: Gemini sessions (path-derived synthetic keys) never showed up in
    git attribution. Post-fix: either vendor_session_id OR synthetic_session_key
    matches.
    """
    db = agentlogs.connect(tmp_path / "syn.db")
    synth_key = "gemini-path-derived-42"
    db.execute(
        "INSERT INTO sessions (vendor, client, synthetic_session_key, session_uuid, "
        "project_slug) VALUES ('gemini', 'gemini-cli', ?, ?, 'p')",
        (synth_key, f"gemini:{synth_key}"),
    )
    db.execute(
        "INSERT INTO git_commits (hash, project, authored_at, subject, session_id) "
        "VALUES ('abc', 'p', '2026-04-20', 'Test', ?)", (synth_key,),
    )
    row = db.execute("SELECT subject FROM v_session_commits").fetchone()
    assert row is not None
    assert row["subject"] == "Test"
    db.close()


def test_subagent_count_populated(tmp_path: Path) -> None:
    """Migration 002 retention: subagent_count is refreshed from tool_calls."""
    from agentlogs.index import _refresh_session_denorm

    db = agentlogs.connect(tmp_path / "sub.db")
    db.execute(
        "INSERT INTO sessions (vendor, client, vendor_session_id, session_uuid) "
        "VALUES ('claude', 'cc', 's', 'claude:s')"
    )
    pk = db.execute("SELECT session_pk FROM sessions").fetchone()[0]
    db.execute(
        "INSERT INTO runs (run_id, session_pk, vendor, client, started_at) "
        "VALUES ('r1', ?, 'claude', 'cc', '2026-04-20T12:00:00Z')", (pk,),
    )
    # Two Agent tool calls + one Read — subagent_count should be 2
    db.execute(
        "INSERT INTO tool_calls (tool_call_id, run_id, tool_name) "
        "VALUES ('t1', 'r1', 'Agent'), ('t2', 'r1', 'Task'), ('t3', 'r1', 'Read')"
    )
    _refresh_session_denorm(db, [pk])
    row = db.execute(
        "SELECT subagent_count FROM sessions WHERE session_pk=?", (pk,)
    ).fetchone()
    assert row["subagent_count"] == 2
    db.close()
