"""Tests for the risky-diff-review SHADOW detector — classification logic.

Pure-function tests (no git): blast_reasons + classify via injected commits.
Mirrors the report-only-detector testing style of test_buildthenundo.py.
"""

from __future__ import annotations

# scripts/ is on sys.path via scripts/tests/conftest.py; module name is hyphen-free.
import risky_diff_review_shadow as mod


def test_blast_reasons_matches_governance_paths():
    assert mod.blast_reasons(["CLAUDE.md"]) == ["constitution/goals"]
    assert mod.blast_reasons([".claude/rules/foo.md"]) == ["behavioral-rule"]
    assert mod.blast_reasons(["skills/hooks/x-guard.sh"]) == ["hook"]
    assert mod.blast_reasons(["migrations/2026-01-01.sql"]) == ["schema/contract"]
    assert mod.blast_reasons([".mcp.json"]) == ["settings/mcp"]


def test_blast_reasons_ignores_ordinary_code():
    assert mod.blast_reasons(["scripts/some_tool.py", "README.md"]) == []


def test_classify_flags_risky_without_test_or_review(monkeypatch):
    commits = [
        # risky (constitution), no test, no review → UNREVIEWED_RISKY
        {"sha": "a" * 12, "date": "2026-06-07T00:00:00", "subject": "edit constitution",
         "session": "sess1", "msg": "edit constitution", "files": ["CLAUDE.md"]},
        # risky, but accompanied by a test → covered
        {"sha": "b" * 12, "date": "2026-06-06T00:00:00", "subject": "schema change",
         "session": "sess2", "msg": "schema change", "files": ["x.sql", "tests/test_x.py"]},
        # risky, no test, but body mentions cross-model review → covered
        {"sha": "c" * 12, "date": "2026-06-05T00:00:00", "subject": "rule edit",
         "session": "sess3", "msg": "rule edit\n\nCross-model review (Gemini + GPT).",
         "files": [".claude/rules/r.md"]},
        # not risky → excluded entirely
        {"sha": "d" * 12, "date": "2026-06-04T00:00:00", "subject": "ordinary",
         "session": "sess4", "msg": "ordinary", "files": ["scripts/tool.py"]},
    ]
    monkeypatch.setattr(mod, "read_commits", lambda _days: [c["sha"] for c in commits])
    monkeypatch.setattr(mod, "commit_info", lambda sha: next(c for c in commits if c["sha"] == sha))

    findings = mod.classify(days=30)
    by_sha = {f["sha"]: f for f in findings}
    assert len(findings) == 3  # the ordinary commit is excluded
    assert by_sha["aaaaaaaaaa"]["verdict"] == "UNREVIEWED_RISKY"
    assert by_sha["bbbbbbbbbb"]["verdict"] == "covered"  # test present
    assert by_sha["cccccccccc"]["verdict"] == "covered"  # review-in-body present


def test_review_signal_propagates_across_a_session(monkeypatch):
    # One commit in the session carries the review; a sibling risky commit in the
    # same session should inherit "had_review" (review happened that session).
    commits = [
        {"sha": "e" * 12, "date": "2026-06-07T00:00:00", "subject": "apply edit",
         "session": "shared", "msg": "apply edit", "files": ["GOALS.md"]},
        {"sha": "f" * 12, "date": "2026-06-07T01:00:00", "subject": "propose edit",
         "session": "shared", "msg": "propose edit\n\nreviewed via /critique", "files": ["GOALS.md"]},
    ]
    monkeypatch.setattr(mod, "read_commits", lambda _days: [c["sha"] for c in commits])
    monkeypatch.setattr(mod, "commit_info", lambda sha: next(c for c in commits if c["sha"] == sha))

    findings = mod.classify(days=30)
    assert all(f["verdict"] == "covered" for f in findings)
    assert mod.find_unreviewed_risky(days=30) == []
