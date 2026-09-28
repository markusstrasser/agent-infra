"""Derived-cache stripping and pytest basetemp pruning for worktree_gc (the disk guard).

Real temp repos + `git worktree add`, the same fixture shape as the other worktree_gc tests.
Idleness is set with os.utime on the tree, its root and its git-dir index/HEAD. Caches are
built the way lanes build them: an ignored `.venv`, and a read-only materialized tree under
the ignored `.claude/cache/index-trees`. The intra-day reaper and the low-disk guard run
`--strip-idle-caches-min 30 --prune-pytest-hours 2`; main() is driven with those flags.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import worktree_gc
from worktree_gc import delete_tree, holders_for, plan_pytest_prune, strip_candidates

MINUTE = 60.0
GUARD_FLAGS = ("--strip-idle-caches-min", "30", "--prune-pytest-hours", "2", "--no-size")
NO_HOLDER = {"/nowhere": [1]}


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


def _status(wt: Path) -> str:
    """`git status` that never rewrites the index: a refresh would reset the idle clock."""
    return _git("--no-optional-locks", "status", "--porcelain", cwd=wt)


@pytest.fixture(autouse=True)
def _fence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """No test prunes the real pytest-of-<user> or reads the real txt-mapping scan, and
    read-only fixtures are made writable again so pytest's own cleanup never chokes on them."""
    monkeypatch.setattr(worktree_gc, "pytest_temp_roots", list)
    monkeypatch.setattr(worktree_gc, "live_mapped_holders", lambda: dict(NO_HOLDER))
    yield
    worktree_gc.make_writable(tmp_path)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    (r / "scripts").mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=r)
    _git("config", "user.email", "t@t.t", cwd=r)
    _git("config", "user.name", "t", cwd=r)
    (r / ".gitignore").write_text(".venv/\n.claude/cache/\n")
    (r / "f.txt").write_text("one\n")
    (r / "scripts" / "a.py").write_text("print('a')\n")
    _git("add", ".", cwd=r)
    _git("commit", "-qm", "init", cwd=r)
    return r


def _read_only_tree(root: Path) -> None:
    """A pre-commit style materialized tree: files 0444, directories 0555."""
    (root / "scripts" / "deep").mkdir(parents=True)
    (root / "scripts" / "deep" / "a.py").write_text("print('a')\n")
    (root / "f.txt").write_text("one\n")
    for path in sorted(root.rglob("*"), reverse=True):
        path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)


def _lane(repo: Path, name: str, commit: bool = True) -> Path:
    """A lane tree carrying both derived caches; with ``commit``, one commit main lacks.

    Without a commit the tree is SAFE (merged and clean), the default apply set, whose
    caches go with the tree rather than through the strip.
    """
    wt = repo.parent / "wts" / name
    _git("worktree", "add", "-q", "-b", f"lane/{name}", str(wt), "main", cwd=repo)
    if commit:
        (wt / "h.txt").write_text(f"{name}\n")
        _git("add", "h.txt", cwd=wt)
        _git("commit", "-qm", f"lane {name}", cwd=wt)
    site = wt / ".venv" / "lib" / "python3.12" / "site-packages"
    site.mkdir(parents=True)
    (site / "mod.py").write_text("x = 1\n")
    (wt / ".venv" / "pyvenv.cfg").write_text("home = /x\n")
    _read_only_tree(wt / ".claude" / "cache" / "index-trees" / "abc123")
    return wt


def _age(wt: Path, minutes: float) -> None:
    stamp = time.time() - minutes * MINUTE
    gd = Path(_git("rev-parse", "--absolute-git-dir", cwd=wt).strip())
    targets = [p for p in wt.rglob("*") if ".git" not in p.parts]
    targets += [wt, gd / "index", gd / "HEAD"]
    for p in targets:
        if p.is_symlink() or p.exists():
            os.utime(p, (stamp, stamp), follow_symlinks=False)


def _main(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *argv: str,
    holders: dict[str, list[int]] | None = None,
) -> tuple[int, str]:
    if holders is not None:
        monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: holders)
    monkeypatch.setattr(worktree_gc, "find_stranded", lambda *a, **k: [])
    monkeypatch.setattr(sys, "argv", ["worktree_gc.py", *argv])
    monkeypatch.setitem(sys.modules, "janitor_receipt", None)  # no real receipt
    rc = worktree_gc.main()
    return rc, capsys.readouterr().out


def _caches(wt: Path) -> tuple[bool, bool]:
    return (wt / ".venv").exists(), (wt / ".claude" / "cache" / "index-trees").exists()


