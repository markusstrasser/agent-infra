#!/usr/bin/env python3
"""Advisory lint: authority-deleting plans need ## Kill-switch vertical slice.

Exit 0: no trigger or section present.
Exit 2: trigger language present, kill-switch section missing.
Exit 1: usage / IO error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TRIGGER = re.compile(
    r"\b("
    r"authority\s+delet|delete\s+the\s+authority|dual[- ]write|cutover|"
    r"multi[- ]phase\s+kernel|kernel\s+refactor|rewrite\s+the\s+pipeline|"
    r"remove[- ]old[- ]path|new\s+authority|control[- ]plane\s+refactor|"
    r"stage[- ]runner\s+redesign"
    r")\b",
    re.I,
)
SECTION = re.compile(r"^#{1,3}\s+Kill-switch\s+vertical\s+slice\b", re.I | re.M)


def lint(text: str) -> tuple[int, str]:
    if not TRIGGER.search(text):
        return 0, "no kill-switch trigger language — skip"
    if SECTION.search(text):
        return 0, "trigger present + Kill-switch vertical slice section OK"
    return 2, "TRIGGERED but missing '## Kill-switch vertical slice' section"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan", type=Path, nargs="+")
    args = ap.parse_args()
    worst = 0
    for p in args.plan:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as e:
            print(f"✗ {p}: {e}", file=sys.stderr)
            return 1
        code, msg = lint(text)
        mark = "✓" if code == 0 else "✗"
        print(f"{mark} {p}: {msg}")
        worst = max(worst, code)
    return worst


if __name__ == "__main__":
    sys.exit(main())
