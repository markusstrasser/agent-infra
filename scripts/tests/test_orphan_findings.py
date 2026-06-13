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

    # Cite the memo (stem) → routed → cleared
    log.write_text("# log\nSource: research/trending-scout-2026-01-02.md\n")
    rep2 = mod.scan(all_memos=True)
    assert rep2["orphaned_findings"] == 0
    assert rep2["flagged_memos"] == []


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
