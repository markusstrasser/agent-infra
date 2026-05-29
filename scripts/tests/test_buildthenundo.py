"""Tests for the build-then-undo detector.

Monkeypatch the two isolated git-reading functions to plant synthetic
scenarios: assert a same-session add->delete is flagged, and a legitimate
revert is NOT.
"""

import buildthenundo as btu

REC = "\x1e"
SEP = "\x1f"


def _commit(sha, session, subject, lines):
    """Build one raw-log commit block: header + name-status lines."""
    head = f"{REC}{sha}{SEP}{session}{SEP}{subject}"
    return "\n".join([head, *lines])


def _log(*blocks):
    # git log is newest-first; tests pass blocks oldest-first, so reverse
    return "\n".join(reversed(blocks))


def _patch(monkeypatch, raw, numstat=None):
    monkeypatch.setattr(btu, "read_git_log", lambda days: raw)
    monkeypatch.setattr(
        btu, "read_numstat",
        lambda sha: numstat.get(sha, {}) if numstat else {},
    )


def test_same_session_add_then_delete_is_flagged(monkeypatch):
    raw = _log(
        _commit("a" * 40, "sess-1", "[x] Build extract pipeline",
                ["A\tscripts/extract.py"]),
        _commit("b" * 40, "sess-1", "[x] Drop extract pipeline — user feedback",
                ["D\tscripts/extract.py"]),
    )
    numstat = {
        "a" * 40: {"scripts/extract.py": (120, 0)},
        "b" * 40: {"scripts/extract.py": (0, 120)},
    }
    _patch(monkeypatch, raw, numstat)
    findings = btu.find_build_then_undo(days=30)
    assert len(findings) == 1
    f = findings[0]
    assert f["confidence"] == "high"
    assert f["files"] == ["scripts/extract.py"]
    assert f["session"] == "sess-1"
    assert f["lines_added"] == 120
    assert f["lines_deleted"] == 120


def test_legitimate_revert_is_not_flagged(monkeypatch):
    raw = _log(
        _commit("c" * 40, "sess-2", "[x] Add risky feature",
                ["A\tscripts/risky.py"]),
        _commit("d" * 40, "sess-2", "[x] Revert risky feature — broke CI",
                ["D\tscripts/risky.py"]),
    )
    _patch(monkeypatch, raw)
    assert btu.find_build_then_undo(days=30) == []


def test_test_files_excluded(monkeypatch):
    raw = _log(
        _commit("e" * 40, "sess-3", "[x] Add test", ["A\tscripts/tests/test_foo.py"]),
        _commit("f" * 40, "sess-3", "[x] Remove test", ["D\tscripts/tests/test_foo.py"]),
    )
    _patch(monkeypatch, raw)
    assert btu.find_build_then_undo(days=30) == []


def test_cross_session_is_medium_confidence(monkeypatch):
    raw = _log(
        _commit("1" * 40, "sess-A", "[x] Build thing", ["A\tscripts/thing.py"]),
        _commit("2" * 40, "sess-B", "[x] Remove thing", ["D\tscripts/thing.py"]),
    )
    _patch(monkeypatch, raw)
    findings = btu.find_build_then_undo(days=30)
    # cross-session: still flagged but medium, no session attribution
    assert len(findings) == 1
    assert findings[0]["confidence"] == "medium"
    assert findings[0]["session"] is None


def test_add_without_delete_is_not_flagged(monkeypatch):
    raw = _log(
        _commit("9" * 40, "sess-X", "[x] Build kept thing", ["A\tscripts/kept.py"]),
    )
    _patch(monkeypatch, raw)
    assert btu.find_build_then_undo(days=30) == []
