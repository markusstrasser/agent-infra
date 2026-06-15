"""Tests for agentlogs.provenance — the code↔conversation link (who / whence).

Covers: file-spec parsing, who happy-path (line → session/model via the git fallback,
the common case since git_commits is a rolling cache), honest degradation (no trailer),
and whence reconstructing commits LIVE from git (not the maybe-stale import table).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import agentlogs
from agentlogs import provenance as pv


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)


def _commit(repo: Path, msg: str, filename: str, content: str) -> str:
    (repo / filename).write_text(content)
    subprocess.run(["git", "-C", str(repo), "add", filename], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", msg], check=True)
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def test_parse_file_spec() -> None:
    assert pv.parse_file_spec("a/b.py:10-20") == ("a/b.py", 10, 20)
    assert pv.parse_file_spec("a/b.py:10") == ("a/b.py", 10, 10)
    assert pv.parse_file_spec("a/b.py") == ("a/b.py", None, None)


def test_who_resolves_line_to_session_and_model(tmp_path: Path) -> None:
    repo = tmp_path / "proj"
    repo.mkdir()
    _init_repo(repo)
    sid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    _commit(repo, f"[x] write it\n\nSession-ID: {sid}", "f.py", "line1\nline2\n")

    db = agentlogs.connect(tmp_path / "w.db")
    db.execute(
        "INSERT INTO sessions (vendor, client, vendor_session_id, session_uuid, model) "
        "VALUES ('claude', 'cc', ?, ?, 'claude-opus-4-8')", (sid, f"claude:{sid}"),
    )
    rel, hunks = pv.who(db, f"{repo / 'f.py'}:1")
    assert rel == "f.py"
    assert len(hunks) == 1
    assert hunks[0].session_id == sid
    assert hunks[0].model == "claude-opus-4-8"
    assert hunks[0].note is None
    db.close()


def test_who_honest_degrade_no_trailer(tmp_path: Path) -> None:
    repo = tmp_path / "proj"
    repo.mkdir()
    _init_repo(repo)
    _commit(repo, "[x] no trailer here", "f.py", "only\n")

    db = agentlogs.connect(tmp_path / "w.db")
    _, hunks = pv.who(db, f"{repo / 'f.py'}:1")
    assert hunks[0].session_id is None
    assert hunks[0].note == "no-trailer"
    assert hunks[0].model is None
    db.close()


def test_whence_reconstructs_from_git_not_stale_table(tmp_path: Path, monkeypatch) -> None:
    """whence must read git live — a session whose commits never reached the
    git_commits cache must still be found."""
    projects = tmp_path / "Projects"
    projects.mkdir()
    repo = projects / "proj"
    repo.mkdir()
    _init_repo(repo)
    sid = "12121212-3434-5656-7878-909090909090"
    _commit(repo, f"[a] first\n\nSession-ID: {sid}", "a.py", "a\n")
    _commit(repo, f"[b] second\n\nSession-ID: {sid}", "b.py", "b\n")
    _commit(repo, "[c] other session, no trailer", "c.py", "c\n")

    monkeypatch.setattr(pv, "PROJECTS_ROOT", projects)
    db = agentlogs.connect(tmp_path / "wh.db")
    db.execute(
        "INSERT INTO sessions (vendor, client, vendor_session_id, session_uuid, "
        "model, project_slug) VALUES ('claude','cc',?,?,'claude-opus-4-8','proj')",
        (sid, f"claude:{sid}"),
    )
    # git_commits intentionally left EMPTY — proves we don't depend on the cache.
    sess, rows = pv.whence(db, sid)
    assert sess is not None
    assert sess["model"] == "claude-opus-4-8"
    assert len(rows) == 2                      # the two trailer'd commits, not the third
    subjects = {r["subject"] for r in rows}
    assert subjects == {"[a] first", "[b] second"}
    db.close()
