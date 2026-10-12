"""Landed dirty lanes: exact-content proof and quarantined opt-in removal."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import worktree_gc


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "test")
    (root / ".gitignore").write_text(".claude/cache/\n.venv/\nscratch/\n")
    (root / "file").write_text("one\ntwo\n" + "context\n" * 20 + "three\n")
    (root / "binary").write_bytes(bytes(range(256)))
    git(root, "add", ".gitignore", "file", "binary")
    git(root, "commit", "-qm", "initial")
    monkeypatch.setattr(worktree_gc, "ARCHIVE_ROOT", tmp_path / "archive")
    monkeypatch.setattr(worktree_gc, "find_stranded", lambda *a, **kw: [])
    monkeypatch.setattr(worktree_gc, "pytest_temp_roots", list)
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: {"/nowhere": [1]})
    monkeypatch.setattr(worktree_gc, "live_mapped_holders", lambda: {"/nowhere": [1]})
    monkeypatch.setitem(sys.modules, "janitor_receipt", None)
    return root


def age(wt: Path, hours: float = 240) -> None:
    stamp = time.time() - hours * 3600
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    for path in [*wt.rglob("*"), wt, admin / "index", admin / "HEAD"]:
        os.utime(path, (stamp, stamp), follow_symlinks=False)


def lane(repo: Path, *, tracked: bool = True, untracked: bool = True) -> Path:
    wt = repo.parent / "lane"
    git(repo, "worktree", "add", "-q", "--detach", str(wt), "main")
    if tracked:
        data = (
            (wt / "file")
            .read_text()
            .replace("two\n", "TWO\n")
            .replace("three\n", "THREE\n")
        )
        (wt / "file").write_text(data)
        (repo / "file").write_text(data)
        binary = bytes(reversed(range(256)))
        (wt / "binary").write_bytes(binary)
        (repo / "binary").write_bytes(binary)
        git(repo, "add", "file", "binary")
    if untracked:
        for root in (wt, repo):
            (root / "notes").mkdir()
            (root / "notes" / "new file\n[1].md").write_bytes(b"landed\x00bytes\n")
        git(repo, "add", "notes")
    git(repo, "commit", "-qm", "parent lands lane diff")
    if tracked:
        git(wt, "add", "file", "binary")
    (wt / ".claude/cache").mkdir(parents=True)
    (wt / ".claude/cache/result.md").write_text("ignored report\n")
    age(wt)
    return wt


def run(monkeypatch: pytest.MonkeyPatch, repo: Path, mode: str, *flags: str) -> int:
    monkeypatch.setattr(
        sys, "argv", ["worktree_gc.py", mode, "--repo", str(repo), "--no-size", *flags]
    )
    return worktree_gc.main()


def row(repo: Path, wt: Path) -> worktree_gc.WorktreeRow:
    return next(
        r for r in worktree_gc.audit_repo(repo, with_size=False) if r.path == wt
    )


def snapshot(repo: Path, wt: Path) -> tuple[object, ...]:
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    files = [p for p in wt.rglob("*") if p.is_file() and not p.is_symlink()]
    files += [p for p in admin.iterdir() if p.is_file()]
    return (
        git(repo, "worktree", "list", "--porcelain"),
        git(repo, "for-each-ref", "--format=%(refname) %(objectname)"),
        tuple(sorted((str(p), p.read_bytes(), p.stat().st_mtime_ns) for p in files)),
    )


def test_complete_diff_is_landed_archived_pinned_and_restorable(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    head = git(wt, "rev-parse", "HEAD")
    wanted = (wt / "file").read_bytes()
    assert row(repo, wt).classify() == "landed"
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert not wt.exists()
    archive = next(worktree_gc.ARCHIVE_ROOT.glob("**/head.txt")).parent
    assert (archive / "head.txt").read_text().strip() == head
    assert head in git(
        repo, "for-each-ref", "--format=%(objectname)", "refs/wt-archive"
    )
    restore = repo.parent / "restored"
    git(repo, "worktree", "add", "-q", "--detach", str(restore), head)
    git(restore, "apply", str(archive / "tracked.patch"))
    assert (restore / "file").read_bytes() == wanted
    assert (restore / "binary").read_bytes() == bytes(reversed(range(256)))
    with tarfile.open(archive / "untracked.tgz") as tgz:
        data = tgz.extractfile("notes/new file\n[1].md")
        assert data is not None and data.read() == b"landed\x00bytes\n"
    with tarfile.open(archive / "ignored-cache.tgz") as tgz:
        data = tgz.extractfile(".claude/cache/result.md")
        assert data is not None and data.read() == b"ignored report\n"
    manifest = json.loads((archive / "content-manifest.json").read_text())
    assert manifest["file"]["sha256"] == hashlib.sha256(wanted).hexdigest()
    assert manifest[".claude/cache/result.md"] == {
        "type": "file",
        "mode": 0o644,
        "size": len(b"ignored report\n"),
        "sha256": hashlib.sha256(b"ignored report\n").hexdigest(),
    }


@pytest.mark.parametrize(
    "mode, flags", [("apply", ()), ("suggest", ("--json",)), ("audit", ())]
)
def test_no_flag_and_read_only_modes_preserve_every_byte(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str,
    flags: tuple[str, ...],
) -> None:
    wt = lane(repo)
    before = snapshot(repo, wt)
    assert run(monkeypatch, repo, mode, *flags) == 0
    output = capsys.readouterr().out
    if mode == "suggest":
        assert json.loads(output)["candidates"][0]["class"] == "landed"
    elif mode == "audit":
        assert "landed" in output
    assert snapshot(repo, wt) == before
    assert not worktree_gc.ARCHIVE_ROOT.exists()


@pytest.mark.parametrize("mode", ["audit", "suggest", "prune"])
def test_opt_in_only_mutates_in_apply(
    repo: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    wt = lane(repo)
    before = snapshot(repo, wt)
    flags = ("--prune-pytest-hours", "24") if mode == "prune" else ()
    assert (
        run(monkeypatch, repo, mode, "--archive-landed-idle-hours", "24", *flags) == 0
    )
    assert snapshot(repo, wt) == before
    assert not worktree_gc.ARCHIVE_ROOT.exists()


@pytest.mark.parametrize("change", ["partial", "later", "absent", "different"])
def test_landing_remains_durable_after_default_changes(
    repo: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    wt = lane(repo)
    if change in ("partial", "later"):
        text = (repo / "file").read_text()
        (repo / "file").write_text(
            text.replace("THREE", "three" if change == "partial" else "later")
        )
        git(repo, "add", "file")
    else:
        path = repo / "notes/new file\n[1].md"
        if change == "absent":
            git(repo, "rm", str(path))
        else:
            path.write_bytes(b"different\n")
            git(repo, "add", str(path))
    git(repo, "commit", "-qm", change)
    assert row(repo, wt).classify() == "landed"
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert not wt.exists()
    assert list(worktree_gc.ARCHIVE_ROOT.glob("**/head.txt"))


@pytest.mark.parametrize("tracked, untracked", [(True, False), (False, True)])
def test_tracked_only_and_untracked_only_lanes(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tracked: bool, untracked: bool
) -> None:
    wt = lane(repo, tracked=tracked, untracked=untracked)
    assert row(repo, wt).classify() == "landed"
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert not wt.exists()


@pytest.mark.parametrize(
    "hold",
    ["cwd", "daemon", "pid-lock", "pidless-lock", "fresh", "keep", "unknown-scan"],
)
def test_holders_locks_freshness_and_keep_veto_landed_archive(
    repo: Path, monkeypatch: pytest.MonkeyPatch, hold: str
) -> None:
    wt = lane(repo)
    flags = []
    if hold in ("cwd", "daemon", "unknown-scan"):
        holders = {} if hold == "unknown-scan" else {str(wt): [os.getpid()]}
        monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: holders)
        if hold == "daemon":
            monkeypatch.setattr(worktree_gc, "daemon_pids", lambda pids: pids)
    elif hold in ("pid-lock", "pidless-lock"):
        reason = f"pid {os.getpid()}" if hold == "pid-lock" else "campaign"
        git(repo, "worktree", "lock", "--reason", reason, str(wt))
    elif hold == "fresh":
        age(wt, 1)
    elif hold == "keep":
        flags = ["--keep", str(wt)]
    before = snapshot(repo, wt)
    assert run(
        monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24", *flags
    ) == (2 if hold == "unknown-scan" else 0)
    assert snapshot(repo, wt) == before
    assert not worktree_gc.ARCHIVE_ROOT.exists()


@pytest.mark.parametrize(
    "revival", ["diff", "untracked", "head", "default", "cwd", "pid-lock", "fresh"]
)
def test_all_evidence_is_rechecked_after_archive(
    repo: Path, monkeypatch: pytest.MonkeyPatch, revival: str
) -> None:
    wt = lane(repo)
    original = worktree_gc.archive_worktree

    def archive_then_change(row: worktree_gc.WorktreeRow) -> worktree_gc.ArchiveResult:
        result = original(row)
        if revival == "diff":
            (wt / "file").write_text("unlanded edit\n")
            age(wt)  # landing proof itself must fail, independently of freshness
        elif revival == "untracked":
            (wt / "new").write_text("unlanded file\n")
            age(wt)
        elif revival == "head":
            (wt / "new").write_text("unique commit\n")
            git(wt, "add", "new")
            git(wt, "commit", "-qm", "unique")
            age(wt)
        elif revival == "default":
            (repo / "file").write_text("main changed\n")
            git(repo, "add", "file")
            git(repo, "commit", "-qm", "main changed")
        elif revival == "cwd":
            monkeypatch.setattr(
                worktree_gc, "live_cwd_holders", lambda: {str(wt): [os.getpid()]}
            )
        elif revival == "pid-lock":
            git(repo, "worktree", "lock", "--reason", f"pid {os.getpid()}", str(wt))
        else:
            age(wt, 1)
        return result

    monkeypatch.setattr(worktree_gc, "archive_worktree", archive_then_change)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists()
    assert list(worktree_gc.ARCHIVE_ROOT.glob("**/head.txt"))


def test_unique_commits_veto_even_when_dirty_diff_is_landed(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    (wt / "unique").write_text("unique\n")
    git(wt, "add", "unique")
    git(wt, "commit", "-qm", "unlanded")
    age(wt)
    assert row(repo, wt).classify() == "skip-dirty"
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists()


def test_patch_equivalent_detached_commits_allow_landing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = repo.parent / "lane"
    git(repo, "worktree", "add", "-q", "--detach", str(wt), "main")
    for root in (repo, wt):
        (root / "committed").write_text("same patch\n")
        git(root, "add", "committed")
        git(root, "commit", "-qm", "parent" if root == repo else "lane")
    for root in (repo, wt):
        (root / "file").write_text("landed dirty diff\n")
    git(repo, "add", "file")
    git(repo, "commit", "-qm", "land diff")
    git(wt, "add", "file")
    age(wt)
    r = row(repo, wt)
    assert r.ahead == 1 and r.dup and r.classify() == "landed"
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert not wt.exists()


def test_archive_self_check_failure_keeps_landed_tree(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    monkeypatch.setattr(
        worktree_gc, "_write_patch", lambda wt, dest: dest.write_bytes(b"garbage\n")
    )
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists()
    assert not git(repo, "for-each-ref", "refs/wt-archive")


@pytest.mark.parametrize("hidden", [True, False])
def test_staged_patch_must_also_be_landed(
    repo: Path, monkeypatch: pytest.MonkeyPatch, hidden: bool
) -> None:
    wt = lane(repo)
    landed = (wt / "file").read_bytes()
    if hidden:
        (wt / "file").write_text("unique staged work\n")
    git(wt, "add", "file")
    (wt / "file").write_bytes(landed)
    age(wt)
    before = snapshot(repo, wt)
    assert row(repo, wt).classify() == ("HOLD" if hidden else "landed")
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    if hidden:
        assert snapshot(repo, wt) == before
        assert not worktree_gc.ARCHIVE_ROOT.exists()
    else:
        assert not wt.exists()


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf"])
def test_invalid_idle_threshold_is_rejected(
    repo: Path, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    with pytest.raises(SystemExit) as error:
        run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", value)
    assert error.value.code == 2


@pytest.mark.parametrize(
    "change", ["tracked", "untracked", "committed", "ignored", "flagged", "clean"]
)
def test_dirty_submodule_content_is_never_assumed_landed(
    repo: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    sub = repo.parent / "sub-source"
    sub.mkdir()
    git(sub, "init", "-q", "-b", "main")
    git(sub, "config", "user.email", "test@example.com")
    git(sub, "config", "user.name", "test")
    (sub / "file").write_text("submodule original\n")
    (sub / ".gitignore").write_text("scratch/\n")
    git(sub, "add", "file", ".gitignore")
    git(sub, "commit", "-qm", "initial")
    git(
        repo,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        "-q",
        str(sub),
        "sub",
    )
    git(repo, "commit", "-qm", "submodule")
    wt = lane(repo)
    git(wt, "-c", "protocol.file.allow=always", "submodule", "update", "--init", "-q")
    if change == "ignored":
        (wt / "sub/scratch").mkdir()
        (wt / "sub/scratch/research.txt").write_text("unique ignored submodule work\n")
    elif change != "clean":
        (wt / "sub" / ("file" if change == "tracked" else "unique")).write_text(
            "unlanded submodule work\n"
        )
        if change == "flagged":
            git(wt / "sub", "update-index", "--skip-worktree", "file")
            (wt / "sub/file").write_text("unique flagged submodule work\n")
    if change == "committed":
        git(wt / "sub", "config", "user.email", "test@example.com")
        git(wt / "sub", "config", "user.name", "test")
        git(wt / "sub", "add", "unique")
        git(wt / "sub", "commit", "-qm", "unique nested commit")
    git(wt, "config", "diff.ignoreSubmodules", "all")
    age(wt)
    before = snapshot(repo, wt)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert candidate.hold_reason and "initialized submodule" in candidate.hold_reason
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert snapshot(repo, wt) == before
    assert not worktree_gc.ARCHIVE_ROOT.exists()
    if change == "clean":
        # A hidden-only child must not bypass the dirty/landed gate via SAFE.
        git(wt, "reset", "--hard", "-q", "main")
        # Ignored cache bytes now count as work. Remove this fixture payload so
        # the control still exercises a genuinely clean parent with a child.
        shutil.rmtree(wt / ".claude/cache")
        age(wt)
        assert row(repo, wt).dirty == 0
        assert row(repo, wt).classify() == "HOLD"
        assert run(monkeypatch, repo, "apply") == 0
        assert wt.exists()


@pytest.mark.parametrize("payload", ["notes.txt", "nested/empty-directory"])
def test_populated_uninitialized_gitlink_is_held(
    repo: Path, monkeypatch: pytest.MonkeyPatch, payload: str
) -> None:
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{head},sub")
    git(repo, "commit", "-qm", "uninitialized gitlink")
    wt = lane(repo)
    child = wt / "sub" / payload
    child.parent.mkdir(parents=True, exist_ok=True)
    if payload.endswith("directory"):
        child.mkdir()
    else:
        child.write_text("unique uninitialized child work\n")
    assert not (wt / "sub/.git").exists()
    age(wt)
    before = snapshot(repo, wt)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert not worktree_gc.dirty_work_on_default(repo, wt)
    assert (
        candidate.hold_reason
        and "populated uninitialized submodule" in candidate.hold_reason
    )
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert snapshot(repo, wt) == before
    assert not worktree_gc.ARCHIVE_ROOT.exists()
    git(wt, "reset", "--hard", "-q", "main")
    age(wt)
    assert row(repo, wt).classify() == "HOLD"
    assert run(monkeypatch, repo, "apply") == 0
    assert child.exists()


@pytest.mark.parametrize("change", ["revert", "still-landed"])
def test_default_ref_moved_during_settle_is_held(
    repo: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    wt = lane(repo)
    wanted = (wt / "file").read_bytes()
    before = git(repo, "rev-parse", "main")

    def settle_then_move_default(_seconds: float) -> None:
        if change == "revert":
            git(repo, "revert", "--no-edit", "HEAD")
        else:
            git(repo, "commit", "--allow-empty", "-qm", "default moved")
        assert git(repo, "rev-parse", "main") != before

    monkeypatch.setattr(worktree_gc.time, "sleep", settle_then_move_default)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists() and (wt / "file").read_bytes() == wanted
    assert wt in {path for path, _, _ in worktree_gc.parse_worktrees(repo)}
    assert not list(wt.parent.glob("gc-quarantine-*"))


def test_quarantine_settle_change_is_held(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    slept = []

    def settle_then_write(seconds: float) -> None:
        slept.append(seconds)
        quarantine = next(
            path
            for path, _, _ in worktree_gc.parse_worktrees(repo)
            if path.name.startswith("gc-quarantine-")
        )
        (quarantine / ".claude/cache/settle.md").write_text("work during settle\n")
        age(quarantine)

    monkeypatch.setattr(worktree_gc.time, "sleep", settle_then_write)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert slept == [worktree_gc.QUARANTINE_SETTLE_SECONDS]
    assert slept[0] > 0
    assert wt.exists()
    assert (wt / ".claude/cache/settle.md").read_text() == "work during settle\n"


def test_staged_rename_original_path_is_not_a_status_record(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "1 x").write_text("rename me\n")
    git(repo, "add", "1 x")
    git(repo, "commit", "-qm", "rename source")
    wt = lane(repo)
    for root in (repo, wt):
        git(root, "mv", "1 x", "renamed")
    git(repo, "commit", "-qm", "land rename")
    age(wt)
    assert row(repo, wt).classify() == "landed"
    assert run(monkeypatch, repo, "audit") == 0
    assert run(monkeypatch, repo, "suggest", "--json") == 0
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert not wt.exists()


def test_quarantine_writer_after_last_holder_scan_is_held(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = lane(repo)
    wrote = False

    def scan_then_write() -> dict[str, list[int]]:
        nonlocal wrote
        # A new writer can discover the repaired registration, despite the rename.
        quarantine = next(
            path
            for path, _, _ in worktree_gc.parse_worktrees(repo)
            if path.name.startswith("gc-quarantine-")
        )
        (quarantine / ".claude/cache/late-work.md").write_text("unique late bytes\n")
        age(quarantine)
        wrote = True
        return {"/nowhere": [1]}

    monkeypatch.setattr(worktree_gc, "live_mapped_holders", scan_then_write)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wrote and wt.exists()
    assert (wt / ".claude/cache/late-work.md").read_text() == "unique late bytes\n"
    assert row(repo, wt).path == wt
    assert "manifest" in capsys.readouterr().err


@pytest.mark.parametrize("change", ["add", "same-size-edit"])
def test_post_archive_cache_change_with_preserved_mtime_is_held(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    change: str,
) -> None:
    wt = lane(repo)
    original = worktree_gc.archive_worktree
    path = wt / ".claude/cache/result.md"
    old_mtime = path.stat().st_mtime_ns
    target = path if change == "same-size-edit" else wt / ".claude/cache/new.md"
    data = b"changed report\n" if change == "same-size-edit" else b"late report\n"

    def archive_then_write(
        candidate: worktree_gc.WorktreeRow,
    ) -> worktree_gc.ArchiveResult:
        result = original(candidate)
        target.write_bytes(data)
        os.utime(target, ns=(old_mtime, old_mtime))
        return result

    monkeypatch.setattr(worktree_gc, "archive_worktree", archive_then_write)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists() and target.read_bytes() == data
    assert target.stat().st_mtime_ns == old_mtime
    assert "manifest" in capsys.readouterr().err


def test_cache_changes_during_archive_are_held(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    original = worktree_gc._archive_ignored_cache

    def archive_then_write(source: Path, dest: Path) -> tuple[int, int]:
        result = original(source, dest)
        (source / ".claude/cache/during.md").write_text("unarchived during capture\n")
        age(source)
        return result

    monkeypatch.setattr(worktree_gc, "_archive_ignored_cache", archive_then_write)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists()
    assert (wt / ".claude/cache/during.md").read_text() == "unarchived during capture\n"
    assert not git(repo, "for-each-ref", "refs/wt-archive")


@pytest.mark.parametrize("capture", ["wrong-bytes", "omitted"])
def test_cache_archive_payload_must_match_manifest_even_if_source_reverts(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capture: str
) -> None:
    wt = lane(repo)
    original = worktree_gc._archive_ignored_cache
    path = wt / ".claude/cache/result.md"
    wanted = path.read_bytes()

    def archive_wrong_bytes(source: Path, dest: Path) -> tuple[int, int]:
        path.write_bytes(
            b"x" * (21 * 1024 * 1024)
            if capture == "omitted"
            else b"wrong archived payload\n"
        )
        result = original(source, dest)
        path.write_bytes(wanted)
        age(source)
        return result

    monkeypatch.setattr(worktree_gc, "_archive_ignored_cache", archive_wrong_bytes)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists() and path.read_bytes() == wanted
    assert not git(repo, "for-each-ref", "refs/wt-archive")


@pytest.mark.parametrize("omitted", ["file", "binary", "addition", "all"])
def test_tracked_patch_payload_must_match_manifest_even_if_source_reverts(
    repo: Path, monkeypatch: pytest.MonkeyPatch, omitted: str
) -> None:
    wt = lane(repo)
    if omitted == "addition":
        for root in (wt, repo):
            (root / "addition").write_bytes(b"landed staged addition\x00\xff")
            git(root, "add", "addition")
        git(repo, "commit", "-qm", "land addition")
        age(wt)
    candidate = row(repo, wt)
    assert candidate.classify() == "landed"
    original = worktree_gc._write_patch
    names = ["file", "binary"] if omitted == "all" else [omitted]
    wanted = {name: (wt / name).read_bytes() for name in names}

    def write_incomplete_patch(source: Path, dest: Path) -> None:
        for name in names:
            path = source / name
            if name == "addition":
                path.unlink()
            else:
                path.write_bytes(
                    subprocess.run(
                        ["git", "show", f"HEAD:{name}"],
                        cwd=source,
                        capture_output=True,
                        check=True,
                    ).stdout
                )
        original(source, dest)
        for name, data in wanted.items():
            (source / name).write_bytes(data)
        age(source)

    monkeypatch.setattr(worktree_gc, "_write_patch", write_incomplete_patch)
    result = worktree_gc.archive_worktree(candidate)
    assert not result.ok and "tracked" in result.reason and "manifest" in result.reason
    assert not git(repo, "for-each-ref", "refs/wt-archive")
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists()
    assert all((wt / name).read_bytes() == data for name, data in wanted.items())
    assert not git(repo, "for-each-ref", "refs/wt-archive")


def test_unique_index_state_during_settle_is_held(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    blob = git(repo, "hash-object", "-w", "--stdin")  # unique empty staged version

    def settle_then_stage(_seconds: float) -> None:
        quarantine = next(
            path
            for path, _, _ in worktree_gc.parse_worktrees(repo)
            if path.name.startswith("gc-quarantine-")
        )
        git(quarantine, "update-index", "--cacheinfo", f"100644,{blob},file")

    monkeypatch.setattr(worktree_gc.time, "sleep", settle_then_stage)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists()
    assert git(wt, "rev-parse", ":file") == blob
    assert (wt / "file").read_bytes() == (repo / "file").read_bytes()


@pytest.mark.parametrize("damage", ["missing", "null", "malformed"])
def test_unreadable_archive_manifest_holds_before_quarantine(
    repo: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    wt = lane(repo)
    original = worktree_gc.archive_worktree

    def archive_then_damage(
        candidate: worktree_gc.WorktreeRow,
    ) -> worktree_gc.ArchiveResult:
        result = original(candidate)
        manifest = result.dir / "content-manifest.json"
        if damage == "missing":
            manifest.unlink()
        else:
            manifest.write_text("null" if damage == "null" else "{")
        return result

    monkeypatch.setattr(worktree_gc, "archive_worktree", archive_then_damage)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists()
    assert not list(wt.parent.glob("gc-quarantine-*"))


def test_duplicate_stanza_at_wrong_location_is_not_landed(repo: Path) -> None:
    stanza = "before\n" * 5 + "value=old\n" + "after\n" * 5
    original = "start\n" + stanza + "gap\n" * 20 + stanza + "end\n"
    (repo / "file").write_text(original)
    git(repo, "add", "file")
    git(repo, "commit", "-qm", "repeated stanzas")
    wt = repo.parent / "lane"
    git(repo, "worktree", "add", "-q", "--detach", str(wt), "main")
    (wt / "file").write_text(original.replace("value=old", "value=new", 1))
    git(wt, "add", "file")
    (wt / "file").write_text(original)
    before, after = original.rsplit("value=old", 1)
    (repo / "file").write_text(before + "value=new" + after)
    git(repo, "add", "file")
    git(repo, "commit", "-qm", "land only second stanza")
    age(wt)
    assert not worktree_gc.dirty_work_on_default(repo, wt)
    assert row(repo, wt).classify() == "HOLD"


@pytest.mark.parametrize("empty", [False, True])
def test_ignored_non_cache_work_holds_tree(
    repo: Path, monkeypatch: pytest.MonkeyPatch, empty: bool
) -> None:
    wt = lane(repo)
    (wt / "scratch").mkdir()
    if not empty:
        (wt / "scratch/research.txt").write_text("unique human work\n")
    age(wt)
    before = snapshot(repo, wt)
    assert not worktree_gc.dirty_work_on_default(repo, wt)
    assert row(repo, wt).classify() == "stale-dirty"
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert snapshot(repo, wt) == before


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_index_flags_hold_hidden_work(
    repo: Path, monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    wt = lane(repo)
    git(wt, "update-index", flag, "binary")
    (wt / "binary").write_bytes(b"unique hidden bytes\x00")
    age(wt)
    before = snapshot(repo, wt)
    assert not worktree_gc.dirty_work_on_default(repo, wt)
    assert row(repo, wt).classify() == "stale-dirty"
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert snapshot(repo, wt) == before


def test_writer_after_check_is_preserved_by_quarantine(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = lane(repo)
    original = worktree_gc.removal_hold
    checks = 0
    wrote = False

    def check_then_write(candidate: worktree_gc.WorktreeRow) -> str | None:
        nonlocal checks, wrote
        result = original(candidate)
        checks += 1
        if checks == 2:
            # Simulate a writer opening the original path after the last holder check.
            try:
                (wt / "late-work").write_text("unique post-check work\n")
            except FileNotFoundError:
                pass  # quarantine has made the old name unreachable
            else:
                wrote = True
                age(wt)
        return result

    monkeypatch.setattr(worktree_gc, "removal_hold", check_then_write)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    if wrote:
        assert (
            wt.exists() and (wt / "late-work").read_text() == "unique post-check work\n"
        )
    else:
        assert not wt.exists()
    assert checks == 3
    assert "[DEGRADED]" not in capsys.readouterr().err


@pytest.mark.parametrize("change", ["delete", "mode", "symlink", "binary"])
@pytest.mark.parametrize("landed", [False, True])
def test_exact_index_and_working_entries(repo: Path, change: str, landed: bool) -> None:
    wt = lane(repo)
    path = wt / "file"
    if change == "delete":
        path.unlink()
    elif change == "mode":
        path.chmod(0o755)
    elif change == "symlink":
        path.unlink()
        path.symlink_to("binary")
    else:
        path.write_bytes(b"unique binary\x00content\xff")
    git(wt, "add", "file")
    if landed:
        main = repo / "file"
        if change == "delete":
            main.unlink()
        elif change == "mode":
            main.chmod(0o755)
        elif change == "symlink":
            main.unlink()
            main.symlink_to("binary")
        else:
            main.write_bytes(path.read_bytes())
        git(repo, "add", "file")
        git(repo, "commit", "-qm", "land exact entry")
    age(wt)
    assert worktree_gc.dirty_work_on_default(repo, wt) is landed


@pytest.mark.parametrize(
    "change", ["diff", "ignored", "flag", "holder", "remove-error"]
)
def test_quarantine_failure_restores_directory_and_registration(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    change: str,
) -> None:
    wt = lane(repo)
    original = worktree_gc.run
    quarantines = []

    def repair_then_revive(
        cmd: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        result = original(cmd, **kwargs)
        if cmd[:3] == ["git", "worktree", "repair"] and "gc-quarantine-" in cmd[3]:
            q = Path(cmd[3])
            quarantines.append(q)
            if change == "diff":
                (q / "file").write_text("unique after rename\n")
            elif change == "ignored":
                (q / "scratch").mkdir()
                (q / "scratch/research.txt").write_text("unique ignored after rename\n")
            elif change == "flag":
                git(q, "update-index", "--skip-worktree", "file")
            elif change == "holder":
                monkeypatch.setattr(
                    worktree_gc, "live_cwd_holders", lambda: {str(q): [os.getpid()]}
                )
            else:

                def fail_remove(*args: object, **kwargs: object) -> None:
                    raise RuntimeError("injected removal failure")

                monkeypatch.setattr(worktree_gc, "remove_worktree", fail_remove)
            age(q)
        return result

    monkeypatch.setattr(worktree_gc, "run", repair_then_revive)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists() and len(quarantines) == 1 and not quarantines[0].exists()
    assert row(repo, wt).path == wt
    assert "[DEGRADED]" in capsys.readouterr().err
    if change == "diff":
        assert (wt / "file").read_text() == "unique after rename\n"
    elif change == "ignored":
        assert (
            wt / "scratch/research.txt"
        ).read_text() == "unique ignored after rename\n"


@pytest.mark.parametrize("hidden", ["ignored", "--assume-unchanged", "--skip-worktree"])
def test_hidden_only_work_never_qualifies_as_clean(
    repo: Path, monkeypatch: pytest.MonkeyPatch, hidden: str
) -> None:
    wt = repo.parent / "lane"
    git(repo, "worktree", "add", "-q", "--detach", str(wt), "main")
    if hidden == "ignored":
        (wt / "scratch").mkdir()
        (wt / "scratch/research.txt").write_text("hidden unique work\n")
    else:
        git(wt, "update-index", hidden, "file")
        (wt / "file").write_text("hidden unique work\n")
    age(wt)
    before = snapshot(repo, wt)
    assert row(repo, wt).classify() == "stale-dirty"
    assert run(monkeypatch, repo, "apply") == 0
    assert snapshot(repo, wt) == before


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_raw_blob_hash_matches_git(tmp_path: Path, object_format: str) -> None:
    git(tmp_path, "init", "-q", "--object-format=" + object_format)
    path = tmp_path / "raw"
    path.write_bytes(b"raw\x00binary\xff\n")
    expected = git(tmp_path, "hash-object", "raw")
    assert worktree_gc._working_entry(tmp_path, "raw", object_format) == (
        "100644",
        expected,
    )


def test_unstaged_landed_edit_with_ancestral_index_is_durable(repo: Path) -> None:
    wt = lane(repo)
    git(wt, "reset", "-q", "HEAD", "--", "file")
    assert worktree_gc.dirty_work_on_default(repo, wt)


@pytest.mark.parametrize(
    "state",
    [
        "rebase-merge",
        "rebase-apply",
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "sequencer",
        "BISECT_LOG",
        "MERGE_AUTOSTASH",
        "REBASE_AUTOSTASH",
        "refs/autostash",
        "refs/worktree/autostash",
    ],
)
def test_unfinished_git_operation_holds_all_gc_routes(
    repo: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    head = git(wt, "rev-parse", "HEAD")
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    if state.startswith("refs/"):
        git(wt, "update-ref", state, head)
    elif state in ("rebase-merge", "rebase-apply", "sequencer"):
        (admin / state).mkdir()
    else:
        (admin / state).write_text(head + "\n")
    age(wt)
    before = snapshot(repo, wt)
    audited = row(repo, wt)
    assert audited.classify() == "HOLD", state
    assert audited.hold_reason and state in audited.hold_reason
    assert not worktree_gc.dirty_work_on_default(repo, wt)
    assert worktree_gc.removal_hold(candidate)
    result = worktree_gc.archive_worktree(candidate)
    assert not result.ok and state in result.reason
    with pytest.raises(RuntimeError, match="unfinished Git operation"):
        worktree_gc.remove_worktree(repo, wt)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert snapshot(repo, wt) == before
    assert not git(repo, "for-each-ref", "refs/wt-archive")


def test_rebase_autostash_holds_unique_work_outside_head_and_index(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo, untracked=False)
    path = wt / "file"
    landed = path.read_bytes()
    path.write_text("unique autostashed research\n")
    autostash = git(wt, "stash", "create")
    assert autostash and git(wt, "show", f"{autostash}:file") == (
        "unique autostashed research"
    )
    path.write_bytes(landed)
    state = Path(git(wt, "rev-parse", "--absolute-git-dir")) / "rebase-merge"
    state.mkdir()
    (state / "autostash").write_text(autostash + "\n")
    age(wt)
    assert git(wt, "rev-parse", "HEAD") == git(repo, "rev-parse", "main^")
    before = snapshot(repo, wt)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists() and snapshot(repo, wt) == before
    assert (state / "autostash").read_text().strip() == autostash
    assert not git(repo, "for-each-ref", "refs/wt-archive")


@pytest.mark.parametrize("partial", [False, True])
def test_untracked_manifest_coverage_cannot_trust_capture_list(
    repo: Path, monkeypatch: pytest.MonkeyPatch, partial: bool
) -> None:
    wt = lane(repo)
    path = wt / "notes/new file\n[1].md"
    wanted = path.read_bytes()
    if partial:
        (wt / "survivor").write_bytes(b"other archived work\n")
    age(wt)
    candidate = row(repo, wt)
    original_run = worktree_gc.run
    original_cache = worktree_gc._archive_ignored_cache
    omitted = []

    def enumerate_without_payload(
        cmd: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if cmd == ["git", "ls-files", "--others", "--exclude-standard", "-z"]:
            path.unlink()
            omitted.append(path)
        return original_run(cmd, **kwargs)

    def restore_after_capture(source: Path, dest: Path) -> tuple[int, int]:
        result = original_cache(source, dest)
        path.write_bytes(wanted)
        age(source)
        return result

    monkeypatch.setattr(worktree_gc, "run", enumerate_without_payload)
    monkeypatch.setattr(worktree_gc, "_archive_ignored_cache", restore_after_capture)
    result = worktree_gc.archive_worktree(candidate)
    assert omitted == [path] and path.read_bytes() == wanted
    manifest = json.loads((result.dir / "content-manifest.json").read_text())
    assert worktree_gc._content_manifest(wt) == manifest
    assert not result.ok and "coverage" in result.reason
    assert not git(repo, "for-each-ref", "refs/wt-archive")
    assert wt.exists()


@pytest.mark.parametrize(
    "phase, change",
    [
        ("settle", "fresh"),
        ("settle", "cwd-original"),
        ("settle", "cwd-quarantine"),
        ("settle", "mapped-original"),
        ("settle", "mapped-quarantine"),
        ("settle", "unknown-cwd"),
        ("settle", "unknown-mapped"),
        ("settle", "pid-lock"),
        ("proof", "fresh"),
        ("proof", "cwd-quarantine"),
        ("proof", "mapped-original"),
        ("proof", "pid-lock"),
    ],
)
def test_final_quarantine_freshness_and_liveness_are_rechecked(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    change: str,
) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    archive = worktree_gc.archive_worktree(candidate)
    assert archive.ok, archive.reason
    wanted = (wt / "file").read_bytes()
    original_proof = worktree_gc.dirty_work_on_default
    proofs = 0
    changed = []

    def revive(quarantine: Path) -> None:
        changed.append(quarantine)
        if change == "fresh":
            (quarantine / "file").write_bytes(wanted)
        elif change == "pid-lock":
            git(
                repo,
                "worktree",
                "lock",
                "--reason",
                f"pid {os.getpid()}",
                str(quarantine),
            )
        else:
            scanner = (
                "live_mapped_holders" if "mapped" in change else "live_cwd_holders"
            )
            held_path = wt if change.endswith("original") else quarantine
            holders = (
                {} if change.startswith("unknown") else {str(held_path): [os.getpid()]}
            )
            monkeypatch.setattr(worktree_gc, scanner, lambda: holders)

    def settle(_seconds: float) -> None:
        if phase == "settle":
            quarantine = next(wt.parent.glob("gc-quarantine-*"))
            revive(quarantine)

    def proof_then_revive(root: Path, tree: Path, **kwargs: object) -> bool:
        nonlocal proofs
        result = original_proof(root, tree, **kwargs)
        proofs += 1
        if phase == "proof" and proofs == 2:
            revive(tree)
        return result

    monkeypatch.setattr(worktree_gc.time, "sleep", settle)
    monkeypatch.setattr(worktree_gc, "dirty_work_on_default", proof_then_revive)
    assert not worktree_gc.remove_landed_from_quarantine(candidate, 24, archive.dir)
    assert len(changed) == 1 and proofs == 2
    assert wt.exists() and (wt / "file").read_bytes() == wanted
    assert wt in {p for p, _, _ in worktree_gc.parse_worktrees(repo)}
    assert not list(wt.parent.glob("gc-quarantine-*"))
