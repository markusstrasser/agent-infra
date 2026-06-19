#!/usr/bin/env python3
"""WebVTT → plain text. Strips cues/timestamps; dedupes rolling-caption repeats.

Usage:
  clean_vtt.py input.vtt [-o output.txt]
  clean_vtt.py -  # stdin

Mirrors youtube-transcript skill; used by intel transcript ingest (not genomics).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TAG_RE = re.compile(r"<[^>]+>")


def clean_vtt(text: str) -> str:
    out: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        if "-->" in line or re.fullmatch(r"\d+", line):
            continue
        line = TAG_RE.sub("", line).strip()
        if not line or line in seen:
            continue
        seen.add(line)
        out.append(line)
    return "\n".join(out) + ("\n" if out else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", nargs="?", default="-", help="VTT file or - for stdin")
    ap.add_argument("-o", "--output", type=Path, help="write here (default: stdout)")
    args = ap.parse_args()
    text = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8", errors="replace")
    result = clean_vtt(text)
    if args.output:
        args.output.write_text(result, encoding="utf-8")
        print(args.output, file=sys.stderr)
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
