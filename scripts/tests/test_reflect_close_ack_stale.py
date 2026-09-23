"""`--ack-stale` acks old un-acked digests with a label, never as a verified close.

The 2026-09-02 queue freeze: 28 close digests (oldest 2026-07-06) had no reviewer and
nagged every SessionStart. Bulk-acking them silently would forge 28 verified closes; the
ack row therefore carries ``reason: stale-unreviewed`` and the pending-close selection
(`latest_digest()` without a session) must skip them afterwards.

Fixture digests carry a live transcript and relative dates inside a widened transcript
horizon, so this file pins --ack-stale alone; expiry past the horizon is pinned in
test_reflect_close_digest_expiry.py.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import reflect_session_close as rsc  # noqa: E402


def _ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


def _digest(sid: str, ts: str, transcript: Path, project: str = "agent-infra") -> dict:
    return {
        "schema": "reflect.close-digest.v1",
        "session_id": sid,
        "project": project,
        "ts": ts,
        "transcript_path": str(transcript),
    }


def _write_log(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_ack_stale_acks_only_old_unacked_digests(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    log = tmp_path / "digest.jsonl"
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")
    old_ts = _ago(10)
    _write_log(
        log,
        [
            _digest("old-unacked", old_ts, transcript),
            _digest("old-acked", _ago(12), transcript),
            {"schema": "reflect.close-ack.v1", "session_id": "old-acked", "rsi_closed": True},
            _digest("fresh-unacked", rsc._utc_now(), transcript),
        ],
    )
    monkeypatch.setattr(rsc, "DIGEST_LOG", log)
    monkeypatch.setattr(rsc, "TRANSCRIPT_HORIZON_DAYS", 90)

    preview = rsc.ack_stale_digests(7, note="test", dry_run=True)
    assert [p["session_id"] for p in preview] == ["old-unacked"]
    assert log.read_text().count("close-ack") == 1  # dry run wrote nothing

    acked = rsc.ack_stale_digests(7, note="bulk test")
    assert [a["session_id"] for a in acked] == ["old-unacked"]
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    new_ack = rows[-1]
    assert new_ack["schema"] == "reflect.close-ack.v1"
    assert new_ack["session_id"] == "old-unacked"
    assert new_ack["reason"] == "stale-unreviewed"
    assert new_ack["note"] == "bulk test"
    assert new_ack["digest_ts"] == old_ts

    # The labeled ack still closes the session for queue purposes …
    assert "old-unacked" in rsc._closed_sessions()
    # … so the pending-close selection moves on to the fresh digest.
    pending = rsc.latest_digest()
    assert pending is not None and pending["session_id"] == "fresh-unacked"
    # And a second pass is idempotent.
    assert rsc.ack_stale_digests(7, note="again") == []
