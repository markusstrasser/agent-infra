"""Idle reap of clean unmerged worktrees and `git worktree lock` awareness for worktree_gc.

Real temp repos + `git worktree add`/`lock`, the same fixture shape as
test_worktree_gc_archive.py. Idleness is set with os.utime on the tree and its git-dir
index/HEAD, which is the clock idle_age_days reads. The intra-day reaper runs
`apply --unmerged-idle-hours 3 --strip-idle-venvs-days 0.05 --no-size`; main() is driven
with exactly those flags.
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
    audit_repo,
    lock_is_stale,
    plan_idle_unmerged,
    remove_worktree,
    should_remove,
)

HOUR = 3600.0
REAP_FLAGS = ("--unmerged-idle-hours", "3", "--strip-idle-venvs-days", "0.05", "--no-size")


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
    (r / "f.txt").write_text("one\n")
    _git("add", ".", cwd=r)
    _git("commit", "-qm", "init", cwd=r)
    return r


def _age_tree(wt: Path, hours: float) -> None:
    stamp = time.time() - hours * HOUR
    gd = Path(_git("rev-parse", "--absolute-git-dir", cwd=wt).strip())
    targets = [p for p in wt.rglob("*") if ".git" not in p.parts]
    targets += [gd / "index", gd / "HEAD"]
    for p in targets:
        if p.is_symlink() or p.exists():
            os.utime(p, (stamp, stamp), follow_symlinks=False)


def _lane(repo: Path, name: str) -> Path:
    """A branched lane with one commit main lacks and an ignored per-lane .venv."""
    wt = repo.parent / "wts" / name
    _git("worktree", "add", "-q", "-b", f"lane/{name}", str(wt), "main", cwd=repo)
    (wt / "h.txt").write_text(f"{name}\n")
    _git("add", "h.txt", cwd=wt)
    _git("commit", "-qm", f"lane {name}", cwd=wt)
    (wt / ".venv" / "lib").mkdir(parents=True)
    (wt / ".venv" / "lib" / "x.py").write_text("x")
    return wt


def _row(repo: Path, wt: Path) -> WorktreeRow:
    rows = [r for r in audit_repo(repo, with_size=False) if r.path == wt]
    assert rows, "worktree not audited"
    return rows[0]


def _dead_pid() -> int:
    child = subprocess.Popen(["true"])
    child.wait()
    with pytest.raises(ProcessLookupError):
        os.kill(child.pid, 0)
    return child.pid


def _main(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: {"/nowhere": [1]})
    monkeypatch.setattr(worktree_gc, "find_stranded", lambda *a, **k: [])
    monkeypatch.setattr(sys, "argv", ["worktree_gc.py", *argv])
    monkeypatch.setitem(sys.modules, "janitor_receipt", None)  # no real receipt
    assert worktree_gc.main() == 0
    return capsys.readouterr().out


def test_idle_clean_unmerged_tree_is_reaped_and_its_branch_kept(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "lane-idle")
    tip = _git("rev-parse", "lane/lane-idle", cwd=repo).strip()
    _age_tree(wt, 4)
    row = _row(repo, wt)
    assert row.classify() == "unmerged" and row.unmerged_clean
    assert plan_idle_unmerged([row], 3, set(), exclude=[]) == [row]

    audit = _main(monkeypatch, capsys, "audit", "--repo", str(repo), *REAP_FLAGS)
    assert f"would-reap-idle {wt}" in audit
    # The reaped row is kept out of the strip plan: its .venv goes with the directory.
    assert f"would-strip {wt}" not in audit
    assert wt.exists()

    out = _main(monkeypatch, capsys, "apply", "--repo", str(repo), *REAP_FLAGS)
    assert f"REAPED-IDLE {wt}" in out and "STRIPPED" not in out
    assert not wt.exists()
    assert _git("rev-parse", "--verify", "lane/lane-idle", cwd=repo).strip() == tip
    assert str(wt) not in _git("worktree", "list", cwd=repo)


def test_tree_idle_less_than_the_threshold_is_kept(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "lane-recent")
    _age_tree(wt, 2)
    assert plan_idle_unmerged([_row(repo, wt)], 3, set(), exclude=[]) == []
    out = _main(monkeypatch, capsys, "apply", "--repo", str(repo), *REAP_FLAGS)
    assert "REAPED-IDLE" not in out
    assert (wt / "h.txt").exists()


@pytest.mark.parametrize("edit", ["tracked", "untracked"])
def test_dirty_unmerged_tree_is_kept(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    edit: str,
) -> None:
    wt = _lane(repo, f"lane-{edit}")
    if edit == "tracked":
        (wt / "f.txt").write_text("edited\n")
    else:
        (wt / "report-stub.md").write_text("a lane's first hour of work\n")
    _age_tree(wt, 10)
    row = _row(repo, wt)
    assert row.dirty and not row.unmerged_clean
    assert plan_idle_unmerged([row], 3, set(), exclude=[]) == []
    _main(monkeypatch, capsys, "apply", "--repo", str(repo), *REAP_FLAGS)
    assert wt.exists()


def test_detached_tree_ahead_of_main_is_kept(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = repo.parent / "wts" / "land-detached"
    _git("worktree", "add", "-q", "--detach", str(wt), "main", cwd=repo)
    (wt / "h.txt").write_text("integration commit\n")
    _git("add", "h.txt", cwd=wt)
    _git("commit", "-qm", "detached work", cwd=wt)
    _age_tree(wt, 10)
    row = _row(repo, wt)
    assert row.branch is None and not row.ancestor
    assert plan_idle_unmerged([row], 3, set(), exclude=[]) == []
    _main(monkeypatch, capsys, "apply", "--repo", str(repo), *REAP_FLAGS)
    assert wt.exists()


def test_git_refuses_the_clean_removal_when_a_lane_writes_after_the_scan(
    repo: Path,
) -> None:
    wt = _lane(repo, "lane-race")
    _age_tree(wt, 10)
    row = _row(repo, wt)
    assert plan_idle_unmerged([row], 3, set(), exclude=[]) == [row]
    (wt / "late.md").write_text("written between the scan and the removal\n")
    with pytest.raises(subprocess.CalledProcessError):
        remove_worktree(repo, wt, force=False)
    assert (wt / "late.md").exists()


def test_live_lock_keeps_the_tree_under_every_flag(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "lane-live")
    reason = f"claude agent agent-live (pid {os.getpid()} start Mon Sep 28 04:00:00 2026)"
    _git("worktree", "lock", "--reason", reason, str(wt), cwd=repo)
    _age_tree(wt, 10)
    row = _row(repo, wt)
    assert row.lock == reason and row.lock_live and row.classify() == "LOCKED"
    assert plan_idle_unmerged([row], 3, set(), exclude=[]) == []
    assert not should_remove(row, True, True, True, set())
    audit = _main(monkeypatch, capsys, "audit", "--repo", str(repo), *REAP_FLAGS)
    assert "LOCKED" in audit and "would-reap-idle" not in audit
    _main(
        monkeypatch,
        capsys,
        "apply",
        "--repo",
        str(repo),
        "--include-unmerged",
        "--force-all",
        *REAP_FLAGS,
    )
    assert wt.exists() and (wt / ".venv").exists()


def test_dead_pid_lock_is_released_and_the_tree_reaped(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = _lane(repo, "lane-dead")
    pid = _dead_pid()
    reason = f"claude agent agent-dead (pid {pid} start Fri Sep 25 22:50:45 2026)"
    _git("worktree", "lock", "--reason", reason, str(wt), cwd=repo)
    _age_tree(wt, 10)
    row = _row(repo, wt)
    assert row.lock_stale and not row.lock_live and row.classify() == "unmerged"
    audit = _main(monkeypatch, capsys, "audit", "--repo", str(repo), *REAP_FLAGS)
    assert "stale-lock" in audit and f"would-reap-idle {wt}" in audit
    out = _main(monkeypatch, capsys, "apply", "--repo", str(repo), *REAP_FLAGS)
    assert f"unlocked {wt}" in out and f"REAPED-IDLE {wt}" in out
    assert not wt.exists()
    assert _git("rev-parse", "--verify", "lane/lane-dead", cwd=repo).strip()


def test_dead_pid_lock_no_longer_pins_a_merged_tree(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = repo.parent / "wts" / "lane-merged"
    _git("worktree", "add", "-q", "-b", "lane/merged", str(wt), "main", cwd=repo)
    _git("worktree", "lock", "--reason", f"claude session s (pid {_dead_pid()})", str(wt), cwd=repo)
    row = _row(repo, wt)
    assert row.classify() == "SAFE" and row.lock_stale
    out = _main(monkeypatch, capsys, "apply", "--repo", str(repo), "--no-size")
    assert f"removed {wt}" in out and not wt.exists()


@pytest.mark.parametrize("reason", [None, "operator: keep for the bisect"])
def test_lock_without_a_pid_is_live(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    reason: str | None,
) -> None:
    wt = _lane(repo, "lane-human")
    _git("worktree", "lock", *(["--reason", reason] if reason else []), str(wt), cwd=repo)
    _age_tree(wt, 10)
    row = _row(repo, wt)
    assert row.lock == (reason or "") and row.lock_live
    _main(monkeypatch, capsys, "apply", "--repo", str(repo), "--force-all", *REAP_FLAGS)
    assert wt.exists()


def test_lock_staleness_needs_a_named_dead_pid(repo: Path) -> None:
    dead = _dead_pid()
    assert not lock_is_stale(None) and not lock_is_stale("")
    assert not lock_is_stale("keep this one")
    assert not lock_is_stale(f"claude agent a (pid {os.getpid()} start x)")
    assert lock_is_stale(f"claude agent a (pid {dead} start x)")
    # A reason with a newline comes back C-quoted from porcelain; the pid still parses.
    wt = _lane(repo, "lane-quoted")
    _git("worktree", "lock", "--reason", f"two\nlines (pid {dead})", str(wt), cwd=repo)
    assert _row(repo, wt).lock_stale


@pytest.mark.parametrize("with_lane", [True, False])
def test_receipt_motor_names_the_receipt_even_when_nothing_is_left(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    with_lane: bool,
) -> None:
    import janitor_receipt

    monkeypatch.setattr(janitor_receipt, "RECEIPT_DIR", tmp_path / "receipts")
    if with_lane:
        _age_tree(_lane(repo, "lane-receipt"), 10)
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: {"/nowhere": [1]})
    monkeypatch.setattr(worktree_gc, "find_stranded", lambda *a, **k: [])
    argv = ["apply", "--repo", str(repo), "--receipt-motor", "worktree_reap", *REAP_FLAGS]
    monkeypatch.setattr(sys, "argv", ["worktree_gc.py", *argv])
    assert worktree_gc.main() == 0
    receipt = janitor_receipt.load_receipt("worktree_reap")
    assert receipt and receipt["success"] and receipt["principal_metric"] == int(with_lane)
    assert janitor_receipt.load_receipt("worktree_gc") is None
