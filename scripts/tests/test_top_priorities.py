"""Tests for top_priorities failure ranking."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import top_priorities as tp  # noqa: E402


def _recent_ts() -> str:
    """A last_seen inside the FAILURE_STALE_DAYS recency gate — a hardcoded date
    here rotted past the gate and silently flipped both tests (2026-07-06)."""
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")



def test_broken_tools_suppresses_shell_env_when_gate_healthy(monkeypatch, tmp_path: Path):
    failures = [
        {
            "cluster": "zsh-env:parse-error",
            "fails": 9,
            "distinct_days": 4,
            "last_seen": _recent_ts(),
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
            "last_seen": _recent_ts(),
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


def test_open_findings_ignores_nested_status_under_behavioral_header(tmp_path: Path, monkeypatch):
    """April noise class: `- **Status:** [ ]` under a retro header without `[ ]` in ###."""
    log = tmp_path / "improvement-log.md"
    log.write_text(
        "### [2026-04-18] SKILL EXECUTION FAILURE: brainstorm bypassed\n"
        "- **Status:** [ ] proposed\n"
        "### [2026-06-13] [ ] HOOK: lose +x bits\n"
        "- **Status:** [ ] proposed\n"
        "- [ ] **Evaluate Tool(param:value) rules** — still open\n"
    )
    monkeypatch.setattr(tp, "IMPROVEMENT_LOG", log)
    rows = tp.open_findings()
    titles = [r["title"] for r in rows]
    assert not any(t.startswith("[2026-04") for t in titles)
    assert any("[ ] HOOK: lose +x" in t for t in titles)
    assert any("Evaluate Tool(param:value)" in t for t in titles)
