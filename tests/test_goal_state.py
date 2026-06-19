"""Tests for scripts/goal_state.py — goal detection for RSI session-close gating."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import goal_state as gs  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def _lines(name: str) -> list[str]:
    return (FIXTURES / name).read_text(encoding="utf-8").splitlines()


class TestGoalStateFromTranscript:
    def test_achieved_fixture_primary_marker(self):
        state = gs.goal_state_from_transcript(_lines("goal-transcript-achieved.jsonl"))
        assert state["status"] == "achieved"
        assert state["source"] == "claude_transcript"
        assert state["evidence_ts"] == "2026-06-15T09:00:20.000Z"
        assert "goal_status.met=true" in state["raw_ref"]

    def test_active_fixture(self):
        state = gs.goal_state_from_transcript(_lines("goal-transcript-active.jsonl"))
        assert state["status"] == "active"

    def test_explicit_rsi_close(self):
        lines = [
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": "/rsi close"}],
                    },
                    "timestamp": "2026-06-15T11:00:00Z",
                }
            )
        ]
        state = gs.goal_state_from_transcript(lines)
        assert state["status"] == "achieved"
        assert state["source"] == "explicit_rsi_close"

    def test_goal_clear(self):
        lines = [
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": "/goal clear"}],
                    },
                    "timestamp": "2026-06-15T11:00:00Z",
                }
            )
        ]
        state = gs.goal_state_from_transcript(lines)
        assert state["status"] == "cleared"

    def test_unknown_degraded_on_unrecognized_attachment(self):
        lines = [
            json.dumps(
                {
                    "type": "attachment",
                    "attachment": {"type": "goal_status", "weird": True},
                    "timestamp": "2026-06-15T11:00:00Z",
                }
            )
        ]
        state = gs.goal_state_from_transcript(lines)
        assert state["status"] == "unknown"
        assert state.get("degraded") is True

    def test_live_probe_fixture(self):
        live = FIXTURES / "goal-transcript-achieved-live.jsonl"
        if not live.exists():
            pytest.skip("live probe fixture not present")
        state = gs.goal_state_from_transcript(live.read_text(encoding="utf-8").splitlines())
        assert state["status"] == "achieved"
        assert state["evidence_ts"] == "2026-06-15T10:50:06.744Z"
        assert "goal_status.met=true" in state["raw_ref"]
        assert "probe-ok.txt" in (state.get("objective") or "")

        lines = _lines("goal-transcript-achieved.jsonl")
        state = gs.goal_state_from_transcript(lines)
        episode = gs.slice_transcript_to_episode(lines, state["evidence_ts"])
        assert len(episode) == 5
        assert "one more thing" not in "\n".join(episode)


class TestGoalStateFromCodex:
    def test_complete_maps_to_achieved(self):
        goal = json.loads((FIXTURES / "codex-goal-complete.json").read_text())
        state = gs.goal_state_from_codex(goal)
        assert state["status"] == "achieved"
        assert state["source"] == "codex_app_server"

    def test_blocked(self):
        goal = json.loads((FIXTURES / "codex-goal-blocked.json").read_text())
        state = gs.goal_state_from_codex(goal)
        assert state["status"] == "blocked"

    def test_null_is_cleared(self):
        state = gs.goal_state_from_codex(None)
        assert state["status"] == "cleared"


class TestTier1Eligible:
    @pytest.mark.parametrize(
        "status,source,real_issue,expected",
        [
            ("achieved", "claude_transcript", False, True),
            ("active", "claude_transcript", False, False),
            ("blocked", "codex_app_server", False, False),
            ("unknown", "claude_transcript", False, False),
            ("unknown", "none", True, True),
        ],
    )
    def test_gating(self, status, source, real_issue, expected):
        goal_state = {"status": status, "source": source}
        if status == "unknown" and not real_issue:
            goal_state["degraded"] = True
        eligible, _reason = gs.tier1_eligible(goal_state, real_issue=real_issue)
        assert eligible is expected
