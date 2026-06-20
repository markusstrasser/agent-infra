"""Tests for pulse_tick.py — phased RSI motor."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pulse_tick as pt  # noqa: E402


def test_run_tick_writes_state(tmp_path, monkeypatch):
    monkeypatch.setattr(pt, "STATE_DIR", tmp_path)
    monkeypatch.setattr(pt, "STATE_FILE", tmp_path / "last-tick.json")
    monkeypatch.setattr(pt, "_phase_substrate", lambda: {"ok": True, "agentlogs_lag_min": 1})
    monkeypatch.setattr(pt, "_phase_drain", lambda: {"ok": True, "disposition_queue": 0})
    state = pt.run_tick(phases=("substrate", "drain"))
    assert state["exit_code"] == 0
    assert (tmp_path / "last-tick.json").is_file()
    loaded = json.loads((tmp_path / "last-tick.json").read_text())
    assert "substrate" in loaded["phases"]
    assert "drain" in loaded["phases"]
