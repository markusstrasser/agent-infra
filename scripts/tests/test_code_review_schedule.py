from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SCHEDULE_PATH = ROOT / "scripts" / "code-review-schedule.py"


def load_schedule():
    spec = importlib.util.spec_from_file_location("code_review_schedule", SCHEDULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_review_propagates_scout_failure(monkeypatch) -> None:
    schedule = load_schedule()
    monkeypatch.setattr(
        schedule.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=2),
    )

    assert schedule.run_review("intel", "patterns") == 2


def test_main_exits_nonzero_when_scout_fails(monkeypatch) -> None:
    schedule = load_schedule()
    monkeypatch.setattr(schedule, "todays_assignment", lambda: ("intel", "patterns"))
    monkeypatch.setattr(schedule, "run_review", lambda *args, **kwargs: 2)
    monkeypatch.setattr(schedule.sys, "argv", ["code-review-schedule.py"])

    assert schedule.main() == 2
