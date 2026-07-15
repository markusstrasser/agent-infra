from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

import genomics_static_boundary_check as boundary


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _launchctl(
    returncode: int = 113,
    output: str = "Could not find service",
):
    def run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode, output, "")

    return run


@pytest.fixture
def genomics_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "genomics"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    (repo / "scripts").mkdir()
    (repo / "docs").mkdir()
    (repo / "scripts/safe.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "docs/history.py").write_text(
        '"historical phenome_behavior_bridge reference"\n',
        encoding="utf-8",
    )
    (repo / "justfile").write_text("test:\n    true\n", encoding="utf-8")
    _git(repo, "add", "scripts/safe.py", "docs/history.py", "justfile")
    return repo


def test_accepts_exact_staged_boundary(genomics_repo: Path) -> None:
    result = boundary.verify_genomics_static_boundary(genomics_repo)
    retired_launchd = boundary.verify_retired_genomics_resync_absent(
        runner=_launchctl(), uid=501
    )

    assert result["evidence_plane"] == "git_index"
    assert result["active_python_files_scanned"] == 1
    assert retired_launchd == {
        "label": boundary.RETIRED_GENOMICS_RESYNC_LABEL,
        "status": "absent",
    }


def test_reads_staged_bytes_not_unstaged_worktree(genomics_repo: Path) -> None:
    safe_module = genomics_repo / "scripts/safe.py"
    safe_module.write_text(
        "from scripts import validate_phenome_schema_sync\n",
        encoding="utf-8",
    )
    assert boundary.verify_genomics_static_boundary(genomics_repo)

    _git(genomics_repo, "add", "scripts/safe.py")
    with pytest.raises(boundary.StaticBoundaryError, match="active genomics Python"):
        boundary.verify_genomics_static_boundary(genomics_repo)


def test_staged_deletion_wins_over_recreated_worktree_file(genomics_repo: Path) -> None:
    retired = genomics_repo / "scripts/phenome_behavior_bridge.py"
    retired.write_text("VALUE = 1\n", encoding="utf-8")
    _git(genomics_repo, "add", "scripts/phenome_behavior_bridge.py")
    _git(genomics_repo, "rm", "--cached", "scripts/phenome_behavior_bridge.py")

    assert retired.is_file()
    assert boundary.verify_genomics_static_boundary(genomics_repo)


@pytest.mark.parametrize(
    ("relative", "content", "message"),
    [
        ("scripts/phenome_behavior_bridge.py", "VALUE = 1\n", "remains in Git index"),
        ("justfile", "prs-schema-sync:\n    true\n", "retired genomics recipe"),
        (
            "scripts/safe.py",
            "from scripts import validate_phenome_schema_sync\n",
            "active genomics Python",
        ),
    ],
)
def test_rejects_each_staged_violation(
    genomics_repo: Path,
    relative: str,
    content: str,
    message: str,
) -> None:
    target = genomics_repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(genomics_repo, "add", relative)

    with pytest.raises(boundary.StaticBoundaryError, match=message):
        boundary.verify_genomics_static_boundary(genomics_repo)


def test_rejects_malformed_staged_python(genomics_repo: Path) -> None:
    safe_module = genomics_repo / "scripts/safe.py"
    safe_module.write_text("if (\n", encoding="utf-8")
    _git(genomics_repo, "add", "scripts/safe.py")
    with pytest.raises(boundary.StaticBoundaryError, match="cannot inspect"):
        boundary.verify_genomics_static_boundary(genomics_repo)


def test_rejects_non_utf8_staged_python(genomics_repo: Path) -> None:
    safe_module = genomics_repo / "scripts/safe.py"
    safe_module.write_bytes(b"\xff\n")
    _git(genomics_repo, "add", "scripts/safe.py")
    with pytest.raises(boundary.StaticBoundaryError, match="not UTF-8"):
        boundary.verify_genomics_static_boundary(genomics_repo)


def test_rejects_loaded_retired_launchd_job(genomics_repo: Path) -> None:
    with pytest.raises(boundary.StaticBoundaryError, match="remains loaded"):
        boundary.verify_retired_genomics_resync_absent(
            runner=_launchctl(returncode=0, output="loaded"),
            uid=501,
        )


def test_refuses_indeterminate_launchctl_failure(genomics_repo: Path) -> None:
    with pytest.raises(boundary.StaticBoundaryError, match="cannot prove"):
        boundary.verify_retired_genomics_resync_absent(
            runner=_launchctl(returncode=64, output="permission denied"),
            uid=501,
        )


def test_json_entrypoint(genomics_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        boundary.main(
            ["--genomics-root", str(genomics_repo)],
            launchctl_runner=_launchctl(),
            uid=501,
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["checks"]["genomics_static_boundary"]["evidence_plane"] == "git_index"
    assert payload["checks"]["retired_genomics_resync"]["status"] == "absent"
