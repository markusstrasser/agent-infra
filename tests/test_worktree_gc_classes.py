"""Regression controls for the 2026-10-12 disk-exhaustion worktree classes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import worktree_gc


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "test")
    (root / ".gitignore").write_text(".claude/cache/\n.venv/\n")
    (root / "file").write_text("original\n")
    git(root, "add", ".gitignore", "file")
    git(root, "commit", "-qm", "initial")
    return root


@pytest.fixture(autouse=True)
def fence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.setattr(worktree_gc, "ARCHIVE_ROOT", tmp_path / "archive")
    monkeypatch.setattr(worktree_gc, "find_stranded", lambda *a, **kw: [])
    monkeypatch.setattr(worktree_gc, "pytest_temp_roots", list)
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: {"/nowhere": [1]})
    monkeypatch.setattr(worktree_gc, "live_mapped_holders", lambda: {"/nowhere": [1]})
    monkeypatch.setitem(sys.modules, "janitor_receipt", None)
    yield
    worktree_gc.make_writable(tmp_path)


def lane(
    repo: Path, *, unique: bool = False, dirty: bool = False, cache: bool = True
) -> Path:
    wt = repo.parent / "lane"
    git(repo, "worktree", "add", "-q", "--detach", str(wt), "main")
    if unique:
        (wt / "file").write_text("unique commit\n")
        git(wt, "add", "file")
        git(wt, "commit", "-qm", "unique")
    if dirty:
        (wt / "file").write_text("uncommitted work\n")
    if cache:
        cache_path = wt / ".claude/cache"
        cache_path.mkdir(parents=True)
        (cache_path / "result.md").write_text("lane report\n")
    stamp = time.time() - 10 * 86400
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    for path in [*wt.rglob("*"), wt, admin / "index", admin / "HEAD"]:
        os.utime(path, (stamp, stamp), follow_symlinks=False)
    return wt


def lock(repo: Path, wt: Path, hours: float, reason: str = "campaign lane") -> Path:
    git(repo, "worktree", "lock", "--reason", reason, str(wt))
    path = Path(git(wt, "rev-parse", "--absolute-git-dir")) / "locked"
    stamp = time.time() - hours * 3600
    os.utime(path, (stamp, stamp))
    return path


def main(monkeypatch: pytest.MonkeyPatch, repo: Path, mode: str, *flags: str) -> int:
    monkeypatch.setattr(
        sys, "argv", ["worktree_gc.py", mode, "--repo", str(repo), "--no-size", *flags]
    )
    return worktree_gc.main()


def archive(monkeypatch: pytest.MonkeyPatch, wt: Path) -> int:
    monkeypatch.setattr(sys, "argv", ["worktree_gc.py", "archive", "--path", str(wt)])
    return worktree_gc.main()


def state(repo: Path, wt: Path) -> tuple[object, ...]:
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    files = [p for p in wt.rglob("*") if p.is_file() and not p.is_symlink()]
    files += [
        p for p in (admin / "index", admin / "HEAD", admin / "locked") if p.exists()
    ]
    return (
        git(repo, "worktree", "list", "--porcelain"),
        git(repo, "for-each-ref", "--format=%(refname) %(objectname)"),
        tuple(sorted((str(p), p.read_bytes(), p.stat().st_mtime_ns) for p in files)),
    )


@pytest.mark.parametrize("hours, aged", [(71, False), (73, True)])
@pytest.mark.parametrize("dirty", [False, True])
@pytest.mark.parametrize("reason", ["campaign lane", ""])
def test_aged_lock_threshold_is_audit_only(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    hours: float,
    aged: bool,
    dirty: bool,
    reason: str,
) -> None:
    wt = lane(repo, dirty=dirty)
    lock(repo, wt, hours, reason)
    before = state(repo, wt)
    assert main(monkeypatch, repo, "audit", "--lock-max-age-hours", "72") == 0
    audit = capsys.readouterr().out
    assert (f"aged-lock {wt} (age" in audit) is aged
    if aged:
        assert f"age {hours:.1f}h" in audit
        assert f"reason={reason or '(no reason given)'}" in audit
    assert "would-archive-aged-lock" not in audit
    assert state(repo, wt) == before
    for mode, flags in (("apply", ()), ("prune", ("--prune-pytest-hours", "2"))):
        assert main(monkeypatch, repo, mode, "--lock-max-age-hours", "72", *flags) == 0
        assert state(repo, wt) == before
        assert not worktree_gc.ARCHIVE_ROOT.exists()


def test_exact_lock_age_threshold_stays_protected(repo: Path) -> None:
    wt = lane(repo)
    locked = lock(repo, wt, 72)
    row = worktree_gc.audit_repo(repo, with_size=False)[0]
    now = locked.stat().st_mtime + 72 * 3600
    assert not worktree_gc.lock_is_aged(row, 72, row.lock, now=now)
    assert worktree_gc.lock_is_aged(row, 72, row.lock, now=now + 1)


@pytest.mark.parametrize("reason", ["campaign lane", ""])
def test_pidless_lock_is_kept_without_opt_in(
    repo: Path, monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    wt = lane(repo)
    lock(repo, wt, 300, reason)
    assert (
        main(monkeypatch, repo, "apply", "--archive-stale-days", "0.25", "--force-all")
        == 0
    )
    assert wt.exists()


def test_live_pid_lock_is_kept_with_all_flags(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo, dirty=True)
    lock(repo, wt, 300, f"campaign (pid {os.getpid()})")
    assert (
        main(
            monkeypatch,
            repo,
            "apply",
            "--lock-max-age-hours",
            "24",
            "--archive-stale-days",
            "0.25",
            "--force-all",
        )
        == 0
    )
    assert wt.exists()


@pytest.mark.parametrize("locked", [False, True])
def test_process_inside_vetoes_explicit_archive(
    repo: Path, monkeypatch: pytest.MonkeyPatch, locked: bool
) -> None:
    wt = lane(repo, dirty=True)
    if locked:
        lock(repo, wt, 300)
    child = subprocess.Popen(["sleep", "30"], cwd=wt / ".claude/cache")
    try:
        # Real process/PID, controlled scan; live lsof is reserved for the read-only audit.
        monkeypatch.setattr(
            worktree_gc,
            "live_cwd_holders",
            lambda: {str(wt / ".claude/cache"): [child.pid]},
        )
        before = state(repo, wt)
        assert archive(monkeypatch, wt) == 2
        assert state(repo, wt) == before
        assert wt.exists()
        assert not list(worktree_gc.ARCHIVE_ROOT.glob("**/ignored-cache.tgz"))
    finally:
        child.terminate()
        child.wait()


def test_live_pid_lock_vetoes_explicit_archive(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo, unique=True, dirty=True)
    lock(repo, wt, 300, f"campaign (pid {os.getpid()})")
    before = state(repo, wt)
    assert archive(monkeypatch, wt) == 2
    assert state(repo, wt) == before
    assert not worktree_gc.ARCHIVE_ROOT.exists()


@pytest.mark.parametrize("revival", ["cwd", "pid-lock", "fresh-lock", "unknown-scan"])
def test_revival_during_archive_holds_the_tree(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    revival: str,
) -> None:
    wt = lane(repo, dirty=True)
    tip = git(wt, "rev-parse", "HEAD")
    original = worktree_gc.archive_worktree

    def archive_and_revive(row: worktree_gc.WorktreeRow) -> worktree_gc.ArchiveResult:
        result = original(row)
        if revival in ("cwd", "unknown-scan"):
            holders = {str(wt): [os.getpid()]} if revival == "cwd" else {}
            monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: holders)
        else:
            lock(
                repo,
                wt,
                0,
                f"pid {os.getpid()}" if revival == "pid-lock" else "new campaign",
            )
        return result

    monkeypatch.setattr(worktree_gc, "archive_worktree", archive_and_revive)
    assert archive(monkeypatch, wt) == 2
    assert wt.exists() and (wt / "file").read_text() == "uncommitted work\n"
    assert tip in git(repo, "for-each-ref", "--format=%(objectname)", "refs/wt-archive")
    if revival in ("pid-lock", "fresh-lock"):
        assert worktree_gc.current_lock(repo, wt) is not None


@pytest.mark.parametrize("flag", ["--include-unmerged", "--force-all"])
def test_detached_unique_head_is_pinned_before_removal(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    flag: str,
) -> None:
    wt = lane(repo, unique=True, cache=False)
    tip = git(wt, "rev-parse", "HEAD")
    assert main(monkeypatch, repo, "apply", flag) == 0
    assert not wt.exists()
    assert (
        tip
        in git(
            repo, "for-each-ref", "--format=%(objectname)", "refs/wt-archive"
        ).splitlines()
    )
    git(repo, "reflog", "expire", "--expire=now", "--all")
    git(repo, "gc", "--prune=now")
    assert git(repo, "cat-file", "-t", tip) == "commit"


def test_idle_branched_unique_head_needs_explicit_archive(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo, unique=True)
    git(wt, "switch", "-qc", "lane/unique")
    stamp = time.time() - 5 * 3600
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    os.utime(admin / "HEAD", (stamp, stamp))
    os.utime(admin / "index", (stamp, stamp))
    tip = git(wt, "rev-parse", "HEAD")
    assert main(monkeypatch, repo, "apply", "--unmerged-idle-hours", "3") == 0
    assert wt.exists()
    assert not git(repo, "for-each-ref", "refs/wt-archive")
    assert archive(monkeypatch, wt) == 0
    assert not wt.exists()
    assert (
        tip
        in git(
            repo, "for-each-ref", "--format=%(objectname)", "refs/wt-archive"
        ).splitlines()
    )


def test_read_only_directory_retry_holds_without_chmod_outside(
    repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    wt = lane(repo)
    sealed = wt / ".claude/cache/sealed"
    sealed.mkdir()
    (sealed / "data").write_text("sealed")
    external = tmp_path / "external"
    external.mkdir()
    (external / "data").write_text("outside")
    (external / "data").chmod(0o444)
    external.chmod(0o555)
    (wt / "symlink").symlink_to(external)
    (sealed / "hardlinked-data").hardlink_to(external / "data")
    sealed.chmod(0o555)
    archive = worktree_gc.archive_worktree(
        next(r for r in worktree_gc.audit_repo(repo, with_size=False) if r.path == wt)
    )
    assert archive.ok, archive.reason
    manifest = json.loads((archive.dir / "content-manifest.json").read_text())
    # Git can unregister before a permission failure. A bound archive must HOLD
    # remaining files rather than widening recovery into a blind recursive delete.
    with pytest.raises((RuntimeError, subprocess.CalledProcessError)):
        worktree_gc.remove_worktree(repo, wt, manifest=manifest)
    assert wt.exists() and (archive.dir / "ignored.tgz").is_file()
    assert f"RETRY {wt}" in capsys.readouterr().out
    assert external.stat().st_mode & 0o777 == 0o555
    assert (external / "data").stat().st_mode & 0o777 == 0o444


def test_master_does_not_substitute_for_main_reachability(repo: Path) -> None:
    wt = lane(repo, unique=True, cache=False)
    tip = git(wt, "rev-parse", "HEAD")
    git(repo, "branch", "master", tip)
    assert not worktree_gc.is_ancestor(repo, tip)
    worktree_gc.remove_worktree(repo, wt)
    assert (
        tip
        in git(
            repo, "for-each-ref", "--format=%(objectname)", "refs/wt-archive"
        ).splitlines()
    )


def test_declared_default_branch_controls_automatic_removal(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = git(repo, "rev-parse", "HEAD")
    wt = lane(repo, unique=True)
    tip = git(wt, "rev-parse", "HEAD")
    git(repo, "merge", "--ff-only", tip)
    git(repo, "update-ref", "refs/remotes/origin/trunk", base)
    git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    assert worktree_gc.ahead_of_main(repo, tip) == 1
    assert not worktree_gc.is_ancestor(repo, tip)
    assert not worktree_gc.all_patches_on_main(repo, tip)
    assert main(monkeypatch, repo, "apply") == 0
    assert wt.exists()


def test_local_default_branch_is_not_replaced_by_stale_remote(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    wt = lane(repo, unique=True)
    tip = git(wt, "rev-parse", "HEAD")
    git(repo, "merge", "--ff-only", tip)
    git(repo, "update-ref", "refs/remotes/origin/main", base)
    git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    assert worktree_gc.ahead_of_main(repo, tip) == 0
    assert worktree_gc.is_ancestor(repo, tip)


@pytest.mark.parametrize("explicit", [False, True])
def test_pin_failure_holds_unique_detached_tree(
    repo: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool
) -> None:
    wt = lane(repo, unique=True)

    def fail_pin(*args: object) -> str:
        raise subprocess.CalledProcessError(
            1, ["git", "update-ref"], stderr="pin refused"
        )

    monkeypatch.setattr(worktree_gc, "_pin_ref", fail_pin)
    if explicit:
        assert archive(monkeypatch, wt) == 2
    else:
        assert main(monkeypatch, repo, "apply", "--include-unmerged") == 0
    assert wt.exists()
    assert not git(repo, "for-each-ref", "refs/wt-archive")


def test_unreadable_cache_report_holds_explicit_archive(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    wt = lane(repo, dirty=True)
    lock(repo, wt, 300)
    (wt / ".claude/cache/result.md").chmod(0)
    assert archive(monkeypatch, wt) == 2
    assert "HOLD" in capsys.readouterr().err
    assert wt.exists() and worktree_gc.current_lock(repo, wt) is not None
    assert not git(repo, "for-each-ref", "refs/wt-archive")


def test_bad_patch_holds_explicit_archive(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo, unique=True, dirty=True)
    before = state(repo, wt)
    monkeypatch.setattr(
        worktree_gc,
        "_write_patch",
        lambda _wt, dest: dest.write_bytes(b"invalid patch\n"),
    )
    assert archive(monkeypatch, wt) == 2
    assert state(repo, wt) == before
    assert not git(repo, "for-each-ref", "refs/wt-archive")


def test_unknown_liveness_refuses_explicit_archive(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo, unique=True, dirty=True)
    before = state(repo, wt)
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", dict)
    assert archive(monkeypatch, wt) == 2
    assert state(repo, wt) == before
    assert not worktree_gc.ARCHIVE_ROOT.exists()


def test_keep_vetoes_aged_lock(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wt = lane(repo)
    lock(repo, wt, 300)
    assert (
        main(
            monkeypatch, repo, "apply", "--lock-max-age-hours", "24", "--keep", str(wt)
        )
        == 0
    )
    assert wt.exists()


def test_unknown_liveness_refuses_aged_lock_reclamation(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wt = lane(repo)
    lock(repo, wt, 300)
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", dict)
    assert main(monkeypatch, repo, "apply", "--lock-max-age-hours", "24") == 2
    assert wt.exists() and not worktree_gc.ARCHIVE_ROOT.exists()


@pytest.mark.parametrize("dirty", [False, True])
@pytest.mark.parametrize("locked", [False, True])
@pytest.mark.parametrize("unique", [False, True])
def test_explicit_archive_pins_and_preserves_reports_before_removal(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    dirty: bool,
    locked: bool,
    unique: bool,
) -> None:
    wt = lane(repo, unique=unique, dirty=dirty)
    tip = git(wt, "rev-parse", "HEAD")
    (wt / "new file.md").write_text("untracked work\n")
    locked_file = lock(repo, wt, 300) if locked else None
    lock_state = (
        (locked_file.read_bytes(), locked_file.stat().st_mtime_ns)
        if locked_file
        else None
    )
    remove = worktree_gc.remove_worktree
    removals: list[Path] = []

    def verify_then_remove(root: Path, path: Path, **kwargs: object) -> None:
        assert tip in git(
            root, "for-each-ref", "--format=%(objectname)", "refs/wt-archive"
        )
        saved = list(worktree_gc.ARCHIVE_ROOT.glob("**/ignored-cache.tgz"))
        assert len(saved) == 1
        assert (saved[0].parent / "RESTORE.md").exists()
        removals.append(path)
        remove(root, path, **kwargs)

    monkeypatch.setattr(worktree_gc, "remove_worktree", verify_then_remove)
    assert archive(monkeypatch, wt) == (2 if locked else 0)
    out = capsys.readouterr().out
    assert "ignored-cache=1 ignored-cache-bytes=12B" in out
    saved = list(worktree_gc.ARCHIVE_ROOT.glob("**/ignored-cache.tgz"))
    assert len(saved) == 1
    dest = saved[0].parent
    assert (dest / "head.txt").read_text().strip() == tip
    assert tip in git(repo, "for-each-ref", "--format=%(objectname)", "refs/wt-archive")
    assert ((dest / "tracked.patch").stat().st_size > 0) is dirty
    with tarfile.open(saved[0]) as packed:
        assert packed.extractfile(".claude/cache/result.md").read() == b"lane report\n"
    with tarfile.open(dest / "untracked.tgz") as packed:
        assert packed.extractfile("new file.md").read() == b"untracked work\n"
    assert wt.exists() is locked
    if locked_file:
        assert (locked_file.read_bytes(), locked_file.stat().st_mtime_ns) == lock_state
        assert removals == []
        assert "separate explicit decision" in out
    else:
        assert removals == [wt]
        assert str(wt) not in git(repo, "worktree", "list", "--porcelain")


@pytest.mark.parametrize("path_kind", ["primary", "ordinary-dir", "missing", "symlink"])
def test_explicit_archive_refuses_non_secondary_paths(
    repo: Path, monkeypatch: pytest.MonkeyPatch, path_kind: str
) -> None:
    if path_kind == "primary":
        path = repo
    elif path_kind == "ordinary-dir":
        path = repo.parent / "ordinary"
        path.mkdir()
    elif path_kind == "missing":
        path = repo.parent / "missing"
    else:
        path = repo.parent / "linked"
        path.symlink_to(lane(repo))
    refs = git(repo, "for-each-ref")
    assert archive(monkeypatch, path) == 2
    assert git(repo, "for-each-ref") == refs
    assert not worktree_gc.ARCHIVE_ROOT.exists()


@pytest.mark.parametrize(
    "kind",
    ["old-safe", "fresh-safe", "unique", "tracked", "untracked", "locked", "duplicate"],
)
def test_default_apply_behavior_is_unchanged(
    repo: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    wt = lane(
        repo,
        unique=kind in ("unique", "duplicate"),
        dirty=kind == "tracked",
        cache=False,
    )
    if kind == "fresh-safe":
        admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
        (admin / "HEAD").touch()
    elif kind == "untracked":
        (wt / "new-file").write_text("work\n")
    elif kind == "locked":
        lock(repo, wt, 300)
    elif kind == "duplicate":
        git(wt, "switch", "-qc", "duplicate")
        tip = git(wt, "rev-parse", "HEAD")
        (repo / "other").write_text("independent\n")
        git(repo, "add", "other")
        git(repo, "commit", "-qm", "main advanced")
        git(repo, "cherry-pick", tip)
    before = state(repo, wt)
    assert main(monkeypatch, repo, "apply") == 0
    assert wt.exists() is (kind != "old-safe")
    if wt.exists():
        assert state(repo, wt) == before
    assert not worktree_gc.ARCHIVE_ROOT.exists()
    assert not git(repo, "for-each-ref", "refs/wt-archive")


@pytest.mark.parametrize("kind", ["safe", "unique", "tracked", "untracked", "locked"])
def test_prune_keeps_work_and_reports_with_existing_flags(
    repo: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    wt = lane(repo, unique=kind == "unique", dirty=kind == "tracked")
    if kind == "untracked":
        (wt / "new-file").write_text("work\n")
    elif kind == "locked":
        lock(repo, wt, 300)
    (wt / ".venv").mkdir()
    (wt / ".venv/derived").write_text("cache\n")
    stamp = time.time() - 10 * 86400
    for path in [*wt.rglob("*"), wt]:
        os.utime(path, (stamp, stamp), follow_symlinks=False)
    before = state(repo, wt)
    assert (
        main(
            monkeypatch,
            repo,
            "prune",
            "--strip-idle-caches-min",
            "30",
            "--prune-pytest-hours",
            "2",
        )
        == 0
    )
    assert wt.exists() and not (wt / ".venv").exists()
    after = state(repo, wt)
    assert after[:2] == before[:2]
    assert after[2] == tuple(entry for entry in before[2] if "/.venv/" not in entry[0])
    assert (wt / ".claude/cache/result.md").read_text() == "lane report\n"
    assert not worktree_gc.ARCHIVE_ROOT.exists()


@pytest.mark.parametrize("threshold", ["0", "-1", "nan", "inf"])
def test_invalid_lock_age_fails_before_scanning(
    repo: Path, monkeypatch: pytest.MonkeyPatch, threshold: str
) -> None:
    with pytest.raises(SystemExit) as result:
        main(monkeypatch, repo, "apply", "--lock-max-age-hours", threshold)
    assert result.value.code == 2
