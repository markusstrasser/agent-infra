"""Archive-then-reap and idle-cache stripping for worktree_gc.

Real temp repos + `git worktree add`; idleness is set with os.utime so the idle clock
(dirty-path and git-dir index/HEAD mtimes, never commit age) is exercised for real.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import worktree_gc
from worktree_gc import (
    WorktreeRow,
    archive_worktree,
    audit_repo,
    plan_cache_strip,
    plan_idle_archive,
    remove_worktree,
    should_remove,
    strip_idle_caches,
)

DAY = 86400.0
NO_MAPPED = {"/nowhere": [1]}


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git("init", "-q", "-b", "main", cwd=r)
    _git("config", "user.email", "t@t.t", cwd=r)
    _git("config", "user.name", "t", cwd=r)
    (r / ".gitignore").write_text(".venv/\n")
    (r / "f.txt").write_text("one\ntwo\n")
    (r / "bin.dat").write_bytes(bytes(range(256)))
    _git("add", ".", cwd=r)
    _git("commit", "-qm", "init", cwd=r)
    return r


@pytest.fixture(autouse=True)
def _no_real_temp_roots_or_lsof(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fence: no test may prune the real pytest-of-<user> or read the real txt-mapping scan."""
    monkeypatch.setattr(worktree_gc, "pytest_temp_roots", list)
    monkeypatch.setattr(worktree_gc, "live_mapped_holders", lambda: {"/nowhere": [1]})


def _age_tree(wt: Path, days: float) -> None:
    stamp = time.time() - days * DAY
    gd = Path(_git("rev-parse", "--absolute-git-dir", cwd=wt).strip())
    targets = [p for p in wt.rglob("*") if ".git" not in p.parts]
    targets += [wt, gd / "index", gd / "HEAD"]
    for p in targets:
        if p.is_symlink() or p.exists():
            os.utime(p, (stamp, stamp), follow_symlinks=False)


def _dirty_tree(repo: Path, name: str, days: float) -> Path:
    wt = repo.parent / "wts" / name
    _git("worktree", "add", "-q", "--detach", str(wt), "main", cwd=repo)
    (wt / "f.txt").write_text("one\nTWO edited\n")
    (wt / "bin.dat").write_bytes(bytes(reversed(range(256))))
    (wt / "notes").mkdir()
    (wt / "notes" / "new file.md").write_text("untracked work\n")
    (wt / ".venv").mkdir()
    (wt / ".venv" / "big").write_text("x")
    _age_tree(wt, days)
    return wt


def _row(repo: Path, wt: Path) -> WorktreeRow:
    rows = [r for r in audit_repo(repo, with_size=False) if r.path == wt]
    assert rows, "worktree not audited"
    return rows[0]


def _run_archive(row: WorktreeRow, root: Path) -> worktree_gc.ArchiveResult:
    res = archive_worktree(row, root=root)
    if res.ok:
        remove_worktree(row.repo_root, row.path)
    return res


def test_idle_stale_dirty_is_archived_removed_pinned_and_restorable(
    repo: Path, tmp_path: Path
) -> None:
    wt = _dirty_tree(repo, "lane-idle", days=8)
    row = _row(repo, wt)
    assert row.classify() == "stale-dirty"
    assert plan_idle_archive([row], 7, set(), exclude=[]) == [row]
    # After planning: `git diff` refreshes the index, which (correctly) resets idle.
    want_diff = _git("diff", "--no-ext-diff", "--binary", "HEAD", cwd=wt)
    want_untracked = (wt / "notes" / "new file.md").read_bytes()
    res = _run_archive(row, tmp_path / "arch")
    assert res.ok, res.reason
    assert not wt.exists()
    head = (res.dir / "head.txt").read_text().strip()
    assert _git("rev-parse", res.ref, cwd=repo).strip() == head
    assert res.ref.startswith("refs/wt-archive/lane-idle-")
    listed = (res.dir / "untracked.list").read_text().splitlines()
    assert listed == ["notes/new file.md"], "caches must be excluded"

    # Restore exactly per RESTORE.md into a fresh worktree.
    restore = repo.parent / "restored"
    _git("worktree", "add", "-q", "--detach", str(restore), head, cwd=repo)
    _git("apply", str(res.dir / "tracked.patch"), cwd=restore)
    subprocess.run(["tar", "-xzf", str(res.dir / "untracked.tgz"), "-C", str(restore)], check=True)
    assert _git("diff", "--no-ext-diff", "--binary", "HEAD", cwd=restore) == want_diff
    assert (restore / "notes" / "new file.md").read_bytes() == want_untracked
    assert "tracked.patch" in (res.dir / "RESTORE.md").read_text()


def test_ref_collision_gets_suffix(repo: Path, tmp_path: Path) -> None:
    wt = _dirty_tree(repo, "lane-coll", days=8)
    day = time.strftime("%Y%m%d")
    first = _git("rev-parse", "HEAD", cwd=repo).strip()
    (repo / "g.txt").write_text("g\n")
    _git("add", "g.txt", cwd=repo)
    _git("commit", "-qm", "g", cwd=repo)
    other = _git("rev-parse", "HEAD", cwd=repo).strip()
    assert other != first
    _git("update-ref", f"refs/wt-archive/lane-coll-{day}", other, cwd=repo)
    res = archive_worktree(_row(repo, wt), root=tmp_path / "arch")
    assert res.ok and res.ref == f"refs/wt-archive/lane-coll-{day}-2"


def test_recently_touched_tree_is_untouched(repo: Path) -> None:
    wt = _dirty_tree(repo, "lane-fresh", days=1)
    row = _row(repo, wt)
    assert plan_idle_archive([row], 7, set(), exclude=[]) == []
    assert wt.exists()


