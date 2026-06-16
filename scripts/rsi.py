#!/usr/bin/env python3
"""rsi.py — RSI loop control surface. Owns the closure brain; reads sensors as feeds.

The single owner of "are my closure instruments alive and trusted." It defines NO
sensor logic — it shells/reads the existing organs (supervision-kpi, fm.py, reflect,
miners) and judges. ADR: decisions/2026-06-16-rsi-unified-control-surface.md.

Phase 1 (this file): `canary` — the null/constant/stale liveness check. This is the
capability whose ABSENCE let supervision-kpi read a dead field (hook_progress, 7x)
instead of hook_success (3600x) and report air=null / hooks_shown=0 for 1591 sessions,
silently. Count/null checks (doctor.py check_telemetry_freshness) miss it because the
bug produced a CONSTANT NON-NULL value, not a zero — so the canary's load-bearing test
is constancy over a window, not just null.

`gate` (thin, FM-ID granularity) and `registry` included; `weights` deferred until
≥2 detectors clear PPV (reflect.PPV_CLEARED is currently empty — no load to weight).

Gov-ID: hook:rsi-instrument-canary
goal: an RSI closure instrument silently going null / constant / stale (the AIR-1591 bug class)
verifier: null
blast_radius: local
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HISTORY = Path.home() / ".claude" / "rsi-canary-history.jsonl"  # the canary's own observation log (append-only, reconstructible — NOT a source of truth)
WINDOW = 5          # observations compared for the constancy test
STALE_SECONDS = 36 * 3600  # an instrument with no fresh observation in 36h is stale


# --- probes: each returns the instrument's current scalar (float) or None if absent ---
# A probe READS an existing sensor; it never recomputes the sensor's logic.

def _run(cmd: list[str], timeout: int = 60) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def _supervision_today() -> tuple[float | None, float | None]:
    """(total_hooks_shown, mean_air) for today — the two instruments that died."""
    out = _run(["uv", "run", "python3", str(Path(__file__).parent / "supervision-kpi.py"), "--today"])
    rows = [json.loads(l) for l in out.splitlines() if l.strip().startswith("{")]
    if not rows:
        return None, None
    hooks = sum(r.get("hooks_shown", 0) for r in rows)
    airs = [r["air"] for r in rows if r.get("air") is not None]
    return float(hooks), (sum(airs) / len(airs) if airs else None)


def probe_hooks_shown() -> float | None:
    return _supervision_today()[0]


def probe_air() -> float | None:
    return _supervision_today()[1]


# name -> (probe, human note). Add a row + a probe to watch a new closure instrument.
INSTRUMENTS = {
    "supervision.hooks_shown": (probe_hooks_shown, "hooks surfaced/turn (was constant 0 for 1591 sessions)"),
    "supervision.air":         (probe_air,         "corrections after a shown hook (was null — the dead-field bug)"),
}


def _read_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    return [json.loads(l) for l in HISTORY.read_text().splitlines() if l.strip()]


def _append(name: str, value, ts: float) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a") as f:
        f.write(json.dumps({"name": name, "value": value, "ts": ts}) + "\n")


def _judge(name: str, hist: list[dict], now: float) -> tuple[str, str]:
    """Return (level, reason). level in {ok, alarm}. Fail loud, PER INSTRUMENT."""
    mine = [h for h in hist if h["name"] == name]
    latest = mine[-1] if mine else None
    if latest is None or latest["value"] is None:
        return "alarm", "NULL — no value produced (instrument absent or dead field)"
    if now - latest["ts"] > STALE_SECONDS:
        age_h = round((now - latest["ts"]) / 3600)
        return "alarm", f"STALE — freshest observation {age_h}h old"
    recent = [h["value"] for h in mine[-WINDOW:] if h["value"] is not None]
    if len(recent) >= WINDOW and len(set(recent)) == 1:
        return "alarm", f"CONSTANT — last {WINDOW} observations all = {recent[-1]} (the AIR-1591 bug class)"
    return "ok", f"value={latest['value']}"


def cmd_canary(args) -> int:
    """Observe every instrument, append to history, judge null/constant/stale."""
    now = time.time()
    for name, (probe, _note) in INSTRUMENTS.items():
        try:
            val = probe()
        except Exception as e:
            val = None
            print(f"  probe error {name}: {e}", file=sys.stderr)
        _append(name, val, now)
    hist = _read_history()
    alarms = 0
    for name, (_probe, note) in INSTRUMENTS.items():
        level, reason = _judge(name, hist, now)
        glyph = "✓" if level == "ok" else "✗"
        print(f"  {glyph} {name}: {reason}" + (f"  — {note}" if level == "alarm" else ""))
        if level == "alarm":
            alarms += 1
    if alarms:
        print(f"\nrsi canary: {alarms} instrument(s) ALARM — a closure metric is dead/blind", file=sys.stderr)
        return 1
    print(f"\nrsi canary: {len(INSTRUMENTS)} instruments live")
    return 0


def cmd_registry(_args) -> int:
    for name, (_probe, note) in INSTRUMENTS.items():
        print(f"  {name} — {note}")
    return 0


def cmd_gate(args) -> int:
    """Thin anti-windup gate at FM-ID granularity: a promoted FM whose recurrence did
    NOT drop after fix_ts should NOT spawn more promotions of its kind. Reads fm.py
    recurrence (the existing metric); adds no measurement. FM-ID is the free granularity
    fm.py emits — axis-level rollup is deferred (ADR open fork)."""
    out = _run(["uv", "run", "python3", str(Path(__file__).parent / "fm.py"), "recurrence"])
    if not out.strip():
        print("  no resolved-FM recurrence data yet (nothing promoted to gate)")
        return 0
    print(out)
    print("  (gate verdict is advisory until a promotion flow exists to freeze — reflect.PPV_CLEARED empty)")
    return 0


def _selftest() -> int:
    """Prove the canary catches a CONSTANT non-null instrument (the AIR bug class) —
    not via the live probes but by injecting a synthetic constant series."""
    now = time.time()
    hist = [{"name": "synthetic", "value": 0.0, "ts": now - i} for i in range(WINDOW)]
    level, reason = _judge("synthetic", hist, now)
    assert level == "alarm" and "CONSTANT" in reason, f"canary failed to flag constant: {level}/{reason}"
    hist2 = [{"name": "syn2", "value": None, "ts": now}]
    level2, _ = _judge("syn2", hist2, now)
    assert level2 == "alarm", "canary failed to flag null"
    hist3 = [{"name": "syn3", "value": 1.0, "ts": now - STALE_SECONDS - 1}]
    level3, _ = _judge("syn3", hist3, now)
    assert level3 == "alarm", "canary failed to flag stale"
    print("rsi selftest: constant + null + stale all flagged ✓")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="rsi.py — RSI loop control surface (canary/gate/registry)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("canary", help="check each closure instrument for null/constant/stale").set_defaults(fn=cmd_canary)
    sub.add_parser("registry", help="list watched instruments").set_defaults(fn=cmd_registry)
    sub.add_parser("gate", help="anti-windup gate (FM-ID granularity, advisory)").set_defaults(fn=cmd_gate)
    sub.add_parser("selftest", help="prove the canary flags constant/null/stale").set_defaults(fn=lambda _a: _selftest())
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
