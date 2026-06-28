"""Verifier for supervision_session report builder."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import supervision_session as ss  # noqa: E402
import supervision_taxonomy as tax  # noqa: E402


def _fake_record(**kwargs) -> ss.SessionRecord:
    defaults = dict(
        session_id="abc123",
        project="agent-infra",
        date="2026-06-28",
        user_turns=10,
        by_type={"over_caution": 1, "rediscovery": 0, "error_correction": 0,
                 "taste_steer": 0, "denial": 0, "repeated_instruction": 0},
        vector={"raise_autonomy": 1, "reduce_error": 0, "grow_coverage": 0, "amplify_taste": 0},
        load=3,
        hooks_shown=2,
        corrections_after_hooks=1,
        air=0.5,
        events=[],
    )
    defaults.update(kwargs)
    return ss.SessionRecord(**defaults)


def test_build_report_schema():
    from datetime import datetime
    r = _fake_record()
    report = ss.build_report([r], days=1, since=datetime(2026, 6, 28), project_filter="agent-infra")
    assert report["schema"] == "supervision.report.v1"
    assert report["correction_events"] == 1
    assert report["correction_rate_pct"] == 10.0
    assert report["vector"]["raise_autonomy"] == 1
    assert "wasted_pct" not in report
    assert "NEW_AGENCY" not in str(report)


def test_autonomy_reading_gain():
    from datetime import datetime, timedelta
    records = []
    for i in range(6):
        records.append(_fake_record(
            date=(datetime(2026, 6, 20) + timedelta(days=i)).strftime("%Y-%m-%d"),
            vector={"raise_autonomy": max(0, 5 - i), "reduce_error": 0,
                    "grow_coverage": 0, "amplify_taste": 0},
            by_type={"over_caution": max(0, 5 - i), "rediscovery": 0, "error_correction": 0,
                     "taste_steer": 0, "denial": 0, "repeated_instruction": 0},
        ))
    trends = ss.compute_direction_trends(records)
    assert trends is not None
    assert trends["raise_autonomy"] > 0
    assert ss.autonomy_reading(trends) == "genuine_gain"


def test_taxonomy_classifies_over_caution_not_new_agency():
    m = tax.classify_regex("why ask? it's free? do")
    assert m is not None and m.type_id == "over_caution"


def test_metric_integrity_warns_when_hooks_invisible():
    from datetime import datetime
    records = [_fake_record(session_id=f"s{i}", hooks_shown=0, air=None) for i in range(6)]
    report = ss.build_report(records, days=7, since=datetime(2026, 6, 28), project_filter=None)
    mi = report["metric_integrity"]
    assert mi["hooks_visibility_ok"] is False
    assert any("hooks_shown=0" in w for w in mi["warnings"])


def test_metric_integrity_ok_when_hooks_present():
    from datetime import datetime
    records = [_fake_record(session_id=f"s{i}") for i in range(6)]
    report = ss.build_report(records, days=7, since=datetime(2026, 6, 28), project_filter=None)
    assert report["metric_integrity"]["hooks_visibility_ok"] is True


def test_session_module_single_source():
    src = (REPO / "scripts" / "supervision_session.py").read_text()
    assert "import supervision_taxonomy" in src
    for banned in ("BLINDSPOT_PATTERNS", "CORRECTION_PATTERNS", "NEW_AGENCY", "wasted_pct"):
        assert banned not in src
