#!/usr/bin/env python3
"""Skills index budget — measure vendor-loaded description totals.

Codex budgets skill index to ~8000 chars (developers.openai.com/codex/skills).
Measure the populations that actually load, not ~/Projects/skills source alone.

Usage:
    uv run python3 scripts/skills_budget.py
    uv run python3 scripts/skills_budget.py --project ~/Projects/intel
    uv run python3 scripts/skills_budget.py --check   # exit 1 if over budget
    uv run python3 scripts/skills_budget.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import con
from common.surface_gates import build_skills_budget


def main() -> int:
    ap = argparse.ArgumentParser(description="Skills description index budget")
    ap.add_argument("--project", type=Path, help="repo path for combined codex+repo check")
    ap.add_argument("--check", action="store_true", help="exit 1 when over budget")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    report = build_skills_budget(args.project)
    if args.as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        con.header("Skills index budget")
        for mount in report.mounts:
            # claude mounts gate on the effective (model-facing) index; codex
            # mounts gate on the raw sum (flag-honoring unverified, fa0ce09).
            gating = (
                mount.effective_description_chars
                if mount.label == "claude_global"
                else mount.description_chars
            )
            flag = ""
            if gating > report.codex_budget_chars:
                flag = " OVER"
            elif gating > report.codex_budget_chars * 0.85:
                flag = " warn"
            con.kv(
                mount.label,
                f"{mount.description_chars} raw / "
                f"{mount.effective_description_chars} effective / "
                f"{mount.skill_count} skills{flag}",
            )
        if report.violations:
            for v in report.violations:
                con.fail(v)
        else:
            con.ok(f"within {report.codex_budget_chars} char ceiling")

    if args.check and report.over_budget:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
