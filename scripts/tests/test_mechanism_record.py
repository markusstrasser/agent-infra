"""Tests for mechanism_record.py — F3 predict-then-falsify gate."""

import sqlite3
import tempfile
from pathlib import Path

import mechanism_record as mr


def _rec(**over) -> mr.MechanismRecord:
    base = dict(
        slug="test-gate",
        change_ref="abc123",
        predicted_failure_class="over_ask spikes",
        expected_trace_observable="fewer over_ask patterns in trace_index",
        metric_query="SELECT COUNT(*) FROM trace_index WHERE pattern='over_ask' "
                     "AND date_seen >= :since AND date_seen < :until",
        direction="decrease",
        control_query="SELECT COUNT(*) FROM trace_index WHERE pattern='unrelated' "
                      "AND date_seen >= :since AND date_seen < :until",
        change_date="2026-06-10",
        rollback_criterion="revert if NOT_FIRED after 30d",
    )
    base.update(over)
    return mr.MechanismRecord(**base)


def _fixture_db(rows) -> str:
    td = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    con = sqlite3.connect(td.name)
    con.execute("CREATE TABLE trace_index (pattern TEXT, date_seen TEXT)")
    con.executemany("INSERT INTO trace_index VALUES (?, ?)", rows)
    con.commit()
    con.close()
    return td.name


def test_validate_requires_control_and_binds():
    bad = _rec(control_query="")
    errs = bad.validate()
    assert any("control_query is REQUIRED" in e for e in errs)
    bad2 = _rec(metric_query="SELECT COUNT(*) FROM trace_index")
    assert any("bind :since and :until" in e for e in bad2.validate())


def test_validate_direction_and_date():
    assert any("direction must be" in e for e in _rec(direction="sideways").validate())
    assert any("change_date not ISO" in e for e in _rec(change_date="last tuesday").validate())


# Fixtures use zero-vs-nonzero presence (rate-independent of the dynamic `now`
# after-window length): "before" = date < change_date 2026-06-10, "after" = >=.

def test_fired_when_metric_drops_control_flat():
    # metric present-before / absent-after (clear decrease); control absent both (flat)
    rows = [("over_ask", "2026-05-20")] * 10
    db = _fixture_db(rows)
    res = mr.check_record(_rec(), Path(db))
    assert res["verdict"] == "FIRED", res


def test_not_fired_when_metric_moves_wrong_way():
    # metric absent-before / present-after = increase, opposite of predicted decrease
    rows = [("over_ask", "2026-06-15")] * 10
    db = _fixture_db(rows)
    res = mr.check_record(_rec(), Path(db))
    assert res["verdict"] == "NOT_FIRED", res


def test_confounded_when_control_also_moves():
    # metric drops (present-before/absent-after) BUT control collapses identically
    rows = [("over_ask", "2026-05-20")] * 10 + [("unrelated", "2026-05-20")] * 10
    db = _fixture_db(rows)
    res = mr.check_record(_rec(), Path(db))
    assert res["verdict"] == "CONFOUNDED", res


def test_roundtrip_save_load(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "RECORDS_DIR", tmp_path)
    rec = _rec()
    path = mr.save_record(rec)
    assert path.exists()
    loaded = mr.load_record(str(path))
    assert loaded.slug == rec.slug
    assert loaded.direction == "decrease"
