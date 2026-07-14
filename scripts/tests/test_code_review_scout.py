from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCOUT_PATH = ROOT / "scripts" / "code-review-scout.py"


def run_scout(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCOUT_PATH), str(project), *args, "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_selected_oversized_files_fail_loud_and_name_every_file(tmp_path: Path) -> None:
    module = tmp_path / "pkg"
    module.mkdir()
    for name in ("one.py", "two.py"):
        (module / name).write_text("x" * 75_001)

    result = run_scout(tmp_path, "--module", "pkg")

    assert result.returncode == 2
    assert "no review was dispatched" in result.stderr
    assert "pkg/one.py: 75001 bytes" in result.stderr
    assert "pkg/two.py: 75001 bytes" in result.stderr


def test_oversized_file_outside_selected_module_does_not_block(tmp_path: Path) -> None:
    selected = tmp_path / "selected"
    selected.mkdir()
    (selected / "ok.py").write_text("x = 1\n" * 20)
    other = tmp_path / "other"
    other.mkdir()
    (other / "huge.py").write_text("x" * 75_001)

    result = run_scout(tmp_path, "--module", "selected")

    assert result.returncode == 0
    assert "selected/ok.py" in result.stdout
    assert "huge.py" not in result.stdout + result.stderr


def test_file_at_exact_limit_is_reviewable(tmp_path: Path) -> None:
    module = tmp_path / "pkg"
    module.mkdir()
    (module / "limit.py").write_text("x" * 75_000)

    result = run_scout(tmp_path, "--module", "pkg")

    assert result.returncode == 0
    assert "pkg/limit.py" in result.stdout


def test_exact_file_selects_no_siblings_and_uses_full_batch_budget(
    tmp_path: Path,
) -> None:
    module = tmp_path / "pkg"
    module.mkdir()
    selected = module / "selected.py"
    selected.write_text("x" * 75_001)
    sibling = module / "sibling.py"
    sibling.write_text("y = 1\n" * 20)

    result = run_scout(tmp_path, "--file", "pkg/selected.py")

    assert result.returncode == 0
    assert "pkg/selected.py" in result.stdout
    assert "pkg/sibling.py" not in result.stdout + result.stderr


def test_exact_file_above_batch_budget_fails_loud(tmp_path: Path) -> None:
    module = tmp_path / "pkg"
    module.mkdir()
    selected = module / "too-large.py"
    selected.write_text("x" * 80_001)

    result = run_scout(tmp_path, "--file", "pkg/too-large.py")

    assert result.returncode == 2
    assert "selected limit=80000" in result.stderr
    assert "pkg/too-large.py: 80001 bytes" in result.stderr


def test_exact_file_cannot_escape_project_root(tmp_path: Path) -> None:
    (tmp_path / "inside.py").write_text("inside = True\n" * 20)
    outside = tmp_path.parent / "outside.py"
    outside.write_text("x = 1\n" * 20)

    result = run_scout(tmp_path, "--file", "../outside.py")

    assert result.returncode == 1
    assert "must stay inside the project root" in result.stderr


def test_stat_failure_raises_coverage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = importlib.util.spec_from_file_location("code_review_scout", SCOUT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "source.py"
    source.write_text("x = 1\n")

    def broken_stat(self: Path):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "stat", broken_stat)
    with pytest.raises(module.CoverageError, match="cannot stat selected source file"):
        module.checked_size(source)


def test_list_modules_reports_oversized_count(tmp_path: Path) -> None:
    module = tmp_path / "pkg"
    module.mkdir()
    (module / "ok.py").write_text("x = 1\n" * 20)
    (module / "huge.py").write_text("x" * 75_001)

    result = subprocess.run(
        [sys.executable, str(SCOUT_PATH), str(tmp_path), "--list-modules"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "pkg" in result.stdout
    assert "oversized=1" in result.stdout
