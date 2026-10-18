"""The removal inventory: unique content must be landed, durable, or held."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest
import worktree_gc
from test_worktree_gc_landed import age, git, lane, row, run
from test_worktree_gc_landed import repo as repo_fixture


@pytest.fixture
def repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Path:
    return repo_fixture.__wrapped__(tmp_path, monkeypatch, request)


def unique_commit(wt: Path) -> str:
    tree = git(wt, "rev-parse", "HEAD^{tree}")
    return git(wt, "commit-tree", tree, "-p", "HEAD", "-m", "unique snapshot")


@pytest.mark.parametrize("namespace", ["worktree", "bisect", "rewritten"])
@pytest.mark.parametrize("kind", ["unique-commit", "blob"])
def test_local_ref_unique_objects_hold_all_routes(
    repo: Path, monkeypatch: pytest.MonkeyPatch, namespace: str, kind: str
) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    ref = f"refs/{namespace}/snapshot"
    oid = (
        unique_commit(wt)
        if kind == "unique-commit"
        else git(wt, "rev-parse", "HEAD:file")
    )
    git(wt, "update-ref", ref, oid)
    age(wt)
    assert row(repo, wt).classify() == "HOLD"
    assert not worktree_gc.dirty_work_on_default(repo, wt)
    assert worktree_gc.removal_hold(candidate)
    result = worktree_gc.archive_worktree(candidate)
    assert not result.ok and ref in result.reason
    with pytest.raises(RuntimeError):
        worktree_gc.remove_worktree(repo, wt)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists() and git(wt, "rev-parse", ref) == oid


@pytest.mark.parametrize("namespace", ["worktree", "bisect", "rewritten"])
def test_landed_local_ref_is_bound_in_manifest_and_archived(
    repo: Path, monkeypatch: pytest.MonkeyPatch, namespace: str
) -> None:
    wt = lane(repo)
    ref = f"refs/{namespace}/snapshot"
    sha = git(repo, "rev-parse", "main")
    git(wt, "update-ref", ref, sha)
    age(wt)
    candidate = row(repo, wt)
    assert candidate.classify() == "landed", candidate.hold_reason
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert not wt.exists()
    dest = next(worktree_gc.ARCHIVE_ROOT.glob("**/head.txt")).parent
    manifest = json.loads((dest / "content-manifest.json").read_text())
    assert manifest[".git/local-refs"]["refs"][ref] == sha


def test_staged_then_overwritten_blob_holds_automatic_removal(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    head_bytes = (wt / "file").read_bytes()
    (wt / "file").write_text("unique staged version A\n")
    git(wt, "add", "file")
    (wt / "file").write_bytes(head_bytes)
    age(wt)
    assert not worktree_gc.dirty_work_on_default(repo, wt)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists() and git(wt, "show", ":file") == "unique staged version A"


def test_explicit_archive_index_blobs_restore_after_prune(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo, untracked=False)
    working = (wt / "file").read_bytes()
    (wt / "file").write_text("unique staged version A\n")
    git(wt, "add", "file")
    oid = git(wt, "rev-parse", ":file")
    (wt / "file").write_bytes(working)
    assert worktree_gc.explicit_archive(wt) == 0
    dest = next(worktree_gc.ARCHIVE_ROOT.glob("**/head.txt")).parent
    git(repo, "reflog", "expire", "--expire=now", "--expire-unreachable=now", "--all")
    git(repo, "gc", "--prune=now")
    assert git(repo, "cat-file", "blob", oid) == "unique staged version A"
    index_ref = (dest / "index-ref.txt").read_text().strip()
    assert index_ref.startswith("refs/wt-archive/")
    assert git(repo, "show", f"{index_ref}:file") == "unique staged version A"
    restore = repo.parent / "restored-index"
    git(
        repo,
        "worktree",
        "add",
        "--detach",
        str(restore),
        (dest / "head.txt").read_text().strip(),
    )
    git(restore, "apply", str(dest / "tracked.patch"))
    shutil.copyfile(
        dest / "git-index",
        Path(git(restore, "rev-parse", "--absolute-git-dir")) / "index",
    )
    assert git(restore, "show", ":file") == "unique staged version A"
    assert (restore / "file").read_bytes() == working


@pytest.mark.parametrize("side", ["old", "new"])
def test_unique_per_worktree_reflog_object_holds(repo: Path, side: str) -> None:
    wt = lane(repo)
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    head, unique = git(wt, "rev-parse", "HEAD"), unique_commit(wt)
    old, new = (unique, head) if side == "old" else (head, unique)
    with (admin / "logs/HEAD").open("a") as log:
        log.write(f"{old} {new} test <t@t.t> 1 +0000\tunique lost history\n")
    assert row(repo, wt).classify() == "HOLD"
    assert not worktree_gc.archive_worktree(row(repo, wt)).ok


@pytest.mark.parametrize(
    "state",
    [
        "config.worktree",
        "info/sparse-checkout",
        "ORIG_HEAD",
        "FETCH_HEAD",
        "AUTO_MERGE",
        "REBASE_HEAD",
        "MERGE_RR",
        "COMMIT_EDITMSG",
        "unknown-state",
        "sharedindex.unique",
        "objects/unique",
        "index.lock",
    ],
)
def test_uncovered_admin_state_holds_all_routes(repo: Path, state: str) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    path = Path(git(wt, "rev-parse", "--absolute-git-dir")) / state
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("unique administrative state\n")
    assert row(repo, wt).classify() == "HOLD"
    assert worktree_gc.removal_hold(candidate)
    assert not worktree_gc.archive_worktree(candidate).ok
    with pytest.raises(RuntimeError):
        worktree_gc.remove_worktree(repo, wt)


@pytest.mark.parametrize(
    "state", ["stash", "lfs", "lfs-storage", "lfs-format", "replace", "grafts"]
)
def test_shared_state_without_worktree_provenance_holds(repo: Path, state: str) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    assert candidate.classify() == "landed"
    if state == "stash":
        (wt / "file").write_text("unique stash\n")
        git(wt, "stash", "push", "-m", "from this worktree")
    elif state == "lfs":
        path = repo / ".git/lfs/objects/unique"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"unique LFS bytes")
    elif state == "lfs-storage":
        git(wt, "config", "lfs.storage", str(repo.parent / "external-lfs"))
    elif state == "lfs-format":
        git(wt, "config", "lfs.repositoryformatversion", "1")
    elif state == "replace":
        git(wt, "replace", "HEAD", unique_commit(wt))
    else:
        (repo / ".git/info/grafts").write_text(git(wt, "rev-parse", "HEAD") + "\n")
    assert row(repo, wt).classify() == "HOLD"
    if state == "replace":
        assert "proof-altering refs: refs/replace/" in row(repo, wt).hold_reason
        assert "proof-altering refs: refs/replace/" in worktree_gc.removal_hold(
            candidate
        )
    assert not worktree_gc.archive_worktree(row(repo, wt)).ok


def test_codex_no_environment_marker_is_preserved_in_archive(repo: Path) -> None:
    wt = lane(repo)
    git(repo, "config", "extensions.worktreeConfig", "true")
    git(wt, "config", "--worktree", "codex.localEnvironmentConfigPath", "__none__")
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    config_bytes = (admin / "config.worktree").read_bytes()
    candidate = row(repo, wt)
    assert candidate.classify() == "landed", candidate.hold_reason
    result = worktree_gc.archive_worktree(candidate)
    assert result.ok, result.reason
    with tarfile.open(result.dir / "git-state.tgz", "r:gz") as archive:
        assert archive.extractfile(".git/config.worktree").read() == config_bytes


@pytest.mark.parametrize("value", ["", "/tmp/environment.toml", "unknown"])
def test_other_codex_environment_values_still_hold(repo: Path, value: str) -> None:
    wt = lane(repo)
    git(repo, "config", "extensions.worktreeConfig", "true")
    git(wt, "config", "--worktree", "codex.localEnvironmentConfigPath", value)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert not worktree_gc.archive_worktree(candidate).ok


def test_shared_lfs_lock_metadata_survives_landed_removal(repo: Path) -> None:
    wt = lane(repo)
    git(repo, "config", "lfs.repositoryformatversion", "0")
    (repo / ".git/lfs/objects/aa/bb").mkdir(parents=True)
    marker = repo / ".git/lfs/cache/locks/refs/heads/main/verifiable"
    marker.parent.mkdir(parents=True)
    marker.write_bytes(b"false")
    assert row(repo, wt).classify() == "landed"
    assert worktree_gc.explicit_archive(wt) == 0
    assert not wt.exists()
    assert marker.read_bytes() == b"false"


def test_shared_lfs_metadata_symlink_into_candidate_still_holds(repo: Path) -> None:
    wt = lane(repo)
    private = wt / "private-lfs"
    private.mkdir()
    (repo / ".git/lfs").symlink_to(private, target_is_directory=True)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert not worktree_gc.archive_worktree(candidate).ok
    assert private.exists()


def test_explicit_archive_leaves_unreadable_peer_index_untouched(repo: Path) -> None:
    wt = lane(repo)
    peer = repo.parent / "unrelated-peer"
    git(repo, "worktree", "add", "-q", "--detach", str(peer), "main")
    peer_index = Path(git(peer, "rev-parse", "--absolute-git-dir")) / "index"
    peer_index.write_bytes(b"unreadable peer index, preserve exactly")
    assert worktree_gc.explicit_archive(wt) == 0
    assert not wt.exists() and peer.exists()
    assert peer_index.read_bytes() == b"unreadable peer index, preserve exactly"


def test_empty_uv_sdist_marker_is_preserved_without_claiming_nested_git(
    repo: Path,
) -> None:
    wt = lane(repo)
    marker = wt / ".uv-cache/sdists-v9/.git"
    marker.parent.mkdir(parents=True)
    marker.write_bytes(b"")
    result = worktree_gc.archive_worktree(row(repo, wt))
    assert result.ok, result.reason
    with tarfile.open(result.dir / "ignored.tgz", "r:gz") as archive:
        assert archive.extractfile(".uv-cache/sdists-v9/.git").read() == b""


def test_session_uuid_marker_requires_archive_and_is_preserved(repo: Path) -> None:
    wt = lane(repo)
    with (repo / ".git/info/exclude").open("a") as stream:
        stream.write("\n.claude/current-session-id\n")
    marker = wt / ".claude/current-session-id"
    session_bytes = b"01a14089-94a2-76d3-b203-9389b01af78e\n"
    marker.write_bytes(session_bytes)
    assert row(repo, wt).classify() == "landed"
    with pytest.raises(RuntimeError):
        worktree_gc.remove_worktree(repo, wt)
    assert marker.read_bytes() == session_bytes
    assert worktree_gc.explicit_archive(wt) == 0
    assert not wt.exists()
    destination = next(worktree_gc.ARCHIVE_ROOT.glob("**/head.txt")).parent
    with tarfile.open(destination / "ignored.tgz", "r:gz") as archive:
        assert archive.extractfile(".claude/current-session-id").read() == session_bytes


@pytest.mark.parametrize("kind", ["text", "directory", "symlink"])
def test_session_marker_with_unknown_content_remains_unproven(
    repo: Path, kind: str
) -> None:
    wt = lane(repo)
    with (repo / ".git/info/exclude").open("a") as stream:
        stream.write("\n.claude/current-session-id\n")
    marker = wt / ".claude/current-session-id"
    if kind == "directory":
        marker.mkdir()
        (marker / "new-source.py").write_text("unique work\n")
    elif kind == "symlink":
        target = repo.parent / "external-session"
        target.write_text("01a14089-94a2-76d3-b203-9389b01af78e\n")
        marker.symlink_to(target)
    else:
        marker.write_text("unique work, not a generated UUID\n")
    assert not worktree_gc.dirty_work_on_default(repo, wt)
    assert row(repo, wt).classify() != "landed"
    assert marker.exists()


@pytest.mark.parametrize("kind", ["nonempty", "directory", "symlink"])
def test_uv_sdist_git_state_other_than_empty_regular_marker_holds(
    repo: Path, kind: str
) -> None:
    wt = lane(repo)
    marker = wt / ".uv-cache/sdists-v9/.git"
    marker.parent.mkdir(parents=True)
    if kind == "directory":
        marker.mkdir()
    elif kind == "symlink":
        target = repo.parent / "external-marker"
        target.write_bytes(b"")
        marker.symlink_to(target)
    else:
        marker.write_bytes(b"gitdir: /tmp/external-repository\n")
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert not worktree_gc.archive_worktree(candidate).ok


@pytest.mark.parametrize("dirty", [False, True])
@pytest.mark.parametrize("packed", [False, True])
def test_shared_notes_do_not_change_landed_or_safe_class(
    repo: Path, dirty: bool, packed: bool
) -> None:
    if dirty:
        wt = lane(repo)
    else:
        wt = repo.parent / "clean-lane"
        git(repo, "worktree", "add", "-q", "--detach", str(wt), "main")
        age(wt)
    expected = "landed" if dirty else "SAFE"
    assert row(repo, wt).classify() == expected
    git(repo, "notes", "--ref=stage-currency", "add", "-m", "semantic ledger", "HEAD")
    notes = git(repo, "rev-parse", "refs/notes/stage-currency")
    if packed:
        git(repo, "pack-refs", "--all")
        assert not (repo / ".git/refs/notes/stage-currency").exists()
    candidate = row(repo, wt)
    assert candidate.classify() == expected, candidate.hold_reason
    assert worktree_gc.removal_hold(candidate) is None
    assert git(repo, "rev-parse", "refs/notes/stage-currency") == notes


@pytest.mark.parametrize("component", ["unique", "notes", "refs"])
@pytest.mark.parametrize("storage", ["candidate", "external"])
def test_symlinked_notes_storage_holds_and_survives_removal(
    repo: Path, monkeypatch: pytest.MonkeyPatch, component: str, storage: str
) -> None:
    wt = lane(repo)
    git(repo, "notes", "--ref=unique", "add", "-m", "unique ledger", "HEAD")
    notes = git(repo, "rev-parse", "refs/notes/unique")
    ref_path = repo / ".git/refs/notes/unique"
    path = {
        "unique": ref_path,
        "notes": ref_path.parent,
        "refs": ref_path.parent.parent,
    }[component]
    target = (wt / ".venv" if storage == "candidate" else repo.parent / "external") / (
        "ref-target"
    )
    target.parent.mkdir()
    path.rename(target)
    path.symlink_to(target, target_is_directory=component != "unique")
    assert git(repo, "notes", "--ref=unique", "show", "HEAD") == "unique ledger"
    age(wt)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD", candidate.hold_reason
    assert "notes" in candidate.hold_reason
    assert worktree_gc.removal_hold(candidate)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists() and target.exists()
    assert git(repo, "rev-parse", "refs/notes/unique") == notes
    assert git(repo, "notes", "--ref=unique", "show", "HEAD") == "unique ledger"


@pytest.mark.parametrize("storage", ["candidate", "external"])
def test_symlinked_packed_notes_hold_and_survive_removal(
    repo: Path, monkeypatch: pytest.MonkeyPatch, storage: str
) -> None:
    annotated = git(repo, "rev-parse", "HEAD")
    git(repo, "notes", "--ref=unique", "add", "-m", "packed ledger", annotated)
    notes = git(repo, "rev-parse", "refs/notes/unique")
    git(repo, "pack-refs", "--all")
    packed = repo / ".git/packed-refs"
    assert not (repo / ".git/refs/notes/unique").exists()
    assert f"{notes} refs/notes/unique" in packed.read_text()
    target = (repo if storage == "candidate" else repo.parent) / "packed-note-roots"
    target.write_bytes(packed.read_bytes())
    if storage == "candidate":
        git(repo, "add", "packed-note-roots")
        git(repo, "commit", "-qm", "track packed note storage")
    wt = repo.parent / "clean-lane"
    git(repo, "worktree", "add", "-q", "--detach", str(wt), "main")
    age(wt)
    before = row(repo, wt)
    assert before.classify() == "SAFE", before.hold_reason
    if storage == "candidate":
        target = wt / target.name
    packed.unlink()
    packed.symlink_to(target)
    assert git(wt, "status", "--porcelain") == ""
    assert git(repo, "notes", "--ref=unique", "show", annotated) == "packed ledger"

    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD", candidate.hold_reason
    assert "packed-refs" in candidate.hold_reason
    assert worktree_gc.removal_hold(before)
    with pytest.raises(RuntimeError, match="undurable"):
        worktree_gc.remove_worktree(repo, wt)
    assert run(monkeypatch, repo, "apply") == 0
    assert wt.exists() and target.exists()
    assert not (repo / ".git/refs/notes/unique").exists()
    assert git(repo, "rev-parse", "refs/notes/unique") == notes
    assert git(repo, "notes", "--ref=unique", "show", annotated) == "packed ledger"


@pytest.mark.parametrize(
    "relative",
    [
        "refs/stash",
        "logs/refs/stash",
        "logs/refs",
        "logs",
        "logs/refs/heads",
        "logs/refs/heads/main",
    ],
)
@pytest.mark.parametrize("storage", ["candidate", "external"])
def test_symlinked_stash_storage_holds_and_survives_removal(
    repo: Path, monkeypatch: pytest.MonkeyPatch, relative: str, storage: str
) -> None:
    for message in ("older peer work", "latest peer work"):
        (repo / "file").write_text(message + "\n")
        git(repo, "stash", "push", "-m", message)
    stashes = git(repo, "stash", "list", "--format=%H").splitlines()
    assert len(stashes) == 2
    log = repo / ".git/logs/refs/stash"
    original_log = log.read_bytes()
    path = repo / ".git" / relative
    directory = path.is_dir()
    target = (repo if storage == "candidate" else repo.parent) / "shared-ref-storage"
    if directory:
        shutil.copytree(path, target)
    else:
        shutil.copyfile(path, target)
    if storage == "candidate":
        git(repo, "add", "shared-ref-storage")
        git(repo, "commit", "-qm", "track shared ref storage")
    wt = repo.parent / "clean-lane"
    git(repo, "worktree", "add", "-q", "--detach", str(wt), "main")
    age(wt)
    before = row(repo, wt)
    assert before.classify() == "SAFE", before.hold_reason
    if storage == "candidate":
        target = wt / target.name
    if directory:
        shutil.rmtree(path)
    else:
        path.unlink()
    path.symlink_to(target, target_is_directory=directory)
    assert git(wt, "status", "--porcelain") == ""
    assert log.read_bytes() == original_log
    assert git(repo, "stash", "list", "--format=%H").splitlines() == stashes

    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD", candidate.hold_reason
    assert relative in candidate.hold_reason
    assert worktree_gc.removal_hold(before)
    with pytest.raises(RuntimeError, match="undurable"):
        worktree_gc.remove_worktree(repo, wt)
    assert run(monkeypatch, repo, "apply") == 0
    assert wt.exists() and target.exists()
    assert log.read_bytes() == original_log
    assert git(repo, "stash", "list", "--format=%H").splitlines() == stashes
    assert git(repo, "show", f"{stashes[-1]}:file") == "older peer work"
    assert git(repo, "show", f"{stashes[0]}:file") == "latest peer work"


@pytest.mark.parametrize("peer_checkout", ["main", "linked"])
@pytest.mark.parametrize("stash_args", [(), ("-m", "peer checkpoint")])
def test_stash_attributed_to_other_branch_does_not_hold(
    repo: Path, stash_args: tuple[str, ...], peer_checkout: str
) -> None:
    wt = lane(repo)
    # Exact branch attribution: "main" is a substring of this lane's branch.
    git(wt, "switch", "-c", "main-topic")
    expected = row(repo, wt).classify()
    assert expected == "landed"
    peer = repo
    if peer_checkout == "linked":
        peer = repo.parent / "peer"
        git(repo, "worktree", "add", "-q", "-b", "peer", str(peer), "main")
    (peer / "file").write_text("peer's unique stash\n")
    git(peer, "stash", "push", *stash_args)
    stash = git(repo, "rev-parse", "refs/stash")
    candidate = row(repo, wt)
    assert candidate.classify() == expected, candidate.hold_reason
    assert worktree_gc.removal_hold(candidate) is None
    assert git(repo, "rev-parse", "refs/stash") == stash


@pytest.mark.parametrize("state", ["rename", "detach", "switch", "detached-stash"])
def test_stash_without_current_peer_checkout_holds(repo: Path, state: str) -> None:
    wt = repo.parent / "topic"
    git(repo, "worktree", "add", "-q", "-b", "topic", str(wt), "main")
    if state == "detached-stash":
        git(wt, "switch", "--detach")
    (wt / "file").write_text("candidate's unfinished work\n")
    git(wt, "stash", "push")
    stash = git(repo, "rev-parse", "refs/stash")
    if state == "rename":
        git(wt, "branch", "-m", "topic-renamed")
    elif state == "detach":
        git(wt, "switch", "--detach")
    elif state == "switch":
        git(wt, "switch", "-c", "other")
    age(wt)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD", candidate.hold_reason
    assert "stash" in candidate.hold_reason
    assert worktree_gc.removal_hold(candidate)
    assert git(repo, "rev-parse", "refs/stash") == stash


@pytest.mark.parametrize("peer_state", ["missing", "different-repository"])
def test_stash_registered_without_live_peer_checkout_holds(
    repo: Path, peer_state: str
) -> None:
    wt = lane(repo)
    peer = repo.parent / "peer"
    git(repo, "worktree", "add", "-q", "-b", "peer", str(peer), "main")
    (peer / "file").write_text("peer's unique stash\n")
    git(peer, "stash", "push", "-m", "peer checkpoint")
    shutil.rmtree(peer)
    if peer_state == "different-repository":
        peer.mkdir()
        git(peer, "init", "-q", "-b", "peer")
        git(peer, "config", "user.email", "test@example.com")
        git(peer, "config", "user.name", "test")
        git(peer, "commit", "--allow-empty", "-qm", "unrelated repository")
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD", candidate.hold_reason
    assert "stash" in candidate.hold_reason
    assert worktree_gc.removal_hold(candidate)


@pytest.mark.parametrize("own_stash_latest", [False, True])
def test_stash_attributed_to_this_branch_holds_all_entries(
    repo: Path, own_stash_latest: bool
) -> None:
    wt = lane(repo)
    git(wt, "switch", "-c", "topic")

    def own_stash() -> None:
        git(wt, "stash", "push", "-m", "own checkpoint")

    def peer_stash() -> None:
        (repo / "file").write_text("peer's unique stash\n")
        git(repo, "stash", "push", "-m", "peer checkpoint")

    for stash in (
        (peer_stash, own_stash) if own_stash_latest else (own_stash, peer_stash)
    ):
        stash()
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert "stash" in candidate.hold_reason
    assert worktree_gc.removal_hold(candidate)
    assert not worktree_gc.dirty_work_on_default(repo, wt)


def test_unattributable_stash_holds(repo: Path) -> None:
    wt = lane(repo)
    stash = git(wt, "stash", "create")
    git(repo, "stash", "store", "-m", "checkpoint without a branch", stash)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert "unattributed stash" in candidate.hold_reason
    assert worktree_gc.removal_hold(candidate)
    assert not worktree_gc.dirty_work_on_default(repo, wt)


@pytest.mark.parametrize(
    "state",
    ["missing-log", "orphan-log", "malformed-log", "tip-mismatch", "old-only-root"],
)
def test_incomplete_stash_attribution_holds(repo: Path, state: str) -> None:
    wt = lane(repo)
    (repo / "file").write_text("peer's unique stash\n")
    git(repo, "stash", "push", "-m", "peer checkpoint")
    log = repo / ".git/logs/refs/stash"
    if state == "missing-log":
        log.unlink()
    elif state == "orphan-log":
        # Keep the reflog evidence which update-ref -d would remove.
        (repo / ".git/refs/stash").unlink()
    elif state == "malformed-log":
        log.write_bytes(b"unreadable stash reflog\n")
    elif state == "tip-mismatch":
        (repo / ".git/refs/stash").write_text(git(repo, "rev-parse", "HEAD") + "\n")
    else:
        _, rest = log.read_bytes().split(b" ", 1)
        log.write_bytes(git(repo, "rev-parse", "HEAD").encode() + b" " + rest)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert "unattributed stash" in candidate.hold_reason
    assert worktree_gc.removal_hold(candidate)


@pytest.mark.parametrize(
    "field, value",
    [
        ("old", b"BROKEN"),
        ("new", b"BROKEN"),
        ("committer", b"BROKEN"),
        ("committer", b"test"),
        ("committer", b"test <>"),
        ("committer", b" <test@example.com>"),
        ("timestamp", b"BROKEN"),
        ("timezone", b"BROKEN"),
        ("timezone", b"+2460"),
        ("separator", b" "),
    ],
)
def test_malformed_stash_reflog_holds(repo: Path, field: str, value: bytes) -> None:
    wt = lane(repo)
    (repo / "file").write_text("peer's unique stash\n")
    git(repo, "stash", "push", "-m", "peer checkpoint")
    log = repo / ".git/logs/refs/stash"
    header, message = log.read_bytes().rstrip(b"\n").split(b"\t", 1)
    old, new, identity = header.split(b" ", 2)
    committer, timestamp, timezone = identity.rsplit(b" ", 2)
    fields = {
        "old": old,
        "new": new,
        "committer": committer,
        "timestamp": timestamp,
        "timezone": timezone,
        "separator": b"\t",
    }
    fields[field] = value
    log.write_bytes(
        b" ".join(
            fields[name]
            for name in ("old", "new", "committer", "timestamp", "timezone")
        )
        + fields["separator"]
        + message
        + b"\n"
    )
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD", candidate.hold_reason
    assert "unattributed stash" in candidate.hold_reason
    assert worktree_gc.removal_hold(candidate)


@pytest.mark.parametrize("location", ["nested", ".venv/nested"])
def test_nested_repository_is_held_even_in_ignored_cache(
    repo: Path, location: str
) -> None:
    wt = lane(repo)
    nested = wt / location
    nested.mkdir(parents=True)
    git(nested, "init", "-q")
    assert row(repo, wt).classify() == "HOLD"
    assert not worktree_gc.archive_worktree(row(repo, wt)).ok


def test_archive_preserves_all_ignored_content_and_reflog_bytes(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    for rel in (".venv/unique", ".claude/cache/index-trees/unique", "scratch/unique"):
        path = wt / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"unique ignored bytes")
    (wt / "scratch/empty").mkdir()
    (wt / "scratch/link").symlink_to("unique")
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    log = (admin / "logs/HEAD").read_bytes()
    assert worktree_gc.explicit_archive(wt) == 0
    assert not wt.exists()
    dest = next(worktree_gc.ARCHIVE_ROOT.glob("**/head.txt")).parent
    with tarfile.open(dest / "ignored.tgz") as archive:
        assert archive.extractfile(".venv/unique").read() == b"unique ignored bytes"
        assert archive.extractfile("scratch/unique").read() == b"unique ignored bytes"
        assert archive.getmember("scratch/empty").isdir()
        assert archive.getmember("scratch/link").linkname == "unique"
    with tarfile.open(dest / "git-state.tgz") as archive:
        assert archive.extractfile(".git/logs/HEAD").read() == log


@pytest.mark.parametrize("land_descendant", [True, False])
def test_file_to_directory_replacement_checks_descendants(
    repo: Path, monkeypatch: pytest.MonkeyPatch, land_descendant: bool
) -> None:
    wt = lane(repo)
    for root in (wt, repo):
        (root / "file").unlink()
        (root / "file").mkdir()
        (root / "file/child").write_text("replacement\n")
        git(root, "add", "file")
    git(repo, "commit", "-qm", "file becomes directory")
    if not land_descendant:
        (wt / "file/extra").write_text("unique descendant\n")
    age(wt)
    assert worktree_gc.dirty_work_on_default(repo, wt) is land_descendant
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists() is not land_descendant


@pytest.mark.parametrize("branched", [True, False])
def test_resolved_head_movement_after_last_proof_aborts(
    repo: Path, monkeypatch: pytest.MonkeyPatch, branched: bool
) -> None:
    wt = lane(repo)
    if branched:
        git(wt, "switch", "-q", "-c", "lane-branch")
    age(wt)
    original = worktree_gc.remove_worktree
    moved = git(repo, "rev-parse", "main")

    def move_then_remove(
        root: Path, path: Path, *args: object, **kwargs: object
    ) -> None:
        # Move to an ancestor of default, so even conservative ancestry guards
        # cannot replace the exact-SHA comparison. Files and index stay untouched.
        log = Path(git(path, "rev-parse", "--absolute-git-dir")) / "logs/HEAD"
        raw_log = log.read_bytes()
        git(path, "update-ref", "HEAD", moved)
        # Symbolic HEAD's literal bytes, index and logs provide no SHA evidence.
        log.write_bytes(raw_log)
        original(root, path, *args, **kwargs)

    monkeypatch.setattr(worktree_gc, "remove_worktree", move_then_remove)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists() and git(wt, "rev-parse", "HEAD") == moved
    dest = next(worktree_gc.ARCHIVE_ROOT.glob("**/head.txt")).parent
    manifest = json.loads((dest / "content-manifest.json").read_text())
    head = manifest[".git/resolved-HEAD"]
    assert head["head_sha"] != moved
    assert head["symbolic_ref"] == ("refs/heads/lane-branch" if branched else None)
    assert head["branch_sha"] == (head["head_sha"] if branched else None)


def test_unmerged_index_is_held_by_explicit_archive(repo: Path) -> None:
    wt = lane(repo)
    head_blob = git(wt, "rev-parse", "HEAD:file")
    git(wt, "update-index", "--force-remove", "file")
    subprocess.run(
        ["git", "update-index", "--index-info"],
        cwd=wt,
        input=f"100644 {head_blob} 1\tfile\n".encode(),
        check=True,
    )
    assert not worktree_gc.archive_worktree(row(repo, wt)).ok
    assert wt.exists()


def test_default_apply_holds_unique_ignored_cache(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = repo.parent / "clean-with-cache"
    git(repo, "worktree", "add", "--detach", str(wt), "main")
    (wt / ".venv").mkdir()
    (wt / ".venv/unique").write_bytes(b"unique ignored bytes")
    age(wt)
    assert row(repo, wt).classify() != "SAFE"
    assert run(monkeypatch, repo, "apply") == 0
    assert (wt / ".venv/unique").read_bytes() == b"unique ignored bytes"
    with pytest.raises(RuntimeError, match="unarchived"):
        worktree_gc.remove_worktree(repo, wt, force=False)


def test_missing_checkout_admin_is_never_blanket_pruned(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = repo.parent / "missing"
    git(repo, "worktree", "add", "--detach", str(missing), "main")
    oid = unique_commit(missing)
    git(missing, "update-ref", "refs/worktree/snapshot", oid)
    admin = Path(git(missing, "rev-parse", "--absolute-git-dir"))
    shutil.rmtree(missing)
    wt = lane(repo)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert not wt.exists() and admin.exists()
    assert (admin / "refs/worktree/snapshot").read_text().strip() == oid


@pytest.mark.parametrize(
    "state", ["intent-to-add", "split-index", "alternates", "lfs-index", "fifo"]
)
def test_unrestorable_object_state_holds(repo: Path, state: str) -> None:
    wt = lane(repo)
    if state == "intent-to-add":
        (wt / "new").write_text("unique new\n")
        git(wt, "add", "-N", "new")
    elif state == "split-index":
        git(wt, "update-index", "--split-index")
    elif state == "alternates":
        (repo / ".git/objects/info/alternates").write_text(
            str(repo.parent / "borrowed") + "\n"
        )
    elif state == "lfs-index":
        working = (wt / "file").read_bytes()
        (wt / "file").write_text(
            "version https://git-lfs.github.com/spec/v1\noid sha256:"
            + "1" * 64
            + "\nsize 1\n"
        )
        git(wt, "add", "file")
        (wt / "file").write_bytes(working)
    else:
        import os

        os.mkfifo(wt / "special")
    result = worktree_gc.archive_worktree(row(repo, wt))
    assert not result.ok and wt.exists(), result.reason


@pytest.mark.parametrize("ref", ["refs/custom/snapshot", "refs/notes/stage-currency"])
def test_shared_ref_objects_survive_landed_removal(
    repo: Path, monkeypatch: pytest.MonkeyPatch, ref: str
) -> None:
    wt = lane(repo)
    if ref.startswith("refs/notes/"):
        git(
            repo,
            "notes",
            "--ref=stage-currency",
            "add",
            "-m",
            "semantic ledger",
            "HEAD",
        )
        oid = git(repo, "rev-parse", ref)
    else:
        oid = unique_commit(wt)
        git(wt, "update-ref", ref, oid)
    age(wt)
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert not wt.exists()
    git(repo, "gc", "--prune=now")
    assert git(repo, "rev-parse", ref) == oid
    assert git(repo, "cat-file", "-t", oid) == "commit"
    if ref.startswith("refs/notes/"):
        assert (
            git(repo, "notes", "--ref=stage-currency", "show", "HEAD")
            == "semantic ledger"
        )


def test_git_storage_override_holds_without_using_redirected_evidence(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(wt / ".venv/objects"))
    result = worktree_gc.archive_worktree(candidate)
    assert not result.ok and "storage override" in result.reason
    assert wt.exists()


@pytest.mark.parametrize(
    "state", ["objects-symlink", "promisor", "admin-symlink", "marker-symlink"]
)
def test_unknown_storage_and_admin_links_hold(repo: Path, state: str) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    if state == "objects-symlink":
        (repo / ".git/objects/linked").symlink_to(wt / "binary")
    elif state == "promisor":
        (repo / ".git/objects/pack/unknown.promisor").write_bytes(b"")
    elif state == "admin-symlink":
        admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
        other = admin.with_name(admin.name + "-moved")
        admin.rename(other)
        admin.symlink_to(other, target_is_directory=True)
    else:
        marker = wt / ".git"
        other = wt / "git-marker"
        marker.rename(other)
        marker.symlink_to(other.name)
    result = worktree_gc.archive_worktree(candidate)
    assert not result.ok and wt.exists()


def test_clean_removal_binds_the_exact_proven_head(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = repo.parent / "clean-head-race"
    git(repo, "worktree", "add", "--detach", str(wt), "main")
    age(wt)
    original = worktree_gc.remove_worktree
    moved = unique_commit(wt)

    def move_then_remove(
        root: Path, path: Path, *args: object, **kwargs: object
    ) -> None:
        git(path, "update-ref", "HEAD", moved)
        original(root, path, *args, **kwargs)

    monkeypatch.setattr(worktree_gc, "remove_worktree", move_then_remove)
    assert run(monkeypatch, repo, "apply") == 0
    assert wt.exists() and git(wt, "rev-parse", "HEAD") == moved
    assert not git(repo, "for-each-ref", "refs/wt-archive")


def test_branch_prune_holds_shared_reflog_and_moved_sha(repo: Path) -> None:
    git(repo, "branch", "branch-to-keep")
    original = git(repo, "rev-parse", "branch-to-keep")
    worktree_gc._prune_branch(repo, "branch-to-keep", original)
    assert git(repo, "rev-parse", "branch-to-keep") == original
    log = repo / ".git/logs/refs/heads/branch-to-keep"
    log.unlink()
    moved = unique_commit(repo)
    git(repo, "config", "core.logAllRefUpdates", "false")
    git(repo, "update-ref", "refs/heads/branch-to-keep", moved)
    worktree_gc._prune_branch(repo, "branch-to-keep", original)
    assert git(repo, "rev-parse", "branch-to-keep") == moved


@pytest.mark.parametrize("name", ["gitdir", "commondir"])
def test_extra_structural_admin_content_holds(repo: Path, name: str) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    path = Path(git(wt, "rev-parse", "--absolute-git-dir")) / name
    path.write_bytes(path.read_bytes() + b"unique non-linkage content\n")
    result = worktree_gc.archive_worktree(candidate)
    assert not result.ok and wt.exists()


def test_resolve_undo_index_blobs_hold_both_routes(repo: Path) -> None:
    wt = lane(repo)
    original = git(wt, "rev-parse", ":file")
    oids = []
    for data in (b"unique conflict side A\n", b"unique conflict side B\n"):
        result = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=wt,
            input=data,
            capture_output=True,
            check=True,
        )
        oids.append(result.stdout.decode().strip())
    records = f"0 {'0' * 40}\tfile\n" + "".join(
        f"100644 {oid} {stage}\tfile\n"
        for stage, oid in enumerate([original, *oids], 1)
    )
    subprocess.run(
        ["git", "update-index", "--index-info"],
        cwd=wt,
        input=records.encode(),
        check=True,
    )
    git(wt, "add", "file")
    assert all(oid in git(wt, "ls-files", "--resolve-undo") for oid in oids)
    assert row(repo, wt).classify() == "HOLD"
    result = worktree_gc.archive_worktree(row(repo, wt))
    assert not result.ok and "index extension" in result.reason


@pytest.mark.parametrize("state", ["unknown-extension", "version4"])
def test_uninventoried_index_layout_holds(repo: Path, state: str) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    if state == "version4":
        git(wt, "update-index", "--index-version=4")
    else:
        path = Path(git(wt, "rev-parse", "--absolute-git-dir")) / "index"
        raw = (
            path.read_bytes()[:-20]
            + b"XTRA"
            + (40).to_bytes(4, "big")
            + unique_commit(wt).encode()
        )
        path.write_bytes(raw + hashlib.sha1(raw).digest())
    result = worktree_gc.archive_worktree(candidate)
    assert not result.ok and (
        "index extension" in result.reason or "index version" in result.reason
    )


def test_noncommit_detached_head_holds_unique_tag_metadata(repo: Path) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    git(wt, "tag", "-a", "temporary-tag", "-m", "unique tag metadata", "HEAD")
    tag = git(wt, "rev-parse", "refs/tags/temporary-tag")
    git(wt, "update-ref", "-d", "refs/tags/temporary-tag")
    (Path(git(wt, "rev-parse", "--absolute-git-dir")) / "HEAD").write_text(tag + "\n")
    result = worktree_gc.archive_worktree(candidate)
    assert not result.ok and wt.exists()


def test_cached_tree_unique_objects_cannot_hide_outside_index(repo: Path) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    index = Path(git(wt, "rev-parse", "--absolute-git-dir")) / "index"
    raw = index.read_bytes()[:-20]
    # Invalidated TREE has no root OID. Replace it by a syntactically valid
    # positive cache pointing at a different tree, while retaining stage entries.
    tree = git(repo, "rev-parse", "main^{tree}")
    index_tree = git(wt, "write-tree")
    raw = index.read_bytes()[:-20]
    raw = raw.replace(bytes.fromhex(index_tree), bytes.fromhex(tree))
    assert tree != index_tree
    index.write_bytes(raw + hashlib.sha1(raw).digest())
    result = worktree_gc.archive_worktree(candidate)
    assert not result.ok and "TREE cache" in result.reason


def test_unknown_admin_added_after_guard_is_held_by_manifest(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    original = worktree_gc._worktree_state_hold

    def add_after_guard(path: Path) -> str | None:
        result = original(path)
        (admin / "future-state").write_bytes(b"unique future state")
        return result

    monkeypatch.setattr(worktree_gc, "_worktree_state_hold", add_after_guard)
    with pytest.raises(RuntimeError, match="administrative state"):
        worktree_gc.archive_worktree(candidate)
    assert (admin / "future-state").read_bytes() == b"unique future state"


def test_saved_index_envelope_cannot_depend_on_live_guard(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wt = lane(repo)
    candidate = row(repo, wt)
    path = Path(git(wt, "rev-parse", "--absolute-git-dir")) / "index"
    original_bytes = path.read_bytes()
    data = original_bytes[:-20] + b"XTRA" + (4).to_bytes(4, "big") + b"root"
    unsupported = data + hashlib.sha1(data).digest()
    original = worktree_gc._worktree_state_hold

    def masked_guard(tree: Path) -> str | None:
        path.write_bytes(original_bytes)
        result = original(tree)
        path.write_bytes(unsupported)
        return result

    monkeypatch.setattr(worktree_gc, "_worktree_state_hold", masked_guard)
    result = worktree_gc.archive_worktree(candidate)
    assert not result.ok and "captured index" in result.reason
    assert wt.exists()


def test_archive_ref_creation_never_overwrites_peer_root(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = git(repo, "rev-parse", "HEAD")
    peer = unique_commit(repo)
    original = worktree_gc.run
    collided = []

    def race(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd[:2] == ["git", "update-ref"] and len(cmd) == 5 and not collided:
            git(repo, "update-ref", cmd[2], peer)
            collided.append(cmd[2])
        return original(cmd, **kwargs)

    monkeypatch.setattr(worktree_gc, "run", race)
    ref = worktree_gc._pin_ref(repo, "peer-race", "20261012", head)
    assert ref != collided[0]
    assert git(repo, "rev-parse", collided[0]) == peer
    assert git(repo, "rev-parse", ref) == head


def test_reflog_tag_object_is_not_silently_peeled(repo: Path) -> None:
    wt = lane(repo)
    git(wt, "tag", "-a", "temporary", "-m", "unique tag", "HEAD")
    tag = git(wt, "rev-parse", "refs/tags/temporary")
    git(wt, "update-ref", "-d", "refs/tags/temporary")
    log = Path(git(wt, "rev-parse", "--absolute-git-dir")) / "logs/HEAD"
    head = git(wt, "rev-parse", "HEAD")
    with log.open("a") as out:
        out.write(f"{tag} {head} test <t@t.t> 1 +0000\tunique tag history\n")
    assert row(repo, wt).classify() == "HOLD"
