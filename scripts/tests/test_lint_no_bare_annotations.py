"""Phase A — Caller-migration lint tests.

The lint catches raw `FROM annotations` outside the writer allowlist
(which would bypass the chain-aware annotations_current view and surface
superseded attestations as if they were live).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lint_no_bare_annotations_read import scan_file, scan_paths  # type: ignore


def test_detects_raw_from_annotations(tmp_path):
    """Caught-red-handed: a freshly-written read-side query that uses
    raw `FROM annotations` is flagged."""
    bad = tmp_path / "bad.py"
    bad.write_text(
        'def q(con):\n'
        '    return con.execute("SELECT * FROM annotations WHERE x = 1").fetchall()\n'
    )
    violations = scan_file(bad)
    assert len(violations) == 1
    assert "FROM annotations" in violations[0][1]


def test_ignores_annotations_current(tmp_path):
    """Reads from the chain-aware view are correct, no violation."""
    good = tmp_path / "good.py"
    good.write_text(
        'def q(con):\n'
        '    return con.execute("SELECT * FROM annotations_current").fetchall()\n'
    )
    assert scan_file(good) == []


def test_ignores_annotations_history(tmp_path):
    """Word-boundary terminator: `annotations_history` isn't `annotations`."""
    good = tmp_path / "good.py"
    good.write_text(
        'def q(con):\n'
        '    return con.execute("SELECT * FROM annotations_log").fetchall()\n'
    )
    assert scan_file(good) == []


def test_detects_inside_fstring(tmp_path):
    """f-strings are also scanned (AST JoinedStr handling)."""
    bad = tmp_path / "bad.py"
    bad.write_text(
        'WHERE = " WHERE scope=?"\n'
        'def q(con):\n'
        '    return con.execute(f"SELECT * FROM annotations{WHERE}", ["x"]).fetchall()\n'
    )
    assert len(scan_file(bad)) == 1


def test_writer_allowlist_skipped(tmp_path):
    """A file under the allowlist (corpus_core/index.py suffix) is skipped
    even if it contains raw FROM annotations (writer is legitimate)."""
    # Mimic an allowlisted writer path.
    writer_dir = tmp_path / "corpus_core"
    writer_dir.mkdir()
    writer_file = writer_dir / "index.py"
    writer_file.write_text(
        'def rebuild():\n'
        '    return "DELETE FROM annotations"  # writer is the only DELETE site\n'
    )
    out = scan_paths([writer_file])
    assert writer_file not in out


def test_live_repo_clean():
    """The live scripts/ + packages/ tree must be clean — no raw
    `FROM annotations` outside the writer allowlist."""
    violations = scan_paths([ROOT / "scripts"])
    if violations:
        msg = "\n".join(
            f"  {p}:{ln}: {ctx}"
            for p, vs in violations.items() for ln, ctx in vs
        )
        pytest.fail(f"live tree has raw FROM annotations:\n{msg}")
