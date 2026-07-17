#!/usr/bin/env python3
"""infra_usage_check.py — detect built-but-unadopted gated infra (adoption ratchet).

Walks a declared registry of governance/gated surfaces and reports zero-caller /
zero-artifact age. Read-only. Complements improvement_log_accretion (log shape)
with *usage* evidence so we stop rediscovering dead ceremony (F3 / session_quality class).

Default is report-only (exit 0). Pass --strict to exit 1 on unadopted once a real
consumer (hook / maintain-tick / CI) is wired. Source-text `rg` is a labeled proxy —
not agentlogs execution evidence (Opus 2026-07-12 leftovers critique).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


@dataclass
class InfraSurface:
    id: str
    kind: str  # artifact_dir | script | recipe
    path: str
    description: str
    # For artifact_dir: ignore these filenames when counting "real" usage
    ignore_names: tuple[str, ...] = ()
    # Min age days with zero real usage → UNADOPTED
    stale_days: int = 14
    # Explicit park: still report, but do not fail --strict (F3-class)
    parked: bool = False
    parked_reason: str = ""
    parked_at: str = ""  # ISO date YYYY-MM-DD


# Declared gated / ceremony surfaces. Add rows when shipping a new gate.
REGISTRY: list[InfraSurface] = [
    InfraSurface(
        id="f3-mechanism-records",
        kind="artifact_dir",
        path="mechanism-records",
        description="F3 predict-then-falsify mechanism-records/ (exclude example template)",
        ignore_names=("README.md", "example-tool-error-rate.json"),
        stale_days=14,
        parked=True,
        parked_reason="F3 predict-then-falsify parked — no live consumers; keep visible",
        parked_at="2026-07-04",
    ),
    InfraSurface(
        id="mechanism-record-script",
        kind="script",
        path="scripts/mechanism_record.py",
        description="F3 recorder script — callers outside tests?",
        parked=True,
        parked_reason="paired with f3-mechanism-records park",
        parked_at="2026-07-04",
    ),
    InfraSurface(
        id="improvement-log-accretion",
        kind="script",
        path="scripts/improvement_log_accretion.py",
        description="L1 accretion report (just gov-accretion-check)",
    ),
    InfraSurface(
        id="infra-usage-check-recipe",
        kind="recipe",
        path="infra-usage-check",
        description="just infra-usage-check — this ratchet (self-register)",
        stale_days=21,
    ),
    InfraSurface(
        id="gov-accretion-check-recipe",
        kind="recipe",
        path="gov-accretion-check",
        description="just gov-accretion-check",
        stale_days=21,
    ),
    InfraSurface(
        id="tool-trim-audit-recipe",
        kind="recipe",
        path="tool-trim-audit",
        description="just tool-trim-audit (exploratory screen, not delete list)",
        stale_days=21,
    ),
]


def _git_last_touch(rel: Path) -> datetime | None:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO), "log", "-1", "--format=%cI", "--", str(rel)],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if not out:
            return None
        return datetime.fromisoformat(out.replace("Z", "+00:00"))
    except (subprocess.CalledProcessError, ValueError, OSError):
        return None


def _count_script_callers(rel: Path) -> int:
    """Labeled proxy: non-test source mentions via rg (NOT agentlogs execution)."""
    stem = rel.stem
    try:
        out = subprocess.check_output(
            [
                "rg", "-l",
                rf"{stem}|{rel.as_posix()}",
                str(REPO / "scripts"),
                str(REPO / "justfile"),
                str(REPO / ".claude"),
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return 0
    files = [Path(p) for p in out.splitlines() if p.strip()]
    callers = [
        f for f in files
        if f.resolve() != (REPO / rel).resolve()
        and "test_" not in f.name
        and "/tests/" not in str(f)
        and f.name != "infra_usage_check.py"
    ]
    return len(callers)


def _recipe_declared(name: str) -> bool:
    just = REPO / "justfile"
    if not just.is_file():
        return False
    # Match recipe header line: optional attrs then `name` or `name args:`
    pat = re.compile(rf"^{re.escape(name)}(\s|:|$|\*)", re.M)
    return bool(pat.search(just.read_text(encoding="utf-8", errors="replace")))


def check_surface(s: InfraSurface, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    rel = Path(s.path)
    abs_path = REPO / rel
    result = {
        "id": s.id,
        "kind": s.kind,
        "path": s.path,
        "description": s.description,
        "status": "ok",
        "detail": "",
        "usage_count": 0,
        "age_days": None,
        "parked": s.parked,
        "parked_reason": s.parked_reason or None,
        "parked_at": s.parked_at or None,
        "adoption_signal": "rg_proxy",
    }
    if s.kind == "artifact_dir":
        if not abs_path.is_dir():
            result["status"] = "missing"
            result["detail"] = "directory absent"
            return _maybe_park(result, s, now)
        real = [
            p for p in abs_path.iterdir()
            if p.is_file() and p.name not in s.ignore_names and not p.name.startswith(".")
        ]
        result["usage_count"] = len(real)
        result["adoption_signal"] = "artifact_files"
        if real:
            result["status"] = "adopted"
            result["detail"] = f"{len(real)} real artifact(s)"
            return result
        touched = _git_last_touch(rel)
        if touched:
            age = (now - touched).days
            result["age_days"] = age
            if age >= s.stale_days:
                result["status"] = "unadopted"
                result["detail"] = f"0 real artifacts; path last touched {age}d ago"
            else:
                result["status"] = "young"
                result["detail"] = f"0 real artifacts; only {age}d old (<{s.stale_days}d)"
        else:
            result["status"] = "unadopted"
            result["detail"] = "0 real artifacts; no git history"
        return _maybe_park(result, s, now)

    if s.kind == "script":
        if not abs_path.is_file():
            result["status"] = "missing"
            result["detail"] = "script absent"
            return _maybe_park(result, s, now)
        n = _count_script_callers(rel)
        result["usage_count"] = n
        touched = _git_last_touch(rel)
        age = (now - touched).days if touched else None
        result["age_days"] = age
        if n > 0:
            result["status"] = "adopted"
            result["detail"] = f"{n} non-test caller(s) [rg_proxy]"
        elif age is not None and age >= s.stale_days:
            result["status"] = "unadopted"
            result["detail"] = f"0 callers [rg_proxy]; last touched {age}d ago"
        else:
            result["status"] = "young" if age is not None else "unadopted"
            result["detail"] = f"0 callers [rg_proxy]; age={age}d"
        return _maybe_park(result, s, now)

    if s.kind == "recipe":
        result["adoption_signal"] = "justfile_declare"
        declared = _recipe_declared(s.path)
        result["usage_count"] = 1 if declared else 0
        # Recipe "touch" ≈ justfile mtime via git on justfile
        touched = _git_last_touch(Path("justfile"))
        age = (now - touched).days if touched else None
        result["age_days"] = age
        if declared:
            # Declared ≠ used. Mark young until agentlogs-backed adoption exists.
            result["status"] = "young"
            result["detail"] = "declared in justfile (usage unmeasured — no agentlogs signal yet)"
        elif age is not None and age >= s.stale_days:
            result["status"] = "unadopted"
            result["detail"] = f"recipe not in justfile; justfile age={age}d"
        else:
            result["status"] = "missing"
            result["detail"] = "recipe not in justfile"
        return _maybe_park(result, s, now)

    result["status"] = "unknown_kind"
    return result


def _maybe_park(result: dict, s: InfraSurface, now: datetime) -> dict:
    if s.parked and result["status"] in ("unadopted", "missing", "young"):
        result["status"] = "parked"
        result["detail"] = f"parked — {result['detail']}"
        if s.parked_at:
            try:
                parked_days = (now.date() - date.fromisoformat(s.parked_at)).days
                result["parked_age_days"] = parked_days
                if parked_days >= 30:
                    result["detail"] += f" (parked {parked_days}d — revisit)"
            except ValueError:
                pass
    return result


def run() -> dict:
    now = datetime.now(timezone.utc)
    rows = [check_surface(s, now=now) for s in REGISTRY]
    unadopted = [r for r in rows if r["status"] == "unadopted"]
    parked_stale = [
        r for r in rows
        if r["status"] == "parked" and (r.get("parked_age_days") or 0) >= 30
    ]
    return {
        "generated_at": now.isoformat(),
        "surfaces": rows,
        "n_unadopted": len(unadopted),
        "unadopted_ids": [r["id"] for r in unadopted],
        "n_parked": sum(1 for r in rows if r["status"] == "parked"),
        "n_parked_stale": len(parked_stale),
        "adoption_signal_note": "rg_proxy / justfile_declare — not agentlogs execution",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 on unadopted (default: report-only exit 0 until a real consumer is wired)",
    )
    args = ap.parse_args()
    report = run()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"# infra-usage-check — {report['n_unadopted']} unadopted / "
            f"{len(report['surfaces'])} surfaces ({report.get('n_parked', 0)} parked; "
            f"{report.get('n_parked_stale', 0)} parked≥30d) "
            f"[{'strict' if args.strict else 'report-only'}]"
        )
        print(f"  note: {report['adoption_signal_note']}")
        for r in report["surfaces"]:
            flag = {
                "unadopted": "✗", "adopted": "✓", "young": "·",
                "missing": "?", "parked": "⏸",
            }.get(r["status"], " ")
            print(f"  {flag} [{r['status']}] {r['id']}: {r['detail']}")
        if report["n_unadopted"]:
            print("\nUNADOPTED → retire, wire a consumer, or park explicitly.")
    if args.strict and report["n_unadopted"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
