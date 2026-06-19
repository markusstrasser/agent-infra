"""Tests for codebase-map hierarchical partitioning."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("_cmap", ROOT / "scripts" / "codebase-map.py")
assert _spec and _spec.loader
_cmap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cmap)

_refresh_spec = importlib.util.spec_from_file_location(
    "_refresh_on_commit", ROOT / "scripts" / "refresh_codebase_map_on_commit.py"
)
assert _refresh_spec and _refresh_spec.loader
_refresh_on_commit = importlib.util.module_from_spec(_refresh_spec)
_refresh_spec.loader.exec_module(_refresh_on_commit)


def _entry(stem: str) -> tuple[str, str, Path]:
    return (stem, "", Path(f"/fake/{stem}.py"))


def test_small_group_not_split():
    entries = [_entry(f"f{i}") for i in range(10)]
    parts = _cmap.partition_group("scripts", entries, max_files=80)
    assert parts == {"scripts": entries}


def test_large_group_splits_by_prefix():
    entries = [_entry(f"modal_{i}") for i in range(50)]
    entries += [_entry(f"pipeline_{i}") for i in range(50)]
    parts = _cmap.partition_group("scripts", entries, max_files=80)
    assert len(parts) >= 2
    assert sum(len(v) for v in parts.values()) == 100
    assert all(len(v) <= 80 for v in parts.values())


def test_slugify_strips_glob_markers():
    assert _cmap.slugify_group("scripts/modal_*") == "scripts-modal"


def test_staged_paths_git_failure_is_non_fatal(capsys):
    with patch.object(
        _refresh_on_commit,
        "_git",
        side_effect=RuntimeError("git -C agent-infra diff --cached: fatal: unable to read tree"),
    ):
        assert _refresh_on_commit._staged_paths(Path("/tmp/fake")) == []
    err = capsys.readouterr().err
    assert "skip staged read" in err


def test_main_uses_repo_root_not_cwd(tmp_path, monkeypatch):
    genomics = tmp_path / "genomics"
    genomics.mkdir()
    wrong_cwd = tmp_path / "agent-infra-wrong-cwd"
    wrong_cwd.mkdir()
    monkeypatch.chdir(wrong_cwd)
    monkeypatch.setattr(
        sys,
        "argv",
        ["refresh_codebase_map_on_commit.py", "--repo-root", str(genomics)],
    )
    with patch.object(_refresh_on_commit, "_staged_paths", return_value=[]) as staged:
        rc = _refresh_on_commit.main()
    assert rc == 0
    staged.assert_called_once_with(genomics.resolve())
