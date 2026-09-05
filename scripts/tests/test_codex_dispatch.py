"""Exercise live Codex argument parsing without launching a model."""
from pathlib import Path
from types import SimpleNamespace
import shutil
import subprocess

import pytest

import autoresearch
import codex_dispatch


def check_codex_arguments(command: list[str]) -> None:
    assert command[command.index("-s") + 1] == "workspace-write"
    assert "--dangerously-bypass-approvals-and-sandbox" not in command
    if shutil.which("codex") is None:
        pytest.skip("installed Codex parser is unavailable")
    result = subprocess.run([*command, "--help"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_dispatch_preserves_project_model_and_output(monkeypatch, tmp_path: Path) -> None:
    commands = []
    def capture(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(pid=123, poll=lambda: 0)
    with monkeypatch.context() as patch:
        patch.setattr(codex_dispatch.subprocess, "Popen", capture)
        result = codex_dispatch.dispatch(
            [{"name": "bounded", "prompt": "Review this", "model": "gpt-6-astra"}],
            tmp_path / "reports", project=str(tmp_path),
        )
    command = commands[0]
    assert command[command.index("-C") + 1] == str(tmp_path)
    assert command[command.index("-m") + 1] == "gpt-6-astra"
    assert command[command.index("-o") + 1] == result[0]["output_file"]
    assert "Review this" in command
    check_codex_arguments(command)


@pytest.mark.parametrize("model", [None, "gpt-6-astra"])
def test_mutator_preserves_worktree_and_optional_model(monkeypatch, tmp_path: Path, model) -> None:
    calls = []
    def capture(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="Changed bounded file\n", stderr="")
    with monkeypatch.context() as patch:
        patch.setattr(autoresearch.subprocess, "run", capture)
        description, cost = autoresearch._run_mutator_codex(
            {"model": model, "mutator_timeout": 31}, tmp_path, "Edit one file",
        )
    command, options = calls[0]
    assert options["cwd"] == tmp_path
    assert options["timeout"] == 31
    assert (description, cost) == ("Changed bounded file", 0.0)
    assert ("-m" in command) == bool(model)
    if model:
        assert command[command.index("-m") + 1] == model
    check_codex_arguments(command)
