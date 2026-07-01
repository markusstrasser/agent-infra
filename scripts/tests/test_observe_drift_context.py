"""Tests for observe_drift_context size-cap accounting."""
from __future__ import annotations

import sys
from pathlib import Path

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
