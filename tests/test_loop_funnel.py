"""Tests for scripts/loop_funnel.py."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import loop_funnel as lf  # noqa: E402


@pytest.fixture()
def paths(tmp_path, monkeypatch):
    cap = tmp_path / "reflect-capture.jsonl"
    proc = tmp_path / "reflect-processed.json"
    qdir = tmp_path / "reflect-quarantine"
    qdir.mkdir()
    steward = tmp_path / "steward-proposals"
    steward.mkdir()
    digest = tmp_path / "reflect-close-digest.jsonl"
    monkeypatch.setattr(lf, "CAPTURE_LOG", cap)
    monkeypatch.setattr(lf, "PROCESSED", proc)
    monkeypatch.setattr(lf, "QUARANTINE_DIR", qdir)
    monkeypatch.setattr(lf, "STEWARD_DIR", steward)
    monkeypatch.setattr(lf, "DIGEST_LOG", digest)
    monkeypatch.setattr(lf, "CLOSE_QUEUE", tmp_path / "close-queue")
    return {"cap": cap, "proc": proc, "qdir": qdir, "steward": steward, "digest": digest}


def test_metrics_and_needs_attention(paths):
    paths["cap"].write_text('{"kind":"correction"}\n' * 5, encoding="utf-8")
    paths["proc"].write_text(json.dumps({"hashes": ["a", "b"]}), encoding="utf-8")
    (paths["steward"] / "x.md").write_text("# x", encoding="utf-8")
    m = lf.metrics()
    assert m["captured"] == 5
    assert m["classified"] == 2
    assert m["unclassified"] == 3
    assert m["steward_proposals"] == 1
    assert lf.needs_attention(m)


def _digest_row(sid: str, transcript: Path) -> dict:
    return {
        "schema": "reflect.close-digest.v1",
        "invoke_skill": True,
        "session_id": sid,
        "project": "genomics",
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "transcript_path": str(transcript),
    }


def test_rsi_pending_respects_ack(paths, tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")
    paths["digest"].write_text(
        json.dumps(_digest_row("s1", transcript))
        + "\n"
        + json.dumps({"rsi_closed": True, "session_id": "s1"})
        + "\n",
        encoding="utf-8",
    )
    assert lf.rsi_pending() == []


def test_rsi_pending_honours_prefix_ack(paths, tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")
    sid = "45eed8bb-0adf-4b91-8775-622295a0c272"
    paths["digest"].write_text(json.dumps(_digest_row(sid, transcript)) + "\n", encoding="utf-8")
    assert [r["session_id"] for r in lf.rsi_pending()] == [sid]
    with paths["digest"].open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"rsi_closed": True, "session_id": sid[:8]}) + "\n")
    assert lf.rsi_pending() == []


def test_render_includes_quarantine(monkeypatch):
    sample = {
        "captured": 10,
        "classified": 10,
        "unclassified": 0,
        "quarantine_pending": 1,
        "steward_proposals": 0,
        "rsi_close_pending": 0,
        "close_queue_open": 0,
        "fm_evidence_rows": 0,
        "disposition_queue": 1,
        "rsi_pending": [],
        "quarantine": [
            {
                "action": "attach",
                "fm_id": "fm24",
                "cluster_summary": "retry x3",
                "confidence": 0.5,
            }
        ],
    }
    monkeypatch.setattr(lf, "metrics", lambda: sample)
    text = lf.render(sample)
    assert "retry" in text
