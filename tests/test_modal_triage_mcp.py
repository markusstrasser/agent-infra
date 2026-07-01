"""modal-triage MCP must FAIL LOUD on `modal app list --json` schema drift.

2026-07-01: the running MCP returned 25 all-null records with is_running=True (a stale
pre-key-normalization process) — a silent-proxy lie that nearly caused a wrongful kill of
a progressing job. The durable guard: when key-normalization yields no app_id, never guess
liveness — raise _ModalParseDrift (status/triage) or return an error (list_apps).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modal_triage_mcp as mt


def _mock_modal(records):
    return lambda args: (0, json.dumps(records), "")


def test_valid_snake_case_1_5_1_parses():
    rec = mt._app_record(
        mt._norm_record({"app_id": "ap-1", "state": "ephemeral", "created_at": None})
    )
    assert rec["app_id"] == "ap-1"


def test_title_case_1_4_2_still_normalizes():
    rec = mt._app_record(mt._norm_record({"App ID": "ap-1", "State": "ephemeral"}))
    assert rec["app_id"] == "ap-1"


def test_app_record_none_app_id_on_key_drift():
    # a future schema (camelCase) doesn't normalize to app_id → None: the fail-loud trigger.
    rec = mt._app_record(mt._norm_record({"appId": "ap-1", "State": "ephemeral"}))
    assert rec["app_id"] is None


def test_find_record_raises_parse_drift(monkeypatch):
    monkeypatch.setattr(mt, "_run_modal", _mock_modal([{"appId": "ap-1"}, {"appId": "ap-2"}]))
    with pytest.raises(mt._ModalParseDrift):
        mt._find_record("ap-1")


def test_find_record_genuine_not_found_still_returns_none(monkeypatch):
    # A real (parseable) record set with no match must still return None, NOT raise —
    # so "app not found" stays a valid answer distinct from parse drift.
    monkeypatch.setattr(mt, "_run_modal", _mock_modal([{"app_id": "ap-1", "state": "x"}]))
    assert mt._find_record("ap-1") is not None
    assert mt._find_record("ap-absent") is None


def _unwrap(tool):
    return getattr(tool, "fn", tool)


def test_list_apps_fails_loud_not_garbage(monkeypatch):
    monkeypatch.setattr(mt, "_run_modal", _mock_modal([{"appId": "ap-1"}, {"appId": "ap-2"}]))
    fn = _unwrap(mt.list_apps)
    if not callable(fn):
        pytest.skip("list_apps not directly callable in this FastMCP version")
    out = json.loads(fn())
    assert "error" in out and "parse drift" in out["error"]
    assert "apps" not in out  # never emits is_running garbage


def test_status_fails_loud_on_drift(monkeypatch):
    monkeypatch.setattr(mt, "_run_modal", _mock_modal([{"appId": "ap-1"}]))
    fn = _unwrap(mt.status)
    if not callable(fn):
        pytest.skip("status not directly callable in this FastMCP version")
    out = json.loads(fn("ap-1"))
    assert "error" in out and "UNKNOWN" in out["error"]
