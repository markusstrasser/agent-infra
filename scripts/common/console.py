"""Minimal console output utilities — colors, progress, tables.

Detects whether output is going to a human terminal or being captured by
an agent (Claude Code Bash tool, Modal logs, pipe). When captured, strips
ANSI to avoid wasting model tokens on escape sequences.

Usage:
    from common.console import con, status, progress

    con.ok("check passed")
    con.warn("something iffy")
    con.fail("broken")
    con.header("Section Name")
    con.kv("key", "value")

    # Line-based progress (no \\r, works everywhere)
    for i, item in enumerate(items):
        progress(i + 1, len(items), f"processing {item}")

    # Status context manager
    with status("fetching data"):
        result = fetch()
    # prints: ✓ fetching data (1.2s)
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager

# ── Detection ────────────────────────────────────────────────────────

def _is_color_terminal() -> bool:
    """True if stdout is a real terminal that supports color."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


COLOR = _is_color_terminal()

# ── ANSI primitives ─────────────────────────────────────────────────

def _ansi(code: str, text: str) -> str:
    if not COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def green(text: str) -> str:  return _ansi("32", text)
def yellow(text: str) -> str: return _ansi("33", text)
def red(text: str) -> str:    return _ansi("31", text)
def bold(text: str) -> str:   return _ansi("1", text)
def dim(text: str) -> str:    return _ansi("2", text)
def cyan(text: str) -> str:   return _ansi("36", text)

# ── Symbols ──────────────────────────────────────────────────────────

SYM_OK   = lambda: green("✓")
SYM_WARN = lambda: yellow("!")
SYM_FAIL = lambda: red("✗")
SYM_STEP = lambda: cyan("▸")
SYM_DONE = lambda: green("●")

# ── Console ──────────────────────────────────────────────────────────

class Console:
    """Structured terminal output with automatic color detection."""

    def ok(self, msg: str):
        print(f"  {SYM_OK()} {msg}")

    def warn(self, msg: str):
        print(f"  {SYM_WARN()} {msg}")

    def fail(self, msg: str):
        print(f"  {SYM_FAIL()} {msg}")

    def header(self, title: str):
        print(f"\n{bold(f'[{title}]')}")

    def step(self, msg: str):
        print(f"  {SYM_STEP()} {msg}")

    def kv(self, key: str, value: str, width: int = 20):
        """Key-value line, key right-padded."""
        print(f"  {dim(key.ljust(width))} {value}")

    def summary(self, total: int, ok: int = 0, warn: int = 0, fail: int = 0):
        parts = []
        if ok:   parts.append(green(f"{ok} pass"))
        if warn: parts.append(yellow(f"{warn} warn"))
        if fail: parts.append(red(f"{fail} fail"))
        print(f"\n{bold(str(total))} checks: {', '.join(parts)}")

    def table(self, headers: list[str], rows: list[list[str]], widths: list[int] | None = None):
        """Simple aligned table. No box drawing — works in all contexts."""
        if not rows:
            return
        if widths is None:
            widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) + 2
                      for i, h in enumerate(headers)]
        header_line = "".join(bold(h.ljust(w)) for h, w in zip(headers, widths))
        print(f"  {header_line}")
        sep = dim("─" * sum(widths))
        print(f"  {sep}")
        for row in rows:
            line = "".join(str(cell).ljust(w) for cell, w in zip(row, widths))
            print(f"  {line}")


con = Console()

# ── Progress ─────────────────────────────────────────────────────────

def progress(current: int, total: int, label: str = ""):
    """Line-based progress — no \\r, works in Claude Code Bash, Modal, pipes.

    Prints every item if total <= 20, otherwise at 10% intervals + first/last.
    """
    if total <= 20 or current == 1 or current == total or current % max(1, total // 10) == 0:
        pct = current * 100 // total
        bar_w = 20
        filled = pct * bar_w // 100
        bar = f"{'█' * filled}{'░' * (bar_w - filled)}"
        suffix = f" — {label}" if label else ""
        print(f"  {dim(f'[{current}/{total}]')} {bar} {pct}%{suffix}")


# ── Status context manager ───────────────────────────────────────────

@contextmanager
def status(label: str):
    """Times a block and prints result with ✓/✗.

        with status("loading config"):
            cfg = load()
        # ✓ loading config (0.3s)
    """
    t0 = time.monotonic()
    try:
        yield
        dt = time.monotonic() - t0
        print(f"  {SYM_OK()} {label} {dim(f'({dt:.1f}s)')}")
    except Exception:
        dt = time.monotonic() - t0
        print(f"  {SYM_FAIL()} {label} {dim(f'({dt:.1f}s)')}")
        raise


# ── Color by status ──────────────────────────────────────────────────

def color_status(text: str) -> str:
    """Color a status string by its value — for tables/lists."""
    low = text.lower().strip()
    if low in ("pass", "done", "ok", "success", "active"):
        return green(text)
    elif low in ("warn", "partial", "running", "pending"):
        return yellow(text)
    elif low in ("fail", "failed", "error", "broken"):
        return red(text)
    return text
