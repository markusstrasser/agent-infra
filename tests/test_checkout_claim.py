"""Tests for scripts/checkout_claim.py — the per-checkout claim-lock primitive.

Covers the load-bearing invariants from the ADR: claim/read round-trip, precise
live-peer detection, stale (dead-pid) reclaim, owner-only release, and fail-open on
missing/corrupt locks.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import checkout_claim as cc


def _dead_pid() -> int:
    """A pid guaranteed not alive: spawn a trivial process, reap it, return its pid."""
    p = subprocess.Popen(["true"])
    p.wait()
    return p.pid


def test_claim_and_read_roundtrip(tmp_path: Path) -> None:
    c = cc.claim(tmp_path, "sess-A", started_at="2026-06-16T00:00:00+00:00")
    assert c.session_id == "sess-A"
    assert c.pid == os.getpid()
    back = cc.read_claim(tmp_path)
    assert back is not None
    assert back.session_id == "sess-A"
    assert back.started_at == "2026-06-16T00:00:00+00:00"
    # Lock lives under .claude/ (gitignored runtime state)
    assert (tmp_path / ".claude" / "checkout-claim.json").is_file()


def test_peer_held_distinguishes_self_from_live_peer(tmp_path: Path) -> None:
    # A live holder (my own pid) under session A.
    cc.claim(tmp_path, "sess-A", pid=os.getpid())
    # Another session sees a live peer ...
    peer = cc.peer_held(tmp_path, "sess-B")
    assert peer is not None and peer.session_id == "sess-A"
    # ... but the owner does not see itself as a peer.
    assert cc.peer_held(tmp_path, "sess-A") is None


def test_stale_claim_is_not_a_live_holder(tmp_path: Path) -> None:
    cc.claim(tmp_path, "sess-dead", pid=_dead_pid())
    assert cc.read_claim(tmp_path) is not None        # the file is still there ...
    assert cc.live_holder(tmp_path) is None            # ... but the holder is dead
    assert cc.peer_held(tmp_path, "sess-other") is None  # so it never blocks isolation


def test_reused_pid_is_not_a_live_holder(tmp_path: Path) -> None:
    # 2026-10-14: a launch reported a live peer whose pid macOS had given to
    # SafariLaunchAgent. The pid exists, but its start time is not the claimed one.
    cc.claim(tmp_path, "sess-A", pid=os.getpid())
    lock = tmp_path / ".claude" / "checkout-claim.json"
    d = json.loads(lock.read_text(encoding="utf-8"))
    assert d["proc_start"]                               # fingerprint recorded
    d["proc_start"] = "Thu Jan  1 00:00:00 1970"
    lock.write_text(json.dumps(d), encoding="utf-8")
    assert cc.live_holder(tmp_path) is None
    assert cc.peer_held(tmp_path, "sess-B") is None


def test_lock_without_fingerprint_is_stale(tmp_path: Path) -> None:
    # Locks written before the fingerprint hold the claim helper's own pid.
    lock = tmp_path / ".claude" / "checkout-claim.json"
    lock.parent.mkdir(parents=True)
    lock.write_text(json.dumps({"pid": os.getpid(), "session_id": "launch-65590",
                                "started_at": "2026-10-13T15:07:24+00:00", "host": "h"}),
                    encoding="utf-8")
    assert cc.read_claim(tmp_path) is not None
    assert cc.live_holder(tmp_path) is None


def test_cli_claim_records_the_given_pid(tmp_path: Path) -> None:
    holder = subprocess.Popen(["sleep", "30"])
    try:
        rc = cc.main(["-C", str(tmp_path), "claim", "--session", "s", "--pid", str(holder.pid)])
        assert rc == 0
        c = cc.read_claim(tmp_path)
        assert c is not None and c.pid == holder.pid and c.proc_start
        assert cc.peer_held(tmp_path, "other") is not None
    finally:
        holder.kill()
        holder.wait()
    assert cc.peer_held(tmp_path, "other") is None      # stale once the holder exits


def test_cli_claim_refuses_a_dead_pid(tmp_path: Path, capsys) -> None:
    rc = cc.main(["-C", str(tmp_path), "claim", "--session", "s", "--pid", str(_dead_pid())])
    assert rc == 3
    assert "not running" in capsys.readouterr().err
    assert cc.read_claim(tmp_path) is None


def test_release_is_owner_only(tmp_path: Path) -> None:
    cc.claim(tmp_path, "sess-A")
    assert cc.release(tmp_path, "sess-B") is False      # not the owner
    assert cc.read_claim(tmp_path) is not None          # lock survives
    assert cc.release(tmp_path, "sess-A") is True        # owner releases
    assert cc.read_claim(tmp_path) is None


def test_fail_open_on_missing_and_corrupt(tmp_path: Path) -> None:
    assert cc.read_claim(tmp_path) is None              # missing → None, not error
    assert cc.live_holder(tmp_path) is None
    lock = tmp_path / ".claude" / "checkout-claim.json"
    lock.parent.mkdir(parents=True)
    lock.write_text("{not valid json", encoding="utf-8")
    assert cc.read_claim(tmp_path) is None              # corrupt → None, not error


def test_peer_cli_exit_codes(tmp_path: Path) -> None:
    cc.claim(tmp_path, "sess-A", pid=os.getpid())
    # peer subcommand: exit 0 when a live peer holds it, 1 otherwise
    assert cc.main(["-C", str(tmp_path), "peer", "--session", "sess-B"]) == 0
    assert cc.main(["-C", str(tmp_path), "peer", "--session", "sess-A"]) == 1


def test_status_json_shape(tmp_path: Path, capsys) -> None:
    cc.claim(tmp_path, "sess-A", pid=os.getpid())
    cc.main(["-C", str(tmp_path), "status", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["alive"] is True
    assert out["holder"]["session_id"] == "sess-A"
