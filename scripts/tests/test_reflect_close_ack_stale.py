"""`--ack-stale` acks old un-acked digests with a label, never as a verified close.

The 2026-09-02 queue freeze: 28 close digests (oldest 2026-07-06) had no reviewer and
nagged every SessionStart. Bulk-acking them silently would forge 28 verified closes; the
ack row therefore carries ``reason: stale-unreviewed`` and the pending-close selection
(`latest_digest()` without a session) must skip them afterwards.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import reflect_session_close as rsc  # noqa: E402


def _digest(sid: str, ts: str, project: str = "agent-infra") -> dict:
    return {"schema": "reflect.close-digest.v1", "session_id": sid, "project": project, "ts": ts}


def _write_log(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_ack_stale_acks_only_old_unacked_digests(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    log = tmp_path / "digest.jsonl"
    _write_log(
        log,
        [
            _digest("old-unacked", "2026-07-06T19:47:20+00:00"),
            _digest("old-acked", "2026-07-10T10:00:00+00:00"),
            {"schema": "reflect.close-ack.v1", "session_id": "old-acked", "rsi_closed": True},
            _digest("fresh-unacked", rsc._utc_now()),
        ],
    )
    monkeypatch.setattr(rsc, "DIGEST_LOG", log)

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
    assert new_ack["digest_ts"] == "2026-07-06T19:47:20+00:00"

    # The labeled ack still closes the session for queue purposes …
    assert "old-unacked" in rsc._closed_sessions()
    # … so the pending-close selection moves on to the fresh digest.
    pending = rsc.latest_digest()
    assert pending is not None and pending["session_id"] == "fresh-unacked"
    # And a second pass is idempotent.
    assert rsc.ack_stale_digests(7, note="again") == []
