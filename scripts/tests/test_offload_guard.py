"""Fixture tests for offload_guard — DATA_LOSS class prevention."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from offload_guard import (
    files_content_equal,
    refuse_whole_dir_offload,
    safe_to_delete_ssd_copy,
    tracked_under,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "t"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    # mixed tree: tracked prereg + untracked out/
    exp = repo / "experiments" / "mealy"
    exp.mkdir(parents=True)
    (exp / "PREREG.md").write_text("tracked\n")
    out = exp / "out"
    out.mkdir()
    (out / "raw.bin").write_bytes(b"x" * 100)
    (out / "curated.json").write_text('{"ok":1}\n')
    subprocess.run(["git", "add", "experiments/mealy/PREREG.md"], cwd=repo, check=True, capture_output=True)
    # only curated tracked under out/ — mirrors real mixed dir
    subprocess.run(
        ["git", "add", "experiments/mealy/out/curated.json"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def test_refuse_when_tracked_present(git_repo: Path):
    ok, reason = refuse_whole_dir_offload(git_repo, git_repo / "experiments" / "mealy")
    assert ok is False
    assert "REFUSE" in reason
    assert "git-tracked" in reason
    tracked = tracked_under(git_repo, git_repo / "experiments" / "mealy")
    assert any("PREREG.md" in t for t in tracked)
    assert any("curated.json" in t for t in tracked)


def test_allow_untracked_only_dir(git_repo: Path):
    pure = git_repo / "scratch_artifacts"
    pure.mkdir()
    (pure / "blob.bin").write_bytes(b"abc")
    ok, reason = refuse_whole_dir_offload(git_repo, pure)
    assert ok is True
    assert "OK" in reason


def test_dir_level_delete_refused(tmp_path: Path):
    local = tmp_path / "local" / "out"
    ssd = tmp_path / "ssd" / "out"
    local.mkdir(parents=True)
    ssd.mkdir(parents=True)
    (local / "a").write_text("partial")
    (ssd / "a").write_text("partial")
    (ssd / "raw_only_on_ssd").write_bytes(b"lost_if_rmrf")
    ok, reason = safe_to_delete_ssd_copy(local, ssd)
    assert ok is False
    assert "dir-level" in reason.lower() or "REFUSE" in reason


def test_per_file_equal_allows_delete(tmp_path: Path):
    local = tmp_path / "local.aif"
    ssd = tmp_path / "ssd.aif"
    content = b"same-bytes-content"
    local.write_bytes(content)
    ssd.write_bytes(content)
    assert files_content_equal(local, ssd)
    ok, reason = safe_to_delete_ssd_copy(local, ssd)
    assert ok is True
    assert "OK" in reason


def test_per_file_differ_refuses(tmp_path: Path):
    local = tmp_path / "local.aif"
    ssd = tmp_path / "ssd.aif"
    local.write_bytes(b"aaa")
    ssd.write_bytes(b"bbb")
    ok, reason = safe_to_delete_ssd_copy(local, ssd)
    assert ok is False
    assert "REFUSE" in reason
