#!/usr/bin/env python3
"""Operator status briefing — one-page repo + RSI glance.

llm: none

Usage:
  operator_status_briefing.py --repo ~/Projects/genomics
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from tool_contract import LlmClass, print_llm_header

SCRIPTS = Path(__file__).resolve().parent
REPO_INFRA = SCRIPTS.parent


def run_py(script: str, *args: str, cwd: Path | None = None) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=cwd or REPO_INFRA,
        capture_output=True, text=True,
    )
    return r.returncode, (r.stdout + r.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--project", help="session telemetry filter (default: repo name)")
    args = ap.parse_args()

    print_llm_header(LlmClass.NONE)
    repo = args.repo.resolve()
    project = args.project or repo.name
    day = date.today().isoformat()

    sections: list[str] = [f"# Operator status briefing — {day}", f"**Repo:** `{repo}`", ""]

    code, baseline = run_py("baseline_since_last_green.py", "--repo", str(repo), "--suggest-only")
    sections.extend(["## Baseline since last green", "", baseline.strip(), ""])

    code, commit = run_py(
        "commit_slice_planning.py", "--repo", str(repo), "--status-only", "--include-untracked",
    )
    sections.extend(["## Commit slice status", "", commit.strip(), ""])

    audit_dir = repo / "docs" / "audit"
    if audit_dir.is_dir():
        code, triage = run_py(
            "audit_findings_consolidation.py", str(audit_dir),
            "--repo", str(repo), "--date", day, "--kind", "backlog",
        )
        sections.extend(["## Findings consolidation (backlog)", "", triage.strip()[:1500], ""])

    code, telem = run_py(
        "session_automation_telemetry.py", "--days", "7", "--project", project,
    )
    sections.extend(["## Session telemetry (7d)", "", telem.strip(), ""])

    code, funnel = run_py("loop_funnel.py", cwd=REPO_INFRA)
    sections.extend(["## RSI loop funnel", "", funnel.strip(), ""])

    out = repo / "artifacts" / "operator-status-briefing" / f"{day}-briefing.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(sections) + "\n")
    print(out.read_text())
    print(f"\nwritten: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
