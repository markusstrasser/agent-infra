"""Tests for scripts/claude-launch.sh — the Phase-3 launch wrapper.

Exercised via CLAUDE_LAUNCH_DRYRUN=1 (prints the decision, never execs claude or
prompts) + subprocess cwd= (no shell `cd`). Covers the four decision paths:
headless passthrough, not-a-git-repo passthrough, no-peer share, live-peer prompt.
The peer-detection truth itself is unit-tested in test_checkout_claim.py; here we
test that the wrapper branches on it correctly.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "claude-launch.sh"
sys.path.insert(0, str(ROOT / "scripts"))
import checkout_claim as cc


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)


def _run(cwd: Path, *args: str, session: str = "me") -> str:
    env = {**os.environ, "CLAUDE_LAUNCH_DRYRUN": "1", "CLAUDE_SESSION_ID": session}
    r = subprocess.run(["bash", str(WRAPPER), *args], cwd=str(cwd),
                       env=env, capture_output=True, text=True, timeout=60)
    return r.stdout + r.stderr


def test_headless_passthrough(tmp_path: Path) -> None:
    _git_init(tmp_path)
    out = _run(tmp_path, "-p", "hello")
    assert "[dry-run] exec" in out
    assert "-p" in out
    assert "live peer" not in out          # headless never reaches peer detection


def test_not_a_git_repo_passthrough(tmp_path: Path) -> None:
    out = _run(tmp_path)                     # no git init
    assert "[dry-run] exec" in out
    assert "live peer" not in out


def test_no_peer_share(tmp_path: Path) -> None:
    _git_init(tmp_path)                      # git repo, but no claim lock
    out = _run(tmp_path)
    assert "[dry-run] exec" in out
    assert "would prompt" not in out         # nothing held it → straight to share


def test_live_peer_triggers_prompt(tmp_path: Path) -> None:
    _git_init(tmp_path)
    # A live peer (my own pid) under a DIFFERENT session holds the checkout.
    cc.claim(tmp_path, "peer-session", pid=os.getpid())
    out = _run(tmp_path, session="me")
    assert "live peer" in out
    assert "would prompt" in out             # wrapper branches into the prompt path
