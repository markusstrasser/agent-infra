"""Positive + negative controls for stranded-worktree discovery.

`git worktree list` structurally cannot see a tree whose admin dir was deleted, so the
scan that finds them is the only thing standing between an aborted removal and bytes
nobody ever reclaims. A scanner nobody positive-controls is a scanner that silently
finds nothing — which is indistinguishable from a clean box.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from worktree_gc import _repo_from_admin, find_stranded  # noqa: E402


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git("init", "-q", "-b", "main", cwd=r)
    _git("config", "user.email", "t@t.t", cwd=r)
    _git("config", "user.name", "t", cwd=r)
    (r / "f.txt").write_text("one\n")
    _git("add", "f.txt", cwd=r)
    _git("commit", "-qm", "init", cwd=r)
    return r


def _strand(repo: Path, wt: Path) -> None:
    """Reproduce the real failure: unregister, leave the files."""
    _git("worktree", "add", "-q", "--detach", str(wt), cwd=repo)
    admin = repo / ".git" / "worktrees" / wt.name
    assert admin.is_dir(), "precondition: worktree registered"
    shutil.rmtree(admin)


def test_finds_a_stranded_tree_and_names_its_repo(repo: Path, tmp_path: Path) -> None:
    root = tmp_path / "tmproot"
    root.mkdir()
    wt = root / "lane-a"
    _strand(repo, wt)

    # Precondition: this is exactly the blind spot — git cannot see it.
    listed = subprocess.run(
        ["git", "worktree", "list"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout
    assert "lane-a" not in listed

    rows = find_stranded({}, roots=(root,), with_size=False)
    assert [r.path for r in rows] == [wt]
    assert rows[0].repo_root == repo
    assert rows[0].reclaimable, "clean stranded tree must be reclaimable"


def test_deletions_from_the_aborted_removal_do_not_count_as_work(
    repo: Path, tmp_path: Path
) -> None:
    """A half-removed tree is missing files; that is damage, not work to preserve."""
    root = tmp_path / "tmproot"
    root.mkdir()
    wt = root / "lane-half"
    _strand(repo, wt)
    (wt / "f.txt").unlink()  # the removal got this far before aborting

    rows = find_stranded({}, roots=(root,), with_size=False)
    assert rows[0].tracked_dirty == 0
    assert rows[0].reclaimable


def test_real_modification_blocks_reclaim(repo: Path, tmp_path: Path) -> None:
    root = tmp_path / "tmproot"
    root.mkdir()
    wt = root / "lane-dirty"
    _strand(repo, wt)
    (wt / "f.txt").write_text("edited in the worktree\n")

    rows = find_stranded({}, roots=(root,), with_size=False)
    assert rows[0].tracked_dirty == 1
    assert not rows[0].reclaimable


def test_live_holder_blocks_reclaim(repo: Path, tmp_path: Path) -> None:
    root = tmp_path / "tmproot"
    root.mkdir()
    wt = root / "lane-held"
    _strand(repo, wt)

    rows = find_stranded({str(wt): [4242]}, roots=(root,), with_size=False)
    assert rows[0].held == [4242]
    assert not rows[0].reclaimable


def test_a_standalone_clone_is_not_a_stranded_worktree(repo: Path, tmp_path: Path) -> None:
    """NEGATIVE CONTROL — `.git` as a DIRECTORY is a clone. Six of these were
    misread as stranded worktrees in the 2026-07-25 first pass."""
    root = tmp_path / "tmproot"
    root.mkdir()
    clone = root / "upstream-tool"
    subprocess.run(
        ["git", "clone", "-q", str(repo), str(clone)], check=True, capture_output=True
    )
    assert (clone / ".git").is_dir()

    assert find_stranded({}, roots=(root,), with_size=False) == []


def test_a_registered_worktree_is_not_reported(repo: Path, tmp_path: Path) -> None:
    """NEGATIVE CONTROL — a healthy worktree belongs to the normal audit, not here."""
    root = tmp_path / "tmproot"
    root.mkdir()
    wt = root / "lane-ok"
    _git("worktree", "add", "-q", "--detach", str(wt), cwd=repo)

    assert find_stranded({}, roots=(root,), with_size=False) == []


def test_unreadable_neighbour_does_not_abort_the_scan(repo: Path, tmp_path: Path) -> None:
    """/private/tmp holds other uids' sandboxes; one EACCES must not blind the scan."""
    root = tmp_path / "tmproot"
    root.mkdir()
    wt = root / "lane-a"
    _strand(repo, wt)
    blocked = root / "aaa-unreadable"  # sorts BEFORE lane-a, so it is hit first
    blocked.mkdir()
    (blocked / ".git").write_text("gitdir: /nonexistent\n")
    blocked.chmod(0o000)
    try:
        rows = find_stranded({}, roots=(root,), with_size=False)
        assert [r.path for r in rows] == [wt]
    finally:
        blocked.chmod(0o755)


def test_finds_a_stranded_tree_nested_one_level(repo: Path, tmp_path: Path) -> None:
    """cursor-agent -w nests: ~/.cursor/worktrees/<repo>/<name>. A flat scan misses it."""
    root = tmp_path / "cursor-worktrees"
    (root / "genomics").mkdir(parents=True)
    wt = root / "genomics" / "lane-a"
    _strand(repo, wt)

    rows = find_stranded({}, roots=(root,), with_size=False)
    assert [r.path for r in rows] == [wt]


def test_scan_does_not_descend_into_a_worktree(repo: Path, tmp_path: Path) -> None:
    """A checkout can contain thousands of dirs; walking into one is pure waste."""
    root = tmp_path / "tmproot"
    root.mkdir()
    outer = root / "lane-outer"
    _strand(repo, outer)
    nested = outer / "nested-decoy"
    nested.mkdir()
    (nested / ".git").write_text("gitdir: /nonexistent/admin\n")

    rows = find_stranded({}, roots=(root,), with_size=False)
    assert [r.path for r in rows] == [outer], "must stop at the first .git marker"


def test_repo_from_admin_survives_a_dead_admin_dir() -> None:
    assert _repo_from_admin("/x/y/repo/.git/worktrees/gone") is None  # repo doesn't exist
    assert _repo_from_admin("/no/git/segment/here") is None
