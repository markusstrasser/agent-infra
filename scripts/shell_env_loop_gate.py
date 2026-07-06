#!/usr/bin/env python3
"""shell_env_loop_gate.py — promote cross-harness shell-env failures into the RSI loop.

When scan_tool_failures surfaces zsh-env:* clusters above threshold AND
cross-harness shell guards are missing/broken (doctor), stage an actionable
candidate so /improve harvest doesn't rely on the human noticing transcript noise.

Usage:
    shell_env_loop_gate.py --days 30
    shell_env_loop_gate.py --failures-json artifacts/observe/.../failures.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()
SKILL = HOME / "Projects" / "skills" / "observe"
SCAN = SKILL / "scripts" / "scan_tool_failures.py"
PROMOTE_FAILS = 50
PROMOTE_DAYS = 2

SHELL_ENV_PREFIX = "zsh-env:"


def _run_scan(days: int) -> list[dict]:
    if not SCAN.is_file():
        return []
    proc = subprocess.run(
        [sys.executable, str(SCAN), "--days", str(days), "--json", "--interactive-only"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        return []
    return json.loads(proc.stdout or "[]")


def _cross_harness_status() -> tuple[bool, list[str]]:
    """Return (healthy, issues). Imports doctor check without running full suite."""
    sys.path.insert(0, str(REPO / "scripts"))
    import doctor as doc  # noqa: E402

    checks = doc.check_cross_harness_shell_env()
    ok_statuses = frozenset({"pass", "ok"})
    issues = [c.message for c in checks if c.status not in ok_statuses]
    return (len(issues) == 0, issues)


def assess(*, days: int = 30, failures: list[dict] | None = None) -> dict:
    rows = failures if failures is not None else _run_scan(days)
    shell_rows = [r for r in rows if str(r.get("cluster", "")).startswith(SHELL_ENV_PREFIX)]
    total_fails = sum(int(r.get("fails", 0)) for r in shell_rows)
    max_days = max((int(r.get("distinct_days", 0)) for r in shell_rows), default=0)
    healthy, issues = _cross_harness_status()
    promote = (
        total_fails >= PROMOTE_FAILS
        and max_days >= PROMOTE_DAYS
        and not healthy
    )
    return {
        "assessed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": days,
        "shell_env_clusters": shell_rows,
        "total_fails": total_fails,
        "max_distinct_days": max_days,
        "cross_harness_healthy": healthy,
        "cross_harness_issues": issues,
        "promote_actionable": promote,
        "promote_threshold_fails": PROMOTE_FAILS,
        "fix_hint": (
            "source agent-zsh-safe.sh in ~/.zshenv + ~/.zshrc rc phase; "
            "wire ~/.cursor/hooks.json with cursor_shell_guards.py"
        ),
    }


def stage_candidate(gate: dict, out_dir: Path) -> Path:
    """Persist the gate assessment and stage a candidate only when actionable."""
    out_dir.mkdir(parents=True, exist_ok=True)
    gate_path = out_dir / "shell-env-gate.json"
    gate_path.write_text(json.dumps(gate, indent=2) + "\n")
    if not gate.get("promote_actionable"):
        return gate_path
    cand_path = out_dir / "shell-env-candidate.jsonl"
    row = {
        "schema": "observe.candidate.v1",
        "kind": "infra_finding",
        "candidate_id": f"shell_env_gate_{gate['assessed_at'][:10]}",
        "mode": "failures",
        "state": "candidate",
        "promoted": False,
        "checkable": True,
        "priority": "high",
        "summary": (
            f"Cross-harness shell env gap — {gate['total_fails']} zsh-env fails / "
            f"{gate['window_days']}d; doctor: {', '.join(gate['cross_harness_issues'][:3])}"
        ),
        "action": gate["fix_hint"],
        "evidence": json.dumps(gate["shell_env_clusters"][:5]),
    }
    cand_path.write_text(json.dumps(row) + "\n")
    return gate_path


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Gate cross-harness shell-env failures into the loop.")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--failures-json", type=Path, help="reuse existing failures.json")
    ap.add_argument("--artifact-dir", type=Path, help="write shell-env-gate.json + candidate here")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    failures = None
    if args.failures_json and args.failures_json.is_file():
        failures = json.loads(args.failures_json.read_text() or "[]")

    gate = assess(days=args.days, failures=failures)
    if args.artifact_dir:
        stage_candidate(gate, args.artifact_dir)

    if args.json:
        print(json.dumps(gate, indent=2))
    else:
        status = "PROMOTE" if gate["promote_actionable"] else "ok"
        print(
            f"{status}: zsh-env fails={gate['total_fails']}/{args.days}d "
            f"cross_harness={'healthy' if gate['cross_harness_healthy'] else 'BROKEN'}"
        )
        if gate["cross_harness_issues"]:
            for issue in gate["cross_harness_issues"]:
                print(f"  - {issue}")
    return 1 if gate["promote_actionable"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
