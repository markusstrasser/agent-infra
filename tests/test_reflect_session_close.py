"""Tests for scripts/reflect_session_close.py — async digest drain."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import reflect_session_close as rsc  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def paths(tmp_path, monkeypatch):
    queue = tmp_path / "close-queue"
    digest = tmp_path / "reflect-close-digest.jsonl"
    capture = tmp_path / "reflect-capture.jsonl"
    transcript = FIXTURES / "goal-transcript-achieved.jsonl"
    monkeypatch.setattr(rsc, "CLOSE_QUEUE", queue)
    monkeypatch.setattr(rsc, "DIGEST_LOG", digest)
    monkeypatch.setattr(rsc, "CAPTURE_LOG", capture)
    monkeypatch.setattr(rsc, "UNSUPPORTED_SHADOW", tmp_path / "unsupported-shadow.jsonl")
    monkeypatch.setattr(rsc, "MAINTAIN", tmp_path / "MAINTAIN.md")
    return {"queue": queue, "digest": digest, "transcript": transcript}


def _write_intent(
    queue: Path, session: str, transcript: Path, tier1: bool = True, processed: bool = False
) -> Path:
    queue.mkdir(parents=True, exist_ok=True)
    intent = {
        "schema": "reflect.close-intent.v1",
        "session_id": session,
        "project": "agent-infra",
        "ts": "2026-06-15T12:00:00+00:00",
        "reason": "clear",
        "transcript_path": str(transcript),
        "goal_state": {
            "source": "claude_transcript",
            "status": "achieved" if tier1 else "active",
            "evidence_ts": "2026-06-15T09:00:20.000Z",
            "raw_ref": "fixture",
        },
        "tier1_eligible": tier1,
        "tier1_reason": "goal_achieved" if tier1 else "goal_still_active",
        "processed": processed,
    }
    path = queue / f"{session}.json"
    path.write_text(json.dumps(intent), encoding="utf-8")
    return path


class TestReflectSessionClose:
    def test_build_digest_eligible(self, paths):
        intent = {
            "session_id": "sess-001",
            "project": "agent-infra",
            "transcript_path": str(paths["transcript"]),
            "reason": "clear",
            "goal_state": {
                "status": "achieved",
                "evidence_ts": "2026-06-15T09:00:20.000Z",
            },
        }
        digest = rsc.build_digest(intent)
        assert digest is not None
        assert digest["tier1_reason"] == "goal_achieved"
        assert digest["episode_line_count"] == 5
        assert digest["invoke_skill"] is True

    def test_build_digest_skips_active_goal(self, paths):
        intent = {
            "session_id": "sess-002",
            "project": "agent-infra",
            "transcript_path": str(paths["transcript"]),
            "goal_state": {"status": "active"},
        }
        assert rsc.build_digest(intent) is None

    def test_drain_writes_digest_and_flips_processed(self, paths):
        intent_path = _write_intent(paths["queue"], "sess-drain", paths["transcript"])
        stats = rsc.drain_queue(limit=5)
        assert stats["written"] == 1
        assert stats["read"] == 1
        lines = paths["digest"].read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["schema"] == "reflect.close-digest.v1"
        reread = json.loads(intent_path.read_text(encoding="utf-8"))
        assert reread["processed"] is True
        assert reread["digest_written"] is True

    def test_drain_reaches_past_processed_head(self, paths):
        """Wedge regression (outage 2026-06-18→07-06): processed files with the oldest
        mtimes must not occupy the limit window and starve unprocessed intents."""
        import os

        old = 1_600_000_000
        for i in range(3):
            p = _write_intent(paths["queue"], f"sess-done-{i}", paths["transcript"], processed=True)
            os.utime(p, (old + i, old + i))
        _write_intent(paths["queue"], "sess-starved", paths["transcript"])
        stats = rsc.drain_queue(limit=3)
        assert stats["written"] == 1
        assert stats["read"] == 1
        row = json.loads(paths["digest"].read_text(encoding="utf-8").strip().splitlines()[-1])
        assert row["session_id"] == "sess-starved"

    def test_drain_skip_reasons_accounted(self, paths):
        _write_intent(paths["queue"], "sess-active", paths["transcript"], tier1=False)
        stats = rsc.drain_queue(limit=5)
        assert stats["written"] == 0
        assert stats["skipped"] == {"tier1_not_eligible": 1}
        reread = json.loads((paths["queue"] / "sess-active.json").read_text(encoding="utf-8"))
        assert reread["processed"] is True
        assert reread["digest_written"] is False

    def test_drain_pending_after_counts_backlog(self, paths):
        for i in range(4):
            _write_intent(paths["queue"], f"sess-bulk-{i}", paths["transcript"])
        stats = rsc.drain_queue(limit=2)
        assert stats["read"] == 2
        assert stats["pending_after"] == 2

    def test_silent_zero_exits_nonzero(self, paths, monkeypatch):
        silent = {"read": 5, "written": 0, "skipped": {}, "unreadable": 0, "pending_after": 0}
        monkeypatch.setattr(rsc, "drain_queue", lambda limit=10: silent)
        assert rsc.main(["--drain"]) == 1

    def test_all_skipped_drain_exits_zero(self, paths):
        _write_intent(paths["queue"], "sess-active", paths["transcript"], tier1=False)
        assert rsc.main(["--drain"]) == 0

    def test_empty_queue_drain_exits_zero(self, paths):
        assert rsc.main(["--drain"]) == 0

    def test_pending_nudge_after_digest(self, paths):
        _write_intent(paths["queue"], "sess-nudge", paths["transcript"])
        rsc.drain_queue()
        nudge = rsc.pending_nudge()
        assert nudge is not None
        assert "/rsi close" in nudge

    def test_pending_nudge_cleared_after_ack(self, paths):
        _write_intent(paths["queue"], "sess-nudge", paths["transcript"])
        rsc.drain_queue()
        rsc.ack_digest("sess-nudge")
        assert rsc.pending_nudge() is None


class TestLatestDigest:
    """Ack-vs-digest selection: the digest log mixes digest.v1 + close-ack.v1 rows;
    latest_digest must never return an ack (the `tail -1` Step-1 failure class)."""

    def _drain_and_ack(self, paths, sessions_acked, sessions_open):
        for sid in (*sessions_acked, *sessions_open):
            _write_intent(paths["queue"], sid, paths["transcript"])
        rsc.drain_queue(limit=20)
        for sid in sessions_acked:
            rsc.ack_digest(sid)

    def test_session_lookup_skips_trailing_ack(self, paths):
        self._drain_and_ack(paths, sessions_acked=["sess-a"], sessions_open=[])
        last = json.loads(paths["digest"].read_text().strip().splitlines()[-1])
        assert last["schema"] == "reflect.close-ack.v1"  # tail -1 would return this
        row = rsc.latest_digest("sess-a")
        assert row is not None
        assert row["schema"] == "reflect.close-digest.v1"
        assert row["session_id"] == "sess-a"

    def test_bare_lookup_returns_latest_unacked(self, paths):
        self._drain_and_ack(paths, sessions_acked=["sess-a"], sessions_open=["sess-b"])
        row = rsc.latest_digest()
        assert row is not None
        assert row["session_id"] == "sess-b"
        assert row["schema"] == "reflect.close-digest.v1"

    def test_bare_lookup_none_when_all_acked(self, paths):
        self._drain_and_ack(paths, sessions_acked=["sess-a", "sess-b"], sessions_open=[])
        assert rsc.latest_digest() is None

    def test_cli_latest_digest(self, paths, capsys):
        self._drain_and_ack(paths, sessions_acked=["sess-a"], sessions_open=["sess-b"])
        assert rsc.main(["--latest-digest", "sess-b"]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["session_id"] == "sess-b"
        assert rsc.main(["--latest-digest", "sess-missing"]) == 1
        # bare form (empty string sentinel from the skill's `$(cat ...)` when file absent)
        assert rsc.main(["--latest-digest", ""]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["session_id"] == "sess-b"


class TestHindsightMode3:
    def test_append_hindsight_grade_validates(self, tmp_path, monkeypatch):
        grades = tmp_path / "loop" / "hindsight_grades.jsonl"
        monkeypatch.setattr(
            rsc,
            "_HINDSIGHT_GRADES",
            {"arc-agi": grades},
        )
        (tmp_path / "loop").mkdir(parents=True)
        assert rsc.append_hindsight_grade("arc-agi", {"item": "operator:x", "grade": "DERIVABLE"})
        rows = [json.loads(l) for l in grades.read_text().splitlines()]
        assert rows[0]["item"] == "operator:x"
        assert not rsc.append_hindsight_grade("arc-agi", {"item": "operator:y", "grade": "MAYBE"})

    def test_ack_with_hindsight_appends(self, paths, tmp_path, monkeypatch, capsys):
        grades = tmp_path / "arc-agi" / "loop" / "hindsight_grades.jsonl"
        grades.parent.mkdir(parents=True)
        monkeypatch.setattr(rsc, "_HINDSIGHT_GRADES", {"arc-agi": grades})
        _write_intent(paths["queue"], "sess-h", paths["transcript"])
        rsc.drain_queue()
        digest_line = paths["digest"].read_text().strip().splitlines()[-1]
        row = json.loads(digest_line)
        row["project"] = "arc-agi"
        row["session_id"] = "sess-h"
        paths["digest"].write_text(
            paths["digest"].read_text().rsplit("\n", 1)[0] + "\n" + json.dumps(row) + "\n",
            encoding="utf-8",
        )
        payload = json.dumps(
            {
                "item": "operator:why-stop",
                "grade": "DERIVABLE",
                "evidence": "why did you stop",
                "gap": "noop",
            }
        )
        assert rsc.main(["--ack", "sess-h", "--hindsight", payload]) == 0
        err = capsys.readouterr().err
        assert "1 hindsight grade(s) appended" in err
        saved = json.loads(grades.read_text().strip())
        assert saved["grade"] == "DERIVABLE"
