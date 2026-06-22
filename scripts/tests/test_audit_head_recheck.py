"""HEAD-recheck pass for audit consolidation (steward proposal 2026-06-22).

The scout audit re-surfaced stale/duplicate findings every wave (34 "confirmed"
→ ~12 real on 2026-06-22). `head_recheck` re-reads each finding's cited
file:line against the CURRENT tree and DROPS only dangling pointers (file gone /
line past EOF), FLAGS lines that changed since the scout ran, and KEEPS on any
uncertainty. It must never drop a real, still-locatable finding.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_findings_consolidation import extract_file_line, head_recheck  # noqa: E402


def test_extract_file_line_evidence_then_claim() -> None:
    assert extract_file_line({"evidence": "scripts/foo.py:42"}) == ("scripts/foo.py", 42)
    assert extract_file_line({"claim": "bug at lib/x.sh:7 in handler"}) == ("lib/x.sh", 7)
    assert extract_file_line({"evidence": "no locator here", "claim": "prose"}) is None


def test_extract_file_line_ignores_urls() -> None:
    # A URL with :port must not be parsed as a repo file:line (would mis-drop).
    assert extract_file_line({"evidence": "see http://example.com:8080/x"}) is None


def test_drops_missing_file(tmp_path: Path) -> None:
    findings = [{"id": "a", "evidence": "scripts/gone.py:5", "source": "s.md"}]
    kept, dropped = head_recheck(findings, tmp_path, tmp_path)
    assert kept == []
    assert len(dropped) == 1
    assert "gone" in dropped[0]["_drop_reason"]


def test_drops_line_past_eof(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "x.py").write_text("line1\nline2\n")
    findings = [{"id": "b", "evidence": "scripts/x.py:99", "source": "s.md"}]
    kept, dropped = head_recheck(findings, tmp_path, tmp_path)
    assert kept == []
    assert len(dropped) == 1
    assert "past EOF" in dropped[0]["_drop_reason"]


def test_keeps_valid_line_no_git(tmp_path: Path) -> None:
    # Valid pointer, tmp_path is not a git repo → blame returns None → kept, no flag.
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "x.py").write_text("a\nb\nc\n")
    findings = [{"id": "c", "evidence": "scripts/x.py:2", "source": "s.md"}]
    kept, dropped = head_recheck(findings, tmp_path, tmp_path)
    assert dropped == []
    assert len(kept) == 1
    assert "stale_flag" not in kept[0]


def test_keeps_no_locator(tmp_path: Path) -> None:
    findings = [{"id": "d", "claim": "some prose finding with no path", "source": "s.md"}]
    kept, dropped = head_recheck(findings, tmp_path, tmp_path)
    assert dropped == []
    assert len(kept) == 1


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_flags_line_changed_after_scout(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "x.py").write_text("a\nb\nc\n")
    _git(repo, "add", "x.py")
    _git(repo, "commit", "-q", "-m", "init")

    audit = tmp_path / "audit"
    audit.mkdir()
    src = audit / "s.md"
    src.write_text("scout output")
    old = time.time() - 86_400  # scout ran a day before the commit
    os.utime(src, (old, old))

    findings = [{"id": "g", "evidence": "x.py:2", "source": "s.md"}]
    kept, dropped = head_recheck(findings, repo, audit)
    assert dropped == []
    assert len(kept) == 1
    assert "stale_flag" in kept[0]  # commit newer than scout mtime → flag for re-verify
