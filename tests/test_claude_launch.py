"""Tests for scripts/claude-launch.sh — the Phase-3 launch wrapper.

Exercised via CLAUDE_LAUNCH_DRYRUN=1 (prints the decision, never execs claude or
prompts) + subprocess cwd= (no shell `cd`). Covers the four decision paths:
headless passthrough, not-a-git-repo passthrough, no-peer share, live-peer prompt.
The peer-detection truth itself is unit-tested in test_checkout_claim.py; here we
test that the wrapper branches on it correctly.
"""
from __future__ import annotations

import os
import pty
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


def test_share_path_claims_the_pid_that_becomes_claude(tmp_path: Path) -> None:
    # Real (non-dry-run) launch on a pty with a fake claude on PATH. The lock must
    # name the wrapper's $$, which exec hands to claude, not the claim helper's pid
    # (2026-10-14: the helper's pid was recorded, and macOS later reused it).
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "claude"
    fake.write_text('#!/bin/bash\necho "$$" > "$FAKE_CLAUDE_PIDFILE"\n', encoding="utf-8")
    fake.chmod(0o755)
    pidfile = tmp_path / "claude.pid"
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_LAUNCH_DRYRUN"}
    env.update(PATH=f"{bindir}:{env['PATH']}", CLAUDE_SESSION_ID="me",
               FAKE_CLAUDE_PIDFILE=str(pidfile))
    master, slave = pty.openpty()             # [ -t 0 ] must hold, as at a terminal
    try:
        r = subprocess.run(["bash", str(WRAPPER)], cwd=str(repo), env=env, stdin=slave,
                           capture_output=True, text=True, timeout=60)
    finally:
        os.close(slave)
        os.close(master)
    assert r.returncode == 0, r.stderr
    assert "claim failed" not in r.stderr
    c = cc.read_claim(repo)
    assert c is not None and c.session_id == "me"
    assert c.pid == int(pidfile.read_text(encoding="utf-8"))
    assert c.proc_start
