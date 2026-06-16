#!/usr/bin/env python3
"""Lint closeout dispatch.json — partition invariants for review closeout.

Usage:
    uv run python3 scripts/lint_closeout_dispatch.py .model-review/dispatch.json
    uv run python3 scripts/lint_closeout_dispatch.py --require-fresh 24 .model-review/dispatch.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from common import con
from common.surface_gates import FailureEnvelope, validate_closeout_dispatch


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate review dispatch.json partition")
    ap.add_argument("dispatch", type=Path, nargs="?", default=Path(".model-review/dispatch.json"))
    ap.add_argument(
        "--require-fresh",
        type=float,
        metavar="HOURS",
        help="fail if dispatch file older than N hours",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    path = args.dispatch.expanduser().resolve()
    if not path.is_file():
        env = FailureEnvelope(
            check="closeout-dispatch",
            reason=f"missing {path}",
            fix="uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py triage --mode close --repo . --packet .model-review/plan-close-context.md",
        )
        print(env.format(), file=sys.stderr)
        return 2

    if args.require_fresh is not None:
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h > args.require_fresh:
            env = FailureEnvelope(
                check="closeout-dispatch",
                reason=f"dispatch stale ({age_h:.1f}h > {args.require_fresh}h)",
                fix=f"uv run python3 ${{CLAUDE_SKILL_DIR}}/scripts/review_gate.py triage --mode close --repo . --packet .model-review/plan-close-context.md",
            )
            print(env.format(), file=sys.stderr)
            return 2

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        env = FailureEnvelope(
            check="closeout-dispatch",
            reason=f"invalid JSON: {exc}",
            fix=f"regenerate via review_gate.py triage",
        )
        print(env.format(), file=sys.stderr)
        return 2

    errors = validate_closeout_dispatch(data)
    if args.json:
        print(json.dumps({"path": str(path), "ok": not errors, "errors": errors}, indent=2))
    elif errors:
        con.fail(path.name)
        for err in errors:
            print(f"  - {err}")
    else:
        con.ok(f"{path.name} partition valid ({data.get('artifact', '?')})")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
