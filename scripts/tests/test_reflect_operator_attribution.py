"""Operator attribution in reflect capture: only operator-typed text may become a signal.

Regressions (steward proposals 2026-07-12 and 2026-07-15):
- a headless `claude -p` grader's own prompt was quoted as `operator_added_value`
  and fired operator_dx (session 5e968e6b);
- teammate relays ("Another Claude session sent a message: <teammate-message …>")
  and <local-command-stdout> frames were 4 of 4 operator_dx items in digest b49d6a14;
- 48 of 49 captured fail_then_user rescues were the harness interrupt marker.

Line shapes mirror what Claude Code writes (entrypoint / promptSource / origin
stamps, surveyed over 489 transcripts on 2026-09-23). The behaviour tests import
only reflect_capture so they run unchanged against the pre-fix module.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import reflect_capture as rc  # noqa: E402

OPERATOR_STAMP = {"entrypoint": "cli", "promptSource": "typed", "origin": {"kind": "human"}}


def _user(text: str, **stamps) -> dict:
    return {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "text", "text": text}]},
        **stamps,
    }


def _tool_use(name: str, inp: dict) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "tool_use", "name": name, "input": inp}]},
    }


def _tool_result(*, is_error: bool) -> dict:
    return {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "tool_result", "is_error": is_error, "content": "x"}]},
    }


def _signals(objs: list[dict]) -> list[dict]:
    return rc.extract_signals(rc.parse_events([json.dumps(o) for o in objs]), [])


def _operator_rows(signals: list[dict]) -> list[dict]:
    return [s for s in signals if s["subtype"] in ("operator_dx", "f_tag", "negation", "fail_then_user")]


HEADLESS_PROMPT = _user(
    "You review an AI coding agent's final message. #f flag it when you ask why did you stop "
    "early, and check RSI discipline. Don't flag uncertain cases.",
    entrypoint="sdk-cli",
    promptSource="sdk",
)
TEAMMATE_RELAY = _user(
    'Another Claude session sent a message: <teammate-message teammate_id="sess-analyst" '
    'color="blue">why didn\'t you find the existing RSI tooling? that\'s not it</teammate-message>',
    entrypoint="cli",
)
LOCAL_COMMAND = _user(
    "<local-command-stdout>Compacted. PreCompact hook RSI digest: wrong turn noted</local-command-stdout>",
    entrypoint="cli",
)
INTERRUPT = _user("[Request interrupted by user for tool use]", entrypoint="cli")
STAMPED_NOTIFICATION = _user(
    "3 background agents finished. #f one reported: why did you stop the RSI sweep?",
    entrypoint="cli",
    promptSource="system",
    origin={"kind": "task-notification"},
)


class TestIsOperatorAuthored:
    """The canonical predicate (common.transcript_text) — imported per test on purpose."""

    @staticmethod
    def _pred():
        from common.transcript_text import is_operator_authored

        return is_operator_authored

    def test_typed_and_queued_operator_lines(self):
        pred = self._pred()
        assert pred(_user("go on", **OPERATOR_STAMP))
        assert pred(_user("also check X", entrypoint="cli", promptSource="queued", origin={"kind": "human"}))

    def test_origin_stamp_decides(self):
        pred = self._pred()
        assert not pred(STAMPED_NOTIFICATION)
        assert not pred(_user("limit reset, continue", origin={"kind": "auto-continuation"}))
        assert not pred(_user("please review", origin={"kind": "peer", "from": "uds:/tmp/x"}))

    def test_headless_dispatch_is_not_operator(self):
        pred = self._pred()
        assert not pred(HEADLESS_PROMPT)
        assert not pred(_user("Watch tick — read the log", entrypoint="sdk-cli"))
        assert not pred(_user("Fallback tick for session", entrypoint="cli", promptSource="system"))

    def test_unstamped_frames_are_not_operator(self):
        pred = self._pred()
        for obj in (TEAMMATE_RELAY, LOCAL_COMMAND, INTERRUPT):
            assert not pred(obj), obj["message"]["content"][0]["text"][:40]
        assert not pred(_user('<teammate-message teammate_id="x">hi</teammate-message>'))
        assert not pred(_user("<local-command-caveat>Caveat: local commands</local-command-caveat>"))

    def test_legacy_unstamped_operator_text_still_counts(self):
        pred = self._pred()
        assert pred(_user("#f you skipped the bridge step"))
        assert pred({"role": "user", "content": "flat legacy form"})

    def test_non_text_and_harness_lines_are_not_operator(self):
        pred = self._pred()
        assert not pred(_tool_result(is_error=True))
        assert not pred(_user("summary #f", isCompactSummary=True))
        assert not pred(_user("skill body", isMeta=True))
        assert not pred({"type": "assistant", "message": {"role": "assistant", "content": "hi"}})


class TestCaptureAttribution:
    def test_headless_prompt_yields_no_operator_signal(self):
        assert _operator_rows(_signals([HEADLESS_PROMPT])) == []

    def test_teammate_relay_yields_no_operator_signal(self):
        assert _operator_rows(_signals([_tool_use("Bash", {"command": "ls"}), TEAMMATE_RELAY])) == []

    def test_local_command_output_yields_no_operator_signal(self):
        assert _operator_rows(_signals([_tool_use("Bash", {"command": "ls"}), LOCAL_COMMAND])) == []

    def test_stamped_notification_yields_no_f_tag(self):
        assert _operator_rows(_signals([STAMPED_NOTIFICATION])) == []

    def test_interrupt_marker_is_not_a_rescue(self):
        seq = [_tool_use("Bash", {"command": "boom"}), _tool_result(is_error=True), INTERRUPT]
        assert _operator_rows(_signals(seq)) == []

    def test_operator_follow_up_after_interrupt_is_the_rescue(self):
        seq = [
            _tool_use("Bash", {"command": "boom"}),
            _tool_result(is_error=True),
            INTERRUPT,
            _user("use the staging db instead", **OPERATOR_STAMP),
        ]
        rescues = [s for s in _signals(seq) if s["subtype"] == "fail_then_user"]
        assert [r["trigger"] for r in rescues] == ["use the staging db instead"]

    def test_operator_text_still_fires(self):
        dx = [s for s in _signals([_user("why did you stop?", **OPERATOR_STAMP)]) if s["subtype"] == "operator_dx"]
        assert len(dx) == 1 and dx[0]["operator_added_value"] == "why did you stop?"
        tags = [s for s in _signals([_user("#f you skipped the sync")]) if s["subtype"] == "f_tag"]
        assert len(tags) == 1

    def test_notification_does_not_break_a_blind_retry_run(self):
        seq = [
            _tool_use("Bash", {"command": "pytest -k a"}),
            _tool_use("Bash", {"command": "pytest -k b"}),
            STAMPED_NOTIFICATION,
            _tool_use("Bash", {"command": "pytest -k c"}),
        ]
        assert [s["subtype"] for s in _signals(seq)].count("retry_run") == 1


def test_headless_session_end_queues_no_tier1_close(tmp_path, monkeypatch):
    """End to end: the 5e968e6b shape — a headless grader session — must not queue a
    Tier-1 close on the strength of its own dispatch prompt."""
    monkeypatch.setattr(rc, "CAPTURE_LOG", tmp_path / "reflect-capture.jsonl")
    monkeypatch.setattr(rc, "CLOSE_QUEUE", tmp_path / "close-queue")
    monkeypatch.setattr(rc, "TESTBED", {"arc-agi"})
    project = tmp_path / "arc-agi"
    project.mkdir()
    transcript = tmp_path / "5e968e6b.jsonl"
    transcript.write_text(
        "\n".join(json.dumps(o) for o in (HEADLESS_PROMPT, _tool_use("Read", {"file_path": "a.py"}))) + "\n",
        encoding="utf-8",
    )
    payload = {"session_id": "5e968e6b-0000", "cwd": str(project), "transcript_path": str(transcript)}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert rc.main() == 0
    log = tmp_path / "reflect-capture.jsonl"
    rows = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    assert _operator_rows(rows) == []
    intent = json.loads((tmp_path / "close-queue" / "5e968e6b-0000.json").read_text())
    assert intent["tier1_eligible"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
