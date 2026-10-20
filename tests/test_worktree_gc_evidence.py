"""Archived administrative evidence must survive expiration and object pruning."""

from __future__ import annotations

import json
import subprocess
import tarfile
from pathlib import Path

import pytest
import worktree_gc
from test_worktree_gc_landed import git, lane, row
from test_worktree_gc_landed import repo as repo_fixture


@pytest.fixture(params=["sha1", "sha256"])
def repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Path:
    monkeypatch.setenv("GIT_DEFAULT_HASH", request.param)
    return repo_fixture.__wrapped__(tmp_path, monkeypatch, request)


def blob(wt: Path, data: bytes) -> str:
    return (
        subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=wt,
            input=data,
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .strip()
    )


def evidence(wt: Path) -> tuple[dict[str, str], dict[str, bytes]]:
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    common = Path(git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    tree = git(wt, "rev-parse", "HEAD^{tree}")
    lost = git(wt, "commit-tree", tree, "-p", "HEAD", "-m", "lost reflog commit")
    head = git(wt, "rev-parse", "HEAD")
    with (admin / "logs/HEAD").open("a") as log:
        log.write(f"{lost} {head} test <t@t.t> 1 +0000\tlost history\n")
    roots = {"lost": lost}
    # Two paths exercise stage/path encoding and absent stages without quoting.
    for path in ("file", "odd\nname\tfile"):
        stages = [blob(wt, f"{path} stage {n}".encode()) for n in (1, 2, 3)]
        records = f"0 {'0' * len(head)}\t{path}\0".encode() + b"".join(
            f"100644 {oid} {n}\t{path}\0".encode()
            for n, oid in enumerate(stages, 1)
            if path == "file" or n != 2
        )
        subprocess.run(
            ["git", "update-index", "-z", "--index-info"],
            cwd=wt,
            input=records,
            check=True,
        )
        (wt / path).write_text("resolved\n")
        git(wt, "add", "--", path)
        for n, oid in enumerate(stages, 1):
            if path == "file" or n != 2:
                roots[f"{n}/{path}"] = oid
    auto_blob = blob(wt, b"AUTO_MERGE-only bytes\n")
    auto_tree = (
        subprocess.run(
            ["git", "mktree"],
            cwd=wt,
            input=f"100644 blob {auto_blob}\tauto\n".encode(),
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .strip()
    )
    (admin / "AUTO_MERGE").write_text(auto_tree + "\n")
    roots.update(auto_tree=auto_tree, auto_blob=auto_blob)
    payloads = {
        ".git/MERGE_RR": b"1" * 40 + b"\tfile\0",
        ".git/common-rr-cache/" + "1" * 40 + "/preimage": b"conflict\0preimage\n",
        ".git/common-rr-cache/" + "1" * 40 + "/postimage": b"resolved\n",
    }
    for rel, raw in payloads.items():
        path = (
            common / "rr-cache" / rel.removeprefix(".git/common-rr-cache/")
            if rel.startswith(".git/common-rr-cache/")
            else admin / rel.removeprefix(".git/")
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return roots, payloads


def test_all_evidence_archives_without_manual_cleanup_and_survives_prune(
    repo: Path,
) -> None:
    wt = lane(repo)
    roots, payloads = evidence(wt)
    assert row(repo, wt).classify() == "HOLD"
    assert worktree_gc.explicit_archive(wt) == 0
    assert not wt.exists()
    dest = next(worktree_gc.ARCHIVE_ROOT.glob("**/head.txt")).parent
    pins = json.loads((dest / "evidence-manifest.json").read_text())
    assert pins["reflog-1"]["oid"] == roots["lost"]
    assert pins["auto-merge"]["oid"] == roots["auto_tree"]
    reuc = pins["reuc"]["ref"]
    assert reuc.startswith("refs/wt-archive/lane-evidence/reuc")
    assert git(repo, "cat-file", "-t", reuc) == "commit"
    with tarfile.open(dest / "git-state.tgz") as packed:
        for path, raw in payloads.items():
            assert packed.extractfile(path).read() == raw
    git(repo, "reflog", "expire", "--expire=now", "--all")
    git(repo, "gc", "--prune=now")
    for pin in pins.values():
        assert git(repo, "rev-parse", pin["ref"]) == pin["oid"]
        assert git(repo, "cat-file", "-t", pin["ref"]) == pin["kind"]
    assert (
        git(repo, "rev-parse", f"{pins['auto-merge']['ref']}:auto")
        == roots["auto_blob"]
    )
    for path, oid in roots.items():
        if "/" in path:
            stage, original = path.split("/", 1)
            assert git(repo, "rev-parse", f"{reuc}:p-{original}/{stage}") == oid
            assert git(repo, "cat-file", "-t", oid) == "blob"
    assert git(repo, "cat-file", "-t", roots["lost"]) == "commit"


@pytest.mark.parametrize("kind", ["reflog", "reuc", "auto-merge"])
def test_failed_pin_names_object_and_keeps_worktree(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    wt = lane(repo)
    roots, _ = evidence(wt)
    original = worktree_gc.run

    def fail_pin(args, **kwargs):
        if (
            args[:2] == ["git", "update-ref"]
            and "-evidence/" in args[2]
            and kind in args[2]
        ):
            return subprocess.CompletedProcess(args, 1, "", "injected pin failure")
        return original(args, **kwargs)

    monkeypatch.setattr(worktree_gc, "run", fail_pin)
    assert worktree_gc.explicit_archive(wt) == 2
    assert wt.exists()
    error = capsys.readouterr().err
    assert "could not pin" in error and "-evidence/" in error
    if kind != "reuc":
        assert roots["lost" if kind == "reflog" else "auto_tree"] in error


def test_direct_removal_cannot_bypass_evidence_archive(repo: Path) -> None:
    wt = lane(repo)
    evidence(wt)
    with pytest.raises(RuntimeError):
        worktree_gc.remove_worktree(repo, wt, operator_archive=True)
    assert wt.exists()


def test_missing_reuc_blob_names_path_stage_and_object(repo: Path) -> None:
    wt = lane(repo)
    roots, _ = evidence(wt)
    oid = roots["2/file"]
    common = Path(git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    (common / "objects" / oid[:2] / oid[2:]).unlink()
    result = worktree_gc.archive_worktree(row(repo, wt))
    assert not result.ok and wt.exists()
    assert "REUC '2/file'" in result.reason and oid in result.reason


@pytest.mark.parametrize(
    "mutation", ["deleted-ref", "moved-ref", "manifest", "payload", "live-rerere"]
)
def test_removal_rechecks_pins_and_saved_evidence(repo: Path, mutation: str) -> None:
    wt = lane(repo)
    evidence(wt)
    result = worktree_gc.archive_worktree(row(repo, wt))
    assert result.ok, result.reason
    manifest = json.loads((result.dir / "content-manifest.json").read_text())
    path = result.dir / "evidence-manifest.json"
    pins = json.loads(path.read_text())
    if mutation == "deleted-ref":
        git(repo, "update-ref", "-d", pins["reflog-1"]["ref"])
    elif mutation == "moved-ref":
        git(repo, "update-ref", pins["reflog-1"]["ref"], "HEAD")
    elif mutation == "manifest":
        del pins["reuc"]
        path.write_text(json.dumps(pins))
    elif mutation == "payload":
        (result.dir / "git-state.tgz").write_bytes(b"corrupt payload")
    else:
        common = Path(
            git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir")
        )
        (common / "rr-cache" / ("1" * 40) / "postimage").write_bytes(b"new resolution")
    with pytest.raises((RuntimeError, tarfile.TarError)):
        worktree_gc.remove_worktree(
            repo, wt, manifest=manifest, operator_archive=True, archive_dir=result.dir
        )
    assert wt.exists()


def test_local_rerere_bytes_archive_and_shared_rerere_keeps_classification(
    repo: Path,
) -> None:
    wt = lane(repo)
    common = Path(git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    shared = common / "rr-cache" / ("2" * 40) / "postimage"
    shared.parent.mkdir(parents=True)
    shared.write_bytes(b"shared resolution\0\n")
    assert row(repo, wt).classify() == "landed"
    admin = Path(git(wt, "rev-parse", "--absolute-git-dir"))
    local = admin / "rr-cache" / ("3" * 40) / "preimage"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"local preimage\0\n")
    (admin / "MERGE_RR").write_bytes(b"3" * 40 + b"\tfile\0")
    raw_index = (admin / "index").read_bytes()
    assert row(repo, wt).classify() == "HOLD"
    result = worktree_gc.archive_worktree(row(repo, wt))
    assert result.ok, result.reason
    assert (admin / "index").read_bytes() == raw_index
    with tarfile.open(result.dir / "git-state.tgz") as packed:
        assert (
            packed.extractfile(".git/rr-cache/" + "3" * 40 + "/preimage").read()
            == local.read_bytes()
        )
        assert (
            packed.extractfile(".git/common-rr-cache/" + "2" * 40 + "/postimage").read()
            == shared.read_bytes()
        )
    manifest = json.loads((result.dir / "content-manifest.json").read_text())
    worktree_gc.remove_worktree(
        repo, wt, manifest=manifest, operator_archive=True, archive_dir=result.dir
    )
    assert not wt.exists() and shared.read_bytes() == b"shared resolution\0\n"


def test_reuc_can_retain_both_file_and_descendant_history(repo: Path) -> None:
    wt = lane(repo)
    head = git(wt, "rev-parse", "HEAD")
    stages = [blob(wt, f"historical side {n}".encode()) for n in (1, 2, 3)]
    for path in ("file", "file/child"):
        if path != "file":
            git(wt, "rm", "-f", "file")
            (wt / "file").mkdir()
            (wt / path).write_text("resolved descendant\n")
        records = f"0 {'0' * len(head)}\t{path}\0".encode() + b"".join(
            f"100644 {oid} {n}\t{path}\0".encode() for n, oid in enumerate(stages, 1)
        )
        subprocess.run(
            ["git", "update-index", "-z", "--index-info"],
            cwd=wt,
            input=records,
            check=True,
        )
        git(wt, "add", "--", path)
    undo = git(wt, "ls-files", "--resolve-undo", "-z")
    assert "\tfile\0" in undo and "\tfile/child\0" in undo
    result = worktree_gc.archive_worktree(row(repo, wt))
    assert result.ok, result.reason
    pins = json.loads((result.dir / "evidence-manifest.json").read_text())
    reuc_ref = pins["reuc"]["ref"]
    for stage, oid in enumerate(stages, 1):
        assert git(repo, "rev-parse", f"{reuc_ref}:p-file/{stage}") == oid
        assert git(repo, "rev-parse", f"{reuc_ref}:p-file/p-child/{stage}") == oid
