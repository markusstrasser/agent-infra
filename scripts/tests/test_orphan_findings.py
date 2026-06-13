"""Tests for orphan_findings.py — the orphaned-findings ratchet.

Pure-function tests: verdict extraction (actionable vs not) + the deterministic
memo-cite routed signal. Mirrors the report-only-detector testing style.
"""

from __future__ import annotations

from pathlib import Path

# scripts/ is on sys.path via scripts/tests/conftest.py; module name is hyphen-free.
import orphan_findings as mod

MEMO = """# Trending Scout — 2026-01-02

### 1. A real adoptable feature
| Verdict | **Adopt** |

### 2. Something to just keep an eye on
| Verdict | **Watch** |

### 3. A pattern worth extracting
| Verdict | **Extract pattern** |

### 4. Pure informational
| Verdict | **FYI** |
"""


def _write(dirp: Path, name: str, body: str) -> Path:
    p = dirp / name
    p.write_text(body)
    return p


def test_extract_findings_classifies_actionable(tmp_path):
    memo = _write(tmp_path, "trending-scout-2026-01-02.md", MEMO)
    findings = mod.extract_findings(memo)
    assert len(findings) == 4
    by_title = {f["title"]: f["actionable"] for f in findings}
    assert by_title["A real adoptable feature"] is True
    assert by_title["A pattern worth extracting"] is True   # Extract = actionable
    assert by_title["Something to just keep an eye on"] is False  # Watch
    assert by_title["Pure informational"] is False           # FYI


def test_scan_flags_uncited_memo_and_clears_when_cited(tmp_path, monkeypatch):
    research = tmp_path / "research"
    research.mkdir()
    _write(research, "trending-scout-2026-01-02.md", MEMO)
    log = tmp_path / "improvement-log.md"
    log.write_text("# log\n")  # memo NOT cited yet
    monkeypatch.setattr(mod, "RESEARCH", research)
    monkeypatch.setattr(mod, "LOG", log)

    rep = mod.scan(all_memos=True)
    assert rep["actionable"] == 2  # Adopt + Extract
    assert rep["orphaned_findings"] == 2
    assert len(rep["flagged_memos"]) == 1

    # Bare memo-path cite does NOT clear (finding-level fix) — siblings stay flagged.
    log.write_text("# log\nSource: research/trending-scout-2026-01-02.md\n")
    assert mod.scan(all_memos=True)["orphaned_findings"] == 2

    # An explicit RECONCILIATION entry citing the memo clears it (bulk-triage).
    log.write_text("# log\n### [x] RECONCILIATION: triaged trending-scout-2026-01-02\n")
    rep2 = mod.scan(all_memos=True)
    assert rep2["orphaned_findings"] == 0
    assert rep2["flagged_memos"] == []


def test_parser_still_matches_real_trending_memo_format():
    """Drift guard: the parser is coupled to trending-scout's live output template
    (### N. Title + | Verdict | **X** |). If the skill changes its format, this
    breaks LOUDLY — otherwise extract_findings silently returns 0 and the ratchet
    reports a false all-clear. Couples parser to reality, not just a fixture."""
    real = sorted(mod.RESEARCH.glob("trending-scout-*.md"))
    if not real:
        return  # no memos yet (fresh checkout) — nothing to couple against
    # At least one recent memo must yield verdicts; 0 across all = parser drift.
    total = sum(len(mod.extract_findings(m)) for m in real)
    assert total > 0, ("orphan_findings parser found 0 verdicts across all "
                       "trending-scout memos — output template likely drifted")


def test_drift_pins_exact_count_on_a_known_multifinding_memo():
    """Partial-extraction guard (#2 from 2026-06-14 critique): a weak >0 check
    can't catch a multi-finding memo where the parser silently extracts only some.
    Pin an exact count on a known real memo so partial drift breaks loudly."""
    memo = mod.RESEARCH / "trending-scout-2026-06-11.md"
    if not memo.exists():
        return
    findings = mod.extract_findings(memo)
    # This memo has 9 numbered findings (### 1..9, each with a Verdict row).
    assert len(findings) == 9, (
        f"expected 9 findings in {memo.name}, parser got {len(findings)} — "
        "partial extraction drift")


def test_partial_citation_does_not_clear_sibling_findings(tmp_path, monkeypatch):
    """Regression for the 2026-06-14 cross-model finding: citing ONE finding from a
    multi-finding memo must NOT clear the others. Memo-stem cite alone is no longer
    a whole-memo clear — only an explicit RECONCILIATION entry is."""
    research = tmp_path / "research"
    research.mkdir()
    _write(research, "trending-scout-2026-02-02.md",
           "### 1. Distinctive alpha widget feature\n| Verdict | **Adopt** |\n\n"
           "### 2. Separate beta gadget mechanism\n| Verdict | **Adopt** |\n")
    log = tmp_path / "improvement-log.md"
    monkeypatch.setattr(mod, "RESEARCH", research)
    monkeypatch.setattr(mod, "LOG", log)

    # Promote ONLY finding 1 (cite memo + its distinctive tokens). Finding 2 must still flag.
    log.write_text("# log\n### [x] adopt alpha widget feature\n"
                   "Source: research/trending-scout-2026-02-02.md\n")
    rep = mod.scan(all_memos=True)
    assert rep["orphaned_findings"] == 1
    titles = [f["title"] for m in rep["flagged_memos"] for f in m["findings"]]
    assert titles == ["Separate beta gadget mechanism"]

    # Explicit RECONCILIATION entry clears the whole memo (bulk-triage assertion).
    log.write_text("# log\n### [x] RECONCILIATION: triaged trending-scout-2026-02-02\n"
                   "all dispositioned\n")
    assert mod.scan(all_memos=True)["orphaned_findings"] == 0


def test_memo_with_only_nonactionable_verdicts_never_flags(tmp_path, monkeypatch):
    research = tmp_path / "research"
    research.mkdir()
    _write(research, "trending-scout-2026-01-03.md",
           "### 1. watch only\n| Verdict | **Watch** |\n")
    log = tmp_path / "improvement-log.md"
    log.write_text("# log\n")  # uncited, but no actionable verdicts
    monkeypatch.setattr(mod, "RESEARCH", research)
    monkeypatch.setattr(mod, "LOG", log)
    rep = mod.scan(all_memos=True)
    assert rep["flagged_memos"] == []
