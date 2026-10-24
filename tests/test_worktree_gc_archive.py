"""Archive-then-reap and idle-cache stripping for worktree_gc.

Real temp repos + `git worktree add`; idleness is set with os.utime so the idle clock
(dirty-path and git-dir index/HEAD mtimes, never commit age) is exercised for real.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
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
        manifest = json.loads((res.dir / "content-manifest.json").read_text())
        remove_worktree(row.repo_root, row.path, manifest=manifest)
    return res


def test_idle_stale_dirty_is_archived_removed_pinned_and_restorable(
    repo: Path, tmp_path: Path
) -> None:
    wt = _dirty_tree(repo, "lane-idle", days=8)
    row = _row(repo, wt)
    assert row.classify() == "HOLD"
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
    subprocess.run(
        ["tar", "-xzf", str(res.dir / "untracked.tgz"), "-C", str(restore)], check=True
    )
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
        ["worktree_gc.py", "archive", "--path", str(wt)],
    )
    monkeypatch.setitem(sys.modules, "janitor_receipt", None)  # no real receipt
    assert worktree_gc.main() == 2
    out = capsys.readouterr().err
    assert f"HOLD {wt}: archive self-check failed:" in out
    assert wt.exists()


def test_strip_idle_venv_keeps_symlinked_cache_and_tree(
    repo: Path, tmp_path: Path
) -> None:
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
    assert plan_cache_strip([row], 60, set(), exclude=[], mapped=NO_MAPPED) == [
        (row, [wt / ".venv"])
    ]
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


def test_trees_sharing_a_leaf_name_never_share_an_archive(
    repo: Path, tmp_path: Path
) -> None:
    # Codex lanes all end in `<lane>/<repo>`: keyed by the leaf alone, the second archive of a
    # day overwrote the first after the first tree was already gone.
    first = _dirty_tree(repo, f"lane-a/{repo.name}", days=8)
    second = _dirty_tree(repo, f"lane-b/{repo.name}", days=8)
    (second / "f.txt").write_text("second lane edit\n")
    root = tmp_path / "archives"
    one = _run_archive(_row(repo, first), root)
    two = _run_archive(_row(repo, second), root)
    assert one.ok and two.ok
    assert (one.dir.name, two.dir.name) == (
        f"lane-a--{repo.name}",
        f"lane-b--{repo.name}",
    )
    assert b"TWO edited" in (one.dir / "tracked.patch").read_bytes()
    assert b"second lane edit" in (two.dir / "tracked.patch").read_bytes()
    # Same name on the same day (a tree re-created and archived again) gets a suffix.
    assert worktree_gc._fresh_dir(tmp_path / "x" / "lane") == tmp_path / "x" / "lane"
    assert worktree_gc._fresh_dir(tmp_path / "x" / "lane") == tmp_path / "x" / "lane-2"


def test_editing_inside_an_untracked_dir_counts_as_activity(repo: Path) -> None:
    wt = _dirty_tree(repo, "lane-busy", days=8)
    assert worktree_gc.idle_age_days(wt) >= 7.9
    (wt / "notes" / "new file.md").write_text(
        "edited just now\n"
    )  # dir mtime unchanged
    assert worktree_gc.idle_age_days(wt) < 0.01


def test_archive_preserves_small_cache_reports_excluding_large_files_and_symlinks(
    repo: Path,
    tmp_path: Path,
) -> None:
    wt = _dirty_tree(repo, "cache-report", days=8)
    _git("config", "core.excludesFile", "/dev/null", cwd=repo)
    with (wt / ".gitignore").open("a") as ignore:
        ignore.write(".claude/cache/\n")
    cache = wt / ".claude/cache"
    (cache / "x").mkdir(parents=True)
    (cache / "x/result.md").write_text("lane result\n")
    (cache / "empty.md").touch()
    with (cache / "large.bin").open("wb") as large:
        large.truncate(21 * 1024 * 1024)
    (cache / "index-trees").mkdir()
    (cache / "index-trees/excluded.md").write_text("derived")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret").write_text("outside")
    (cache / "linked-dir").symlink_to(outside)
    (cache / "linked-file").symlink_to(outside / "secret")
    res = _run_archive(_row(repo, wt), tmp_path / "arch")
    assert res.ok and not wt.exists()
    assert res.ignored_cache_files == 2 and res.ignored_cache_bytes == 12
    with tarfile.open(res.dir / "ignored-cache.tgz") as archive:
        assert set(archive.getnames()) == {
            ".claude/cache/x/result.md",
            ".claude/cache/empty.md",
        }
        assert (
            archive.extractfile(".claude/cache/x/result.md").read() == b"lane result\n"
        )
    assert "ignored-cache.tgz" in (res.dir / "RESTORE.md").read_text()
    assert (outside / "secret").read_text() == "outside"


def test_symlinked_cache_parent_is_not_archived(repo: Path, tmp_path: Path) -> None:
    wt = _dirty_tree(repo, "cache-link", days=8)
    outside = tmp_path / "outside"
    (outside / "cache").mkdir(parents=True)
    (outside / "cache/result.md").write_text("external")
    (wt / ".claude").symlink_to(outside)
    res = archive_worktree(_row(repo, wt), root=tmp_path / "arch")
    assert res.ok and res.ignored_cache_files == 0
    with tarfile.open(res.dir / "ignored-cache.tgz") as archive:
        assert archive.getnames() == []


SOURCE_EPOCH = ".claude/cache/source-epochs/content/abc/tree"


def _nested_repo(path: Path) -> None:
    """A real self-contained repository with objects and refs, as source-epochs keep."""
    (path / "scripts").mkdir(parents=True)
    (path / "scripts/stage.py").write_text("print('materialized source')\n")
    _git("init", "-q", cwd=path)
    _git("config", "user.email", "t@t.t", cwd=path)
    _git("config", "user.name", "t", cwd=path)
    _git("add", ".", cwd=path)
    _git("commit", "-qm", "epoch", cwd=path)


def _read_only_dirs(root: Path) -> None:
    for directory, _dirs, _files in os.walk(root, topdown=False):
        os.chmod(directory, 0o555)


def _epoch_tree(
    repo: Path, name: str, *, ignored: bool = True, epoch: bool = True
) -> Path:
    wt = _dirty_tree(repo, name, days=8)
    _git("config", "core.excludesFile", "/dev/null", cwd=repo)
    if ignored:
        with (wt / ".gitignore").open("a") as ignore:
            ignore.write(".claude/cache/\n")
    (wt / ".claude/cache/x").mkdir(parents=True)
    (wt / ".claude/cache/x/result.md").write_text("lane result\n")
    if epoch:
        _nested_repo(wt / SOURCE_EPOCH)
    return wt


def test_ignored_source_epoch_nested_repo_archives_without_hold(
    repo: Path, tmp_path: Path
) -> None:
    wt = _epoch_tree(repo, "source-epoch")
    epochs = wt / ".claude/cache/source-epochs"
    head = (wt / SOURCE_EPOCH / ".git/HEAD").read_bytes()
    _read_only_dirs(epochs)  # genomics materializes epoch trees read-only
    assert epochs in worktree_gc.strip_candidates(wt)
    row = _row(repo, wt)
    assert row.hold_reason is None
    res = _run_archive(row, tmp_path / "arch")
    assert res.ok, res.reason
    assert not wt.exists()
    # Rebuildable strip-class trees are listed, not archived; ignored lane output
    # beside them keeps its bytes.
    assert head
    with tarfile.open(res.dir / "ignored-cache.tgz") as archive:
        assert set(archive.getnames()) == {".claude/cache/x/result.md"}
    with tarfile.open(res.dir / "ignored.tgz") as archive:
        names = set(archive.getnames())
    assert ".claude/cache/x/result.md" in names
    assert not any(n.startswith((".claude/cache/source-epochs", ".venv")) for n in names)
    stripped = (res.dir / "stripped-caches.txt").read_text().splitlines()
    assert stripped == [".claude/cache/source-epochs", ".venv"]


@pytest.mark.parametrize("epoch", [False, True], ids=["alone", "beside-epoch"])
@pytest.mark.parametrize("nested", ["vendor/lib", ".claude/cache/vendor/lib"])
def test_nested_repo_outside_strip_caches_still_holds(
    repo: Path, tmp_path: Path, nested: str, epoch: bool
) -> None:
    wt = _epoch_tree(repo, "vendor-repo", epoch=epoch)
    _nested_repo(wt / nested)
    row = _row(repo, wt)
    assert row.hold_reason == f"nested repository: {nested}"
    res = archive_worktree(row, root=tmp_path / "arch")
    assert not res.ok and res.reason == f"nested repository: {nested}"
    assert (wt / nested / ".git").is_dir()


@pytest.mark.parametrize("state", ["tracked", "unignored"])
def test_source_epoch_that_is_tracked_or_unignored_still_holds(
    repo: Path, tmp_path: Path, state: str
) -> None:
    wt = _epoch_tree(repo, f"epoch-{state}", ignored=state == "tracked")
    if state == "tracked":
        (wt / ".claude/cache/source-epochs/README").write_text("somebody's notes\n")
        _git("add", "-f", ".claude/cache/source-epochs/README", cwd=wt)
    assert wt / ".claude/cache/source-epochs" not in worktree_gc.strip_candidates(wt)
    row = _row(repo, wt)
    assert row.hold_reason == f"nested repository: {SOURCE_EPOCH}"
    res = archive_worktree(row, root=tmp_path / "arch")
    assert not res.ok and res.reason == f"nested repository: {SOURCE_EPOCH}"
    assert (wt / SOURCE_EPOCH / ".git").is_dir()


ORIG_HOLD = "unlanded or unreadable worktree-local ref: ORIG_HEAD"


def _is_ancestor(repo: Path, oid: str, tip: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", oid, tip],
            cwd=repo,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def _orig_head_lane(repo: Path, name: str, unique: int) -> tuple[Path, list[str]]:
    """Detached tree on unique scratch commits only its HEAD keeps, edit landed."""
    _git("switch", "-qc", "scratch", cwd=repo)
    shas = []
    for n in range(unique):
        (repo / f"scratch{n}.txt").write_text(f"candidate scratch {n}\n")
        _git("add", f"scratch{n}.txt", cwd=repo)
        _git("commit", "-qm", f"scratch {n}", cwd=repo)
        shas.append(_git("rev-parse", "HEAD", cwd=repo).strip())
    _git("switch", "-q", "main", cwd=repo)
    _git("branch", "-qD", "scratch", cwd=repo)
    wt = repo.parent / "wts" / name
    _git("worktree", "add", "-q", "--detach", str(wt), shas[-1], cwd=repo)
    (repo / "f.txt").write_text("one\nTWO landed\n")
    _git("commit", "-qam", "land the lane edit", cwd=repo)
    (wt / "f.txt").write_text("one\nTWO landed\n")
    assert (wt / "f.txt").read_text() == _git("show", "main:f.txt", cwd=repo)
    return wt, shas


def _set_orig_head(wt: Path, oid: str) -> None:
    # Written as Git's files backend stores it; update-ref could add a reflog.
    admin = Path(_git("rev-parse", "--absolute-git-dir", cwd=wt).strip())
    (admin / "ORIG_HEAD").write_text(oid + "\n")


def _cli_archive(monkeypatch: pytest.MonkeyPatch, root: Path, wt: Path) -> int:
    monkeypatch.setattr(worktree_gc, "ARCHIVE_ROOT", root)
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: {"/nowhere": [1]})
    monkeypatch.setattr(worktree_gc, "find_stranded", lambda *a, **k: [])
    monkeypatch.setattr(sys, "argv", ["worktree_gc.py", "archive", "--path", str(wt)])
    monkeypatch.setitem(sys.modules, "janitor_receipt", None)  # no real receipt
    return worktree_gc.main()


@pytest.mark.parametrize("behind", [0, 1], ids=["orig-is-head", "orig-below-head"])
def test_orig_head_reachable_from_pinned_head_archives_and_removes(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, behind: int
) -> None:
    wt, shas = _orig_head_lane(repo, f"lane-orig-{behind}", unique=2)
    head, orig = shas[-1], shas[-1 - behind]
    _set_orig_head(wt, orig)
    assert not _is_ancestor(repo, orig, "main")
    # Classification keeps the default-ancestor rule; suggest/apply are unchanged.
    row = _row(repo, wt)
    assert (row.hold_reason, row.classify()) == (ORIG_HOLD, "HOLD")
    assert _cli_archive(monkeypatch, tmp_path / "arch", wt) == 0
    assert not wt.exists()
    dest = next((tmp_path / "arch").glob("**/head.txt")).parent
    with tarfile.open(dest / "git-state.tgz") as packed:
        assert packed.extractfile(".git/ORIG_HEAD").read() == f"{orig}\n".encode()
    pins = dict(
        line.split()
        for line in _git(
            "for-each-ref",
            "--format=%(objectname) %(refname)",
            "refs/wt-archive",
            cwd=repo,
        ).splitlines()
    )
    # The removed tree's admin state was ORIG_HEAD's last root besides HEAD's pin.
    _git(
        "reflog",
        "expire",
        "--expire=now",
        "--expire-unreachable=now",
        "--all",
        cwd=repo,
    )
    _git("gc", "-q", "--prune=now", cwd=repo)
    assert _git("cat-file", "-t", orig, cwd=repo).strip() == "commit"
    assert _is_ancestor(repo, orig, pins[head])


def _assert_orig_head_holds(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    wt: Path,
) -> None:
    assert _cli_archive(monkeypatch, tmp_path / "arch", wt) == 2
    assert (
        f"HOLD {wt}: archive self-check failed: {ORIG_HOLD}" in capsys.readouterr().err
    )
    with pytest.raises(RuntimeError, match=ORIG_HOLD):
        remove_worktree(repo, wt)
    assert wt.exists() and (wt / "f.txt").read_text() == "one\nTWO landed\n"
    assert not _git("for-each-ref", "refs/wt-archive", cwd=repo).strip()


def test_orig_head_reachable_from_neither_default_nor_head_is_pinned(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A chain rebuild leaves such an ORIG_HEAD; every autopilot candidate archive
    # held on it until the archive pinned it like an unreachable reflog object.
    wt, shas = _orig_head_lane(repo, "lane-orig-foreign", unique=1)
    _git("switch", "-qc", "elsewhere", cwd=repo)
    (repo / "elsewhere.txt").write_text("unrelated unique work\n")
    _git("add", "elsewhere.txt", cwd=repo)
    _git("commit", "-qm", "unrelated", cwd=repo)
    foreign = _git("rev-parse", "HEAD", cwd=repo).strip()
    _git("switch", "-q", "main", cwd=repo)
    _git("branch", "-qD", "elsewhere", cwd=repo)
    _set_orig_head(wt, foreign)
    assert not _is_ancestor(repo, foreign, "main")
    assert not _is_ancestor(repo, foreign, shas[-1])
    # Classification still holds: suggest and the automatic classes never pin.
    row = _row(repo, wt)
    assert (row.hold_reason, row.classify()) == (ORIG_HOLD, "HOLD")
    with pytest.raises(RuntimeError, match=ORIG_HOLD):
        remove_worktree(repo, wt)
    assert _cli_archive(monkeypatch, tmp_path / "arch", wt) == 0
    assert not wt.exists()
    dest = next((tmp_path / "arch").glob("**/head.txt")).parent
    pins = json.loads((dest / "evidence-manifest.json").read_text())
    assert pins["orig-head"]["oid"] == foreign
    assert pins["orig-head"]["ref"].endswith("-evidence/orig-head")
    _git(
        "reflog",
        "expire",
        "--expire=now",
        "--expire-unreachable=now",
        "--all",
        cwd=repo,
    )
    _git("gc", "-q", "--prune=now", cwd=repo)
    assert _git("rev-parse", pins["orig-head"]["ref"], cwd=repo).strip() == foreign
    assert _git("cat-file", "-t", foreign, cwd=repo).strip() == "commit"


def _set_claude_base(wt: Path, oid: str) -> None:
    # Claude Code writes the bare object ID with no newline.
    admin = Path(_git("rev-parse", "--absolute-git-dir", cwd=wt).strip())
    (admin / "CLAUDE_BASE").write_text(oid)


def test_claude_base_naming_the_tree_base_archives_raw_bytes(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt, shas = _orig_head_lane(repo, "lane-claude-base", unique=1)
    base = _git("rev-parse", f"{shas[0]}^", cwd=repo).strip()
    _set_claude_base(wt, base)
    assert _cli_archive(monkeypatch, tmp_path / "arch", wt) == 0
    assert not wt.exists()
    dest = next((tmp_path / "arch").glob("**/head.txt")).parent
    with tarfile.open(dest / "git-state.tgz") as packed:
        assert packed.extractfile(".git/CLAUDE_BASE").read() == base.encode()


def test_unreadable_claude_base_holds(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    wt, _shas = _orig_head_lane(repo, "lane-claude-base-bad", unique=1)
    _set_claude_base(wt, "not an object id")
    assert _cli_archive(monkeypatch, tmp_path / "arch", wt) == 2
    hold = "unlanded or unreadable worktree-local ref: CLAUDE_BASE"
    assert f"HOLD {wt}: archive self-check failed: {hold}" in capsys.readouterr().err
    assert wt.exists() and (wt / "f.txt").read_text() == "one\nTWO landed\n"
    assert not _git("for-each-ref", "refs/wt-archive", cwd=repo).strip()


@pytest.mark.parametrize("content", ["garbage", "missing", "blob"])
def test_unreadable_orig_head_holds(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    content: str,
) -> None:
    wt, shas = _orig_head_lane(repo, f"lane-orig-{content}", unique=1)
    oid = {
        "garbage": "not an object id",
        "missing": "0123456789abcdef0123456789abcdef01234567",
        "blob": _git("rev-parse", f"{shas[-1]}:scratch0.txt", cwd=repo).strip(),
    }[content]
    _set_orig_head(wt, oid)
    _assert_orig_head_holds(repo, tmp_path, monkeypatch, capsys, wt)
