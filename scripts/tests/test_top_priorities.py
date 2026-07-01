"""Tests for top_priorities failure ranking."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import top_priorities as tp  # noqa: E402


def test_broken_tools_suppresses_shell_env_when_gate_healthy(monkeypatch, tmp_path: Path):
    failures = [
        {
            "cluster": "zsh-env:parse-error",
            "fails": 9,
            "distinct_days": 4,
            "last_seen": "2026-07-01T11:51",
            "sample": "(eval):5: parse error near `if'",
        }
    ]

    monkeypatch.setattr(tp, "FAILURES_SCRIPT", tmp_path / "scan_tool_failures.py")
    tp.FAILURES_SCRIPT.write_text("# stub")
    monkeypatch.setattr(tp, "_run_json", lambda _cmd: failures)
    monkeypatch.setattr(
        tp.shell_env_loop_gate,
        "assess",
        lambda **_kwargs: {"cross_harness_healthy": True, "promote_actionable": False},
    )

    assert not [row for row in tp.broken_tools() if row["title"].startswith("Shell env:")]


def test_broken_tools_keeps_shell_env_when_gate_promotes(monkeypatch, tmp_path: Path):
    failures = [
        {
            "cluster": "zsh-env:parse-error",
            "fails": 9,
            "distinct_days": 4,
            "last_seen": "2026-07-01T11:51",
            "sample": "(eval):5: parse error near `if'",
        }
    ]

    monkeypatch.setattr(tp, "FAILURES_SCRIPT", tmp_path / "scan_tool_failures.py")
    tp.FAILURES_SCRIPT.write_text("# stub")
    monkeypatch.setattr(tp, "_run_json", lambda _cmd: failures)
    monkeypatch.setattr(
        tp.shell_env_loop_gate,
        "assess",
        lambda **_kwargs: {"cross_harness_healthy": False, "promote_actionable": True},
    )

    rows = tp.broken_tools()
    assert [row for row in rows if row["title"].startswith("Shell env: zsh parse-error")]
