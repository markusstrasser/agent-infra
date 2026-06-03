"""Tests for scripts/reflect.py — the deep pass (cluster → classify → emit),
including the close-review fixes: shadow-omission hold, no-silent-cap-drop,
project-isolated clustering, idempotent attach, merge-before-mint proposal guard.

Hermetic: CAPTURE_LOG / PROCESSED / QUARANTINE_DIR and fm.FM_FILE / fm.EVIDENCE_LOG
are monkeypatched onto temp paths; no real state, no LLM.
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


def _omission(session, n=1, project="intel"):
    return {"kind": "omission", "subtype": "entity-write-without-identity-read",
            "strength": "shadow", "project": project, "session": session,
            "hash": f"o{session}{n}", "trigger": "wrote analysis/companies/X.md without identity read"}


def _retry(session, n=1, project="intel"):
    return {"kind": "correction", "subtype": "retry_run", "strength": "medium",
            "project": project, "session": session, "hash": f"r{session}{n}",
            "trigger": "Bash x4 varied-input run"}


def _neg(session, trigger, project="intel"):
    return {"kind": "correction", "subtype": "negation", "project": project,
            "session": session, "hash": f"n{session}{hash(trigger) % 9999}", "trigger": trigger}


def _write_capture(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# ── clustering (project-isolated, type-strict) ───────────────────────────────
def test_omissions_bucket_by_project_subtype(env):
    clusters = reflect.cluster_signals([_omission("s1"), _omission("s2"), _omission("s3")])
    assert len(clusters) == 1 and reflect._distinct_sessions(clusters[0]) == 3


def test_same_subtype_different_projects_do_not_collide(env):
    clusters = reflect.cluster_signals([_retry("s1"), _retry("s2", project="agent-infra")])
    assert len(clusters) == 2  # project-scoped keying — no cross-repo collision


def test_free_correction_does_not_join_retry_bucket(env):
    # identical trigger text, but a negation must NOT contaminate the retry bucket
    clusters = reflect.cluster_signals([_retry("s1"), _neg("s2", "Bash x4 varied-input run")])
    assert len(clusters) == 2


def test_distinct_corrections_form_separate_clusters(env):
    a = _neg("s1", "the alpha widget is wrong")
    b = _neg("s2", "totally unrelated zzz qqq topic")
    assert len(reflect.cluster_signals([a, b])) == 2


# ── classification: merge-before-mint ────────────────────────────────────────
def test_anchor_forces_attach(env):
    cls = reflect.classify_cluster([_retry("s1"), _retry("s2"), _retry("s3")], fm.parse_blocks())
    assert cls["action"] == "attach"
    assert cls["fm_id"] == "fm24-retry-without-diagnosis"  # PROBE_FM anchor
    assert cls["axis"] == "reach"


def test_no_anchor_low_sim_proposes_mint_with_two_merges(env):
    cluster = [_neg(f"s{i}", "zzzzz qqqqq vvvvv wwwww") for i in range(3)]
    cls = reflect.classify_cluster(cluster, fm.parse_blocks())
    assert cls["action"] == "mint" and len(cls["merges"]) == 2


def test_mint_needs_two_merges_else_needs_review(env, tmp_path, monkeypatch):
    one = tmp_path / "one.md"
    one.write_text("### F\n<!--\nFM-ID: only-one\nsignature: x\ntarget_surface: y\n"
                   "status: active\nevidence_count: 0\n-->\n", encoding="utf-8")
    monkeypatch.setattr(fm, "FM_FILE", one)
    cluster = [_neg(f"s{i}", "zzz qqq vvv") for i in range(3)]
    cls = reflect.classify_cluster(cluster, fm.parse_blocks())
    assert cls["action"] == "needs-review" and len(cls["merges"]) < 2


# ── run_classify: shadow hold, auto-record, no-silent-drop, caps ─────────────
def test_omission_clusters_held_shadow(env):
    _write_capture(reflect.CAPTURE_LOG, [_omission("s1"), _omission("s2"), _omission("s3")])
    r = reflect.run_classify(dry_run=False)
    assert r["auto_recorded"] == [] and r["quarantined"] == [] and r["deferred"] == 1
    # held → never processed → still fresh next run (accumulating for PPV)
    assert reflect.run_classify(dry_run=False)["fresh_signals"] == 3
    # and NO durable taxonomy mutation from shadow probes
    ev = env / "fm-evidence.jsonl"
    assert not ev.exists() or ev.read_text().strip() == ""


def test_below_threshold_retry_deferred(env):
    _write_capture(reflect.CAPTURE_LOG, [_retry("s1"), _retry("s1", 2)])  # 2 signals, 1 session
    r = reflect.run_classify(dry_run=True)
    assert r["deferred"] == 1 and r["auto_recorded"] == [] and r["quarantined"] == []


def test_attach_auto_records_and_quarantines_enforcer(env):
    _write_capture(reflect.CAPTURE_LOG, [_retry("s1"), _retry("s2"), _retry("s3")])
    r = reflect.run_classify(dry_run=False)
    assert any(a["fm_id"] == "fm24-retry-without-diagnosis" for a in r["auto_recorded"])
    assert len((env / "fm-evidence.jsonl").read_text().strip().splitlines()) == 3
    assert len(r["quarantined"]) == 1 and r["quarantined"][0]["mode"] == "report-only"
    qfiles = list((env / "quarantine").glob("*.jsonl"))
    assert qfiles and "pending" in qfiles[0].read_text()


def test_processed_prevents_reclassification(env):
    _write_capture(reflect.CAPTURE_LOG, [_retry("s1"), _retry("s2"), _retry("s3")])
    reflect.run_classify(dry_run=False)
    assert reflect.run_classify(dry_run=False)["fresh_signals"] == 0


def test_evidence_attach_idempotent(env):
    _write_capture(reflect.CAPTURE_LOG, [_retry("s1"), _retry("s2"), _retry("s3")])
    reflect.run_classify(dry_run=False)
    # force a full re-run (e.g. a crash that lost processed state)
    (env / "reflect-processed.json").write_text(json.dumps({"hashes": [], "fm_enforced": []}))
    reflect.run_classify(dry_run=False)
    assert len((env / "fm-evidence.jsonl").read_text().strip().splitlines()) == 3  # NOT 6


def test_enforcer_proposed_once_per_fm(env):
    _write_capture(reflect.CAPTURE_LOG, [_retry("s1"), _retry("s2"), _retry("s3")])
    reflect.run_classify(dry_run=False)
    rows = [_retry("t1"), _retry("t2"), _retry("t3")]
    for i, row in enumerate(rows):
        row["hash"] = f"second{i}"
    _write_capture(reflect.CAPTURE_LOG, rows)
    assert reflect.run_classify(dry_run=False)["quarantined"] == []  # evidence accrues, no 2nd enforcer


def test_capped_mint_not_processed_then_retries(env, monkeypatch):
    # WIP cap full → eligible mint suppressed, NOT processed (no silent drop), retries later
    monkeypatch.setattr(reflect, "_active_quarantine_count", lambda: reflect.WIP_CAP)
    _write_capture(reflect.CAPTURE_LOG, [_neg(f"s{i}", "alpha beta gamma delta") for i in range(3)])
    r = reflect.run_classify(dry_run=False)
    assert r["quarantined"] == [] and r["suppressed"] == 1 and r["capped"] is True
    assert json.loads((env / "reflect-processed.json").read_text())["hashes"] == []
    monkeypatch.setattr(reflect, "_active_quarantine_count", lambda: 0)
    assert len(reflect.run_classify(dry_run=False)["quarantined"]) == 1  # budget freed → emitted


def test_arrival_cap_limits_quarantine(env):
    phrases = ["alpha beta gamma delta", "monsoon tractor velvet quasar",
               "ledger biscuit tundra xenon", "harbor zephyr cobalt mango",
               "pixel walrus orchid fjord", "thunder basil ivory nomad"]
    rows = []
    for k, phrase in enumerate(phrases):
        for i in range(3):
            rows.append(_neg(f"s{k}_{i}", phrase))
    _write_capture(reflect.CAPTURE_LOG, rows)
    r = reflect.run_classify(dry_run=False)
    assert len(r["quarantined"]) <= reflect.ARRIVAL_CAP and r["capped"] is True
