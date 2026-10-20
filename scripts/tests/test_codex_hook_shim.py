"""Tests for codex_hook_shim.py — Claude-dialect hook output -> Codex contract."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SHIM = Path(__file__).resolve().parents[1] / "codex_hook_shim.py"


def test_pending_tool_receipt_is_correlated_without_values(tmp_path: Path) -> None:
    sentinel = "FAKE_SENSITIVE_VALUE_never_log"
    log = tmp_path / ".codex/log/hook_shim_invocations.jsonl"
    log.parent.mkdir(parents=True)
    payload = json.dumps({"tool_name": "Bash", "tool_use_id": sentinel,
                          "tool_input": {"command": sentinel, "timeout_ms": 123}})
    result = run_shim("exit 0", "PreToolUse", payload,
                      extra_env={"HOME": str(tmp_path)})
    receipt = json.loads(log.read_text())
    assert receipt["pending_tool"] == {
        "shape": "valid", "tool_name": "Bash",
        "tool_input_keys": ["command", "timeout_ms"],
        "tool_use_id_sha256": hashlib.sha256(sentinel.encode()).hexdigest(),
    }
    assert sentinel not in log.read_text() + result.stdout + result.stderr
    assert result.returncode == 0


def test_malformed_pending_tool_receipt_preserves_block(tmp_path: Path) -> None:
    log = tmp_path / ".codex/log/hook_shim_invocations.jsonl"
    log.parent.mkdir(parents=True)
    for payload, shape in [("[]", "not_object"), ("null", "not_object"),
                           ("not-json", "invalid_json"),
                           ('{"tool_name":"Bash","tool_input":[]}', "invalid_fields")]:
        result = run_shim("printf blocked >&2; exit 2", "PreToolUse", payload,
                          extra_env={"HOME": str(tmp_path)})
        receipt = json.loads(log.read_text().splitlines()[-1])
        assert receipt["pending_tool"]["shape"] == shape
        assert result.returncode == 2
        assert result.stderr == "blocked"


def test_pending_tool_metadata_does_not_affect_other_events(tmp_path: Path) -> None:
    log = tmp_path / ".codex/log/hook_shim_invocations.jsonl"
    log.parent.mkdir(parents=True)
    result = run_shim("exit 0", "SessionStart", extra_env={"HOME": str(tmp_path)})
    assert "pending_tool" not in json.loads(log.read_text())
    assert result.returncode == 0


def test_oversized_invocation_log_is_rotated_not_lost(tmp_path: Path) -> None:
    log = tmp_path / ".codex/log/hook_shim_invocations.jsonl"
    log.parent.mkdir(parents=True)
    with log.open("wb") as f:  # sparse: past the threshold without using disk
        f.truncate(256 * 1024 * 1024)
    result = run_shim("exit 0", "SessionStart", extra_env={"HOME": str(tmp_path)})
    assert result.returncode == 0
    assert len(log.read_text().splitlines()) == 1
    assert list(log.parent.glob("hook_shim_invocations-until-*.jsonl*"))


def test_unencodable_tool_id_keeps_each_receipt_and_inner_contract(tmp_path: Path) -> None:
    log = tmp_path / ".codex/log/hook_shim_invocations.jsonl"
    log.parent.mkdir(parents=True)
    for count, tool_id in enumerate(["\ud800", "\udfff"], start=1):
        payload = json.dumps({"tool_name": "Bash", "tool_use_id": tool_id,
                              "tool_input": {"command": "FAKE_SECRET_VALUE"}})
        # A real child compares exact stdin without reflecting it to either stream.
        import shlex
        inner = (f"{shlex.quote(sys.executable)} -c " + shlex.quote(
            "import sys; expected=" + repr(payload) +
            "; assert sys.stdin.read()==expected; "
            "print('safe output'); print('blocked',file=sys.stderr); sys.exit(2)"))
        result = run_shim(inner, "PreToolUse", payload, extra_env={"HOME": str(tmp_path)})
        assert result.returncode == 2
        assert result.stderr == "blocked\n"
        assert json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"] == "safe output"
        lines = log.read_text().splitlines() if log.exists() else []
        assert len(lines) == count
        receipt = json.loads(lines[-1])
        assert receipt["rc"] == 2 and receipt["event"] == "PreToolUse"
        assert isinstance(receipt["duration_ms"], int)
        assert receipt["pending_tool"] == {"shape": "invalid_fields", "tool_name": "Bash",
                                           "tool_input_keys": ["command"]}
        assert "FAKE_SECRET_VALUE" not in log.read_text() + result.stdout + result.stderr


def run_shim(
    inner_cmd: str,
    event: str,
    payload: str = "{}",
    *,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    env = {"CODEX_HOOK_EVENT": event, "PATH": "/usr/bin:/bin"}
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, str(SHIM), inner_cmd],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
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


def test_noop_hook_does_not_probe_process_tree_for_unused_tty(tmp_path: Path) -> None:
    ps_marker = tmp_path / "ps-called"
    fake_ps = tmp_path / "ps"
    fake_ps.write_text(
        f"#!/bin/sh\nprintf called > {ps_marker}\n",
        encoding="utf-8",
    )
    fake_ps.chmod(0o755)

    res = run_shim(
        "exit 0",
        "PreToolUse",
        extra_env={"PATH": str(tmp_path)},
    )

    assert res.returncode == 0
    assert not ps_marker.exists()


def test_pending_title_is_claimed_before_lazy_tty_probe(tmp_path: Path) -> None:
    ps_marker = tmp_path / "ps-called"
    pid_capture = tmp_path / "agent-pid"
    fake_ps = tmp_path / "ps"
    fake_ps.write_text(
        f"#!/bin/sh\nprintf called >> {ps_marker}\n",
        encoding="utf-8",
    )
    fake_ps.chmod(0o755)
    inner = (
        'printf "%s" "$COCKPIT_AGENT_PID" > "$PID_CAPTURE"; '
        'printf title > "/tmp/cockpit-tab-pending-${COCKPIT_AGENT_PID}"'
    )

    res = run_shim(
        inner,
        "PreToolUse",
        extra_env={"PATH": str(tmp_path), "PID_CAPTURE": str(pid_capture)},
    )

    assert res.returncode == 0
    assert ps_marker.exists()
    agent_pid = pid_capture.read_text(encoding="utf-8")
    assert not Path(f"/tmp/cockpit-tab-pending-{agent_pid}").exists()
