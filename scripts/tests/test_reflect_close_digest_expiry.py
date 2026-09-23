"""Close digests whose verify path is gone expire at listing time instead of nagging.

Regressions (steward proposals 2026-08-18 x2, 2026-08-20):
- digest 666dd3c4 nudged every SessionStart for ~3 weeks after its transcript was
  deleted — /rsi close Step 2 ("verify the fix landed") was unsatisfiable by construction;
- digests 45eed8bb / 9ea76090 sat 17 days, past the transcript-prune horizon, so the
  close degraded to git archaeology.

Contract: a pending digest whose transcript is gone, or that is older than the
transcript-prune horizon (archive_raw_logs.DEFAULT_KEEP_DAYS — reused, not restated),
gets an append-only `expired_unverifiable` ack the first time any surface lists it;
from then on no surface shows it. Surfaces: SessionStart nudge, bare --latest-digest,
the loop funnel (control-plane "RSI close pending"). An explicit lookup still returns
the row, flagged [STALE-DIGEST] on stderr.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import archive_raw_logs  # noqa: E402
import loop_funnel as lf  # noqa: E402
import reflect_session_close as rsc  # noqa: E402

GONE = "666dd3c4-0adf-4b91-8775-622295a0c272"  # transcript deleted
AGED = "45eed8bb-8f3b-47ac-a836-4491025912e8"  # transcript still on disk, digest 40 days old
LIVE = "cba6d45f-f191-4134-a1fa-c541447e2088"  # fresh digest, transcript present


def _ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    log = tmp_path / "reflect-close-digest.jsonl"
    monkeypatch.setattr(rsc, "DIGEST_LOG", log)
    monkeypatch.setattr(lf, "DIGEST_LOG", log)
    for name in ("CAPTURE_LOG", "PROCESSED", "QUARANTINE_DIR", "STEWARD_DIR", "CLOSE_QUEUE",
                 "FM_EVIDENCE", "AGENTLOGS_DB"):
        monkeypatch.setattr(lf, name, tmp_path / "absent" / name)  # funnel reads nothing real
    live = tmp_path / "live.jsonl"
    live.write_text("{}\n", encoding="utf-8")
    rows = [
        {"session_id": GONE, "ts": _ago(2), "transcript_path": str(tmp_path / "deleted.jsonl")},
        {"session_id": AGED, "ts": _ago(40), "transcript_path": str(live)},
        {"session_id": LIVE, "ts": _ago(1), "transcript_path": str(live)},
    ]
    with log.open("w", encoding="utf-8") as fh:
        for row in rows:
            row.update(schema="reflect.close-digest.v1", project="arc-agi", invoke_skill=True)
            fh.write(json.dumps(row) + "\n")
    (tmp_path / "arc-agi").mkdir()
    monkeypatch.chdir(tmp_path / "arc-agi")
    return {"log": log, "live": live, "tmp": tmp_path}


def _rows(log: Path) -> list[dict]:
    return [json.loads(line) for line in log.read_text().splitlines()]


def _expiries(log: Path) -> list[dict]:
    return [r for r in _rows(log) if r.get("reason") == "expired_unverifiable"]


def test_nudge_skips_unverifiable_digests_and_marks_them(env):
    before = env["log"].read_text()
    nudge = rsc.pending_nudge(here="arc-agi")
    assert nudge is not None and LIVE in nudge
    # Only the live digest remains pending; the other two are marked, never deleted.
    assert env["log"].read_text().startswith(before)
    marks = {r["session_id"]: r for r in _expiries(env["log"])}
    assert set(marks) == {GONE, AGED}
    assert marks[GONE]["why"] == "transcript gone" and marks[GONE]["transcript_exists"] is False
    assert marks[AGED]["why"] == "past the transcript horizon" and marks[AGED]["transcript_exists"] is True
    assert all(m["rsi_closed"] is True and m["schema"] == "reflect.close-ack.v1" for m in marks.values())
    assert marks[AGED]["horizon_days"] == archive_raw_logs.DEFAULT_KEEP_DAYS


def test_every_surface_agrees_whichever_lists_first(env, capsys):
    # The loop funnel (control-plane "RSI close pending") is the first listing here.
    m = lf.metrics()
    assert m["rsi_close_pending"] == 1 and [r["session_id"] for r in m["rsi_pending"]] == [LIVE]
    assert m["rsi_close_expired"] == 2
    assert "expired unverifiable: 2" in lf.render(m)
    assert rsc.latest_digest()["session_id"] == LIVE
    assert rsc.main(["--latest-digest", ""]) == 0
    assert json.loads(capsys.readouterr().out)["session_id"] == LIVE
    assert LIVE in (rsc.pending_nudge(here="arc-agi") or "")


def test_expiry_is_written_once(env):
    for _ in range(3):
        rsc.pending_nudge(here="arc-agi")
        lf.rsi_pending()
        rsc.latest_digest()
    assert sorted(r["session_id"] for r in _expiries(env["log"])) == sorted([GONE, AGED])


def test_horizon_is_the_archive_default_not_a_restated_number(env, monkeypatch):
    assert rsc.TRANSCRIPT_HORIZON_DAYS == archive_raw_logs.DEFAULT_KEEP_DAYS
    monkeypatch.setattr(rsc, "TRANSCRIPT_HORIZON_DAYS", 60)
    assert {r["session_id"] for r in rsc.pending_digests(sweep=False)} == {AGED, LIVE}
    monkeypatch.setattr(rsc, "TRANSCRIPT_HORIZON_DAYS", 0.5)
    assert rsc.pending_digests(sweep=False) == []


def test_dry_runs_write_nothing(env):
    before = env["log"].read_text()
    assert [r["session_id"] for r in rsc.pending_digests(sweep=False)] == [LIVE]
    assert rsc.ack_stale_digests(0, note="x", dry_run=True) == [
        {"session_id": LIVE, "project": "arc-agi", "digest_ts": _rows(env["log"])[2]["ts"]}
    ]
    assert env["log"].read_text() == before


def test_explicit_lookup_still_returns_an_expired_digest_flagged_stale(env, capsys):
    assert rsc.main(["--latest-digest", GONE[:8]]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["session_id"] == GONE
    assert "[STALE-DIGEST: transcript gone" in captured.err
    assert rsc.main(["--latest-digest", LIVE]) == 0
    assert "STALE-DIGEST" not in capsys.readouterr().err


def test_nudge_names_the_verifiable_until_date(env):
    nudge = rsc.pending_nudge(here="arc-agi") or ""
    ts = datetime.fromisoformat(_rows(env["log"])[2]["ts"])
    until = (ts + timedelta(days=archive_raw_logs.DEFAULT_KEEP_DAYS)).date().isoformat()
    assert f"verifiable until {until}" in nudge
