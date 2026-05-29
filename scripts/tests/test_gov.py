"""Regression tests for gov.py + gov_intake.py — bugs caught by /critique close
(cross-model review, 2026-05-29). Each test fails on the pre-fix code.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/

import gov  # noqa: E402
import gov_intake  # noqa: E402


# ── F3: advisory-noise must not fire on sparse telemetry ──────────────────────
def _patch_events(monkeypatch, tmp_path, rows):
    ev = tmp_path / "ev.jsonl"
    ev.write_text("x")
    monkeypatch.setattr(gov, "EVENT_LOG", ev)
    monkeypatch.setattr(gov, "load_jsonl", lambda *a, **k: rows)


def test_advisory_noise_floor_ignores_sparse(monkeypatch, tmp_path):
    rows = [{"hook": "h1", "action": "warn", "ts": "2026-05-29T00:00:00Z"}] * 5
    _patch_events(monkeypatch, tmp_path, rows)
    assert gov.advisory_noise(30) == []  # 5 fires < MIN_FIRES floor


def test_advisory_noise_flags_high_volume(monkeypatch, tmp_path):
    rows = [{"hook": "spam", "action": "warn", "ts": "2026-05-29T00:00:00Z"}] * 200
    _patch_events(monkeypatch, tmp_path, rows)
    out = gov.advisory_noise(30)
    assert out and out[0]["hook"] == "spam"


def test_advisory_noise_excludes_blocking(monkeypatch, tmp_path):
    rows = [{"hook": "blocker", "action": "block", "ts": "2026-05-29T00:00:00Z"}] * 200
    _patch_events(monkeypatch, tmp_path, rows)
    assert gov.advisory_noise(30) == []  # has a block action → not advisory-only


# ── F4: Gov-ID parse must not swallow prose / bullets ─────────────────────────
def test_gov_id_ignores_prose_after_block(tmp_path):
    f = tmp_path / "r.md"
    f.write_text("# Title\n\n<!-- Gov-ID: rule:x\ngoal: real goal\nverifier: null\n"
                 "blast_radius: local\n-->\n\nSome prose.\nverifier: evals/should-not-capture\n")
    art = gov.parse_gov_id(f)
    assert art["id"] == "rule:x"
    assert art["verifier"] is None  # prose 'verifier:' after the block must not override


def test_gov_id_ignores_bullet_goal(tmp_path):
    f = tmp_path / "r.md"
    f.write_text("# Title\n\n<!-- Gov-ID: rule:y\n* goal: bullet not metadata\n"
                 "blast_radius: shared\n-->\n")
    art = gov.parse_gov_id(f)
    assert art["goal"] == ""           # '* goal:' bullet is not a field
    assert art["blast_radius"] == "shared"


# ── F6: correction intake must capture multi-line corrections ─────────────────
def test_intake_multiline_capture():
    # A correction spanning multiple lines below the tag. Pre-fix `(.+?)(?:\n|$)`
    # captured only the FIRST line; the DOTALL fix captures the whole body.
    prompt = ("fix the thing\n#f governance:\n"
              "always grep vetoed-decisions before consolidating\n"
              "and cite the incident that drives the rule")
    c = gov_intake._extract_correction(prompt)
    assert c and "grep vetoed-decisions" in c
    assert "cite the incident" in c  # second line — only the DOTALL fix keeps it


def test_intake_same_line_still_works():
    c = gov_intake._extract_correction("#f governance: put routing in the skill")
    assert c == "put routing in the skill"


def test_intake_no_tag_returns_none():
    assert gov_intake._extract_correction("just a normal prompt with no tag") is None
