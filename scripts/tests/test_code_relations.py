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


@pytest.fixture(scope="module")
def live_graph():
    return build_code_relations(ROOT, source_dirs=["scripts", "src"])


@pytest.mark.parametrize(
    ("source", "target", "relation"),
    [
        ("scripts/codebase-map.py", "scripts/code_relations.py", "imports"),
        ("scripts/repo-outline.py", "scripts/code_relations.py", "imports"),
        ("scripts/structure_debt_rank.py", "scripts/code_relations.py", "imports"),
        ("scripts/infra_usage_check.py", "scripts/code_relations.py", "imports"),
        ("scripts/orphan_check.py", "scripts/code_relations.py", "imports"),
        ("justfile", "scripts/pulse.py", "executes"),
        ("scripts/pulse-tick.sh", "scripts/pulse.py", "executes"),
        ("scripts/pulse_tick.py", "scripts/pulse.py", "executes"),
        (
            "ops/launchd/com.agent-infra.pulse-tick.plist",
            "scripts/pulse-tick.sh",
            "launches",
        ),
        ("scripts/pulse.py", "scripts/pulse_tick.py", "imports"),
        ("scripts/pulse.py", "scripts/fm.py", "executes"),
        ("scripts/pulse.py", "scripts/questions_view.py", "imports"),
        ("scripts/orient.py", "scripts/system_inventory.py", "imports"),
        ("scripts/orient.py", "scripts/config.py", "imports"),
        ("justfile", "scripts/infra_usage_check.py", "executes"),
        ("justfile", "scripts/orphan_check.py", "executes"),
        ("justfile", "scripts/structure_debt_rank.py", "executes"),
        (
            "ops/launchd/com.agent-infra.codebase-map-refresh.plist",
            "scripts/refresh-codebase-maps.sh",
            "launches",
        ),
        (
            "scripts/refresh-codebase-maps.sh",
            "scripts/refresh_all_codebase_maps.py",
            "executes",
        ),
        ("scripts/orphan_check.py", "scripts/common/db.py", "imports"),
    ],
)
def test_live_dependency_questions(
    live_graph, source: str, target: str, relation: str
) -> None:
    assert any(
        edge.relation == relation
        and live_graph.nodes[edge.source].path == source
        and live_graph.nodes[edge.target].path == target
        and edge.confidence is Confidence.RESOLVED
        and edge.evidence.line > 0
        for edge in live_graph.relations
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
    assert graph.file_edges("imports") == {}
    assert graph.file_edges("imports", include_ambiguous=True) == {
        "app/main.py": {"one/utils.py", "two/utils.py"}
    }
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
    assert any(
        diagnostic.code == "python_parse_error" and diagnostic.severity == "error"
        for diagnostic in graph.validate()
    )
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


def test_hidden_directory_path_does_not_collapse_into_suffix_match(tmp_path: Path) -> None:
    _write(tmp_path, ".config/tool.py", "VALUE = 1\n")
    _write(tmp_path, "xconfig/tool.py", "VALUE = 2\n")
    _write(tmp_path, "run.sh", "python3 ./.config/tool.py\n")

    graph = build_code_relations(tmp_path)
    edges = [
        edge
        for edge in graph.relations_of_type("executes")
        if graph.nodes[edge.source].path == "run.sh"
    ]

    assert len(edges) == 1
    assert graph.nodes[edges[0].target].path == ".config/tool.py"
    assert edges[0].confidence is Confidence.RESOLVED


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
