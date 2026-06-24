#!/usr/bin/env python3
"""pulse.py — RSI-loop instrument-liveness surface. Owns the closure brain; reads sensors as feeds.

(Named `pulse`, not `rsi`: it checks whether each closure instrument has a pulse — the
RSI loop is the paradigm, this is one narrow tool within it.)

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

Phase 0+: `status` — unified control-plane inbox; `tick` — phased motor; `funnel` — queue depths.
Legacy digest/surface/launchd scatter removed — pulse owns the RSI control plane end-to-end.

Gov-ID: hook:pulse-instrument-canary
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
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

REPO = Path(__file__).resolve().parent.parent
INBOX = Path.home() / ".claude" / "control-plane-inbox.md"
MAINTAIN_DIR = REPO / "artifacts" / "maintain"
HISTORY = Path.home() / ".claude" / "pulse-canary-history.jsonl"  # the canary's own observation log (append-only, reconstructible — NOT a source of truth)
WINDOW = 5          # observations compared for the constancy test
STALE_SECONDS = 36 * 3600  # an instrument with no fresh observation in 36h is stale


# --- probes: each returns the instrument's current scalar (float) or None if absent ---
# A probe READS an existing sensor; it never recomputes the sensor's logic.

def _run(cmd: list[str], timeout: int = 60) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def _supervision_today() -> tuple[float | None, float | None, float | None]:
    """(total_hooks_shown, mean_air, total_correction_load) for today."""
    out = _run(["uv", "run", "python3", str(Path(__file__).parent / "supervision-kpi.py"), "--today"])
    rows = [json.loads(l) for l in out.splitlines() if l.strip().startswith("{")]
    if not rows:
        return None, None, None
    hooks = sum(r.get("hooks_shown", 0) for r in rows)
    airs = [r["air"] for r in rows if r.get("air") is not None]
    load = sum(r.get("load", 0) for r in rows)
    return float(hooks), (sum(airs) / len(airs) if airs else None), float(load)


def probe_hooks_shown() -> float | None:
    return _supervision_today()[0]


def probe_air() -> float | None:
    return _supervision_today()[1]


def probe_correction_load() -> float | None:
    return _supervision_today()[2]


# Each instrument declares a LIVENESS CONTRACT — the test direction, DECLARED not inferred.
# Inferring "expected variance" from history would ingest the AIR-1591 constant-0 as "normal"
# and launder the exact bug the canary exists to catch (repo-grounded critique 2026-06-16).
#   should-vary → constancy means DEAD (null/stale/constant all alarm). For metrics that move
#                 under ordinary operation (the declining-supervision KPIs).
#   may-rest    → constancy is HEALTHY (only null/stale alarm). For metrics legitimately flat
#                 (config flags, thresholds, a gate at its steady state). NOT registered yet —
#                 the slot exists so generalizing the registry can't false-alarm on green.
# floor → for a should-vary OBJECTIVE metric whose SUCCESS state is a stable value (e.g.
#         correction_load → 0 = perfect autonomy). Constant AT the floor is HEALTHY (objective
#         reached); constant ELSEWHERE is the dead-producer bug (319 ≠ 0). This is what stops
#         the canary from false-alarming on its own win — without it, supervision genuinely
#         declining to 0 would read identical to a frozen producer. A no-data day returns None
#         (NULL alarm, separate path), so a real constant-0 only comes from sessions with zero
#         corrections. floor=None (hooks_shown/air) → ANY constancy alarms (0/null WAS the bug).
# Register ONLY gating/trusted/should-vary metrics — a doctor health check (healthy==constant)
# would alarm-on-green and re-blind the operator (do NOT add).
class Instrument(NamedTuple):
    probe: Callable[[], float | None]
    contract: str
    note: str
    floor: float | None = None


INSTRUMENTS = {
    "supervision.hooks_shown":     Instrument(probe_hooks_shown,     "should-vary", "hooks surfaced/turn (was constant 0 for 1591 sessions)"),
    "supervision.air":             Instrument(probe_air,             "should-vary", "corrections after a shown hook (was null — the dead-field bug)"),
    "supervision.correction_load": Instrument(probe_correction_load, "should-vary", "total correction load/day — the declining-supervision objective", floor=0.0),
}


def _read_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    return [json.loads(l) for l in HISTORY.read_text().splitlines() if l.strip()]


def _append(name: str, value, ts: float) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a") as f:
        f.write(json.dumps({"name": name, "value": value, "ts": ts}) + "\n")


def _judge(name: str, hist: list[dict], now: float, contract: str = "should-vary",
           floor: float | None = None) -> tuple[str, str]:
    """Return (level, reason). level in {ok, alarm}. Fail loud, PER INSTRUMENT.
    The constancy test fires ONLY for should-vary metrics — a may-rest metric is
    legitimately flat, so constant != dead there (else alarm-on-green re-blinds).
    A should-vary metric WITH a floor is exempt from the constancy alarm when it
    is constant AT the floor (objective reached) — but still alarms if frozen
    anywhere else (the dead-producer bug)."""
    mine = [h for h in hist if h["name"] == name]
    latest = mine[-1] if mine else None
    if latest is None or latest["value"] is None:
        return "alarm", "NULL — no value produced (instrument absent or dead field)"
    if now - latest["ts"] > STALE_SECONDS:
        age_h = round((now - latest["ts"]) / 3600)
        return "alarm", f"STALE — freshest observation {age_h}h old"
    if contract == "should-vary":
        recent = [h["value"] for h in mine[-WINDOW:] if h["value"] is not None]
        if len(recent) >= WINDOW and len(set(recent)) == 1:
            value = recent[-1]
            if floor is not None and value == floor:
                return "ok", f"AT FLOOR ({floor}) — objective at rest, not a dead producer"
            return "alarm", f"CONSTANT — last {WINDOW} should-vary observations all = {value} (the AIR-1591 bug class)"
    return "ok", f"value={latest['value']}"


def cmd_canary(args) -> int:
    """Observe every instrument, append to history, judge null/constant/stale."""
    now = time.time()
    for name, inst in INSTRUMENTS.items():
        try:
            val = inst.probe()
        except Exception as e:
            val = None
            print(f"  probe error {name}: {e}", file=sys.stderr)
        _append(name, val, now)
    hist = _read_history()
    alarms = 0
    for name, inst in INSTRUMENTS.items():
        level, reason = _judge(name, hist, now, inst.contract, inst.floor)
        glyph = "✓" if level == "ok" else "✗"
        print(f"  {glyph} {name}: {reason}" + (f"  — {inst.note}" if level == "alarm" else ""))
        if level == "alarm":
            alarms += 1
    if alarms:
        print(f"\npulse canary: {alarms} instrument(s) ALARM — a closure metric is dead/blind", file=sys.stderr)
        return 1
    print(f"\npulse canary: {len(INSTRUMENTS)} instruments live")
    return 0


def cmd_registry(_args) -> int:
    for name, inst in INSTRUMENTS.items():
        floor = f" floor={inst.floor}" if inst.floor is not None else ""
        print(f"  {name}  [{inst.contract}{floor}] — {inst.note}")
    return 0


def canary_summary(now: float | None = None) -> dict:
    """Read-only canary verdict from history — does not run probes."""
    now = now or time.time()
    hist = _read_history()
    alarms, ok = [], []
    for name, inst in INSTRUMENTS.items():
        level, reason = _judge(name, hist, now, inst.contract, inst.floor)
        row = {"name": name, "level": level, "reason": reason, "note": inst.note}
        (alarms if level == "alarm" else ok).append(row)
    return {"alarm_count": len(alarms), "alarms": alarms, "ok": ok}


def _latest_maintain_draft() -> dict | None:
    if not MAINTAIN_DIR.is_dir():
        return None
    files = sorted(MAINTAIN_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    f = files[0]
    try:
        rel = str(f.relative_to(REPO))
    except ValueError:
        rel = str(f)
    return {"path": rel, "slug": f.stem, "mtime": f.stat().st_mtime}


def _load_tick_state() -> dict | None:
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import pulse_tick as pt  # noqa: E402
        return pt.last_tick()
    except Exception:
        return None


def _priorities_head(n: int = 5) -> list[dict]:
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import top_priorities as tp  # noqa: E402
        return tp.gather()[:n]
    except Exception:
        return []


def gather_status(repo: Path | None = None) -> dict:
    """Aggregate control-plane metrics from existing sensors (zero new stores)."""
    repo = repo or REPO
    sys.path.insert(0, str(repo / "scripts"))
    import loop_funnel as lf  # noqa: E402
    import questions_view as qv  # noqa: E402
    import predictions  # noqa: E402

    funnel = lf.metrics()
    questions = qv.collect_questions(repo)
    qsection = qv.render_section(questions)
    due = predictions.due_predictions()
    canary = canary_summary()
    maintain = _latest_maintain_draft()
    tick = _load_tick_state()
    return {
        "funnel": funnel,
        "funnel_needs_attention": lf.needs_attention(funnel),
        "questions_count": len(questions.questions),
        "questions_section": qsection,
        "predictions_due": due,
        "canary": canary,
        "maintain_draft": maintain,
        "tick": tick,
        "priorities": _priorities_head(),
    }


def status_needs_attention(m: dict) -> bool:
    if m["funnel_needs_attention"]:
        return True
    if m["questions_count"] > 0:
        return True
    if m["canary"]["alarm_count"] > 0:
        return True
    if m["predictions_due"]:
        return True
    if m.get("maintain_draft"):
        return True
    tick = m.get("tick") or {}
    sense = (tick.get("phases") or {}).get("sense") or {}
    if sense.get("drift_flags"):
        return True
    if sense.get("blindspot_flags", 0) > 0:
        return True
    if m.get("priorities"):
        return True
    return False


def render_status(m: dict) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        f"# Control plane — {stamp}",
        "_Unified RSI surface (`pulse status`). Run `just pulse-tick` on schedule._",
        "",
    ]
    if m["questions_section"]:
        parts.extend([m["questions_section"], ""])
    if m.get("priorities"):
        parts.append("## Top priorities")
        for i, item in enumerate(m["priorities"], 1):
            parts.append(f"{i}. **[{item.get('klass', '?')}]** {item.get('title', '?')}")
            parts.append(f"   - → {item.get('action', '?')}")
        parts.append("")
    parts.append("## Loop funnel")
    sys.path.insert(0, str(REPO / "scripts"))
    import loop_funnel as lf  # noqa: E402
    parts.append(lf.render(m["funnel"]).rstrip())
    parts.append("")
    tick = m.get("tick") or {}
    sense = (tick.get("phases") or {}).get("sense") or {}
    if sense.get("drift_flags"):
        parts.append("## Drift flags")
        for row in sense["drift_flags"][:8]:
            parts.append(f"- **{row.get('check', '?')}**: {(row.get('excerpt') or row.get('error', ''))[:120]}")
        parts.append("")
    if sense.get("blindspot_top"):
        parts.append(f"## Blindspot ({sense.get('blindspot_flags', len(sense['blindspot_top']))} flags)")
        for f in sense["blindspot_top"][:6]:
            parts.append(f"- `{f.get('project', '?')}/{f.get('session', '?')}` [{f.get('type', '?')}]")
        parts.append("")
    parts.append("## Instrument canary")
    if m["canary"]["alarm_count"]:
        for row in m["canary"]["alarms"]:
            parts.append(f"- ✗ **{row['name']}**: {row['reason']}")
    else:
        parts.append(f"- ✓ {len(m['canary']['ok'])} instruments live (run `pulse canary` to refresh)")
    parts.append("")
    if tick.get("tick_id"):
        parts.append(f"_Last tick: {tick['tick_id']} ({tick.get('duration_s', '?')}s, exit {tick.get('exit_code', '?')})_")
        parts.append("")
    if m.get("maintain_draft"):
        d = m["maintain_draft"]
        parts.extend([
            "## Motor draft",
            f"- Latest: `{d['path']}`",
            "",
        ])
    if m["predictions_due"]:
        parts.append("## Predictions due")
        for p in m["predictions_due"][:5]:
            parts.append(f"- `{p.get('id', '?')}` — {p.get('change', '')[:100]}")
        if len(m["predictions_due"]) > 5:
            parts.append(f"- … and {len(m['predictions_due']) - 5} more")
        parts.append("")
    parts.extend([
        "**Next:** `/rsi close` · `just reflect-review` · `/improve maintain` · `just questions`",
    ])
    return "\n".join(parts) + "\n"


def cmd_status(args) -> int:
    m = gather_status(REPO)
    if args.json:
        slim = {
            "funnel_needs_attention": m["funnel_needs_attention"],
            "disposition_queue": m["funnel"]["disposition_queue"],
            "unclassified": m["funnel"]["unclassified"],
            "questions_count": m["questions_count"],
            "predictions_due_count": len(m["predictions_due"]),
            "canary_alarm_count": m["canary"]["alarm_count"],
            "maintain_draft": m.get("maintain_draft"),
            "needs_attention": status_needs_attention(m),
            "last_tick": (m.get("tick") or {}).get("tick_id"),
            "priorities_count": len(m.get("priorities") or []),
        }
        print(json.dumps(slim, indent=2))
        return 0
    digest = render_status(m)
    if args.write_inbox:
        path = Path(args.inbox_path)
        if status_needs_attention(m):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(digest, encoding="utf-8")
            print(f"[pulse status] wrote {path}")
        else:
            path.unlink(missing_ok=True)
            print("[pulse status] all green — inbox cleared")
    else:
        print(digest, end="")
    return 1 if m["canary"]["alarm_count"] else 0


def cmd_funnel(args) -> int:
    sys.path.insert(0, str(REPO / "scripts"))
    import loop_funnel as lf  # noqa: E402
    m = lf.metrics()
    if args.json:
        slim = {k: v for k, v in m.items() if k not in ("rsi_pending", "quarantine")}
        slim["rsi_pending_count"] = len(m["rsi_pending"])
        print(json.dumps(slim, indent=2))
        return 0
    print(lf.render(m), end="")
    return 0


def cmd_tick(args) -> int:
    sys.path.insert(0, str(REPO / "scripts"))
    import pulse_tick as pt  # noqa: E402
    phases = tuple(args.phase) if args.phase else pt.PHASE_ORDER
    state = pt.run_tick(phases=phases)
    if args.json:
        print(json.dumps(state, indent=2))
    else:
        for name, result in state.get("phases", {}).items():
            ok = "✓" if result.get("ok", True) else "✗"
            print(f"  {ok} {name}")
        print(f"\npulse tick: exit {state.get('exit_code', 0)} — state {pt.STATE_FILE}")
    return int(state.get("exit_code", 0))


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
    # floor: constant AT floor = healthy (objective at rest); constant elsewhere = dead.
    floor_hist = [{"name": "fl", "value": 0.0, "ts": now - i} for i in range(WINDOW)]
    lvl_floor, why_floor = _judge("fl", floor_hist, now, floor=0.0)
    assert lvl_floor == "ok" and "FLOOR" in why_floor, f"floor metric at floor should be ok: {lvl_floor}/{why_floor}"
    frozen_hist = [{"name": "fz", "value": 319.0, "ts": now - i} for i in range(WINDOW)]
    lvl_frozen, _ = _judge("fz", frozen_hist, now, floor=0.0)
    assert lvl_frozen == "alarm", "a floor metric frozen ABOVE the floor (319≠0) must still alarm (dead producer)"
    print("pulse selftest: constant + null + stale flagged; floor-at-rest ok, floor-frozen-elsewhere alarms ✓")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="pulse.py — RSI control plane (canary/gate/funnel/status/tick)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("canary", help="check each closure instrument for null/constant/stale").set_defaults(fn=cmd_canary)
    sub.add_parser("registry", help="list watched instruments").set_defaults(fn=cmd_registry)
    sub.add_parser("gate", help="anti-windup gate (FM-ID granularity, advisory)").set_defaults(fn=cmd_gate)
    fn = sub.add_parser("funnel", help="loop funnel queue depths")
    fn.add_argument("--json", action="store_true")
    fn.set_defaults(fn=cmd_funnel)
    tk = sub.add_parser("tick", help="phased RSI motor (substrate→sense→drain→synthesize→motor→surface)")
    tk.add_argument("--phase", action="append", choices=("substrate", "sense", "drain", "synthesize", "motor", "surface"))
    tk.add_argument("--json", action="store_true")
    tk.set_defaults(fn=cmd_tick)
    st = sub.add_parser("status", help="unified control-plane inbox")
    st.add_argument("--json", action="store_true")
    st.add_argument("--write-inbox", action="store_true", help="write ~/.claude/control-plane-inbox.md when attention needed")
    st.add_argument("--inbox-path", default=str(INBOX))
    st.set_defaults(fn=cmd_status)
    sub.add_parser("selftest", help="prove the canary flags constant/null/stale").set_defaults(fn=lambda _a: _selftest())
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
