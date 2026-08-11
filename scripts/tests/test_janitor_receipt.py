"""Janitor receipt v1 — write + staleness check."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import janitor_receipt as jr


def test_write_and_load(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(jr, "RECEIPT_DIR", tmp_path)
    path = jr.write_receipt("worktree_gc", principal_metric=2, detail="removed 2")
    assert path.is_file()
    rec = jr.load_receipt("worktree_gc")
    assert rec is not None
    assert rec["motor"] == "worktree_gc"
    assert rec["principal_metric"] == 2
    assert rec["success"] is True
    assert rec["last_success_ts"]


def test_failed_attempt_preserves_last_success(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(jr, "RECEIPT_DIR", tmp_path)
    jr.write_receipt("uv_cache_prune", principal_metric=1)
    first = jr.load_receipt("uv_cache_prune")["last_success_ts"]
    jr.write_receipt("uv_cache_prune", error_class="lock_timeout", detail="uv lock held")
    rec = jr.load_receipt("uv_cache_prune")
    assert rec["error_class"] == "lock_timeout"
    assert rec["last_success_ts"] == first  # preserved


def test_stale_detection(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(jr, "RECEIPT_DIR", tmp_path)
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = jr.receipt_path("worktree_gc")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"motor":"worktree_gc","last_success_ts":"%s","principal_metric":0,'
        '"error_class":null,"detail":"","success":true,"last_attempt_ts":"%s"}\n' % (old, old)
    )
    rows = jr.stale_motors(("worktree_gc",), max_age_hours=36)
    assert rows[0]["status"] == "stale"


def test_fresh_ok(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(jr, "RECEIPT_DIR", tmp_path)
    jr.write_receipt("reclaim_rotate", principal_metric=0)
    rows = jr.stale_motors(("reclaim_rotate",), max_age_hours=36)
    assert rows[0]["status"] == "ok"
