"""Canonical relation contracts for repo-outline callgraph mode."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "repo_outline", ROOT / "scripts" / "repo-outline.py"
)
assert SPEC and SPEC.loader
repo_outline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repo_outline)


def test_callgraph_uses_resolved_relations_and_external_opt_in(
    tmp_path: Path, capsys
) -> None:
    source = tmp_path / "app.py"
    source.write_text(
        "def local():\n    return 1\n\ndef main():\n    print('x')\n    return local()\n"
    )

    repo_outline.callgraph(source)
    internal = capsys.readouterr().out
    repo_outline.callgraph(source, include_external=True)
    external = capsys.readouterr().out

    assert "main -> local" in internal
    assert "print" not in internal
    assert "main -> local, print" in external
