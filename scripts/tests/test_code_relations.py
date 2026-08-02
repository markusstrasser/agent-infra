"""Held-out contracts for the evidence-bound code relation substrate."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from code_relations import (  # noqa: E402
    AmbiguousTargetError,
    Confidence,
    build_code_relations,
)


def _write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_python_import_and_call_share_source_evidence(tmp_path: Path) -> None:
    _write(tmp_path, "src/util.py", "def work():\n    return 1\n")
    _write(
        tmp_path,
        "src/app.py",
        "from util import work\n\ndef main():\n    return work()\n",
    )

    graph = build_code_relations(
        tmp_path, source_dirs=["src"], include_operational=False
    )
    imports = [
        edge
        for edge in graph.relations_of_type("imports")
        if graph.nodes[edge.source].path == "src/app.py"
        and graph.nodes[edge.target].path == "src/util.py"
    ]
    calls = [
        edge
        for edge in graph.relations_of_type("calls")
        if graph.nodes[edge.source].path == "src/app.py"
        and graph.nodes[edge.target].qualname == "work"
    ]

    assert len(imports) == 1
    assert imports[0].confidence is Confidence.RESOLVED
    assert imports[0].evidence.line == 1
    assert len(calls) == 1
    assert calls[0].confidence is Confidence.RESOLVED
    assert calls[0].evidence.line == 4
    assert all(edge.evidence.snippet for edge in graph.relations)


def test_duplicate_module_name_is_ambiguous_not_arbitrarily_resolved(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app/main.py", "import utils\n")
    _write(tmp_path, "one/utils.py", "VALUE = 1\n")
    _write(tmp_path, "two/utils.py", "VALUE = 2\n")

    graph = build_code_relations(
        tmp_path,
        source_dirs=["app", "one", "two"],
        include_operational=False,
    )
    edges = [
        edge
        for edge in graph.relations_of_type("imports")
        if graph.nodes[edge.source].path == "app/main.py"
    ]

    assert {graph.nodes[edge.target].path for edge in edges} == {
        "one/utils.py",
        "two/utils.py",
    }
    assert {edge.confidence for edge in edges} == {Confidence.AMBIGUOUS}
    assert any(d.code == "ambiguous_target" for d in graph.validate())
    with pytest.raises(AmbiguousTargetError):
        graph.resolve("utils.py")


def test_corrupt_inputs_emit_diagnostics_without_poisoning_other_files(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "src/good.py", "def healthy():\n    return True\n")
    _write(tmp_path, "src/bad.py", "def broken(:\n")
    _write(tmp_path, "ops/launchd/bad.plist", "not a plist")

    graph = build_code_relations(tmp_path, source_dirs=["src"])
    codes = {diagnostic.code for diagnostic in graph.validate()}

    assert "python_parse_error" in codes
    assert "plist_parse_error" in codes
    assert graph.resolve("src/good.py")
    assert any(node.qualname == "healthy" for node in graph.nodes.values())


def test_reverse_impact_crosses_launchd_shell_just_and_python(tmp_path: Path) -> None:
    _write(tmp_path, "scripts/pulse.py", "def main():\n    return 0\n")
    _write(
        tmp_path,
        "scripts/runner.py",
        "def _run(args):\n    return args\n\ndef tick():\n    return _run(['python3', 'scripts/pulse.py'])\n",
    )
    _write(
        tmp_path,
        "scripts/pulse-tick.sh",
        "#!/usr/bin/env bash\nexec uv run python3 \"$REPO/scripts/pulse.py\" tick\n",
    )
    _write(
        tmp_path,
        "justfile",
        "pulse-tick *args:\n    uv run python3 scripts/pulse.py tick {{args}}\n",
    )
    _write(
        tmp_path,
        "ops/launchd/com.test.pulse.plist",
        """<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
<key>Label</key><string>com.test.pulse</string>
<key>ProgramArguments</key><array>
<string>/bin/bash</string><string>scripts/pulse-tick.sh</string>
</array></dict></plist>
""",
    )

    graph = build_code_relations(tmp_path, source_dirs=["scripts"])
    hops = graph.impact("scripts/pulse.py", max_depth=3)
    observed = {
        (
            graph.nodes[hop.relation.source].path,
            hop.relation.relation,
            hop.relation.evidence.line,
        )
        for hop in hops
    }

    assert ("scripts/pulse-tick.sh", "executes", 2) in observed
    assert ("scripts/runner.py", "executes", 5) in observed
    assert ("justfile", "executes", 2) in observed
    assert ("ops/launchd/com.test.pulse.plist", "launches", 5) in observed


def test_fan_in_and_cycles_use_resolved_file_edges(tmp_path: Path) -> None:
    _write(tmp_path, "src/a.py", "import b\n")
    _write(tmp_path, "src/b.py", "import a\n")
    _write(tmp_path, "src/c.py", "import b\n")

    graph = build_code_relations(
        tmp_path, source_dirs=["src"], include_operational=False
    )

    assert graph.fan_in("imports")["src/b.py"] == 2
    assert graph.nodes_in_cycles("imports") == {"src/a.py", "src/b.py"}


def test_integrity_validation_has_no_errors_for_valid_graph(tmp_path: Path) -> None:
    _write(tmp_path, "src/a.py", "def one():\n    return 1\n")
    _write(tmp_path, "src/b.py", "from a import one\nvalue = one()\n")

    graph = build_code_relations(
        tmp_path, source_dirs=["src"], include_operational=False
    )

    assert not [d for d in graph.validate() if d.severity == "error"]
