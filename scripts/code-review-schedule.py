#!/usr/bin/env python3
"""Submit code-review-sweep pipeline with rotating project/focus.

Called by cron/launchd daily. Rotates through projects and focus areas
so each project gets reviewed with a different lens each day.

Usage:
  code-review-schedule.py          # submit today's review
  code-review-schedule.py --dry-run  # show what would be submitted
  code-review-schedule.py --all    # submit all projects (weekend catch-up)
"""

import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECTS = ["intel", "genomics", "agent-infra", "phenome", "skills"]
FOCUSES = ["refactoring", "dead-code", "optimization", "patterns", "security"]

# Each day picks a (project, focus) pair. 5 projects × 5 focuses = 25 day cycle.
# Day 0: intel/refactoring, Day 1: genomics/dead-code, etc.

def todays_assignment() -> tuple[str, str]:
    """Deterministic rotation based on day of year."""
    day = date.today().timetuple().tm_yday
    project = PROJECTS[day % len(PROJECTS)]
    focus = FOCUSES[(day // len(PROJECTS)) % len(FOCUSES)]
    return project, focus


def submit(project: str, focus: str, dry_run: bool = False):
    cmd = [
        "uv", "run", "python3", "scripts/orchestrator.py",
        "submit", "code-review-sweep",
        "--vars", f"project={project}", f"focus={focus}", f"date={date.today()}",
    ]
    if dry_run:
        print(f"  Would submit: project={project} focus={focus}")
        print(f"  Command: {' '.join(cmd)}")
    else:
        print(f"  Submitting: project={project} focus={focus}")
        subprocess.run(cmd, cwd=Path(__file__).parent.parent)


def main():
    dry_run = "--dry-run" in sys.argv
    run_all = "--all" in sys.argv

    if run_all:
        focus = FOCUSES[date.today().timetuple().tm_yday % len(FOCUSES)]
        print(f"# All projects, focus={focus}")
        for project in PROJECTS:
            submit(project, focus, dry_run)
    else:
        project, focus = todays_assignment()
        print(f"# Today's code review: {project}/{focus}")
        submit(project, focus, dry_run)


if __name__ == "__main__":
    main()