def test_idle_tree_loses_both_caches_read_only_tree_included(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "idle")
    _age(wt, 45)
    assert [c.name for c in strip_candidates(wt)] == [".venv", "index-trees"]
    rc, audit = _main(monkeypatch, capsys, "audit", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and f"would-strip {wt} .venv=? .claude/cache/index-trees=?" in audit
    assert _caches(wt) == (True, True)

    rc, out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and f"STRIPPED {wt} .venv=" in out
    assert "stripped 1/1 trees' caches" in out
    assert _caches(wt) == (False, False)
    # Tracked files and the tree itself are untouched; `.claude/cache` itself survives.
    assert (wt / "f.txt").read_text() == "one\n" and (wt / "scripts" / "a.py").exists()
    assert (wt / ".claude" / "cache").is_dir()
    assert not _status(wt).strip()


def test_busy_tree_with_a_real_process_inside_is_skipped(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "busy")
    _age(wt, 600)
    # Positive control through the REAL lsof cwd scan: a process sitting in a subdirectory.
    child = subprocess.Popen(["sleep", "30"], cwd=wt / "scripts")
    try:
        deadline = time.time() + 10
        while not holders_for(wt, worktree_gc.live_cwd_holders()) and time.time() < deadline:
            time.sleep(0.1)
        rc, out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS)
    finally:
        child.kill()
        child.wait()
    assert rc == 0 and "STRIPPED" not in out and "stripped 0/0" in out
    assert _caches(wt) == (True, True)


def test_dirty_tree_loses_caches_and_keeps_every_edit(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "dirty")
    (wt / "f.txt").write_text("one\nedited, uncommitted\n")
    (wt / "scripts" / "a.py").unlink()
    (wt / "notes.md").write_text("untracked work\n")
    _age(wt, 45)
    before = _status(wt)
    assert before.count("\n") == 3
    rc, out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and f"STRIPPED {wt}" in out
    assert _caches(wt) == (False, False)
    assert (wt / "f.txt").read_text() == "one\nedited, uncommitted\n"
    assert (wt / "notes.md").read_text() == "untracked work\n"
    assert _status(wt) == before


def test_recent_activity_anywhere_keeps_the_caches(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "recent")
    _age(wt, 600)
    site = wt / ".venv" / "lib" / "python3.12" / "site-packages"
    # `uv run --project <tree>` from elsewhere installs a package: only site-packages moves.
    (site / "new_pkg").mkdir()
    os.utime(site / "new_pkg", (time.time() - 600 * MINUTE,) * 2)
    _rc, out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert "STRIPPED" not in out and _caches(wt) == (True, True)

    _age(wt, 600)
    (wt / "f.txt").write_text("one\nedit a minute ago\n")  # a dirty path moves the clock too
    os.utime(wt / "f.txt", (time.time() - 60,) * 2)
    _rc, out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert "STRIPPED" not in out and _caches(wt) == (True, True)


def test_a_cache_mapped_by_a_process_elsewhere_stays(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "mapped")
    _age(wt, 600)
    so = wt.resolve() / ".venv" / "lib" / "python3.12" / "site-packages" / "_ext.so"
    monkeypatch.setattr(worktree_gc, "live_mapped_holders", lambda: {str(so): [4242]})
    rc, out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and f"STRIPPED {wt} .claude/cache/index-trees=" in out
    assert _caches(wt) == (True, False)


def test_unknown_mapped_scan_refuses_every_strip_and_fails_loud(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "blind")
    _age(wt, 600)
    monkeypatch.setattr(worktree_gc, "live_mapped_holders", dict)
    rc, _out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 2 and _caches(wt) == (True, True)


def test_tracked_unignored_or_symlinked_caches_are_never_candidates(
    repo: Path, tmp_path: Path
) -> None:
    (repo / ".claude" / "cache" / "index-trees").mkdir(parents=True)
    (repo / ".claude" / "cache" / "index-trees" / "keep.txt").write_text("tracked\n")
    (repo / ".gitignore").write_text(".claude/cache/\n")  # .venv NOT ignored
    _git("add", "-f", ".gitignore", ".claude/cache/index-trees/keep.txt", cwd=repo)
    _git("commit", "-qm", "track a cache-shaped dir", cwd=repo)
    wt = repo.parent / "wts" / "odd"
    _git("worktree", "add", "-q", "--detach", str(wt), "main", cwd=repo)
    (wt / ".venv").mkdir()
    assert strip_candidates(wt) == []  # tracked content, and an unignored .venv

    other = repo.parent / "wts" / "linked"
    _git("worktree", "add", "-q", "--detach", str(other), "main", cwd=repo)
    elsewhere = tmp_path / "main-claude"
    (elsewhere / "cache" / "index-trees").mkdir(parents=True)
    (elsewhere / "cache" / "index-trees" / "precious").write_text("main's\n")
    worktree_gc.delete_tree(other / ".claude")
    (other / ".claude").symlink_to(elsewhere)
    assert strip_candidates(other) == []
    assert (elsewhere / "cache" / "index-trees" / "precious").read_text() == "main's\n"


