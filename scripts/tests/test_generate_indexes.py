"""Research-index regeneration keeps curated rows over generator TODO duplicates."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("generate_indexes", ROOT / "scripts" / "generate-indexes.py")
assert SPEC and SPEC.loader
generate_indexes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_indexes)

CURATED = "| `memo.md` | Memo: the real finding | Before touching X |"
TODO = "| `memo.md` | Memo | TODO |"


def test_curated_row_wins_in_either_order(tmp_path: Path) -> None:
    # 2026-09-27: a curated trending-scout row was dropped because a later TODO duplicate overwrote it
    for rows in ([CURATED, TODO], [TODO, CURATED]):
        index = tmp_path / "research-index.md"
        index.write_text("\n".join(["| File | Topic | Consult before |", "|---|---|---|", *rows]) + "\n")
        entry = generate_indexes.parse_research_index(index)["memo.md"]
        assert entry == {"topic": "Memo: the real finding", "consult_before": "Before touching X"}


def test_later_curated_row_still_updates_earlier_curated_row(tmp_path: Path) -> None:
    index = tmp_path / "research-index.md"
    index.write_text("\n".join([CURATED, "| `memo.md` | Memo: revised | Before Y |"]) + "\n")
    assert generate_indexes.parse_research_index(index)["memo.md"]["consult_before"] == "Before Y"
