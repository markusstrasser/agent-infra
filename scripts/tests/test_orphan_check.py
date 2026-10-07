"""Static relation contracts for the orphaned-generator ratchet."""

from __future__ import annotations

from pathlib import Path

import orphan_check as orphan
from code_relations import build_code_relations


def test_check_script_distinguishes_imported_and_operational_wiring(
    tmp_path: Path, monkeypatch
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    target = scripts / "producer.py"
    target.write_text("def run():\n    return 1\n")
    (scripts / "consumer.py").write_text("from producer import run\nrun()\n")
    (scripts / "launcher.sh").write_text(
        "#!/usr/bin/env bash\npython3 scripts/producer.py\n"
    )
    monkeypatch.setattr(orphan, "REPO", tmp_path)
    monkeypatch.setattr(orphan, "SCRIPTS", scripts)
    graph = build_code_relations(tmp_path, python_source_dirs=[scripts])

    result = orphan.check_script(
        target,
        external_wiring="",
        consumers={},
        graph=graph,
        inv_blob="",
    )

    assert result["imported"] is True
    assert result["wired"] is True
    assert result["flagged"] is False


def test_sibling_path_references_count_as_wiring(tmp_path: Path, monkeypatch) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    loaded = scripts / "claims-reader.py"
    loaded.write_text("def main():\n    return 0\n")
    wrapped = scripts / "export_turns.py"
    wrapped.write_text("print(1)\n")
    prose = scripts / "findings_parse.py"
    prose.write_text("def parse():\n    return []\n")
    (scripts / "verifier.py").write_text(
        'p = Path(__file__).with_name("claims-reader.py")\n'
        "# we own this format, not findings_parse\n"
    )
    (scripts / "prior-context-index").write_text(
        '#!/usr/bin/env bash\nuv run python3 "$AGENT_INFRA/scripts/export_turns.py"\n'
    )
    monkeypatch.setattr(orphan, "SCRIPTS", scripts)
    siblings = orphan.sibling_texts()

    assert orphan.sibling_wired(loaded, siblings) == ["verifier.py"]
    assert orphan.sibling_wired(wrapped, siblings) == ["prior-context-index"]
    assert orphan.sibling_wired(prose, siblings) == []


def test_pytest_modules_are_not_generators() -> None:
    assert not orphan.is_generator(Path("scripts/test_debug_until_dry_verifier.py"))
