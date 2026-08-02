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
    graph = build_code_relations(tmp_path, source_dirs=[scripts])

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
