"""Liveness detection for scheduled jobs.

A job that stops firing produces no error — it produces no run. That is why
`spend-alarm` sat dead for 12 days and `agentlogs-archive` failed weekly for two
weeks with nothing surfacing either (2026-08-18). These pin the two halves the
detector must get right: reading a job's own declared period, and dating its last
actual fire.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import system_inventory as si

_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.agent-infra.demo</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>/tmp/demo.sh</string></array>
  <key>StandardOutPath</key><string>{out}</string>
  <key>StandardErrorPath</key><string>{err}</string>
  {schedule}
</dict>
</plist>
"""

_INTERVAL = "<key>StartInterval</key><integer>1800</integer>"
_DAILY = "<key>StartCalendarInterval</key><dict><key>Hour</key><integer>5</integer></dict>"
_WEEKLY = (
    "<key>StartCalendarInterval</key><dict>"
    "<key>Weekday</key><integer>1</integer><key>Hour</key><integer>5</integer></dict>"
)
_ON_DEMAND = "<key>RunAtLoad</key><true/>"


def _write(tmp_path: Path, schedule: str) -> tuple[Path, Path, Path]:
    out = tmp_path / "demo.out"
    err = tmp_path / "demo.err"
    out.write_text("")
    err.write_text("")
    plist = tmp_path / "com.agent-infra.demo.plist"
    plist.write_text(_PLIST.format(out=out, err=err, schedule=schedule))
    return plist, out, err


def test_start_interval_is_read_verbatim(tmp_path: Path) -> None:
    plist, _out, _err = _write(tmp_path, _INTERVAL)
    assert si.plist_schedule_seconds(plist) == 1800


def test_calendar_interval_periods_distinguish_daily_from_weekly(tmp_path: Path) -> None:
    """StartCalendarInterval is a fire-time spec, not a period: a bare Hour is
    daily, adding Weekday makes it weekly. Treating the weekly archive as daily
    would false-alarm every Tuesday."""
    daily_dir = tmp_path / "daily"
    weekly_dir = tmp_path / "weekly"
    daily_dir.mkdir()
    weekly_dir.mkdir()
    daily_plist, _, _ = _write(daily_dir, _DAILY)
    weekly_plist, _, _ = _write(weekly_dir, _WEEKLY)
    assert si.plist_schedule_seconds(daily_plist) == 86400
    assert si.plist_schedule_seconds(weekly_plist) == 7 * 86400


def test_non_periodic_job_has_no_period(tmp_path: Path) -> None:
    """Silence from an on-demand job is not a signal — it must never be flagged."""
    plist, _out, _err = _write(tmp_path, _ON_DEMAND)
    assert si.plist_schedule_seconds(plist) is None


def test_last_run_uses_newest_sink_not_stderr_alone(tmp_path: Path) -> None:
    """launchd only touches stderr when the run WRITES to stderr, so a stale
    .err beside a fresh .out means the job is healthy, not dead. Reading .err
    alone produced a wrong 14-day-dead verdict on test-health (2026-08-18)."""
    import os

    plist, out, err = _write(tmp_path, _INTERVAL)
    os.utime(err, (1_600_000_000, 1_600_000_000))  # ancient stderr
    os.utime(out, (1_700_000_000, 1_700_000_000))  # recent stdout
    assert si._last_run_epoch(plist) == 1_700_000_000


def test_stale_job_is_flagged_and_fresh_job_is_not(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    import os

    plist, out, err = _write(tmp_path, _INTERVAL)  # period 1800s
    now = 2_000_000_000.0

    monkeypatch.setattr(si, "collect_plist_sources", lambda: [plist])
    monkeypatch.setattr(si, "plist_label", lambda _p: "com.agent-infra.demo")
    monkeypatch.setattr(
        si,
        "collect_launchd_jobs",
        lambda: [{"name": "demo", "label": "com.agent-infra.demo", "last_exit": 0}],
    )

    # Fresh: one period old, inside the 2.5x tolerance (a sleeping laptop).
    fresh = now - 1800
    os.utime(out, (fresh, fresh))
    os.utime(err, (fresh, fresh))
    assert si.collect_stale_jobs(now=now) == []

    # Dead: far beyond tolerance.
    dead = now - 1800 * 100
    os.utime(out, (dead, dead))
    os.utime(err, (dead, dead))
    rows = si.collect_stale_jobs(now=now)
    assert len(rows) == 1
    assert rows[0]["name"] == "demo"
    assert rows[0]["missed_runs"] == 100
