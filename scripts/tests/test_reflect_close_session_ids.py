"""Session-id normalization across the close-digest lifecycle.

Regressions (steward proposals 2026-07-15 #1 and 2026-08-20 "second finding"):
- `--ack b49d6a14` (the nudge's 8-char id) appended an ack row keyed by the prefix;
  every reader compared full ids, so the nudge kept firing for ~3 weeks (666dd3c4
  carried three such inert acks);
- the loop funnel restated its own exact-match closed set, so the control-plane
  "RSI close pending" count could disagree with the SessionStart nudge.

Contract: an ack is written under the full id its key resolves to (unique prefix of
>= 8 chars or the full id); a key naming no digest, or an ambiguous prefix, writes
nothing and exits 1; ack rows already keyed by a prefix still close their digest.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import loop_funnel as lf  # noqa: E402
import reflect_session_close as rsc  # noqa: E402

SID_A = "666dd3c4-0adf-4b91-8775-622295a0c272"
SID_B = "b49d6a14-8f3b-47ac-a836-4491025912e8"
SID_TWIN = "666dd3c4-ffff-4d0d-9c1c-000000000000"  # shares SID_A's 8-char prefix


@pytest.fixture()
def log(tmp_path, monkeypatch):
    path = tmp_path / "reflect-close-digest.jsonl"
    monkeypatch.setattr(rsc, "DIGEST_LOG", path)
    monkeypatch.setattr(lf, "DIGEST_LOG", path)
    (tmp_path / "transcript.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "arc-agi").mkdir()
    monkeypatch.chdir(tmp_path / "arc-agi")  # the closer runs inside the digests' project
    return path


def _digest(log: Path, sid: str, project: str = "arc-agi") -> dict:
    return {
        "schema": "reflect.close-digest.v1",
        "session_id": sid,
        "project": project,
        "ts": rsc._utc_now(),
        "invoke_skill": True,
        "tier1_reason": "real_issue_signal",
        "transcript_path": str(log.parent / "transcript.jsonl"),
    }


def _write(log: Path, rows: list[dict]) -> None:
    with log.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _rows(log: Path) -> list[dict]:
    return [json.loads(line) for line in log.read_text().splitlines()]


def _pending_ids() -> list[str]:
    return [str(r["session_id"]) for r in lf.rsi_pending()]


def test_prefix_ack_is_written_under_the_full_id(log):
    _write(log, [_digest(log, SID_A), _digest(log, SID_B)])
    assert rsc.main(["--ack", SID_B[:8]]) == 0
    ack = _rows(log)[-1]
    assert ack["schema"] == "reflect.close-ack.v1"
    assert ack["session_id"] == SID_B
    assert _pending_ids() == [SID_A]
    assert rsc.pending_nudge(here="arc-agi") is not None  # SID_A still pending
    assert rsc.main(["--ack", SID_A[:8]]) == 0
    assert rsc.pending_nudge(here="arc-agi") is None
    assert rsc.latest_digest() is None
    assert _pending_ids() == []


def test_existing_prefix_ack_rows_close_their_digest(log):
    """The inert rows already in the live log (666dd3c4 x3, b49d6a14, '992ed156-...')."""
    _write(
        log,
        [
            _digest(log, SID_A),
            _digest(log, SID_B),
            {"schema": "reflect.close-ack.v1", "session_id": SID_A[:8], "rsi_closed": True},
            {"schema": "reflect.close-ack.v1", "session_id": SID_B[:9] + "...", "rsi_closed": True},
        ],
    )
    assert rsc.pending_nudge(here="arc-agi") is None
    assert rsc.latest_digest() is None
    assert _pending_ids() == []


def test_unknown_or_short_key_is_refused_and_writes_nothing(log):
    _write(log, [_digest(log, SID_A)])
    before = log.read_text()
    assert rsc.main(["--ack", "deadbeef"]) == 1
    assert rsc.main(["--ack", SID_A[:6]]) == 1  # shorter than the 8-char floor
    assert log.read_text() == before
    assert _pending_ids() == [SID_A]


def test_short_ack_rows_do_not_close_anything(log):
    _write(
        log,
        [_digest(log, SID_A), {"schema": "reflect.close-ack.v1", "session_id": "666d", "rsi_closed": True}],
    )
    assert _pending_ids() == [SID_A]


def test_ambiguous_prefix_is_refused(log, capsys):
    _write(log, [_digest(log, SID_A), _digest(log, SID_TWIN)])
    before = log.read_text()
    assert rsc.main(["--ack", SID_A[:8]]) == 1
    assert log.read_text() == before
    assert "ambiguous" in capsys.readouterr().err
    assert rsc.main(["--latest-digest", SID_A[:8]]) == 1
    assert "ambiguous" in capsys.readouterr().err
    with pytest.raises(rsc.DigestLookupError) as exc:
        rsc.resolve_session(SID_A[:8])
    assert sorted(exc.value.candidates) == sorted([SID_A, SID_TWIN])
    # the full id is never ambiguous
    assert rsc.resolve_session(SID_A) == SID_A


def test_latest_digest_resolves_a_unique_prefix(log, capsys):
    _write(log, [_digest(log, SID_A), _digest(log, SID_B)])
    assert rsc.main(["--latest-digest", SID_B[:8]]) == 0
    assert json.loads(capsys.readouterr().out)["session_id"] == SID_B


def test_nudge_prints_the_full_session_id(log):
    _write(log, [_digest(log, SID_A)])
    nudge = rsc.pending_nudge(here="arc-agi")
    assert nudge is not None and SID_A in nudge


def test_funnel_agrees_with_nudge_on_duplicate_digests(log):
    """One pending close per session, whatever the number of digest rows for it."""
    _write(log, [_digest(log, SID_A), _digest(log, SID_A)])
    assert _pending_ids() == [SID_A]
