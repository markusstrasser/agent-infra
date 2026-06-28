"""Smoke tests for observe_run triangulation and digest composition."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import observe_run as orun  # noqa: E402


def test_triangulate_both_lanes_high_when_both_fire():
    sup = {
        "by_type": {"over_caution": 3, "rediscovery": 5},
        "vector": {"raise_autonomy": 3, "grow_coverage": 5},
        "project_filter": "genomics",
    }
    bs = {"directions": {"raise_autonomy": 29, "grow_coverage": 45}}
    hits = orun.triangulate(sup, bs, None, "genomics")
    themes = {h["theme"] for h in hits}
    assert "over_caution / timidity" in themes
    assert "prior-context / rediscovery" in themes
    high = [h for h in hits if h["confidence"] == "high"]
    assert len(high) >= 2


def test_triangulate_fleet_only_low_when_supervision_zero():
    sup = {
        "by_type": {"over_caution": 0, "rediscovery": 0},
        "project_filter": "agent-infra",
    }
    bs = {"directions": {"raise_autonomy": 29, "grow_coverage": 45}}
    hits = orun.triangulate(sup, bs, None, "agent-infra")
    timidity = [h for h in hits if "timidity" in h["theme"]]
    assert timidity and timidity[0]["confidence"] == "low"
    assert "fleet-only" in timidity[0]["theme"]
    assert timidity[0]["modes"] == ["blindspot"]


def test_annotate_candidates_known_open(tmp_path: Path):
    root = tmp_path / "run"
    root.mkdir()
    (root / "candidates.jsonl").write_text(
        json.dumps({"summary": "watch-drain PG monitor volume-free", "checkable": True}) + "\n"
    )
    # Patch REPO for test
    import observe_run as mod
    orig = mod.REPO
    mod.REPO = tmp_path
    (tmp_path / "improvement-log.md").write_text("- [ ] watch-drain PG-only monitor\n")
    try:
        n = mod.annotate_candidates_known_open(root)
        assert n == 1
        row = json.loads((root / "candidates.jsonl").read_text().strip())
        assert row.get("existing_coverage_match")
    finally:
        mod.REPO = orig


def test_compose_digest_writes_supervision_vector(tmp_path: Path):
    root = tmp_path / "run"
    root.mkdir()
    (root / "coverage-digest.txt").write_text("coverage")
    lane_meta = {
        "supervision": {
            "sessions_analyzed": 10,
            "user_turns": 100,
            "correction_rate_pct": 5.0,
            "autonomy_reading": "mixed",
            "vector": {"raise_autonomy": 2, "reduce_error": 1, "grow_coverage": 2, "amplify_taste": 0},
            "by_type": {"over_caution": 2, "rediscovery": 2},
            "examples": [{"project": "genomics", "session_id": "abc", "type_id": "over_caution", "evidence": "why ask"}],
        },
    }
    preflight = {
        "health": {"indexer_ok": True, "last_index_status": "ok"},
        "saturation": {"saturated": False, "token_overlap": 0.1},
        "promotions_allowed": True,
        "promotion_counts": {"obs": 0},
    }
    orun.compose_digest(root, ["supervision"], lane_meta, preflight, [], None)
    text = (root / "digest.md").read_text()
    assert "correction_rate=5.0%" in text
    assert "NOT legacy wasted%" in text
    assert "wasted_pct" not in text


def test_mode_days_defaults():
    assert orun.MODE_DAYS["supervision"] == 7
    assert orun.MODE_DAYS["drift"] == 21
