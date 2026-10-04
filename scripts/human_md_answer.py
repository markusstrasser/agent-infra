#!/usr/bin/env python3
"""Answer one open HUMAN.md ask in place (the questions-pane mod's write lane).

Usage: human_md_answer.py <path>:<line> <answer text>

<path>:<line> is the `ref` questions_view.py reports for a human-md question.
The heading at that line must parse under questions_view's grammar with an
[open] tag; its tag becomes [answered] and an `[answered: <text> — operator,
<date>]` line is appended at the end of that ask's section. Nothing else in
the file changes. Exits 2 when the ref no longer names an open ask.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from questions_view import _HUMAN_HEAD_RE, _strip_fences  # noqa: E402


def answer(path: Path, line_no: int, text: str, today: str) -> None:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    parsed = _strip_fences(raw).splitlines()
    i = line_no - 1
    m = _HUMAN_HEAD_RE.match(parsed[i]) if 0 <= i < len(parsed) else None
    if not m or m.group("tag").lower() != "open":
        raise LookupError(f"{path}:{line_no} is not an open ask")
    end = next(
        (j for j in range(i + 1, len(parsed)) if _HUMAN_HEAD_RE.match(parsed[j])),
        len(lines),
    )
    while end > i + 1 and not lines[end - 1].strip():
        end -= 1
    lines[i] = lines[i][: m.start("tag") - 1] + "[answered]" + lines[i][m.end("tag") + 1 :]
    flat = " ".join(text.split())
    lines[end:end] = ["", f"[answered: {flat} — operator, questions pane {today}]"]
    path.write_text("\n".join(lines) + ("\n" if raw.endswith("\n") else ""), encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 3 or ":" not in argv[1] or not argv[2].strip():
        print(__doc__, file=sys.stderr)
        return 1
    path_s, _, line_s = argv[1].rpartition(":")
    try:
        answer(Path(path_s), int(line_s), argv[2], dt.date.today().isoformat())
    except LookupError as e:
        print(e, file=sys.stderr)
        return 2
    print(f"answered {path_s}:{line_s}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
