"""Native TREE-cache proof parity, bounded subprocesses, and streaming audit."""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import worktree_gc


@dataclass
class IndexFixture:
    repo: Path
    oid_bytes: int
    entries: bytes
    trees: dict[str, tuple[int, str]]
    blob: str

    def payload(
        self, *, invalid: str | None = None, replace: tuple[str, str] | None = None
    ) -> bytes:
        def record(prefix: str) -> bytes:
            count, oid = self.trees[prefix]
            children = [
                child
                for child in self.trees
                if child and child.rpartition("/")[0] == prefix
            ]
            if invalid == prefix:
                count = -1
            if replace and replace[0] == prefix:
                oid = replace[1]
            result = (
                os.fsencode(prefix.rsplit("/", 1)[-1])
                + b"\0"
                + f"{count} {len(children)}\n".encode()
            )
            if count >= 0:
                result += bytes.fromhex(oid)
            return result + b"".join(record(child) for child in children)

        return record("")

    def index(self, payload: bytes, *, size: int | None = None) -> bytes:
        body = (
            self.entries
            + b"TREE"
            + (len(payload) if size is None else size).to_bytes(4, "big")
            + payload
        )
        return (
            body
            + hashlib.new("sha1" if self.oid_bytes == 20 else "sha256", body).digest()
        )


@pytest.fixture(scope="session", params=["sha1", "sha256"])
def index_fixture(
    tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest
) -> IndexFixture:
    # Tests only read this template. All corruptions are independent raw bytes.
    repo = tmp_path_factory.mktemp("gc-native-index")

    def git(*args: str) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, check=True
        ).stdout

    git("init", "-q", "-b", "main", f"--object-format={request.param}")
    git("config", "user.name", "test")
    git("config", "user.email", "test@example.com")
    names = [
        "at-root",
        "a/entry",
        "a/nested/one",
        "a/nested/two",
        "a-/entry",
        "aa/entry",
        "aa/nested/one",
        "aa/nested/two",
        "odd\n[1]/file",
        "repeat-one/nested/file",
        "repeat-two/nested/file",
    ]
    names += [f"wide-{i:02}/nested/file" for i in range(24)]
    for name in names:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            b"identical subtree" if name.startswith("repeat-") else os.fsencode(name)
        )
    (repo / "executable").write_bytes(b"#!/bin/sh\n")
    (repo / "executable").chmod(0o755)
    (repo / "symlink").symlink_to("at-root")
    git("add", "--", ".")
    # This environment rejects non-UTF-8 filenames. Native Git can preserve
    # them in the index and trees without asking the filesystem to create one.
    blob = git("hash-object", "at-root").decode().strip()
    non_utf8 = os.fsdecode(b"non-utf8-\xff/file")
    git(
        "update-index",
        "--add",
        "--cacheinfo",
        f"100644,{blob},{non_utf8}",
    )
    git("commit", "-qm", "initial")
    commit = git("rev-parse", "HEAD").decode().strip()
    git("update-index", "--add", "--cacheinfo", f"160000,{commit},gitlink")
    root_oid = git("write-tree").decode().strip()
    raw_entries = git("ls-files", "--stage", "-z").split(b"\0")
    entries = (
        b"DIRC" + (2).to_bytes(4, "big") + (len(raw_entries) - 1).to_bytes(4, "big")
    )
    paths = []
    for raw in raw_entries:
        if not raw:
            continue
        metadata, name = raw.split(b"\t", 1)
        mode, oid, stage = metadata.split()
        assert stage == b"0"
        entry = (
            b"\0" * 24
            + int(mode, 8).to_bytes(4, "big")
            + b"\0" * 12
            + bytes.fromhex(oid.decode())
            + len(name).to_bytes(2, "big")
            + name
            + b"\0"
        )
        entries += entry + b"\0" * (-len(entry) % 8)
        paths.append(os.fsdecode(name))
    trees = {"": (len(paths), root_oid)}
    for raw in git("ls-tree", "-r", "-t", "-z", root_oid).split(b"\0"):
        if not raw:
            continue
        metadata, name = raw.split(b"\t", 1)
        _, kind, oid = metadata.split()
        if kind == b"tree":
            prefix = os.fsdecode(name)
            trees[prefix] = (
                sum(path.startswith(prefix + "/") for path in paths),
                oid.decode(),
            )
    return IndexFixture(
        repo,
        20 if request.param == "sha1" else 32,
        entries,
        trees,
        git("rev-parse", "HEAD:at-root").decode().strip(),
    )


