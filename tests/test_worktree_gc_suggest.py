"""Read-only reclaim suggestions, using only disposable Git repositories."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import janitor_receipt
import worktree_gc


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def make_repo(path: Path, branch: str = "main") -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", branch)
    git(path, "config", "user.name", "test")
    git(path, "config", "user.email", "test@example.invalid")
    (path / "tracked.txt").write_text("base\n")
    (path / ".gitignore").write_text(".venv/\n.claude/cache/\n")
    git(path, "add", "tracked.txt", ".gitignore")
    git(path, "commit", "-qm", "base")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path / "repo")


@pytest.fixture(autouse=True)
def fenced_scans(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: {"/nowhere": [1]})
    monkeypatch.setattr(worktree_gc, "live_mapped_holders", lambda: {"/nowhere": [1]})
    monkeypatch.setattr(worktree_gc, "daemon_pids", lambda _pids: set())
    monkeypatch.setattr(worktree_gc, "pytest_temp_roots", list)
    monkeypatch.setattr(janitor_receipt, "RECEIPT_DIR", tmp_path / "receipts")


def tree(repo: Path, name: str, ref: str = "main", detached: bool = False) -> Path:
    wt = repo.parent / "trees" / name
    args = ["worktree", "add", "-q"]
    args += ["--detach"] if detached else ["-b", name]
    git(repo, *args, str(wt), ref)
    return wt


def commit(wt: Path, name: str, content: str, subject: str) -> str:
    (wt / name).write_text(content)
    git(wt, "add", name)
    git(wt, "commit", "-qm", subject)
    return git(wt, "rev-parse", "HEAD")


def age(wt: Path, hours: float = 72) -> None:
    stamp = time.time() - hours * 3600
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    paths = [wt, *wt.rglob("*"), admin / "HEAD", admin / "index", admin / "locked"]
    for path in paths:
        if path.exists():
            os.utime(path, (stamp, stamp), follow_symlinks=False)


def invoke(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *args: str
):
    monkeypatch.setattr(sys, "argv", ["worktree_gc.py", "suggest", "--json", *args])
    result = worktree_gc.main()
    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert set(payload) >= {"candidates", "not_candidates", "liveness_known"}
    assert isinstance(payload["candidates"], list)
    assert isinstance(payload["not_candidates"], list)
    return result, payload, output.err


def by_name(payload):
    return {
        Path(record["path"]).name: record
        for record in payload["candidates"] + payload["not_candidates"]
    }


def snapshot(root: Path):
    """Include ref/index/HEAD/lock contents, mtimes, modes and directory membership."""
    result = {}
    for path in [root, *root.rglob("*")]:
        metadata = path.lstat()
        content = (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        )
        result[str(path.relative_to(root))] = (
            metadata.st_mode,
            metadata.st_mtime_ns,
            content,
        )
    return result


def test_candidate_classes_sizes_counts_and_commands(repo, monkeypatch, capsys):
    safe = tree(repo, "safe")
    dup = tree(repo, "duplicate")
    commit(dup, "dup.txt", "already landed\n", "landed patch")
    # Force a distinct commit identity with the same patch.
    commit(repo, "other.txt", "main only\n", "main diverged")
    git(repo, "cherry-pick", git(dup, "rev-parse", "HEAD"))
    unmerged = tree(repo, "unmerged")
    commit(unmerged, "unique.txt", "unlanded\n", "unique work")
    stale = tree(repo, "stale-dirty")
    (stale / "tracked.txt").write_text("uncommitted\n")
    (stale / "notes").mkdir()
    (stale / "notes" / "one.txt").write_text("untracked\n")
    (stale / "notes" / "two.txt").write_text("also untracked\n")
    dirty = tree(repo, "skip-dirty", ref="unmerged")
    (dirty / "new.txt").write_text("more work\n")
    locked = tree(repo, "aged-lock")
    git(repo, "worktree", "lock", "--reason", "operator hold for review", str(locked))
    for wt in (safe, dup, unmerged, stale, dirty, locked):
        age(wt)
    (unmerged / ".venv").mkdir()
    (unmerged / ".venv" / "large").write_bytes(b"x" * 1024 * 1024)
    age(unmerged)

    result, payload, _ = invoke(
        monkeypatch, capsys, "--repo", str(repo), "--lock-max-age-hours", "48"
    )
    assert result == 0
    records = by_name(payload)
    expected = {
        "safe": "SAFE",
        "duplicate": "DUP",
        "unmerged": "unmerged",
        "stale-dirty": "stale-dirty",
        "skip-dirty": "skip-dirty",
        "aged-lock": "aged-lock",
    }
    assert {key: record["class"] for key, record in records.items()} == expected
    required = {
        "path",
        "class",
        "candidate",
        "size_bytes",
        "idle_hours",
        "commits_not_on_default",
        "patch_unique_commits",
        "no_same_subject_commits",
        "unmatched_commits",
        "dirty_count",
        "tracked_dirty_count",
        "untracked_count",
        "lock_reason",
        "lock_age_hours",
        "archive_command",
    }
    for record in records.values():
        assert record.keys() >= required
        assert record["candidate"] is True
        assert record["size_bytes"] > 0
        assert record["idle_hours"] >= 71
        assert shlex.split(record["archive_command"])[-3:] == [
            "archive",
            "--path",
            record["path"],
        ]
    assert [r["size_bytes"] for r in payload["candidates"]] == sorted(
        (r["size_bytes"] for r in payload["candidates"]), reverse=True
    )
    assert payload["candidates"][0]["path"] == str(unmerged)
    assert records["duplicate"]["commits_not_on_default"] == 1
    assert records["duplicate"]["patch_unique_commits"] == 0
    assert records["stale-dirty"]["dirty_count"] == 3
    assert records["stale-dirty"]["tracked_dirty_count"] == 1
    assert records["stale-dirty"]["untracked_count"] == 2
    assert records["aged-lock"]["lock_reason"] == "operator hold for review"
    assert records["aged-lock"]["lock_age_hours"] >= 71


@pytest.mark.parametrize("detached", [False, True])
def test_subject_hints_do_not_erase_patch_uniqueness(
    repo, monkeypatch, capsys, detached
):
    wt = tree(repo, "subject-lane", detached=detached)
    commit(wt, "lane.txt", "different patch\n", "shared subject")
    commit(wt, "novel.txt", "another patch\n", "novel subject")
    commit(repo, "main.txt", "main patch\n", "shared subject")
    age(wt)
    _, payload, _ = invoke(monkeypatch, capsys, "--repo", str(repo))
    row = by_name(payload)["subject-lane"]
    assert row["class"] == "unmerged"
    assert row["commits_not_on_default"] == 2
    assert row["patch_unique_commits"] == 2
    assert row["no_same_subject_commits"] == 1
    assert row["unmatched_commits"] == 1


@pytest.mark.parametrize("detached", [False, True])
def test_patch_equivalence_independent_of_subject(repo, monkeypatch, capsys, detached):
    wt = tree(repo, "patch-lane", detached=detached)
    sha = commit(wt, "equiv.txt", "same patch\n", "lane subject")
    commit(repo, "main.txt", "main divergence\n", "diverged")
    git(repo, "cherry-pick", sha)
    git(repo, "commit", "--amend", "-qm", "renamed upstream subject")
    age(wt)
    _, payload, _ = invoke(monkeypatch, capsys, "--repo", str(repo))
    row = by_name(payload)["patch-lane"]
    assert row["class"] == "DUP"
    assert row["commits_not_on_default"] == 1
    assert row["patch_unique_commits"] == 0
    assert row["no_same_subject_commits"] == 1
    assert row["unmatched_commits"] == 0


def test_live_process_and_live_pid_lock_are_excluded(repo, monkeypatch, capsys):
    cwd = tree(repo, "live-cwd")
    locked = tree(repo, "live-lock")
    git(repo, "worktree", "lock", "--reason", f"agent pid {os.getpid()}", str(locked))
    for wt in (cwd, locked):
        age(wt)
    monkeypatch.setattr(
        worktree_gc, "live_cwd_holders", lambda: {str(cwd / "nested"): [os.getpid()]}
    )
    _, payload, _ = invoke(
        monkeypatch, capsys, "--repo", str(repo), "--lock-max-age-hours", "1"
    )
    assert payload["candidates"] == []
    rows = by_name(payload)
    assert rows["live-cwd"]["candidate"] is False
    assert "live process inside" in rows["live-cwd"]["not_candidate_reasons"]
    assert rows["live-lock"]["class"] == "LOCKED"
    assert "live-pid lock" in rows["live-lock"]["not_candidate_reasons"]


def test_unknown_liveness_keeps_json_valid_and_excludes_every_tree(
    repo, monkeypatch, capsys
):
    wt = tree(repo, "unknown")
    age(wt)
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", dict)
    result, payload, diagnostic = invoke(monkeypatch, capsys, "--repo", str(repo))
    assert result == 2
    assert payload["liveness_known"] is False
    assert payload["candidates"] == []
    assert "liveness unknown" in payload["not_candidates"][0]["not_candidate_reasons"]
    assert "[DEGRADED]" in diagnostic


def test_suggest_never_mutates_even_with_apply_flags(
    repo, tmp_path, monkeypatch, capsys
):
    wt = tree(repo, "manual lane ; $(touch injected)", detached=True)
    commit(wt, "unlanded.txt", "unique\n", "not landed")
    (wt / "tracked.txt").write_text("dirty\n")
    (wt / "new.txt").write_text("untracked\n")
    (wt / ".venv").mkdir()
    (wt / ".venv" / "cache").write_text("derived\n")
    git(repo, "worktree", "lock", "--reason", "do not unlock automatically", str(wt))
    age(wt, hours=240)
    before = snapshot(tmp_path)

    def forbidden(*_args, **_kwargs):
        pytest.fail("suggest reached a mutation or mutation-planning path")

    monkeypatch.setattr(janitor_receipt, "write_receipt", forbidden)
    for name in (
        "_pin_ref",
        "remove_worktree",
        "archive_worktree",
        "explicit_archive",
        "release_stale_lock",
        "strip_idle_caches",
        "plan_idle_archive",
        "plan_cache_strip",
        "plan_pytest_prune",
        "find_stranded",
    ):
        monkeypatch.setattr(worktree_gc, name, forbidden)
    original_run = worktree_gc.run

    def read_only_run(command, *args, **kwargs):
        assert not (
            {"update-ref", "unlock", "remove", "prune", "branch", "reset", "clean"}
            & set(command)
        ), command
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(worktree_gc, "run", read_only_run)
    result, payload, _ = invoke(
        monkeypatch,
        capsys,
        "--repo",
        str(repo),
        "--force-all",
        "--force-stale",
        "--include-unmerged",
        "--prune-branches",
        "--archive-stale-days",
        "1",
        "--unmerged-idle-hours",
        "1",
        "--strip-idle-caches-min",
        "1",
        "--prune-pytest-hours",
        "1",
        "--lock-max-age-hours",
        "1",
    )
    assert result == 0
    assert snapshot(tmp_path) == before
    command = payload["candidates"][0]["archive_command"]
    assert shlex.split(command)[-3:] == ["archive", "--path", str(wt)]


def test_all_projects_scans_only_disposable_main_checkouts(
    tmp_path, monkeypatch, capsys
):
    projects = tmp_path / "Projects"
    first = make_repo(projects / "first")
    second = make_repo(projects / "second", branch="master")
    first_wt = tree(first, "first-lane")
    second_wt = tree(second, "second-lane", ref="master")
    for wt in (first_wt, second_wt):
        age(wt)
    # Linked checkout and non-repository folders must not double-count anything.
    git(first, "worktree", "add", "-q", "--detach", str(projects / "linked"), "main")
    (projects / "ordinary").mkdir()
    monkeypatch.setattr(worktree_gc, "PROJECTS_HOME", projects)
    _, payload, _ = invoke(monkeypatch, capsys, "--all-projects")
    rows = by_name(payload)
    assert set(rows) == {"first-lane", "second-lane", "linked"}
    assert rows["second-lane"]["default_branch"] == "master"
    assert rows["second-lane"]["commits_not_on_default"] == 0


def test_json_diagnostics_for_missing_tree_go_to_stderr(repo, monkeypatch, capsys):
    wt = tree(repo, "missing")
    git_dir = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    # A missing registration is a diagnostic, never a prefix corrupting hook JSON.
    import shutil

    shutil.rmtree(wt)
    before = git_dir.stat().st_mtime_ns
    result, payload, diagnostic = invoke(monkeypatch, capsys, "--repo", str(repo))
    assert result == 0
    assert payload["candidates"] == []
    assert payload["not_candidates"] == []
    assert "prunable" in diagnostic
    assert git_dir.stat().st_mtime_ns == before
