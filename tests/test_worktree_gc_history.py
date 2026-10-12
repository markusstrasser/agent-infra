"""Same-path historical landing, independently covering working and index bytes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import worktree_gc
from test_worktree_gc_landed import age, git, lane, row, run, snapshot
from test_worktree_gc_landed import repo as repo_fixture


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return repo_fixture.__wrapped__(tmp_path, monkeypatch)


@pytest.mark.parametrize("staged", [False, True])
def test_patch_landed_then_superseded_is_read_only_landed(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    staged: bool,
) -> None:
    wt = lane(repo)
    if not staged:
        git(wt, "reset", "-q", "HEAD", "--", "file", "binary")
    (repo / "file").write_text("later main edit\n")
    git(repo, "add", "file")
    git(repo, "commit", "-qm", "supersede patch landing")
    age(wt)
    before = snapshot(repo, wt)
    assert row(repo, wt).classify() == "landed"
    assert run(monkeypatch, repo, "suggest", "--json") == 0
    record = json.loads(capsys.readouterr().out)["candidates"][0]
    assert record["class"] == "landed" and record["blocking_paths"] == []
    assert snapshot(repo, wt) == before


@pytest.mark.parametrize("kind", ["working", "index-only", "untracked", "fix-up"])
def test_never_landed_exact_bytes_hold_and_name_path(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    wt = lane(repo)
    path = "new" if kind == "untracked" else "file"
    original = (wt / "file").read_bytes()
    (wt / path).write_text("lane bytes never landed\n")
    if kind == "index-only":
        git(wt, "add", path)
        (wt / path).write_bytes(original)
    elif kind == "fix-up":
        (repo / path).write_text("lane bytes never landed\nplus landing fix-up\n")
        git(repo, "add", path)
        git(repo, "commit", "-qm", "land with fix-up")
    age(wt)
    before = snapshot(repo, wt)
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD"
    assert candidate.blocking_paths == (path,)
    assert run(monkeypatch, repo, "suggest", "--json") == 0
    record = json.loads(capsys.readouterr().out)["candidates"][0]
    assert record["class"] == "HOLD" and record["blocking_paths"] == [path]
    assert snapshot(repo, wt) == before
    assert run(monkeypatch, repo, "apply", "--archive-landed-idle-hours", "24") == 0
    assert wt.exists()


@pytest.mark.parametrize("resurrect", [False, True])
@pytest.mark.parametrize("staged", [False, True])
def test_deletion_landed_then_optionally_resurrected(
    repo: Path, resurrect: bool, staged: bool
) -> None:
    wt = lane(repo)
    (wt / "file").unlink()
    if staged:
        git(wt, "add", "file")
    git(repo, "rm", "file")
    git(repo, "commit", "-qm", "land deletion")
    if resurrect:
        (repo / "file").write_text("resurrected later\n")
        git(repo, "add", "file")
        git(repo, "commit", "-qm", "resurrect")
    assert row(repo, wt).classify() == "landed"


def test_unlanded_deletion_holds(repo: Path) -> None:
    wt = lane(repo)
    (wt / "file").unlink()
    candidate = row(repo, wt)
    assert candidate.classify() == "HOLD" and candidate.blocking_paths == ("file",)


@pytest.mark.parametrize("landed", [False, True])
@pytest.mark.parametrize("staged", [False, True])
def test_rename_requires_both_paths_in_default_history(
    repo: Path, landed: bool, staged: bool
) -> None:
    wt = lane(repo)
    rel = "renamed [1]\nfile"
    (wt / "file").rename(wt / rel)
    if staged:
        git(wt, "add", "file", rel)
    git(repo, "rm", "file")
    if landed:
        (repo / rel).write_bytes((wt / rel).read_bytes())
        git(repo, "add", rel)
    git(repo, "commit", "-qm", "land deletion or complete rename")
    if landed:
        (repo / rel).write_text("later rename edit\n")
        git(repo, "add", rel)
        git(repo, "commit", "-qm", "supersede rename bytes")
    candidate = row(repo, wt)
    assert candidate.classify() == ("landed" if landed else "HOLD")
    assert candidate.blocking_paths == (() if landed else (rel,))


@pytest.mark.parametrize("landed", [False, True])
def test_untracked_literal_binary_path_landed_then_removed(
    repo: Path, landed: bool
) -> None:
    wt = lane(repo, untracked=False)
    rel = ":(glob)*\n[1].bin"
    (wt / rel).write_bytes(b"untracked\x00\xffbytes")
    if landed:
        (repo / rel).write_bytes((wt / rel).read_bytes())
        git(repo, "add", "--", f":(literal){rel}")
        git(repo, "commit", "-qm", "land literal untracked path")
        git(repo, "rm", "--", f":(literal){rel}")
        git(repo, "commit", "-qm", "remove later")
    candidate = row(repo, wt)
    assert candidate.classify() == ("landed" if landed else "HOLD")
    assert candidate.blocking_paths == (() if landed else (rel,))


def test_blob_at_another_path_is_not_landing(repo: Path) -> None:
    wt = lane(repo)
    (wt / "file").write_text("only at another path\n")
    (repo / "other").write_bytes((wt / "file").read_bytes())
    git(repo, "add", "other")
    git(repo, "commit", "-qm", "wrong path")
    assert row(repo, wt).blocking_paths == ("file",)


def test_blob_only_before_lane_head_is_not_landing(repo: Path) -> None:
    wanted = b"historical before lane\n"
    (repo / "file").write_bytes(wanted)
    git(repo, "add", "file")
    git(repo, "commit", "-qm", "old version")
    (repo / "file").write_text("baseline\n")
    git(repo, "add", "file")
    git(repo, "commit", "-qm", "replace before lane")
    wt = lane(repo)
    (wt / "file").write_bytes(wanted)
    assert row(repo, wt).blocking_paths == ("file",)


def test_landed_index_only_version_survives_later_overwrite(repo: Path) -> None:
    wt = lane(repo)
    working = (wt / "file").read_bytes()
    for root in (repo, wt):
        (root / "file").write_text("intermediate staged version\n")
        git(root, "add", "file")
    git(repo, "commit", "-qm", "land staged bytes")
    (wt / "file").write_bytes(working)
    (repo / "file").write_text("third version on main\n")
    git(repo, "add", "file")
    git(repo, "commit", "-qm", "supersede both versions")
    assert row(repo, wt).classify() == "landed"


def test_history_read_failure_is_degraded_and_preserves_lane(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wt = lane(repo)
    (repo / "file").write_text("superseded\n")
    git(repo, "add", "file")
    git(repo, "commit", "-qm", "later")

    def unreadable(*args: object) -> set[tuple[str, str] | None]:
        raise OSError("history unavailable")

    monkeypatch.setattr(worktree_gc, "_historical_path_entries", unreadable)
    assert not worktree_gc.dirty_work_on_default(repo, wt)
    assert "[DEGRADED]" in capsys.readouterr().err
    assert wt.exists()
