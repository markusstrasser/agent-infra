"""Cursor self-healing for clash_detect.py — the line-offset cursor must reset to 0 when
the capture log is rotated/truncated (reclaim-rotate, or a manual reset), or it silently
drops every future capture. Pure-function tests; no llmx dispatch.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/

import clash_detect as cd  # noqa: E402


def _set_cursor(tmp_path, monkeypatch, value):
    cur = tmp_path / "clash-capture.cursor"
    cur.write_text(str(value))
    monkeypatch.setattr(cd, "CURSOR", cur)
    return cur


def test_cursor_resumes_when_in_range(tmp_path, monkeypatch):
    _set_cursor(tmp_path, monkeypatch, 3)
    assert cd._effective_cursor(10) == 3  # log has 10 lines, cursor 3 → resume at 3


def test_cursor_resets_on_truncation(tmp_path, monkeypatch):
    _set_cursor(tmp_path, monkeypatch, 5)
    assert cd._effective_cursor(2) == 0  # log shrank to 2 lines → rotated → reprocess from 0


def test_cursor_resets_on_deletion(tmp_path, monkeypatch):
    _set_cursor(tmp_path, monkeypatch, 5)
    assert cd._effective_cursor(0) == 0  # log emptied/deleted → reset, don't skip


def test_cursor_at_boundary_is_in_range(tmp_path, monkeypatch):
    _set_cursor(tmp_path, monkeypatch, 4)
    assert cd._effective_cursor(4) == 4  # cursor == line count → nothing new, NOT a reset


def test_no_cursor_file_defaults_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(cd, "CURSOR", tmp_path / "absent.cursor")
    assert cd._effective_cursor(10) == 0
