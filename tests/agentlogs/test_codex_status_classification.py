from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentlogs.adapters.codex import _is_error_payload


def _shell_output(first_line: str, body: str = "") -> list[dict]:
    """Shape of codex exec/wait function_call_output payloads."""
    return [
        {"type": "input_text", "text": f"{first_line}\nWall time 9.5 seconds\nOutput:\n"},
        {"type": "input_text", "text": body},
    ]


def test_script_completed_with_error_in_body_is_success() -> None:
    # 2026-07-17 re-scan: 1,702/2,169 `wait` "errors" were completed polls whose
    # script stdout happened to contain the word "error".
    payload = _shell_output("Script completed", "╭─ Error ─╮\n│ No such file or directory │")
    assert not _is_error_payload(payload)


def test_script_running_poll_is_success() -> None:
    payload = _shell_output("Script running with cell ID 77", "partial error text")
    assert not _is_error_payload(payload)


def test_script_failed_is_error() -> None:
    assert _is_error_payload(_shell_output("Script failed"))


def test_aborted_by_user_is_error() -> None:
    assert _is_error_payload([{"type": "input_text", "text": "aborted by user after 0.4s"}])


def test_structured_error_flag_wins_over_verdict_line() -> None:
    assert _is_error_payload({"is_error": True, "output": "Script completed"})


def test_substring_fallback_without_verdict_line() -> None:
    assert _is_error_payload("Traceback: ValueError exception raised")
    assert not _is_error_payload("all files written")
