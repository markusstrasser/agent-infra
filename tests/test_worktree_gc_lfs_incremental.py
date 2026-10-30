"""The incremental LFS-pointer check must answer exactly what a full `git grep` would."""

from __future__ import annotations

from pathlib import Path

import pytest
import worktree_gc
from test_worktree_gc_landed import git
from test_worktree_gc_landed import repo as repo_fixture

POINTER = "version https://git-lfs.github.com/spec/v1\noid sha256:" + "1" * 64 + "\nsize 1\n"


@pytest.fixture
def repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Path:
    worktree_gc._TREE_LFS.clear()
    return repo_fixture.__wrapped__(tmp_path, monkeypatch, request)


def branch_tree(repo: Path) -> Path:
    wt = repo.parent / "lfs-lane"
    git(repo, "worktree", "add", "-q", "-b", "lfs-lane", str(wt), "main")
    return wt


def head(wt: Path) -> str:
    return git(wt, "rev-parse", "HEAD")


def test_clean_tree_has_no_pointer(repo: Path) -> None:
    wt = branch_tree(repo)
    assert worktree_gc._lfs_pointer_in(wt, head(wt)) is False


@pytest.mark.parametrize("name", ["data.bin", "glob*[x].bin"])
def test_pointer_committed_only_on_the_branch(repo: Path, name: str) -> None:
    wt = branch_tree(repo)
    (wt / name).write_text(POINTER)
    git(wt, "add", "--", name)
    git(wt, "commit", "-qm", "pointer")
    assert worktree_gc._lfs_pointer_in(wt, head(wt)) is True


def test_pointer_staged_only(repo: Path) -> None:
    wt = branch_tree(repo)
    (wt / "staged.bin").write_text(POINTER)
    git(wt, "add", "staged.bin")
    assert worktree_gc._lfs_pointer_in(wt, head(wt)) is True


def test_pointer_already_on_main_is_still_found(repo: Path) -> None:
    (repo / "main.bin").write_text(POINTER)
    git(repo, "add", "main.bin")
    git(repo, "commit", "-qm", "pointer on main")
    wt = branch_tree(repo)
    assert worktree_gc._lfs_pointer_in(wt, head(wt)) is True
