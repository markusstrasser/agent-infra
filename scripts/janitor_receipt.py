#!/usr/bin/env python3
"""Janitor effect-receipts — motors write last_success; doctor alarms on staleness.

v1 (observe plan 2026-08-11): write + last_success>36h alarm only.
v2 (later): flat-N-nights / should-vary classification after real distributions exist.

Receipt path: ~/.cache/reclaim/<motor>.receipt.json
Schema:
  {
    "motor": "worktree_gc",
    "last_success_ts": "ISO-8601 UTC",
    "principal_metric": 3,          # e.g. trees removed, bytes freed, 0 ok if succeeded
    "error_class": null | "str",
    "detail": "optional one-liner"
  }

Usage:
  uv run python3 scripts/janitor_receipt.py write worktree_gc --metric 2
  uv run python3 scripts/janitor_receipt.py write worktree_gc --error crash --detail "..."
  uv run python3 scripts/janitor_receipt.py check --max-age-hours 36
  from janitor_receipt import write_receipt, load_receipt, stale_motors
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RECEIPT_DIR = Path(os.environ.get("JANITOR_RECEIPT_DIR", Path.home() / ".cache" / "reclaim"))
DEFAULT_MOTORS = ("worktree_gc", "uv_cache_prune", "reclaim_rotate", "agentlogs_archive")
DEFAULT_MAX_AGE_HOURS = 36


def receipt_path(motor: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in motor)
    return RECEIPT_DIR / f"{safe}.receipt.json"


def write_receipt(
    motor: str,
    *,
    principal_metric: int | float | None = None,
    error_class: str | None = None,
    detail: str = "",
    success: bool | None = None,
) -> Path:
    """Write/overwrite a motor receipt. success defaults to (error_class is None)."""
    if success is None:
        success = error_class is None
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "motor": motor,
        "last_success_ts": now if success else None,
        "last_attempt_ts": now,
        "principal_metric": principal_metric,
        "error_class": error_class,
        "detail": detail,
        "success": success,
    }
    # Preserve last_success_ts on failed attempt if prior receipt had one
    path = receipt_path(motor)
    if not success and path.is_file():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
            if prev.get("last_success_ts"):
                payload["last_success_ts"] = prev["last_success_ts"]
        except (OSError, json.JSONDecodeError):
            pass
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def load_receipt(motor: str) -> dict | None:
    path = receipt_path(motor)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def stale_motors(
    motors: tuple[str, ...] = DEFAULT_MOTORS,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
) -> list[dict]:
    """Return list of {motor, status, message} for missing/stale/error receipts.

    status: missing | stale | error | ok
    """
    now = datetime.now(timezone.utc)
    max_age = timedelta(hours=max_age_hours)
    out: list[dict] = []
    for motor in motors:
        rec = load_receipt(motor)
        if rec is None:
            out.append(
                {
                    "motor": motor,
                    "status": "missing",
                    "message": f"no receipt at {receipt_path(motor)}",
                }
            )
            continue
        if rec.get("error_class"):
            out.append(
                {
                    "motor": motor,
                    "status": "error",
                    "message": f"error_class={rec['error_class']}: {rec.get('detail') or ''}".strip(),
                    "receipt": rec,
                }
            )
            # still check staleness of last success below
        ts = _parse_ts(rec.get("last_success_ts"))
        if ts is None:
            out.append(
                {
                    "motor": motor,
                    "status": "missing",
                    "message": "receipt has no last_success_ts (never succeeded)",
                    "receipt": rec,
                }
            )
            continue
        age = now - ts
        if age > max_age:
            out.append(
                {
                    "motor": motor,
                    "status": "stale",
                    "message": f"last_success {rec['last_success_ts']} "
                    f"({age.total_seconds()/3600:.1f}h > {max_age_hours}h)",
                    "receipt": rec,
                }
            )
        else:
            out.append(
                {
                    "motor": motor,
                    "status": "ok",
                    "message": f"last_success {rec['last_success_ts']} "
                    f"metric={rec.get('principal_metric')}",
                    "receipt": rec,
                }
            )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="write a motor receipt")
    w.add_argument("motor")
    w.add_argument("--metric", type=float, default=None)
    w.add_argument("--error", default=None, dest="error_class")
    w.add_argument("--detail", default="")
    w.add_argument("--fail", action="store_true", help="mark success=false without error_class")

    c = sub.add_parser("check", help="print status for known motors; exit 1 if any stale/error/missing")
    c.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_HOURS)
    c.add_argument(
        "--motors",
        default=",".join(DEFAULT_MOTORS),
        help="comma-separated motor names",
    )
    c.add_argument(
        "--require-all",
        action="store_true",
        help="missing receipt is fail (default: missing=warn for motors never wired)",
    )

    args = ap.parse_args(argv)
    if args.cmd == "write":
        path = write_receipt(
            args.motor,
            principal_metric=args.metric,
            error_class=args.error_class,
            detail=args.detail,
            success=False if args.fail else None,
        )
        print(f"wrote {path}")
        return 0

    if args.cmd == "check":
        motors = tuple(m.strip() for m in args.motors.split(",") if m.strip())
        rows = stale_motors(motors, max_age_hours=args.max_age_hours)
        bad = 0
        for r in rows:
            st = r["status"]
            mark = {"ok": "✓", "missing": "!", "stale": "✗", "error": "✗"}.get(st, "?")
            print(f"  {mark} {r['motor']}: {r['message']}")
            if st in ("stale", "error"):
                bad += 1
            elif st == "missing" and args.require_all:
                bad += 1
        return 1 if bad else 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