def index_hold(fixture: IndexFixture, raw: bytes) -> str | None:
    # These are the same failures caught by the real closed-inventory guard.
    try:
        return worktree_gc._index_state_hold(
            fixture.repo, fixture.repo / ".git", fixture.oid_bytes, raw=raw
        )
    except (ValueError, subprocess.CalledProcessError) as error:
        return str(error)


def test_cached_subtrees_share_one_native_listing(
    index_fixture: IndexFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    original = subprocess.run

    def record(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append(cmd)
        return original(cmd, **kwargs)

    monkeypatch.setattr(worktree_gc.subprocess, "run", record)
    assert (
        index_hold(index_fixture, index_fixture.index(index_fixture.payload())) is None
    )
    assert len(index_fixture.trees) > 40
    assert [cmd[1] for cmd in calls].count("cat-file") == 1
    assert "--batch" in next(cmd for cmd in calls if cmd[1] == "cat-file")
    listings = [cmd for cmd in calls if cmd[1] == "ls-tree"]
    assert len(listings) == 1
    assert "-r" in listings[0] and "-t" in listings[0] and "-z" in listings[0]


@pytest.mark.parametrize("invalid", ["", "a", "a/nested"])
def test_invalidated_parent_still_proves_valid_children(
    index_fixture: IndexFixture, invalid: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    original = subprocess.run

    def record(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append(cmd)
        return original(cmd, **kwargs)

    monkeypatch.setattr(worktree_gc.subprocess, "run", record)
    raw = index_fixture.index(index_fixture.payload(invalid=invalid))
    assert index_hold(index_fixture, raw) is None
    assert [cmd[1] for cmd in calls].count("cat-file") == 1
    listed_oids = [cmd[-1] for cmd in calls if cmd[1] == "ls-tree"]
    assert len(listed_oids) == len(set(listed_oids))


@pytest.mark.parametrize("invalid", [None, ""])
def test_repeated_cached_oids_share_native_evidence(
    index_fixture: IndexFixture, invalid: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_oid = index_fixture.trees["repeat-one"][1]
    child_oid = index_fixture.trees["repeat-one/nested"][1]
    assert parent_oid == index_fixture.trees["repeat-two"][1]
    assert child_oid == index_fixture.trees["repeat-two/nested"][1]
    calls = []
    original = subprocess.run

    def record(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append((cmd, kwargs.get("input")))
        return original(cmd, **kwargs)

    monkeypatch.setattr(worktree_gc.subprocess, "run", record)
    assert (
        index_hold(
            index_fixture, index_fixture.index(index_fixture.payload(invalid=invalid))
        )
        is None
    )
    batches = [data for cmd, data in calls if cmd[1] == "cat-file"]
    assert len(batches) == 1
    requested = batches[0].decode("ascii").splitlines()
    assert requested.count(parent_oid) == requested.count(child_oid) == 1
    assert len(requested) == len(set(requested))
    listed_oids = [cmd[-1] for cmd, _ in calls if cmd[1] == "ls-tree"]
    assert len(listed_oids) == len(set(listed_oids))


@pytest.mark.parametrize("command", ["cat-file", "ls-tree"])
@pytest.mark.parametrize("fault", ["error", "malformed"])
def test_native_tree_evidence_failure_holds(
    index_fixture: IndexFixture,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    fault: str,
) -> None:
    original = subprocess.run

    def failed(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        if cmd[1] == command:
            if fault == "error":
                raise subprocess.CalledProcessError(
                    1, cmd, stderr="unreadable native evidence"
                )
            return subprocess.CompletedProcess(
                cmd, 0, b"malformed\n" if command == "cat-file" else b"malformed\0", ""
            )
        return original(cmd, **kwargs)

    monkeypatch.setattr(worktree_gc.subprocess, "run", failed)
    assert index_hold(index_fixture, index_fixture.index(index_fixture.payload()))


@pytest.mark.parametrize("kind", [b"tree", b"blob"])
def test_duplicate_native_tree_paths_hold(
    index_fixture: IndexFixture, monkeypatch: pytest.MonkeyPatch, kind: bytes
) -> None:
    original = subprocess.run

    def duplicate(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        result = original(cmd, **kwargs)
        if cmd[1] == "ls-tree":
            record = next(
                record
                for record in result.stdout.split(b"\0")
                if record and record.split(b"\t", 1)[0].split()[1] == kind
            )
            result.stdout += record + b"\0"
        return result

    monkeypatch.setattr(worktree_gc.subprocess, "run", duplicate)
    assert "duplicate native tree path" in (
        index_hold(index_fixture, index_fixture.index(index_fixture.payload())) or ""
    )


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_duplicate_native_directories_cannot_merge_cached_subtrees(
    tmp_path: Path, object_format: str
) -> None:
    # Construct the reviewer's malformed tree with native Git objects: the
    # first `a` owns only `x`, but the cached `a` claims both `x` and `y`.
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str, data: bytes | None = None) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=repo, input=data, capture_output=True, check=True
        ).stdout

    git("init", "-q", f"--object-format={object_format}")
    blob = git("hash-object", "-w", "--stdin", data=b"payload").decode().strip()

    def tree(data: bytes) -> str:
        return (
            git("hash-object", "--literally", "-t", "tree", "-w", "--stdin", data=data)
            .decode()
            .strip()
        )

    first = tree(b"100644 x\0" + bytes.fromhex(blob))
    second = tree(b"100644 y\0" + bytes.fromhex(blob))
    root = tree(
        b"40000 a\0" + bytes.fromhex(first) + b"40000 a\0" + bytes.fromhex(second)
    )
    records = [
        record
        for record in git("ls-tree", "-r", "-t", "-z", root).split(b"\0")
        if record
    ]
    assert [record.split(b"\t", 1)[1] for record in records] == [
        b"a",
        b"a/x",
        b"a",
        b"a/y",
    ]
    entries = b"DIRC" + (2).to_bytes(4, "big") + (2).to_bytes(4, "big")
    for name in (b"a/x", b"a/y"):
        entry = (
            b"\0" * 24
            + (0o100644).to_bytes(4, "big")
            + b"\0" * 12
            + bytes.fromhex(blob)
            + len(name).to_bytes(2, "big")
            + name
            + b"\0"
        )
        entries += entry + b"\0" * (-len(entry) % 8)
    fixture = IndexFixture(
        repo, len(blob) // 2, entries, {"": (2, root), "a": (2, first)}, blob
    )
    assert index_hold(fixture, fixture.index(fixture.payload())) is not None


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
@pytest.mark.parametrize("uncached_parent", [False, True])
def test_literal_slash_native_name_cannot_merge_cached_subtrees(
    tmp_path: Path, object_format: str, uncached_parent: bool
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str, data: bytes | None = None) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=repo, input=data, capture_output=True, check=True
        ).stdout

    git("init", "-q", f"--object-format={object_format}")
    blob = git("hash-object", "-w", "--stdin", data=b"payload").decode().strip()

    def tree(data: bytes) -> str:
        return (
            git("hash-object", "--literally", "-t", "tree", "-w", "--stdin", data=data)
            .decode()
            .strip()
        )

    child = tree(b"100644 x\0" + bytes.fromhex(blob))
    root = tree(
        b"40000 a\0" + bytes.fromhex(child) + b"100644 a/y\0" + bytes.fromhex(blob)
    )
    records = [
        record
        for record in git("ls-tree", "-r", "-t", "-z", root).split(b"\0")
        if record
    ]
    assert [record.split(b"\t", 1)[1] for record in records] == [
        b"a",
        b"a/x",
        b"a/y",
    ]
    prefix = b"outer/" if uncached_parent else b""
    trees = {"": (2, root), "a": (2, child)}
    if uncached_parent:
        # The malformed object need not itself have a valid TREE-cache record.
        outer = tree(b"40000 outer\0" + bytes.fromhex(root))
        trees = {"": (2, outer), "outer": (-1, root), "outer/a": (2, child)}
    entries = b"DIRC" + (2).to_bytes(4, "big") + (2).to_bytes(4, "big")
    for name in (prefix + b"a/x", prefix + b"a/y"):
        entry = (
            b"\0" * 24
            + (0o100644).to_bytes(4, "big")
            + b"\0" * 12
            + bytes.fromhex(blob)
            + len(name).to_bytes(2, "big")
            + name
            + b"\0"
        )
        entries += entry + b"\0" * (-len(entry) % 8)
    fixture = IndexFixture(repo, len(blob) // 2, entries, trees, blob)
    assert index_hold(fixture, fixture.index(fixture.payload())) is not None


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
@pytest.mark.parametrize("name", [b"", b".", b"..", b"a/y", b"x\0suffix"])
def test_raw_native_tree_entry_names_hold(
    tmp_path: Path, object_format: str, name: bytes
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str, data: bytes | None = None) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=repo, input=data, capture_output=True, check=True
        ).stdout

    git("init", "-q", f"--object-format={object_format}")
    blob = git("hash-object", "-w", "--stdin", data=b"payload").decode().strip()
    oid = (
        git(
            "hash-object",
            "--literally",
            "-t",
            "tree",
            "-w",
            "--stdin",
            data=b"100644 " + name + b"\0" + bytes.fromhex(blob),
        )
        .decode()
        .strip()
    )
    # An embedded NUL disrupts entry framing; parsing the entire raw object
    # must reject it rather than accepting the apparent first component.
    with pytest.raises(ValueError):
        worktree_gc._validate_native_tree_names(repo, [oid], len(blob) // 2)


@pytest.mark.parametrize(
    "damage",
    [
        "header",
        "oid",
        "kind",
        "size",
        "negative-size",
        "object",
        "separator",
        "trailing",
        "mode",
        "name",
        "entry",
    ],
)
def test_raw_native_tree_batch_framing_failure_holds(
    index_fixture: IndexFixture, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    original = subprocess.run

    def corrupt(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        result = original(cmd, **kwargs)
        if cmd[1] != "cat-file":
            return result
        header, rest = result.stdout.split(b"\n", 1)
        oid, kind, size = header.split(b" ")
        tree = rest[: int(size)]
        separator = rest[int(size) : int(size) + 1]
        tail = rest[int(size) + 1 :]
        assert separator == b"\n"
        if damage == "header":
            result.stdout = b"unterminated header"
            return result
        if damage == "oid":
            oid = b"0" * len(oid)
        elif damage == "kind":
            kind = b"blob"
        elif damage == "size":
            size = b"not-a-size"
        elif damage == "negative-size":
            size = b"-1"
        elif damage == "object":
            result.stdout = header + b"\n" + tree[:-1]
            return result
        elif damage == "separator":
            separator = b"!"
        elif damage == "trailing":
            tail += b"unparsed"
        else:
            if damage == "mode":
                tree = b"8" + tree[1:]
            elif damage == "name":
                tree = b"100644 unterminated"
            else:
                tree = b"100644 x\0" + bytes.fromhex(index_fixture.blob)[:-1]
            size = str(len(tree)).encode("ascii")
        result.stdout = b" ".join((oid, kind, size)) + b"\n" + tree + separator + tail
        return result

    monkeypatch.setattr(worktree_gc.subprocess, "run", corrupt)
    assert index_hold(index_fixture, index_fixture.index(index_fixture.payload()))


@pytest.mark.parametrize("prefix", ["", "a", "a/nested", "a-", "aa"])
def test_tree_cache_mismatch_holds(index_fixture: IndexFixture, prefix: str) -> None:
    other = "aa" if prefix != "aa" else "a"
    raw = index_fixture.index(
        index_fixture.payload(replace=(prefix, index_fixture.trees[other][1]))
    )
    assert "TREE cache" in (index_hold(index_fixture, raw) or "")


@pytest.mark.parametrize("damage", ["envelope", "oid", "header", "counts", "trailing"])
def test_malformed_extension_holds(index_fixture: IndexFixture, damage: str) -> None:
    payload = index_fixture.payload()
    size = None
    if damage == "envelope":
        size = len(payload) + index_fixture.oid_bytes + 1
    elif damage == "oid":
        payload = b"\0" + b"1 0\n" + b"\0" * (index_fixture.oid_bytes - 1)
    elif damage == "header":
        payload = b"\0missing newline"
    elif damage == "counts":
        payload = b"\0-2 0\n"
    else:
        payload += b"unparsed"
    assert index_hold(index_fixture, index_fixture.index(payload, size=size))


@pytest.mark.parametrize("object_kind", ["blob", "missing"])
def test_cached_root_must_be_an_existing_tree(
    index_fixture: IndexFixture, object_kind: str
) -> None:
    oid = (
        index_fixture.blob
        if object_kind == "blob"
        else "0" * (index_fixture.oid_bytes * 2)
    )
    raw = index_fixture.index(index_fixture.payload(replace=("", oid)))
    assert index_hold(index_fixture, raw)


@pytest.mark.parametrize("cls", ["HELD", "DAEMON", "LOCKED", "HOLD", "SAFE"])
def test_audit_flushes_classified_row_before_next_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cls: str
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()

    class Output(io.StringIO):
        flushed = ""

        def flush(self) -> None:
            self.flushed = self.getvalue()

    output = Output()
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setattr(
        sys, "argv", ["worktree_gc.py", "audit", "--repo", str(repo), "--no-size"]
    )
    monkeypatch.setattr(
        worktree_gc,
        "parse_worktrees",
        lambda _: [
            (first, None, "lock" if cls == "LOCKED" else None),
            (second, None, None),
        ],
    )
    holders = {str(first): [123]} if cls in ("HELD", "DAEMON") else {"/nowhere": [1]}
    monkeypatch.setattr(worktree_gc, "live_cwd_holders", lambda: holders)
    monkeypatch.setattr(
        worktree_gc, "daemon_pids", lambda _: {123} if cls == "DAEMON" else set()
    )
    monkeypatch.setattr(
        worktree_gc,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(
            a[0], 0, "a" * 40 if a[0][1] == "rev-parse" else "", ""
        ),
    )
    monkeypatch.setattr(worktree_gc, "_hidden_work", lambda _: (0, 0))
    monkeypatch.setattr(worktree_gc, "_codex_owner_thread", lambda _: None)
    monkeypatch.setattr(worktree_gc, "is_ancestor", lambda *a: True)
    monkeypatch.setattr(worktree_gc, "ahead_of_main", lambda *a: 0)
    monkeypatch.setattr(worktree_gc, "last_commit_rel", lambda *a: "old")
    monkeypatch.setattr(worktree_gc, "idle_age_days", lambda _: 10)

    def proof(wt: Path) -> str | None:
        if wt == second:
            assert str(first) in output.flushed
            assert cls in output.flushed
            assert str(second) not in output.flushed
            assert output.flushed.count(str(first)) == 1
            raise RuntimeError("second proof unfinished")
        return "uncovered state" if cls == "HOLD" else None

    monkeypatch.setattr(worktree_gc, "_worktree_state_hold", proof)
    with pytest.raises(RuntimeError, match="second proof unfinished"):
        worktree_gc.main()
