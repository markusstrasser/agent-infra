#!/usr/bin/env python3
"""Tests for stop-bg-job-liveness.py.

Carries the positive-control PAIR the watcher-arming rule demands (F12): a
synthetic POSITIVE (the advisory must actually fire on the failure it exists for)
AND the zero-match negatives (it must stay silent on every legitimate shape). A
gate that only proves it can stay quiet has proved nothing.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

HOOK = Path(__file__).parent / "stop-bg-job-liveness.py"
spec = importlib.util.spec_from_file_location("bgliveness", HOOK)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _transcript(tmp_path: Path, assistant_text: str) -> str:
    p = tmp_path / "transcript.jsonl"
    rows = [
        {"message": {"role": "user", "content": "go"}},
        {
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": assistant_text}],
            }
        },
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return str(p)


def _tasks(tmp_path: Path, session: str, jobs: dict[str, str]) -> None:
    d = tmp_path / "claude-501" / "-slug" / session / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    for job_id, content in jobs.items():
        (d / f"{job_id}.output").write_text(content)


def _run(monkeypatch, capsys, tmp_path, *, text, jobs, holders, session="sess-abc123"):
    _tasks(tmp_path, session, jobs)
    monkeypatch.setattr(mod, "_task_outputs", lambda s: sorted(
        str(p) for p in (tmp_path / "claude-501" / "-slug" / session / "tasks").glob("*.output")
    ))
    monkeypatch.setattr(mod, "_holders", lambda path: holders)
    # Never let dedupe suppress a test assertion.
    monkeypatch.setattr(mod, "_deduped", lambda s, j: False)
    envelope = {
        "session_id": session,
        "transcript_path": _transcript(tmp_path, text),
        "stop_hook_active": False,
    }
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps(envelope)))
    rc = mod.main()
    return rc, capsys.readouterr().err


# ---------------------------------------------------------------- positives

def test_fires_when_awaited_job_is_gone(monkeypatch, capsys, tmp_path):
    """The exact benchmarks.bio signature: awaiting a job with zero holders."""
    rc, err = _run(
        monkeypatch, capsys, tmp_path,
        text=(
            "I'll stop polling and end my turn here. The background monitor "
            "b7refde6z will surface the motif activity tables when the scan finishes."
        ),
        jobs={"b7refde6z": "scanning...\npartial row 1\n"},
        holders=[],
    )
    assert rc == 0
    assert "NOT RUNNING" in err
    assert "b7refde6z" in err
    assert "partial row 1" in err  # the tail is handed back, not just a verdict


def test_says_ending_the_turn_is_correct(monkeypatch, capsys, tmp_path):
    """Anti-ratchet: the gate must authorize stopping, not only push 'keep going'."""
    _, err = _run(
        monkeypatch, capsys, tmp_path,
        text="Waiting for the helper to finish before I end the turn.",
        jobs={"bhelper01": "done\n"},
        holders=[],
    )
    assert "ENDING THE TURN IS CORRECT" in err


def test_generic_await_without_named_id_still_fires(monkeypatch, capsys, tmp_path):
    _, err = _run(
        monkeypatch, capsys, tmp_path,
        text="The job is still running; I'll report once it completes.",
        jobs={"bz76vjrcw": "output\n"},
        holders=[],
    )
    assert "NOT RUNNING" in err


# ---------------------------------------------------------------- negatives

def test_silent_when_job_is_actually_live(monkeypatch, capsys, tmp_path):
    """A real wait is legitimate — nagging it is the iatrogenic failure."""
    rc, err = _run(
        monkeypatch, capsys, tmp_path,
        text="Waiting for the scan to finish; I'll report when it completes.",
        jobs={"bi4f9yfdw": "tick 1\n"},
        holders=["51587", "51660"],
    )
    assert rc == 0
    assert err == ""


def test_silent_when_not_awaiting(monkeypatch, capsys, tmp_path):
    """Turn finished and merely mentions background work -> no fire."""
    rc, err = _run(
        monkeypatch, capsys, tmp_path,
        text="I read the background job's output and the analysis is complete.",
        jobs={"bz76vjrcw": "done\n"},
        holders=[],
    )
    assert rc == 0
    assert err == ""


def test_silent_when_no_background_jobs(monkeypatch, capsys, tmp_path):
    session = "sess-none"
    monkeypatch.setattr(mod, "_task_outputs", lambda s: [])
    envelope = {
        "session_id": session,
        "transcript_path": _transcript(tmp_path, "Waiting for it to finish."),
        "stop_hook_active": False,
    }
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps(envelope)))
    assert mod.main() == 0
    assert capsys.readouterr().err == ""


def test_respects_stop_hook_active(monkeypatch, capsys, tmp_path):
    envelope = {"session_id": "s", "transcript_path": "", "stop_hook_active": True}
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps(envelope)))
    assert mod.main() == 0
    assert capsys.readouterr().err == ""


def test_lsof_unavailable_stays_silent(monkeypatch, capsys, tmp_path):
    """Fail open: if lsof can't answer, assume live rather than nag falsely."""
    rc, err = _run(
        monkeypatch, capsys, tmp_path,
        text="Waiting for the job to finish.",
        jobs={"bx1234567": "x\n"},
        holders=["unknown"],
    )
    assert rc == 0
    assert err == ""


