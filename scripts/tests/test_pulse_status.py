"""Tests for pulse.py status — additive control-plane inbox."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pulse  # noqa: E402


def test_canary_summary_flags_constant_history(tmp_path, monkeypatch):
    now = 1_700_000_000.0
    hist = tmp_path / "pulse-canary-history.jsonl"
    rows = [{"name": "supervision.hooks_shown", "value": 0.0, "ts": now - i} for i in range(5)]
    hist.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    monkeypatch.setattr(pulse, "HISTORY", hist)
    summary = pulse.canary_summary(now=now)
    assert summary["alarm_count"] == len(pulse.INSTRUMENTS)


def test_status_needs_attention_on_questions():
    m = {
        "funnel_needs_attention": False,
        "questions_count": 2,
        "canary": {"alarm_count": 0},
        "predictions_due": [],
        "maintain_draft": None,
    }
    assert pulse.status_needs_attention(m)


def test_status_needs_attention_green():
    m = {
        "funnel_needs_attention": False,
        "questions_count": 0,
        "canary": {"alarm_count": 0},
        "predictions_due": [],
        "maintain_draft": None,
    }
    assert not pulse.status_needs_attention(m)


def test_cmd_status_write_inbox_clears_when_green(tmp_path, monkeypatch):
    inbox = tmp_path / "control-plane-inbox.md"
    inbox.write_text("stale")
    monkeypatch.setattr(
        pulse,
        "gather_status",
        lambda _repo=None: {
            "funnel": {
                "captured": 0,
                "classified": 0,
                "unclassified": 0,
                "quarantine_pending": 0,
                "steward_proposals": 0,
                "rsi_close_pending": 0,
                "close_queue_open": 0,
                "fm_evidence_rows": 0,
                "disposition_queue": 0,
                "rsi_pending": [],
                "quarantine": [],
                "session_split_7d": {},
            },
            "funnel_needs_attention": False,
            "questions_count": 0,
            "questions_section": "",
            "predictions_due": [],
            "canary": {"alarm_count": 0, "alarms": [], "ok": []},
            "maintain_draft": None,
            "priorities": [],
        },
    )

    class Args:
        json = False
        write_inbox = True
        inbox_path = str(inbox)

    assert pulse.cmd_status(Args()) == 0
    assert not inbox.exists()


def test_cmd_status_write_inbox_when_attention(tmp_path, monkeypatch):
    inbox = tmp_path / "control-plane-inbox.md"
    monkeypatch.setattr(
        pulse,
        "gather_status",
        lambda _repo=None: {
            "funnel": {
                "captured": 1,
                "classified": 1,
                "unclassified": 0,
                "quarantine_pending": 0,
                "steward_proposals": 0,
                "rsi_close_pending": 0,
                "close_queue_open": 0,
                "fm_evidence_rows": 0,
                "disposition_queue": 0,
                "rsi_pending": [],
                "quarantine": [],
                "session_split_7d": {},
            },
            "funnel_needs_attention": False,
            "questions_count": 1,
            "questions_section": "## Questions for you\n- test?",
            "predictions_due": [],
            "canary": {"alarm_count": 0, "alarms": [], "ok": [{"name": "x", "level": "ok", "reason": "ok", "note": ""}]},
            "maintain_draft": None,
            "priorities": [],
            "tick": None,
        },
    )

    class Args:
        json = False
        write_inbox = True
        inbox_path = str(inbox)

    assert pulse.cmd_status(Args()) == 0
    assert inbox.is_file()
    assert "Control plane" in inbox.read_text()
