"""Import-graph contracts for structure_debt_rank."""

from __future__ import annotations

from pathlib import Path

import structure_debt_rank as debt


def test_python_graph_metrics_preserve_fan_in_and_cycles(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("import b\n")
    (src / "b.py").write_text("import a\n")
    (src / "c.py").write_text("import b\n")
    files = ["src/a.py", "src/b.py", "src/c.py"]

    fan_in, cycles = debt._python_graph_metrics(str(tmp_path), files)

    assert fan_in["src/b.py"] == 2
    assert cycles == {"src/a.py", "src/b.py"}
