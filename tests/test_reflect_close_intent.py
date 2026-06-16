"""Integration tests for close-intent enqueue in reflect_capture.main()."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import reflect_capture as rc  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    capture = tmp_path / "reflect-capture.jsonl"
    queue = tmp_path / "close-queue"
    transcript = FIXTURES / "goal-transcript-achieved.jsonl"
    monkeypatch.setattr(rc, "CAPTURE_LOG", capture)
    monkeypatch.setattr(rc, "CLOSE_QUEUE", queue)
    return {"capture": capture, "queue": queue, "transcript": transcript}


def test_main_enqueues_tier1_on_achieved_goal(env, monkeypatch):
    monkeypatch.setattr(rc, "TESTBED", {"agent-infra"})
    payload = {
        "session_id": "probe-session-001",
        "transcript_path": str(env["transcript"]),
        "cwd": str(REPO_ROOT),
        "reason": "clear",
    }
    sys.stdin = StringIO(json.dumps(payload))
    rc.main()
    intent_path = env["queue"] / "probe-session-001.json"
    assert intent_path.exists()
    intent = json.loads(intent_path.read_text())
    assert intent["tier1_eligible"] is True
    assert intent["goal_state"]["status"] == "achieved"
