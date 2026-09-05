"""Tests for drift source completeness, failure handling, and size caps."""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import observe_drift_context as odc  # noqa: E402


def test_build_drift_context_reserves_coverage_tail(monkeypatch, tmp_path: Path):
    def fake_extract(project: str, sessions: int, work: Path) -> tuple[str, int]:
        chunk = f"\n\n# PROJECT: {project}\n" + ("x" * 80)
        return chunk, len(chunk.encode("utf-8"))

    def fake_coverage(script: Path, out: Path) -> None:
        out.write_text("coverage\n" + ("c" * 120))

    monkeypatch.setattr(odc, "_extract_project", fake_extract)
    monkeypatch.setattr(odc, "_run_shell_to_file", fake_coverage)

    out = odc.build_drift_context(
        tmp_path,
        projects=["agent-infra", "genomics", "phenome"],
        sessions=1,
        max_bytes=380,
    )

    raw = out.read_bytes()
    text = raw.decode("utf-8")
    assert len(raw) <= 380
    assert "# PROJECT: agent-infra" in text
    assert "coverage" in text
    assert text.endswith(odc.POSTAMBLE)


@pytest.mark.parametrize("failed_source", ["extract_transcript.py", "extract_codex_transcript.py"])
def test_extract_project_propagates_source_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failed_source: str,
) -> None:
    for source in ("claude", "codex"):
        (tmp_path / f"test-project-{source}.md").write_text(f"previous {source} run")

    def fake_run(command: list[str]) -> None:
        if Path(command[1]).name == failed_source:
            raise subprocess.CalledProcessError(7, command)
        Path(command[command.index("--output") + 1]).write_text("fresh successful source")

    monkeypatch.setattr(odc, "_run", fake_run)
    with pytest.raises(subprocess.CalledProcessError) as error:
        odc._extract_project("test-project", 5, tmp_path)
    assert error.value.returncode == 7
    source = "claude" if failed_source == "extract_transcript.py" else "codex"
    assert (tmp_path / f"test-project-{source}.md").read_text() == f"previous {source} run"


@pytest.mark.parametrize("claude,codex", [("", ""), ("", "Codex evidence"), ("Claude evidence", ""), ("Claude evidence", "Codex evidence")])
def test_extract_project_keeps_each_successful_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, claude: str, codex: str,
) -> None:
    def fake_run(command: list[str]) -> None:
        content = claude if Path(command[1]).name == "extract_transcript.py" else codex
        Path(command[command.index("--output") + 1]).write_text(content)

    monkeypatch.setattr(odc, "_run", fake_run)
    chunk, size = odc._extract_project("test-project", 5, tmp_path)
    if not claude and not codex:
        assert (chunk, size) == ("", 0)
    else:
        assert "# PROJECT: test-project" in chunk
        assert claude in chunk
        assert codex in chunk
        assert size == len(chunk.encode("utf-8"))


def test_build_drift_failure_preserves_previous_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    out = tmp_path / "observe-context.md"
    out.write_text("previous complete context")

    def fail_extract(*args) -> tuple[str, int]:
        raise subprocess.CalledProcessError(7, ["extractor"])

    monkeypatch.setattr(odc, "_extract_project", fail_extract)
    monkeypatch.setattr(odc, "_run_shell_to_file", lambda script, target: target.write_text("coverage"))
    with pytest.raises(subprocess.CalledProcessError):
        odc.build_drift_context(tmp_path, ["test-project"], 5, odc.DEFAULT_MAX)
    assert out.read_text() == "previous complete context"
