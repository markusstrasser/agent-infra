"""Metadata admission and explicit-only removal of Codex app worktrees."""

from __future__ import annotations

import json
import os
import sys
import tarfile
from pathlib import Path

import pytest
import worktree_gc
from test_worktree_gc_landed import age, git, lane, row, run, snapshot
from test_worktree_gc_landed import repo as repo_fixture

OWNER = "019f45fe-c02b-7192-9d42-0bec7ac7744f"
CONFIG = f"[agent]\n\tsession-id = {OWNER}\n".encode()
THREAD = json.dumps({"version": 1, "ownerThreadId": OWNER}).encode()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return repo_fixture.__wrapped__(tmp_path, monkeypatch)


def metadata(wt: Path, name: str, raw: bytes) -> Path:
    path = Path(git(wt, "rev-parse", "--absolute-git-dir")) / name
    path.write_bytes(raw)
    return path


@pytest.mark.parametrize(
    "name,raw", [("config.worktree", CONFIG), ("codex-thread.json", THREAD)]
)
def test_metadata_admitted_and_raw_bytes_archived(
    repo: Path, monkeypatch: pytest.MonkeyPatch, name: str, raw: bytes
) -> None:
    wt = lane(repo)
    metadata(wt, name, raw)
    age(wt)
    candidate = row(repo, wt)
    assert candidate.classify() == "landed", candidate.hold_reason
    if name == "codex-thread.json":
        assert candidate.codex_owner_thread == OWNER
    monkeypatch.setattr(sys, "argv", ["worktree_gc.py", "archive", "--path", str(wt)])
    assert worktree_gc.main() == 0
    assert not wt.exists()
    dest = next(worktree_gc.ARCHIVE_ROOT.glob("**/head.txt")).parent
    with tarfile.open(dest / "git-state.tgz") as archive:
        assert archive.extractfile(f".git/{name}").read() == raw


@pytest.mark.parametrize(
    "section,key,value,offending",
    [
        ("core", "sparseCheckout", "true", "core.sparsecheckout"),
        ("extensions", "worktreeConfig", "true", "extensions.worktreeconfig"),
        ("include", "path", "outside.config", "include.path"),
    ],
)
def test_extra_config_key_holds_and_names_key(
    repo: Path, section: str, key: str, value: str, offending: str
) -> None:
    wt = lane(repo)
    metadata(wt, "config.worktree", CONFIG + f"[{section}]\n{key} = {value}\n".encode())
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert offending in candidate.hold_reason
    assert not worktree_gc.archive_worktree(candidate).ok


def test_config_file_does_not_follow_includes(repo: Path) -> None:
    wt = lane(repo)
    included = repo.parent / "outside.config"
    included.write_text("[outside]\nunique-key = sentinel\n")
    path = metadata(
        wt, "config.worktree", CONFIG + f"[include]\npath = {included}\n".encode()
    )
    result = worktree_gc.run(
        ["git", "config", "--file", str(path), "--null", "--list"], cwd=wt
    )
    assert result.returncode == 0
    assert "include.path\n" in result.stdout
    assert "outside.unique-key" not in result.stdout
    assert "include.path" in row(repo, wt).hold_reason


def test_unparsable_config_holds(repo: Path) -> None:
    wt = lane(repo)
    metadata(wt, "config.worktree", b"[broken\n")
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert "config.worktree" in candidate.hold_reason


@pytest.mark.parametrize(
    "raw",
    [
        b"{",
        b"[]",
        b"null",
        b' {"version": 1} ',
        json.dumps({"version": 1, "ownerThreadId": OWNER, "extra": 1}).encode(),
        json.dumps({"version": 2, "ownerThreadId": OWNER}).encode(),
        json.dumps({"version": True, "ownerThreadId": OWNER}).encode(),
        json.dumps({"version": 1.0, "ownerThreadId": OWNER}).encode(),
        b'{"version": 1, "ownerThreadId": "not-a-uuid"}',
        b'{"version": 1, "ownerThreadId": 123}',
        f'{{"version": 2, "version": 1, "ownerThreadId": "{OWNER}"}}'.encode(),
    ],
)
def test_invalid_codex_metadata_holds(repo: Path, raw: bytes) -> None:
    wt = lane(repo)
    metadata(wt, "codex-thread.json", raw)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert "codex-thread.json" in candidate.hold_reason
    assert not worktree_gc.archive_worktree(candidate).ok


@pytest.mark.parametrize("name", ["config.worktree", "codex-thread.json"])
@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_metadata_requires_regular_file(repo: Path, name: str, kind: str) -> None:
    wt = lane(repo)
    path = Path(git(wt, "rev-parse", "--absolute-git-dir")) / name
    if kind == "symlink":
        target = repo.parent / "outside"
        target.write_bytes(CONFIG if name == "config.worktree" else THREAD)
        path.symlink_to(target)
    elif kind == "directory":
        path.mkdir()
    else:
        os.mkfifo(path)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert name in candidate.hold_reason


@pytest.mark.parametrize("clean", [False, True])
def test_app_owned_suggested_but_all_automatic_routes_skip(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    clean: bool,
) -> None:
    wt = lane(repo)
    if clean:
        git(wt, "reset", "--hard", "main")
        (wt / ".claude/cache/result.md").unlink()
        (wt / ".claude/cache").rmdir()
        (wt / ".claude").rmdir()
    metadata(wt, "codex-thread.json", THREAD)
    age(wt)
    before = snapshot(repo, wt)
    assert run(monkeypatch, repo, "suggest", "--json") == 0
    result = json.loads(capsys.readouterr().out)
    record = next(r for r in result["candidates"] if r["path"] == str(wt))
    assert record["class"] == ("SAFE" if clean else "landed")
    assert record["codex_owner_thread"] == OWNER
    assert snapshot(repo, wt) == before
    assert run(monkeypatch, repo, "suggest") == 0
    assert OWNER in capsys.readouterr().out
    candidate = row(repo, wt)
    assert not worktree_gc.should_remove(candidate, True, True, True, set())
    assert worktree_gc.plan_landed_archive([candidate], 24, set(), []) == []
    assert worktree_gc.plan_idle_unmerged([candidate], 24, set(), []) == []
    assert worktree_gc.removal_hold(candidate) == "codex-app-owned"
    with pytest.raises(RuntimeError, match="codex-app-owned"):
        worktree_gc.remove_worktree(repo, wt)
    assert (
        run(
            monkeypatch,
            repo,
            "apply",
            "--archive-landed-idle-hours",
            "24",
            "--unmerged-idle-hours",
            "24",
            "--force-all",
        )
        == 0
    )
    assert "codex-app-owned" in capsys.readouterr().out
    assert snapshot(repo, wt) == before


def test_app_ownership_added_after_plan_prevents_quarantine(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    archived = worktree_gc.archive_worktree(candidate)
    assert archived.ok
    metadata(wt, "codex-thread.json", THREAD)
    assert not worktree_gc.remove_landed_from_quarantine(candidate, 24, archived.dir)
    assert wt.exists()
    assert not list(wt.parent.glob("gc-quarantine-*"))


def test_app_owned_caches_kept_by_cron(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    cache = wt / ".venv"
    cache.mkdir()
    (cache / "payload").write_text("derived cache\n")
    metadata(wt, "codex-thread.json", THREAD)
    age(wt)
    assert run(monkeypatch, repo, "prune", "--strip-idle-caches-min", "1") == 0
    assert cache.exists()
    assert worktree_gc.strip_idle_caches(wt) == {}
