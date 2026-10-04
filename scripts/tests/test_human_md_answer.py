from pathlib import Path

import pytest

from human_md_answer import answer
from questions_view import ViewResult, _parse_human_md

DOC = """# HUMAN.md

## 2026-10-01 — pick a lane  [open]
session: abc

Body line.

## 2026-10-02 — second ask  [open]
Other body.
"""


def _parse(path: Path) -> ViewResult:
    result = ViewResult()
    _parse_human_md(path, path.read_text(), result)
    return result


def test_answer_moves_ask_from_open_to_awaiting_agent(tmp_path: Path) -> None:
    f = tmp_path / "repo" / "HUMAN.md"
    f.parent.mkdir()
    f.write_text(DOC)
    answer(f, 3, "take  B\nnow", "2026-10-04")
    text = f.read_text()
    assert "## 2026-10-01 — pick a lane  [answered]" in text
    assert "Body line.\n\n[answered: take B now — operator, questions pane 2026-10-04]\n\n## 2026-10-02" in text
    result = _parse(f)
    assert [q.prompt for q in result.questions] == ["2026-10-02 — second ask"]
    assert [q.prompt for q in result.awaiting_agent] == ["2026-10-01 — pick a lane"]


def test_answer_refuses_a_ref_that_is_not_an_open_ask(tmp_path: Path) -> None:
    f = tmp_path / "HUMAN.md"
    f.write_text(DOC)
    with pytest.raises(LookupError):
        answer(f, 4, "x", "2026-10-04")
    answer(f, 3, "x", "2026-10-04")
    with pytest.raises(LookupError):
        answer(f, 3, "again", "2026-10-04")