def test_held_tree_is_never_planned(repo: Path) -> None:
    wt = _dirty_tree(repo, "lane-held", days=30)
    row = _row(repo, wt)
    row.held = 1  # what main() sets from the lsof cwd scan
    assert plan_idle_archive([row], 7, set(), exclude=[]) == []
    assert plan_cache_strip([row], 1, set(), exclude=[], mapped=NO_MAPPED) == []
    row.held, row.daemon_held = 0, 1
    assert plan_idle_archive([row], 7, set(), exclude=[]) == []
    assert plan_cache_strip([row], 1, set(), exclude=[], mapped=NO_MAPPED) == []


def test_failed_self_check_holds_and_keeps_tree(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = _dirty_tree(repo, "lane-bad", days=8)
    monkeypatch.setattr(
        worktree_gc, "_write_patch", lambda _wt, dest: dest.write_bytes(b"garbage\n")
    )
    res = _run_archive(_row(repo, wt), tmp_path / "arch")
    assert not res.ok and "patch" in res.reason
    assert wt.exists() and (wt / "f.txt").read_text() == "one\nTWO edited\n"
    assert not _git("for-each-ref", "refs/wt-archive", cwd=repo).strip()


def test_hold_line_printed_on_failed_self_check(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    wt = _dirty_tree(repo, "lane-bad2", days=8)
    monkeypatch.setattr(
        worktree_gc, "_write_patch", lambda _wt, dest: dest.write_bytes(b"garbage\n")
    )
    monkeypatch.setattr(worktree_gc, "ARCHIVE_ROOT", tmp_path / "arch")
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: {"/nowhere": [1]})
    monkeypatch.setattr(worktree_gc, "find_stranded", lambda *a, **k: [])
    monkeypatch.setattr(
        sys,
        "argv",
        ["worktree_gc.py", "apply", "--repo", str(repo), "--archive-stale-days", "7"],
    )
    monkeypatch.setitem(sys.modules, "janitor_receipt", None)  # no real receipt
    assert worktree_gc.main() == 0
    out = capsys.readouterr().out
    assert f"HOLD {wt}: archive self-check failed (" in out
    assert wt.exists()


def test_strip_idle_venv_keeps_symlinked_cache_and_tree(repo: Path, tmp_path: Path) -> None:
    wt = repo.parent / "wts" / "lane-unmerged"
    _git("worktree", "add", "-q", "-b", "feat", str(wt), "main", cwd=repo)
    (wt / "h.txt").write_text("h\n")
    _git("add", "h.txt", cwd=wt)
    _git("commit", "-qm", "feat", cwd=wt)
    (wt / ".venv" / "lib").mkdir(parents=True)
    (wt / ".venv" / "lib" / "x.py").write_text("x")
    shared = tmp_path / "shared-uv-cache"
    shared.mkdir()
    (shared / "wheel").write_text("w")
    (wt / ".uv-cache").symlink_to(shared)
    (repo / ".gitignore").write_text(".venv/\n.uv-cache\n")  # untracked noise off
    _age_tree(wt, 3)
    row = _row(repo, wt)
    assert row.classify() in ("unmerged", "skip-dirty")

    assert plan_idle_archive([row], None, set(), exclude=[]) == []
    assert plan_cache_strip([row], 60, set(), exclude=[], mapped=NO_MAPPED) == [(row, [wt / ".venv"])]
    sizes = strip_idle_caches(wt)
    assert set(sizes) == {".venv"}
    assert not (wt / ".venv").exists()
    assert (wt / ".uv-cache").is_symlink() and (shared / "wheel").read_text() == "w"
    assert wt.exists() and (wt / "h.txt").exists()


def test_no_flags_plans_nothing_and_removal_policy_unchanged(repo: Path) -> None:
    wt = _dirty_tree(repo, "lane-noflag", days=30)
    row = _row(repo, wt)
    assert plan_idle_archive([row], None, set(), exclude=[]) == []
    assert plan_cache_strip([row], None, set(), exclude=[], mapped=NO_MAPPED) == []
    assert not should_remove(row, False, False, False, set())
    assert should_remove(row, False, True, False, set())  # --force-stale as before


def test_trees_sharing_a_leaf_name_never_share_an_archive(repo: Path, tmp_path: Path) -> None:
    # Codex lanes all end in `<lane>/<repo>`: keyed by the leaf alone, the second archive of a
    # day overwrote the first after the first tree was already gone.
    first = _dirty_tree(repo, f"lane-a/{repo.name}", days=8)
    second = _dirty_tree(repo, f"lane-b/{repo.name}", days=8)
    (second / "f.txt").write_text("second lane edit\n")
    root = tmp_path / "archives"
    one = _run_archive(_row(repo, first), root)
    two = _run_archive(_row(repo, second), root)
    assert one.ok and two.ok
    assert (one.dir.name, two.dir.name) == (f"lane-a--{repo.name}", f"lane-b--{repo.name}")
    assert b"TWO edited" in (one.dir / "tracked.patch").read_bytes()
    assert b"second lane edit" in (two.dir / "tracked.patch").read_bytes()
    # Same name on the same day (a tree re-created and archived again) gets a suffix.
    assert worktree_gc._fresh_dir(tmp_path / "x" / "lane") == tmp_path / "x" / "lane"
    assert worktree_gc._fresh_dir(tmp_path / "x" / "lane") == tmp_path / "x" / "lane-2"


def test_editing_inside_an_untracked_dir_counts_as_activity(repo: Path) -> None:
    wt = _dirty_tree(repo, "lane-busy", days=8)
    assert worktree_gc.idle_age_days(wt) >= 7.9
    (wt / "notes" / "new file.md").write_text("edited just now\n")  # dir mtime unchanged
    assert worktree_gc.idle_age_days(wt) < 0.01
