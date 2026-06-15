#!/usr/bin/env python3
"""cursor_commands_extract.py — capture Cursor CLI's backend-injected built-in commands.

Cursor's built-in slash commands (/multi-model-review, /best-of-n, /babysit, ...)
are NOT on disk. The backend injects them into the agent system prompt as a
<cursor_commands> block at runtime, so a filesystem grep of ~/.cursor/skills-cursor/
finds nothing — they only appear in saved agent transcripts. (Discovered 2026-06-15
after wrongly reporting Cursor had no /multi-model-review; see the cursor-builtins
memory note.)

This is the Cursor analogue of binary_skills_extract.py: it harvests the freshest
<cursor_commands> block from the newest transcript that carries one and writes it to
research/binary-extracts/cursor-commands.md. vendor-sweep commits the diff — the
inter-capture delta is Cursor's unpublished built-in-command changelog.

Idempotent: unchanged content produces no write (so no git churn).
"""
from __future__ import annotations
import glob
import json
import os
import re
import sys

TRANSCRIPTS = os.path.expanduser("~/.cursor/projects/*/agent-transcripts/**/*.jsonl")
OUT = os.path.join(os.path.dirname(__file__), "..", "research", "binary-extracts", "cursor-commands.md")
BLOCK = re.compile(r"<cursor_commands>(.*?)</cursor_commands>", re.S)


def _texts(obj):
    if isinstance(obj, dict):
        t = obj.get("text")
        if obj.get("type") == "text" and isinstance(t, str):
            yield t
        for v in obj.values():
            yield from _texts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _texts(v)


def newest_block() -> str | None:
    """Return the cursor_commands block from the most recently modified transcript
    that contains one. Picks the longest block in that file (fullest injection)."""
    files = sorted(glob.glob(TRANSCRIPTS, recursive=True), key=os.path.getmtime, reverse=True)
    for path in files:
        best = None
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if "<cursor_commands>" not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    for t in _texts(obj):
                        m = BLOCK.search(t)
                        if m and (best is None or len(m.group(1)) > len(best)):
                            best = m.group(1)
        except OSError:
            continue
        if best:
            return best.strip()
    return None


def main() -> int:
    block = newest_block()
    if not block:
        print("[cursor-commands] no <cursor_commands> block found in any transcript; skipping.")
        return 0
    # Stable, diff-friendly rendering: list of command names + the full block.
    names = sorted(set(re.findall(r"--- Cursor Command: ([a-z0-9-]+) ---", block)))
    header = (
        "# Cursor CLI built-in commands (backend-injected `<cursor_commands>`)\n\n"
        "> Auto-captured by scripts/cursor_commands_extract.py from the newest Cursor\n"
        "> agent transcript carrying a <cursor_commands> block. These are NOT on disk;\n"
        "> the inter-capture diff is Cursor's unpublished built-in-command changelog.\n\n"
        f"Commands seen: {', '.join(names) if names else '(none parsed)'}\n\n---\n\n"
    )
    out = header + block + "\n"
    out_path = os.path.abspath(OUT)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    old = ""
    if os.path.exists(out_path):
        old = open(out_path, encoding="utf-8", errors="replace").read()
    if old == out:
        print(f"[cursor-commands] unchanged ({len(names)} commands).")
        return 0
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"[cursor-commands] captured {len(names)} commands -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