def test_fails_open_on_garbage_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO("not json"))
    assert mod.main() == 0


# ---------------------------------------------------------------- predicate unit

@pytest.mark.parametrize("text", [
    "waiting for the scan",
    "I'll report when it completes",
    "the job is still running",
    "will notify you once it finishes",
    "ending my turn here",
    "continue polling until the file appears",
])
def test_awaiting_predicate_positive(text):
    assert mod.AWAITING.search(text)


@pytest.mark.parametrize("text", [
    "The analysis is complete and committed.",
    "I read the output file and summarized the findings.",
    "Here are the three findings with their evidence paths.",
])
def test_awaiting_predicate_negative(text):
    assert not mod.AWAITING.search(text)


# ------------------------------------------- regression: multi-job scoping
# Found by an unmocked live-fire control, not by the mocked tests above: a real
# session had TWO background jobs, one live and one dead, and the turn named the
# dead one. Deciding liveness before scoping let the unrelated live job vouch for
# the dead one, so the gate stayed silent on exactly the failure it exists for.

def test_named_dead_job_fires_despite_unrelated_live_job(monkeypatch, capsys, tmp_path):
    session = "sess-multi"
    _tasks(tmp_path, session, {"bdeadjob1": "partial\n", "blivejob9": "running\n"})
    tasks = tmp_path / "claude-501" / "-slug" / session / "tasks"
    monkeypatch.setattr(mod, "_task_outputs", lambda s: sorted(str(p) for p in tasks.glob("*.output")))
    monkeypatch.setattr(mod, "_holders", lambda path: [] if "bdeadjob1" in path else ["999"])
    monkeypatch.setattr(mod, "_deduped", lambda s, j: False)
    envelope = {
        "session_id": session,
        "transcript_path": _transcript(
            tmp_path, "Ending my turn here; monitor bdeadjob1 will surface the tables."
        ),
        "stop_hook_active": False,
    }
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps(envelope)))
    assert mod.main() == 0
    err = capsys.readouterr().err
    assert "bdeadjob1" in err and "NOT RUNNING" in err
    assert "blivejob9" not in err  # must not speak about a job it isn't awaiting


def test_unnamed_await_defers_to_any_live_job(monkeypatch, capsys, tmp_path):
    """Generic await + something still running -> silent (the wait is legitimate)."""
    session = "sess-generic"
    _tasks(tmp_path, session, {"bdeadjob1": "x\n", "blivejob9": "y\n"})
    tasks = tmp_path / "claude-501" / "-slug" / session / "tasks"
    monkeypatch.setattr(mod, "_task_outputs", lambda s: sorted(str(p) for p in tasks.glob("*.output")))
    monkeypatch.setattr(mod, "_holders", lambda path: [] if "bdeadjob1" in path else ["999"])
    monkeypatch.setattr(mod, "_deduped", lambda s, j: False)
    envelope = {
        "session_id": session,
        "transcript_path": _transcript(tmp_path, "Waiting for the jobs to finish."),
        "stop_hook_active": False,
    }
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps(envelope)))
    assert mod.main() == 0
    assert capsys.readouterr().err == ""
