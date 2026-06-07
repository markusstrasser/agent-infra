"""Tests for codex_hook_shim.py — Claude-dialect hook output -> Codex contract."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SHIM = Path(__file__).resolve().parents[1] / "codex_hook_shim.py"


def run_shim(inner_cmd: str, event: str, payload: str = "{}") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SHIM), inner_cmd],
        input=payload,
        text=True,
        capture_output=True,
        env={"CODEX_HOOK_EVENT": event, "PATH": "/usr/bin:/bin"},
    )


def test_top_level_additional_context_is_rewrapped() -> None:
    inner = """printf '%s' '{"decision":"allow","additionalContext":"use /epistemics"}'"""
    res = run_shim(inner, "PreToolUse")
    assert res.returncode == 0
    out = json.loads(res.stdout)
    assert "additionalContext" not in out  # lifted out of top level
    hs = out["hookSpecificOutput"]
    assert hs["hookEventName"] == "PreToolUse"
    assert hs["additionalContext"] == "use /epistemics"


def test_exit2_with_stdout_decision_gets_stderr_reason() -> None:
    inner = """printf '%s' '{"decision":"block","reason":"PROCESS CEILING"}'; exit 2"""
    res = run_shim(inner, "PreToolUse")
    assert res.returncode == 2
    assert "PROCESS CEILING" in res.stderr  # reason copied to stderr for Codex
    assert json.loads(res.stdout)["decision"] == "block"


def test_exit2_plain_stderr_passthrough() -> None:
    # data-guard style: reason already on stderr, exit 2.
    inner = """printf 'BLOCKED: data/ is read-only' >&2; exit 2"""
    res = run_shim(inner, "PreToolUse")
    assert res.returncode == 2
    assert res.stderr.strip() == "BLOCKED: data/ is read-only"
    assert res.stdout == ""


def test_noop_hook_emits_nothing() -> None:
    res = run_shim("exit 0", "PreToolUse")
    assert res.returncode == 0
    assert res.stdout == ""
    assert res.stderr == ""


def test_non_json_stdout_on_strict_event_becomes_additional_context() -> None:
    inner = """printf 'just a reminder'"""
    res = run_shim(inner, "PreToolUse")
    assert res.returncode == 0
    out = json.loads(res.stdout)
    assert out["hookSpecificOutput"]["additionalContext"] == "just a reminder"


def test_plain_text_passthrough_on_sessionstart() -> None:
    inner = """printf 'context line'"""
    res = run_shim(inner, "SessionStart")
    assert res.returncode == 0
    assert res.stdout == "context line"  # SessionStart accepts plain text


def test_payload_reaches_inner_hook_on_stdin() -> None:
    inner = """cat"""  # echoes stdin to stdout
    res = run_shim(inner, "SessionStart", payload="hello-payload")
    assert "hello-payload" in res.stdout


def test_block_decision_without_reason_gets_one() -> None:
    inner = """printf '%s' '{"decision":"block"}'; exit 2"""
    res = run_shim(inner, "PreToolUse")
    assert res.returncode == 2
    out = json.loads(res.stdout)
    assert out["reason"]  # non-empty reason synthesized
    assert res.stderr.strip()  # and mirrored to stderr
