"""Derived-cache stripping and pytest basetemp pruning for worktree_gc (the disk guard).

Real temp repos + `git worktree add`, the same fixture shape as the other worktree_gc tests.
Idleness is set with os.utime on the tree, its root and its git-dir index/HEAD. Caches are
built the way lanes build them: an ignored `.venv`, and a read-only materialized tree under
the ignored `.claude/cache/index-trees`. The intra-day reaper and the low-disk guard run
`--strip-idle-caches-min 30 --prune-pytest-hours 2`; main() is driven with those flags.
"""

from __future__ import annotations

import contextlib
import os
import signal
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


def test_cargo_target_is_a_candidate_only_beside_cargo_toml(repo: Path) -> None:
    (repo / ".gitignore").write_text(".venv/\n.claude/cache/\ntarget/\n")
    _git("commit", "-qam", "ignore target", cwd=repo)
    plain = repo.parent / "wts" / "plain"
    _git("worktree", "add", "-q", "--detach", str(plain), "main", cwd=repo)
    (plain / "target" / "data").mkdir(parents=True)
    assert strip_candidates(plain) == []  # an ignored target/ outside Cargo may hold anything

    (repo / "Cargo.toml").write_text('[package]\nname = "x"\n')
    _git("add", "Cargo.toml", cwd=repo)
    _git("commit", "-qm", "cargo", cwd=repo)
    rust = repo.parent / "wts" / "rust"
    _git("worktree", "add", "-q", "--detach", str(rust), "main", cwd=repo)
    (rust / "target" / "debug" / "deps").mkdir(parents=True)
    (rust / "target" / "debug" / "deps" / "libx.rlib").write_bytes(b"\0" * 64)
    assert strip_candidates(rust) == [rust / "target"]


