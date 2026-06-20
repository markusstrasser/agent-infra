"""Tests for gov_steer_linkage — constitution chunker + theme join."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gov_steer_linkage as gsl  # noqa: E402


def test_load_themes_has_ten():
    themes = gsl.load_themes()
    assert len(themes) == 10
    assert themes[0]["id"] == "verify_first"
    assert "keywords" in themes[0]


def test_parse_constitution_principles(tmp_path, monkeypatch):
    md = tmp_path / "CLAUDE.md"
    md.write_text(
        "# X\n\n### Principles\n\n"
        "**1. Architecture over instructions.** If it matters, enforce with hooks.\n\n"
        "**2. Enforce by category.** Table here.\n\n"
        "### Autonomy Boundaries\n\nHard limits.\n"
    )
    monkeypatch.setattr(gsl, "CLAUDE_MD", md)
    principles = gsl.parse_constitution_principles(md)
    assert len(principles) == 2
    assert principles[0]["id"] == "constitution:P1"
    assert "Architecture" in principles[0]["goal"]
    assert principles[0]["blast_radius"] == "constitution"


def test_score_themes_on_text():
    themes = gsl.load_themes()
    hits = gsl.score_themes_on_text("verify before you claim — measure first", themes)
    assert "verify_first" in hits
    assert hits["verify_first"] >= 2


def test_steer_signal_glob_and_aggregate(tmp_path, monkeypatch):
    observe = tmp_path / "artifacts" / "observe"
    observe.mkdir(parents=True)
    row = {
        "kind": "steer",
        "vector": "just do it now without asking",
        "quote": "why waiting",
        "before": "agent asked whether to proceed",
    }
    (observe / "2026-06-20-steer-signals.jsonl").write_text(json.dumps(row) + "\n")
    monkeypatch.setattr(gsl, "REPO", tmp_path)
    monkeypatch.setattr(gsl, "STEER_GLOB_OBSERVE", observe / "*-steer-signals.jsonl")
    monkeypatch.setattr(gsl, "STEER_GLOB_PROBE", tmp_path / "none" / "probe-*.jsonl")

    paths = gsl.steer_signal_paths()
    assert len(paths) == 1
    signals = gsl.load_steer_signals(paths)
    totals = gsl.aggregate_theme_hits(signals, gsl.load_themes())
    assert totals.get("act_now", 0) >= 1


def test_orphan_themes_detects_unlinked():
    themes = [{"id": "act_now", "label": "Act", "keywords": ["just do"]}]
    totals = {"act_now": 10}
    joined = [{"id": "rule:x", "goal": "prevent git accidents", "theme_hits": {}}]
    orphans = gsl.orphan_themes(totals, joined, themes, min_hits=3)
    assert orphans and orphans[0]["theme_id"] == "act_now"


def test_gov_owner_links_atom_to_theme():
    themes = gsl.load_themes()
    atom = {"id": "rule:planning-scope", "goal": "unrelated short goal", "kind": "rule"}
    joined = gsl.join_atoms_to_themes([atom], themes)
    assert "scope_narrow" in joined[0]["theme_hits"]
    orphans = gsl.orphan_themes({"scope_narrow": 100}, joined, themes, min_hits=3)
    assert not orphans
