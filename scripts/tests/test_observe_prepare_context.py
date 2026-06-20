"""Tests for observe_prepare_context coverage-digest subprocess handling."""

from __future__ import annotations

import subprocess
from pathlib import Path

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
