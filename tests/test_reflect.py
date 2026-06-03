"""Tests for scripts/reflect.py — the deep pass (cluster → classify → emit).

Hermetic: CAPTURE_LOG / PROCESSED / QUARANTINE_DIR and fm.FM_FILE / fm.EVIDENCE_LOG
are monkeypatched onto temp paths; no real state, no LLM (use_llm defaults off).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fm  # noqa: E402
import reflect  # noqa: E402

SAMPLE_FM_MD = """# FM
### Failure Mode 25
<!--
FM-ID: fm25-belief6-fae
signature: outcome-claim or external-attribution without trace
target_surface: belief-6 analyst labels
status: active
evidence_count: 0
-->
### Failure Mode 24
<!--
FM-ID: fm24-retry-without-diagnosis
signature: same tool called 3+ times with varied params and no diagnosis
target_surface: spinning-detector
status: active
evidence_count: 0
-->
### Failure Mode 15
<!--
FM-ID: fm15-silent-semantic-failure
signature: reasoning drift wrong bucket misleading diagnostic no runtime exception
target_surface: critique close
status: active
evidence_count: 0
-->
"""


@pytest.fixture()
def env(tmp_path, monkeypatch):
    fm_file = tmp_path / "agent-failure-modes.md"
    fm_file.write_text(SAMPLE_FM_MD, encoding="utf-8")
    monkeypatch.setattr(fm, "FM_FILE", fm_file)
    monkeypatch.setattr(fm, "EVIDENCE_LOG", tmp_path / "fm-evidence.jsonl")
    monkeypatch.setattr(reflect, "CAPTURE_LOG", tmp_path / "reflect-capture.jsonl")
    monkeypatch.setattr(reflect, "PROCESSED", tmp_path / "reflect-processed.json")
    monkeypatch.setattr(reflect, "QUARANTINE_DIR", tmp_path / "quarantine")
    return tmp_path


def _omission(session, n=1):
    return {"schema": "reflect.capture.v1", "kind": "omission",
            "subtype": "entity-write-without-identity-read", "strength": "shadow",
            "session": session, "hash": f"h{session}{n}",
            "trigger": "wrote analysis/companies/X.md without identity read"}


def _write_capture(path: Path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# ── clustering ───────────────────────────────────────────────────────────────
def test_omissions_bucket_by_subtype(env):
    sigs = [_omission("s1"), _omission("s2"), _omission("s3")]
    clusters = reflect.cluster_signals(sigs)
    assert len(clusters) == 1
    assert reflect._distinct_sessions(clusters[0]) == 3


def test_distinct_corrections_form_separate_clusters(env):
    a = {"kind": "correction", "subtype": "negation", "session": "s1", "hash": "a",
         "trigger": "the alpha widget is wrong"}
    b = {"kind": "correction", "subtype": "negation", "session": "s2", "hash": "b",
         "trigger": "totally unrelated zzz qqq topic"}
    clusters = reflect.cluster_signals([a, b])
    assert len(clusters) == 2


# ── classification: merge-before-mint ────────────────────────────────────────
def test_anchor_forces_attach(env):
    blocks = fm.parse_blocks()
    cluster = [_omission("s1"), _omission("s2"), _omission("s3")]
    cls = reflect.classify_cluster(cluster, blocks)
    assert cls["action"] == "attach"
    assert cls["fm_id"] == "fm25-belief6-fae"  # the PROBE_FM anchor
    assert cls["axis"] == "reach"


def test_no_anchor_low_sim_proposes_mint_with_two_merges(env):
    blocks = fm.parse_blocks()
    cluster = [{"kind": "correction", "subtype": "negation", "session": f"s{i}",
                "hash": f"m{i}", "trigger": "zzzzz qqqqq vvvvv wwwww"} for i in range(3)]
    cls = reflect.classify_cluster(cluster, blocks)
    assert cls["action"] == "mint"
    assert len(cls["merges"]) == 2  # merge-before-mint names the 2 nearest FMs


# ── run_classify: auto-record vs quarantine, thresholds, caps ────────────────
def test_below_threshold_is_deferred_not_processed(env):
    _write_capture(reflect.CAPTURE_LOG, [_omission("s1"), _omission("s2")])  # only 2 sessions
    r = reflect.run_classify(dry_run=True)
    assert r["auto_recorded"] == [] and r["quarantined"] == []
    assert r["deferred"] == 1


def test_attach_auto_records_and_quarantines_enforcer(env):
    _write_capture(reflect.CAPTURE_LOG, [_omission("s1"), _omission("s2"), _omission("s3")])
    r = reflect.run_classify(dry_run=False)
    # auto-record: evidence attached to the existing FM
    assert any(a["fm_id"] == "fm25-belief6-fae" for a in r["auto_recorded"])
    ev = (env / "fm-evidence.jsonl").read_text().strip().splitlines()
    assert len(ev) == 3  # one row per session-instance
    # enforcer proposal quarantined (behavior change → human gate), report-only
    assert len(r["quarantined"]) == 1
    assert r["quarantined"][0]["mode"] == "report-only"
    qfiles = list((env / "quarantine").glob("*.jsonl"))
    assert qfiles and "pending" in qfiles[0].read_text()


def test_processed_prevents_reclassification(env):
    _write_capture(reflect.CAPTURE_LOG, [_omission("s1"), _omission("s2"), _omission("s3")])
    reflect.run_classify(dry_run=False)
    r2 = reflect.run_classify(dry_run=False)
    assert r2["fresh_signals"] == 0 and r2["auto_recorded"] == []


def test_enforcer_proposed_once_per_fm(env):
    _write_capture(reflect.CAPTURE_LOG, [_omission("s1"), _omission("s2"), _omission("s3")])
    reflect.run_classify(dry_run=False)
    # add 3 more of the SAME subtype/FM in new sessions
    rows = [_omission("s1"), _omission("s2"), _omission("s3"),
            _omission("t1"), _omission("t2"), _omission("t3")]
    for i, row in enumerate(rows):
        row["hash"] = f"second{i}"
        row["session"] = ["t1", "t2", "t3", "t4", "t5", "t6"][i]
    _write_capture(reflect.CAPTURE_LOG, rows)
    r2 = reflect.run_classify(dry_run=False)
    # evidence still attaches, but no SECOND enforcer for the same FM
    assert r2["quarantined"] == []


def test_arrival_cap_limits_quarantine(env):
    # 6 GENUINELY dissimilar mint-bound clusters (distinct words, so difflib does
    # not merge them) — must exceed the arrival cap of 3.
    phrases = [
        "alpha beta gamma delta", "monsoon tractor velvet quasar",
        "ledger biscuit tundra xenon", "harbor zephyr cobalt mango",
        "pixel walrus orchid fjord", "thunder basil ivory nomad",
    ]
    rows = []
    for k, phrase in enumerate(phrases):
        for i in range(3):
            rows.append({"kind": "correction", "subtype": "negation",
                         "session": f"s{k}_{i}", "hash": f"c{k}_{i}", "trigger": phrase})
    _write_capture(reflect.CAPTURE_LOG, rows)
    r = reflect.run_classify(dry_run=False)
    assert len(r["quarantined"]) <= reflect.ARRIVAL_CAP
    assert r["capped"] is True
