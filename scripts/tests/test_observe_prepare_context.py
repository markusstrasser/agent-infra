"""Tests for observe context source failures and coverage-digest handling."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import observe_prepare_context as opc


def test_run_shell_to_file_success(tmp_path: Path) -> None:
    script = tmp_path / "ok.sh"
    out = tmp_path / "out.txt"
    script.write_text('echo "hello"')
    opc._run_shell_to_file(script, out)
    assert out.read_text() == "hello\n"


def test_run_shell_to_file_sigpipe_with_output(tmp_path: Path) -> None:
    """Exit 141 with non-empty output is benign (downstream closed the pipe)."""
    script = tmp_path / "pipe.sh"
    out = tmp_path / "out.txt"
    script.write_text('echo "partial"; exit 141')
    opc._run_shell_to_file(script, out)
    assert out.read_text() == "partial\n"


def test_run_shell_to_file_sigpipe_empty_raises(tmp_path: Path) -> None:
    script = tmp_path / "empty.sh"
    out = tmp_path / "out.txt"
    script.write_text("exit 141")
    try:
        opc._run_shell_to_file(script, out)
    except subprocess.CalledProcessError as exc:
        assert exc.returncode == opc.SIGPIPE
    else:
        raise AssertionError("expected CalledProcessError")


@pytest.mark.parametrize("failed_source", ["extract_transcript.py", "extract_codex_transcript.py"])
def test_extract_source_failure_preserves_prior_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failed_source: str,
) -> None:
    out = tmp_path / "input.md"
    out.write_text("previous Claude run")
    codex_out = tmp_path / "codex.md"
    codex_out.write_text("previous Codex run")

    def fake_run(command: list[str]) -> None:
        if Path(command[1]).name == failed_source:
            raise subprocess.CalledProcessError(7, command)
        Path(command[command.index("--output") + 1]).write_text("fresh successful source")

    monkeypatch.setattr(opc, "_run", fake_run)
    with pytest.raises(subprocess.CalledProcessError) as error:
        opc.extract("test-project", 5, 1, True, out, True)
    assert error.value.returncode == 7
    failed_output = out if failed_source == "extract_transcript.py" else codex_out
    assert failed_output.read_text().startswith("previous")


def test_extract_accepts_successful_empty_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(command: list[str]) -> None:
        Path(command[command.index("--output") + 1]).write_text("")

    monkeypatch.setattr(opc, "_run", fake_run)
    opc.extract("test-project", 5, 1, True, tmp_path / "input.md", True)
    assert (tmp_path / "input.md").read_text() == ""
    assert (tmp_path / "codex.md").read_text() == ""


@pytest.mark.parametrize("claude_file_exists", [False, True])
def test_build_context_retains_codex_only_source(tmp_path: Path, claude_file_exists: bool) -> None:
    if claude_file_exists:
        (tmp_path / "input.md").write_text("")
    (tmp_path / "codex.md").write_text("Codex conversation evidence")
    (tmp_path / "coverage-digest.txt").write_text("coverage")

    out, size, notes = opc.build_context(tmp_path, opc.DEFAULT_MAX, True)
    assert "Codex conversation evidence" in out.read_text()
    assert size == out.stat().st_size
    assert notes == []


def test_build_context_tolerates_successful_absent_sources(tmp_path: Path) -> None:
    (tmp_path / "coverage-digest.txt").write_text("coverage")

    out, _, notes = opc.build_context(tmp_path, opc.DEFAULT_MAX, True)
    assert out.read_text() == "coverage"
    assert notes == []


def test_run_shell_to_file_real_error_raises(tmp_path: Path) -> None:
    script = tmp_path / "fail.sh"
    out = tmp_path / "out.txt"
    script.write_text('echo "oops"; exit 2')
    try:
        opc._run_shell_to_file(script, out)
    except subprocess.CalledProcessError as exc:
        assert exc.returncode == 2
    else:
        raise AssertionError("expected CalledProcessError")