def test_prune_mode_never_removes_a_worktree(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "merged", commit=False)  # SAFE: the default apply set
    _age(wt, 600)
    rc, out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and wt.exists() and "removed" not in out
    assert _caches(wt) == (False, False)
    with pytest.raises(SystemExit):
        _main(monkeypatch, capsys, "prune", "--repo", str(repo), "--no-size", holders=NO_HOLDER)


def _basetemp(root: Path, name: str, hours: float, lock_pid: int | None = None) -> Path:
    entry = root / name
    _read_only_tree(entry / "test_thing0" / "materialized")
    entry.chmod(0o755)
    (entry / "test_thing0").chmod(0o755)
    if lock_pid is not None:
        (entry / ".lock").write_text(str(lock_pid))
    stamp = time.time() - hours * 3600
    for p in [entry, *entry.rglob("*")]:
        os.utime(p, (stamp, stamp), follow_symlinks=False)
    return entry


def _dead_pid() -> int:
    child = subprocess.Popen(["true"])
    child.wait()
    return child.pid


def test_old_exited_pytest_basetemps_are_pruned_read_only_included(tmp_path: Path) -> None:
    root = tmp_path / "pytest-of-someone"
    old = _basetemp(root, "pytest-3", hours=3)
    # garbage-* goes whatever its mtime: pytest re-renames it (fresh mtime) at every exit.
    garbage = _basetemp(root, "garbage-0d52ca9c-0c59-476a-b723-f433cf273fa4", 0.01, _dead_pid())
    cleaning = _basetemp(root, "garbage-91084df3-c8e6-4271-84d6-5e2783c8c6cd", 3, os.getpid())
    running = _basetemp(root, "pytest-4", hours=3, lock_pid=os.getpid())
    fresh = _basetemp(root, "pytest-5", hours=0.5)
    held = _basetemp(root, "pytest-6", hours=3)
    other = _basetemp(root, "not-pytest", hours=3)
    (root / "pytest-current").symlink_to(fresh)
    holders = {str((held / "test_thing0").resolve()): [4242]}

    plan = plan_pytest_prune([root], 2, holders)
    assert sorted(p.name for p, _age_h in plan) == sorted([old.name, garbage.name])
    assert {p.name: age_h >= 2.9 for p, age_h in plan} == {old.name: True, garbage.name: False}
    for path, _age_h in plan:
        assert delete_tree(path)
    assert not old.exists() and not garbage.exists()
    assert running.exists() and fresh.exists() and held.exists() and other.exists()
    assert cleaning.exists()  # a live pytest is deleting it itself
    assert (root / "pytest-current").is_symlink()


def test_guard_prunes_pytest_basetemps_through_main(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "pytest-of-someone"
    old = _basetemp(root, "pytest-7", hours=5)
    monkeypatch.setattr(worktree_gc, "pytest_temp_roots", lambda: [root])
    rc, audit = _main(monkeypatch, capsys, "audit", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and f"would-prune-pytest {old}" in audit and old.exists()
    rc, out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and f"PRUNED-PYTEST {old}" in out and "pruned 1/1 pytest temp dirs" in out
    assert not old.exists()


def test_delete_tree_enters_a_mode_000_directory(tmp_path: Path) -> None:
    top = tmp_path / "t"
    (top / "sealed" / "inner").mkdir(parents=True)
    (top / "sealed" / "inner" / "f").write_text("x")
    (top / "sealed" / "inner").chmod(0o555)
    (top / "sealed").chmod(0)
    assert stat.S_IMODE((top / "sealed").stat().st_mode) == 0
    assert delete_tree(top) and not top.exists()


def test_holders_match_the_kernel_spelling_of_a_symlinked_path(tmp_path: Path) -> None:
    real = (tmp_path / "real").resolve()
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    # lsof reports /private/var/... for a $TMPDIR spelled /var/...; the link plays /var here.
    assert holders_for(link, {str(real / "sub"): [7]}) == [7]
    assert holders_for(link, {str(real) + "-sibling": [7]}) == []
