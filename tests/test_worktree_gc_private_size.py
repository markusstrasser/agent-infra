"""APFS private-size accounting: clone-shared blocks are not reclaimable."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import worktree_gc

SIZE = 20 * 1024 * 1024
MB = 1024 * 1024


def du_bytes(path: Path) -> int:
    out = subprocess.run(
        ["du", "-sk", str(path)], check=True, capture_output=True, text=True
    ).stdout.split()
    return int(out[0]) * 1024


def write_big(path: Path) -> None:
    path.write_bytes(b"x" * SIZE)


def test_clone_is_private_only_for_new_blocks(tmp_path: Path) -> None:
    source = tmp_path / "source"
    clone = tmp_path / "clone"
    source.mkdir()
    clone.mkdir()
    write_big(source / "big")
    subprocess.run(["cp", "-c", str(source / "big"), str(clone / "big")], check=True)

    assert du_bytes(clone) >= SIZE - MB
    assert worktree_gc.private_tree_bytes(clone) < MB


def test_plain_copy_is_private_in_full(tmp_path: Path) -> None:
    source = tmp_path / "source"
    plain = tmp_path / "plain"
    source.mkdir()
    plain.mkdir()
    write_big(source / "big")
    subprocess.run(["cp", str(source / "big"), str(plain / "big")], check=True)

    private = worktree_gc.private_tree_bytes(plain)
    assert SIZE - MB <= private <= SIZE + MB
    assert du_bytes(plain) >= SIZE - MB


def test_hard_link_counts_once_and_symlinks_are_not_followed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    tree = tmp_path / "tree"
    outside.mkdir()
    tree.mkdir()
    write_big(outside / "big")
    write_big(tree / "big")
    single = worktree_gc.private_tree_bytes(tree)

    os.link(tree / "big", tree / "big-link")
    (tree / "outside-link").symlink_to(outside / "big")
    doubled = worktree_gc.private_tree_bytes(tree)

    assert SIZE - MB <= single <= SIZE + MB
    assert doubled == single


def test_missing_tree_fails_loud_with_path_and_errno(tmp_path: Path) -> None:
    missing = tmp_path / "absent"
    with pytest.raises(worktree_gc.PrivateSizeError) as caught:
        worktree_gc.private_tree_bytes(missing)
    message = str(caught.value)
    assert str(missing) in message
    assert "errno 2" in message
