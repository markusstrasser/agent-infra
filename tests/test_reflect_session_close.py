"""Tests for scripts/reflect_session_close.py — async digest drain."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import reflect_session_close as rsc  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def paths(tmp_path, monkeypatch):
    queue = tmp_path / "close-queue"
    digest = tmp_path / "reflect-close-digest.jsonl"
    capture = tmp_path / "reflect-capture.jsonl"
    transcript = FIXTURES / "goal-transcript-achieved.jsonl"
    monkeypatch.setattr(rsc, "CLOSE_QUEUE", queue)
    monkeypatch.setattr(rsc, "DIGEST_LOG", digest)
    monkeypatch.setattr(rsc, "CAPTURE_LOG", capture)
    monkeypatch.setattr(rsc, "MAINTAIN", tmp_path / "MAINTAIN.md")
    return {"queue": queue, "digest": digest, "transcript": transcript}


def _write_intent(queue: Path, session: str, transcript: Path, tier1: bool = True) -> Path:
    queue.mkdir(parents=True, exist_ok=True)
    intent = {
        "schema": "reflect.close-intent.v1",
        "session_id": session,
        "project": "agent-infra",
        "ts": "2026-06-15T12:00:00+00:00",
        "reason": "clear",
        "transcript_path": str(transcript),
        "goal_state": {
            "source": "claude_transcript",
            "status": "achieved" if tier1 else "active",
            "evidence_ts": "2026-06-15T09:00:20.000Z",
            "raw_ref": "fixture",
        },
        "tier1_eligible": tier1,
        "tier1_reason": "goal_achieved" if tier1 else "goal_still_active",
        "processed": False,
    }
    path = queue / f"{session}.json"
    path.write_text(json.dumps(intent), encoding="utf-8")
    return path


class TestReflectSessionClose:
    def test_build_digest_eligible(self, paths):
        intent = {
            "session_id": "sess-001",
            "project": "agent-infra",
            "transcript_path": str(paths["transcript"]),
            "reason": "clear",
            "goal_state": {
                "status": "achieved",
                "evidence_ts": "2026-06-15T09:00:20.000Z",
            },
        }
        digest = rsc.build_digest(intent)
        assert digest is not None
        assert digest["tier1_reason"] == "goal_achieved"
        assert digest["episode_line_count"] == 5
        assert digest["invoke_skill"] is True

    def test_build_digest_skips_active_goal(self, paths):
        intent = {
            "session_id": "sess-002",
            "project": "agent-infra",
            "transcript_path": str(paths["transcript"]),
            "goal_state": {"status": "active"},
        }
        assert rsc.build_digest(intent) is None

    def test_drain_writes_digest(self, paths):
        _write_intent(paths["queue"], "sess-drain", paths["transcript"])
        count = rsc.drain_queue(limit=5)
        assert count == 1
        lines = paths["digest"].read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["schema"] == "reflect.close-digest.v1"

    def test_pending_nudge_after_digest(self, paths):
        _write_intent(paths["queue"], "sess-nudge", paths["transcript"])
        rsc.drain_queue()
        nudge = rsc.pending_nudge()
        assert nudge is not None
        assert "/rsi close" in nudge

    def test_pending_nudge_cleared_after_ack(self, paths):
        _write_intent(paths["queue"], "sess-nudge", paths["transcript"])
        rsc.drain_queue()
        rsc.ack_digest("sess-nudge")
        assert rsc.pending_nudge() is None
