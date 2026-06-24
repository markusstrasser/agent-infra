#!/usr/bin/env python3
"""pulse_tick.py — phased RSI motor (internal to pulse CLI).

Single orchestrator replacing drift-sentinel, blindspot-miner, act-drain,
gov-report, integrate-rank, and maintain-tick launchd jobs. Writes inspectable
state to artifacts/pulse/last-tick.json; surfaces via `pulse status --write-inbox`.

Phases: substrate → sense → drain → synthesize → motor → surface
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
STATE_DIR = REPO / "artifacts" / "pulse"
STATE_FILE = STATE_DIR / "last-tick.json"
EMB = Path.home() / "Projects" / "emb"

PHASE_ORDER = ("substrate", "sense", "drain", "synthesize", "motor", "surface")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], timeout: int = 300, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd or REPO),
    )


def _phase_substrate() -> dict:
    db = Path.home() / ".claude" / "agentlogs.db"
    if not db.is_file():
        return {"ok": False, "error": "agentlogs.db missing"}
    try:
        import sqlite3

        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        row = con.execute("SELECT MAX(started_at) FROM runs").fetchone()
        con.close()
        if not row or not row[0]:
            return {"ok": False, "error": "no runs in agentlogs.db"}
        latest = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
        lag_min = round((datetime.now(timezone.utc) - latest).total_seconds() / 60)
        ok = lag_min < 240
        return {"ok": ok, "agentlogs_lag_min": lag_min, "latest_run": row[0]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _drift_sections() -> list[dict]:
    """Deterministic drift checks (ported from drift-sentinel.sh)."""
    checks = [
        ("freshness", ["just", "-f", str(REPO / "justfile"), "freshness"], "DUE"),
        ("orphan_findings", [sys.executable, str(SCRIPTS / "orphan_findings.py")], "un-harvested in [1-9]"),
        ("orphan_check", [sys.executable, str(SCRIPTS / "orphan_check.py")], "candidate orphan"),
        ("orient_drift", [sys.executable, str(SCRIPTS / "orient.py"), "--drift"], "✗"),
        ("context_budget", [sys.executable, str(SCRIPTS / "context-budget.py"), "--check"], "OVER"),
        ("skills_budget", [sys.executable, str(SCRIPTS / "skills_budget.py"), "--check"], "OVER|fail"),
        ("worktree_stranded", [sys.executable, str(SCRIPTS / "worktree_gc.py"), "--check"], "STRANDED"),
    ]
    flags: list[dict] = []
    for name, cmd, pat in checks:
        try:
            r = _run(cmd, timeout=120)
            text = (r.stdout or "") + (r.stderr or "")
            import re

            if re.search(pat, text, re.I):
                flags.append({"check": name, "excerpt": "\n".join(text.splitlines()[:8])})
        except Exception as exc:
            flags.append({"check": name, "error": str(exc)[:120]})
    return flags


def _phase_sense() -> dict:
    # drift_flags are ADVISORY output (context-budget warnings, orphan candidates,
    # DUE sweeps, stranded worktrees) surfaced to the human via the status digest/inbox.
    # Their presence is the STEADY STATE, not a tick failure — conflating "advisory drift
    # exists" with "the tick failed" pinned pulse-tick permanently exit-1 → permanently RED
    # in launchd/system-inventory, making the health sweep pure noise. exit_code must reflect
    # EXECUTION health only: a canary ALARM (dead instrument, below) or a phase crash.
    out: dict = {"ok": True, "drift_flags": _drift_sections()}

    # blindspot miner (emb env)
    if EMB.is_dir():
        try:
            r = _run(
                ["uv", "run", "--project", str(EMB), "python3", str(SCRIPTS / "blindspot_miner.py"),
                 "--days", "7", "--json", "--no-file"],
                timeout=600,
            )
            if r.returncode == 0 and r.stdout.strip():
                flags = json.loads(r.stdout)
                out["blindspot_flags"] = len(flags)
                out["blindspot_top"] = flags[:6]
            else:
                out["blindspot_error"] = (r.stderr or r.stdout or f"exit {r.returncode}")[:200]
        except Exception as exc:
            out["blindspot_error"] = str(exc)[:200]
    else:
        out["blindspot_skipped"] = "emb not found"

    # gov shrink report (report-only)
    try:
        r = _run([sys.executable, str(SCRIPTS / "gov.py"), "report"], timeout=180)
        out["gov_report_exit"] = r.returncode
        out["gov_report_ok"] = r.returncode == 0
    except Exception as exc:
        out["gov_report_ok"] = False
        out["gov_report_error"] = str(exc)[:200]

    # instrument canary + register predictions
    try:
        r = _run([sys.executable, str(SCRIPTS / "pulse.py"), "canary"], timeout=120)
        out["canary_exit"] = r.returncode
        out["canary_ok"] = r.returncode == 0
        if r.returncode != 0:
            out["ok"] = False
    except Exception as exc:
        out["canary_ok"] = False
        out["canary_error"] = str(exc)[:200]
        out["ok"] = False

    try:
        r = _run([sys.executable, str(SCRIPTS / "register_implementations.py")], timeout=120)
        out["register_impl"] = (r.stdout or r.stderr or "")[:300]
    except Exception as exc:
        out["register_impl_error"] = str(exc)[:120]

    return out


def _phase_drain() -> dict:
    sys.path.insert(0, str(SCRIPTS))
    import act_drain as ad  # noqa: E402
    import loop_funnel as lf  # noqa: E402

    summary = ad.run_classify()
    metrics = lf.metrics()
    return {
        "ok": True,
        "classify_summary": summary[:500],
        "disposition_queue": metrics["disposition_queue"],
        "unclassified": metrics["unclassified"],
        "funnel": {k: metrics[k] for k in (
            "captured", "classified", "unclassified", "quarantine_pending",
            "steward_proposals", "rsi_close_pending", "disposition_queue",
        )},
    }


def _phase_synthesize() -> dict:
    memo = REPO / "research" / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-auto-integration-rank.md"
    try:
        r = _run(
            [sys.executable, str(SCRIPTS / "sensor_integration_ranking.py"), "--no-llm"],
            timeout=180,
        )
        return {
            "ok": r.returncode == 0,
            "exit": r.returncode,
            "memo": str(memo.relative_to(REPO)) if memo.is_file() else None,
            "stdout_tail": (r.stdout or "")[-300:],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _phase_motor() -> dict:
    try:
        r = _run([sys.executable, str(SCRIPTS / "maintain_tick.py"), "--json"], timeout=300)
        if r.stdout.strip():
            try:
                body = json.loads(r.stdout)
            except json.JSONDecodeError:
                body = {"raw": r.stdout[:500]}
        else:
            body = {"exit": r.returncode, "stderr": (r.stderr or "")[:300]}
        body["ok"] = r.returncode == 0
        return body
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _phase_surface() -> dict:
    try:
        r = _run(
            [sys.executable, str(SCRIPTS / "pulse.py"), "status", "--write-inbox"],
            timeout=120,
        )
        return {"ok": r.returncode in (0, 1), "exit": r.returncode, "log": (r.stdout or r.stderr or "")[:300]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


PHASE_RUNNERS = {
    "substrate": _phase_substrate,
    "sense": _phase_sense,
    "drain": _phase_drain,
    "synthesize": _phase_synthesize,
    "motor": _phase_motor,
    "surface": _phase_surface,
}


def run_tick(phases: tuple[str, ...] | None = None) -> dict:
    phases = phases or PHASE_ORDER
    tick_id = _utc_now()
    state: dict = {"tick_id": tick_id, "started_at": tick_id, "phases": {}}
    t0 = time.time()
    exit_code = 0
    for name in phases:
        if name not in PHASE_RUNNERS:
            state["phases"][name] = {"ok": False, "error": f"unknown phase {name}"}
            exit_code = 1
            continue
        try:
            result = PHASE_RUNNERS[name]()
        except Exception as exc:
            result = {"ok": False, "error": str(exc)[:200]}
        state["phases"][name] = result
        if not result.get("ok", True):
            exit_code = 1
    state["finished_at"] = _utc_now()
    state["duration_s"] = round(time.time() - t0, 1)
    state["exit_code"] = exit_code
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def last_tick() -> dict | None:
    if not STATE_FILE.is_file():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