def test_unlanded_cargo_build_survives_idle_reaper_but_not_low_disk_guard(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Lanes idle for hours waiting on peers; idle time alone never costs them a rebuild."""
    (repo / ".gitignore").write_text(".venv/\n.claude/cache/\ntarget/\n")
    (repo / "Cargo.toml").write_text('[package]\nname = "x"\n')
    _git("add", ".gitignore", "Cargo.toml", cwd=repo)
    _git("commit", "-qm", "cargo", cwd=repo)
    wt = _lane(repo, "waiting")  # one commit main lacks: unlanded work
    (wt / "target" / "debug").mkdir(parents=True)
    (wt / "target" / "debug" / "x").write_bytes(b"\0" * 64)
    _age(wt, 600)
    rc, audit = _main(monkeypatch, capsys, "audit", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and f"would-strip {wt} .venv=?" in audit and "target=" not in audit
    rc, _out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and wt.exists() and not (wt / "target").exists()


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


def _cargo(repo: Path) -> None:
    (repo / ".gitignore").write_text(".venv/\n.claude/cache/\ntarget/\n")
    (repo / "Cargo.toml").write_text('[package]\nname = "x"\n')
    _git("add", ".gitignore", "Cargo.toml", cwd=repo)
    _git("commit", "-qm", "cargo", cwd=repo)


def _build(wt: Path) -> None:
    (wt / "target" / "debug" / "deps").mkdir(parents=True)
    (wt / "target" / "debug" / "deps" / "libx.rlib").write_bytes(b"\0" * 64)


def test_prune_strips_without_the_removal_audit(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The audit's git proofs and whole-tree walks were 143 s of a 148 s prune plan on
    2026-11-09, the day the guard's prune timed out twice; prune never reads them."""
    _cargo(repo)
    wt = _lane(repo, "audit-free")
    _build(wt)
    _age(wt, 45)

    def audit(*_args: object, **_kwargs: object) -> None:
        pytest.fail("prune ran the removal audit")

    for name in (
        "audit_repo",
        "_audit_worktree",
        "_hidden_work",
        "_worktree_state_hold",
        "dirty_work_on_default",
    ):
        monkeypatch.setattr(worktree_gc, name, audit)
    rc, out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and f"STRIPPED {wt} " in out and "target=" in out
    assert not (wt / "target").exists() and _caches(wt) == (False, False)
    assert "timing: startup" in out and " strip " in out


def test_cargo_target_trees_are_planned_first(repo: Path) -> None:
    _cargo(repo)
    light = _lane(repo, "venv-only")
    heavy = _lane(repo, "with-target")
    _build(heavy)
    for wt in (light, heavy):
        _age(wt, 45)
    by_path = {row.path: row for row in worktree_gc.audit_repo(repo, with_size=False)}
    rows = [by_path[light], by_path[heavy]]
    plan = worktree_gc.plan_cache_strip(rows, 30, set(), exclude=[], mapped=NO_HOLDER)
    assert [row.path for row, _caches in plan] == [heavy, light]
    assert heavy / "target" in plan[0][1]
    parallel = worktree_gc.plan_cache_strip(
        rows, 30, set(), exclude=[], mapped=NO_HOLDER, workers=4
    )
    assert parallel == plan


def test_git_call_past_its_bound_keeps_the_caches(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slow = _lane(repo, "slow-git")
    quick = _lane(repo, "quick-git")
    for wt in (slow, quick):
        _age(wt, 600)
    real_run = worktree_gc.run
    bounds: list[float | None] = []

    def run(
        cmd: list[str],
        cwd: Path | None = None,
        check: bool = False,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if cwd == slow and "status" in cmd:
            bounds.append(timeout)
            raise subprocess.TimeoutExpired(cmd, timeout or 0)
        return real_run(cmd, cwd=cwd, check=check, timeout=timeout)

    monkeypatch.setattr(worktree_gc, "run", run)
    rc, out = _main(monkeypatch, capsys, "prune", "--repo", str(repo), *GUARD_FLAGS, holders=NO_HOLDER)
    assert rc == 0 and bounds == [worktree_gc.PRUNE_GIT_TIMEOUT_S]
    assert f"HOLD {slow}: git ran past {worktree_gc.PRUNE_GIT_TIMEOUT_S:g}s" in out
    assert f"STRIPPED {slow}" not in out and _caches(slow) == (True, True)
    assert f"STRIPPED {quick}" in out and _caches(quick) == (False, False)


def test_killed_prune_keeps_finished_strips_and_names_the_step(
    repo: Path, tmp_path: Path
) -> None:
    """The disk guard appends prune's stdout to its log under `timeout 1800`, which SIGTERMs
    the process group. Block-buffered, a kill lost every finished line; now each strip line
    lands at once and the kill prints the step it cut. A fake `du` lets the first tree's
    strip finish and stalls the second's, whichever order the plan picks."""
    _cargo(repo)
    trees = {name: _lane(repo, name) for name in ("kill-a", "kill-b")}
    for wt in trees.values():
        _build(wt)
        _age(wt, 45)
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "du").write_text(
        "#!/bin/sh\n"
        'case "$2" in\n'
        "*/wts/kill-a/*) t=kill-a ;;\n"
        "*/wts/kill-b/*) t=kill-b ;;\n"
        '*) exec /usr/bin/du "$@" ;;\n'
        "esac\n"
        '[ -s "$DU_MARK" ] || printf %s "$t" > "$DU_MARK"\n'
        '[ "$(cat "$DU_MARK")" = "$t" ] || exec sleep 300\n'
        'exec /usr/bin/du "$@"\n'
    )
    (fake / "du").chmod(0o755)
    mark = tmp_path / "du-first-tree"
    log = tmp_path / "disk-guard.log"
    # The guard's launchd job runs with stdout block-buffered. A caller's PYTHONUNBUFFERED
    # (Claude Code's background shells set it) would hide a lost line.
    env = {key: value for key, value in os.environ.items() if key != "PYTHONUNBUFFERED"}
    env |= {
        "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
        "DU_MARK": str(mark),
        "JANITOR_RECEIPT_DIR": str(tmp_path / "receipts"),
    }
    argv = [sys.executable, worktree_gc.__file__, "prune", "--repo", str(repo)]
    with log.open("ab") as sink:
        proc = subprocess.Popen(
            [*argv, "--strip-idle-caches-min", "30", "--no-size"],
            stdout=sink,
            stderr=sink,
            cwd=tmp_path,
            env=env,
            start_new_session=True,
        )
    try:
        deadline = time.time() + 120
        while (
            "STRIPPED " not in log.read_text()
            and proc.poll() is None
            and time.time() < deadline
        ):
            time.sleep(0.2)
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGTERM)  # GNU timeout signals its whole group
        rc = proc.wait(timeout=60)
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
    text = log.read_text()
    assert mark.is_file(), text
    done = trees.pop(mark.read_text())
    (cut,) = trees.values()
    assert f"STRIPPED {done} " in text and "target=" in text, text
    assert "[KILLED] SIGTERM during strip; startup" in text, text
    assert rc == 128 + signal.SIGTERM, text
    assert not (done / "target").exists() and _caches(done) == (False, False)
    assert (cut / "target").is_dir() and _caches(cut) == (True, True)


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
