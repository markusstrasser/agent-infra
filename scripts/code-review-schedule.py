#!/usr/bin/env python3
"""Run code-review scout with rotating project/focus.

Called by cron/launchd or `/loop /code-review`. Rotates through projects and
focus areas so each project gets reviewed with a different lens each day.

Usage:
  code-review-schedule.py          # run today's review
  code-review-schedule.py --dry-run  # show what would run
  code-review-schedule.py --all    # run all projects (weekend catch-up)
"""

import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCOUT = ROOT / "scripts" / "code-review-scout.py"
PROJECTS_ROOT = Path.home() / "Projects"

PROJECTS = ["intel", "genomics", "agent-infra", "phenome", "skills", "hutter"]
FOCUSES = ["refactoring", "dead-code", "optimization", "patterns", "security"]


def todays_assignment() -> tuple[str, str]:
    """Deterministic rotation based on day of year."""
    day = date.today().timetuple().tm_yday
    project = PROJECTS[day % len(PROJECTS)]
    focus = FOCUSES[(day // len(PROJECTS)) % len(FOCUSES)]
    return project, focus


def run_review(project: str, focus: str, dry_run: bool = False):
    project_path = PROJECTS_ROOT / project
    cmd = [
        "uv", "run", "python3", str(SCOUT), str(project_path),
        "--focus", focus,
        "--provider", "cursor",
        "--workers", "2",
    ]
    if dry_run:
        print(f"  Would run: project={project} focus={focus}")
        print(f"  Command: {' '.join(cmd)}")
    else:
        print(f"  Running: project={project} focus={focus}")
        subprocess.run(cmd, cwd=ROOT, check=False)


def main():
    dry_run = "--dry-run" in sys.argv
    run_all = "--all" in sys.argv

    if run_all:
        focus = FOCUSES[date.today().timetuple().tm_yday % len(FOCUSES)]
        print(f"# All projects, focus={focus}")
        for project in PROJECTS:
            run_review(project, focus, dry_run)
    else:
        project, focus = todays_assignment()
        print(f"# Today's code review: {project}/{focus}")
        run_review(project, focus, dry_run)


if __name__ == "__main__":
    main()
