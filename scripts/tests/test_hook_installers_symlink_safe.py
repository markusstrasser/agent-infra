#!/usr/bin/env python3
"""Guard: hook installers must never write THROUGH a symlink into .git/hooks/.

Regression test for the 2026-06-19 clobber: `just install-hooks` did
`printf ... > .git/hooks/pre-commit` while pre-commit was a SYMLINK into the
skills repo, so the redirect followed the link and overwrote
skills/hooks/pre-commit-guards.sh with a 4-line stub -> blocked ALL commits
repo-wide. Fixed in 545434c by `rm -f .git/hooks/pre-commit` before the write.

This is P0 of .claude/plans/c2417c3c-worktree-isolation-adoption.md. Worktrees
share the common .git (hooks included), so the shared-.git/hooks clobber class
is precisely the one thing session isolation does NOT fix -> it needs its own
deterministic guard.

Two invariants:
  1. (durable) Every justfile recipe / shell script that writes `> .git/hooks/<name>`
     must first `rm -f .git/hooks/<name>` (or use `ln -sf`) in the same block, so
     the redirect can never resolve through an existing symlink.
  2. (live) The installed .git/hooks/pre-commit, if present, is a real regular file
     that chains the guard dispatcher -> not the clobbered stub, not a dangling link.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# A redirect target like `> .git/hooks/pre-commit` (optional whitespace after `>`).
_WRITE = re.compile(r">\s*\.git/hooks/([A-Za-z0-9._-]+)")


def _rmf(name: str) -> re.Pattern[str]:
    return re.compile(rf"rm\s+-f[^\n]*\.git/hooks/{re.escape(name)}")


def _lnsf(name: str) -> re.Pattern[str]:
    return re.compile(rf"ln\s+-s[a-z]*f[^\n]*\.git/hooks/{re.escape(name)}")


def _recipe_blocks(text: str) -> list[str]:
    """Split a justfile into recipe blocks (col-0 header + its indented body)."""
    blocks: list[str] = []
    cur: list[str] = []
    for line in text.splitlines():
        if cur and line and not line[0].isspace() and not line.startswith("#"):
            blocks.append("\n".join(cur))
            cur = []
        cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def _installer_texts() -> list[tuple[str, str]]:
    """(label, block-text) for every justfile recipe + shell script that writes a hook."""
    out: list[tuple[str, str]] = []
    jf = REPO / "justfile"
    if jf.exists():
        for blk in _recipe_blocks(jf.read_text(encoding="utf-8")):
            if _WRITE.search(blk):
                out.append((f"justfile::{blk.splitlines()[0]}", blk))
    scripts = REPO / "scripts"
    if scripts.exists():
        for sh in scripts.rglob("*.sh"):
            txt = sh.read_text(encoding="utf-8", errors="ignore")
            if _WRITE.search(txt):
                out.append((str(sh.relative_to(REPO)), txt))
    return out


def _hooks_dir() -> Path | None:
    """The real hooks dir, worktree-aware (common dir, not the per-worktree .git)."""
    try:
        common = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    p = Path(common)
    if not p.is_absolute():
        p = (REPO / p).resolve()
    return p / "hooks"


def test_hook_writes_are_symlink_safe() -> None:
    offenders: list[str] = []
    for label, txt in _installer_texts():
        for name in sorted(set(_WRITE.findall(txt))):
            if not (_rmf(name).search(txt) or _lnsf(name).search(txt)):
                offenders.append(
                    f"{label}: writes `> .git/hooks/{name}` without a preceding "
                    f"`rm -f` / `ln -sf` (write-through-symlink risk; see 545434c)"
                )
    assert not offenders, "hook installer can clobber a symlinked hook:\n  " + "\n  ".join(offenders)


def test_live_pre_commit_is_real_and_chains_guard() -> None:
    hooks = _hooks_dir()
    if hooks is None:
        return  # not a git checkout in this context — nothing to assert
    hook = hooks / "pre-commit"
    if not hook.exists():
        return  # hooks not installed here — `just install-hooks` not run
    assert not hook.is_symlink(), (
        f"{hook} is a symlink — installer must `rm -f` before writing (write-through risk)"
    )
    body = hook.read_text(encoding="utf-8", errors="ignore")
    assert "pre-commit-guards.sh" in body, (
        f"{hook} does not chain the guard dispatcher — possible clobbered stub (see 545434c)"
    )
