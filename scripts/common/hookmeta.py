"""Hook metadata helpers — git-derived deploy dates for hooks.

Extracted from hook-outcome-correlator.py so both the correlator and the
governance tooling (scripts/gov.py) share one implementation rather than
forking the decay logic.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Manual overrides for hook deploy dates. Auto-derivation from git log covers
# the common case (filename contains hook name); overrides are only needed
# when a hook predates its current filename or was renamed.
HOOK_DEPLOY_OVERRIDES: dict[str, str] = {
    "commit-check": "2026-03-01",
    "search-burst": "2026-03-01",
    "subagent-gate": "2026-03-01",
    "source-check": "2026-03-02",
    "spinning": "2026-03-08",
}


def _git_first_commit_dates(repo: Path, subdir: str) -> dict[str, str]:
    """Map basename -> ISO date of first commit adding that file under subdir."""
    if not (repo / ".git").exists():
        return {}
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), "log", "--reverse", "--diff-filter=A",
             "--format=%ai", "--name-only", "--", subdir],
            text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return {}
    date: str | None = None
    result: dict[str, str] = {}
    for line in out.splitlines():
        if not line.strip():
            continue
        if len(line) >= 10 and line[0].isdigit() and line[4] == "-":
            date = line[:10]
        elif date:
            fname = line.rsplit("/", 1)[-1]
            result.setdefault(fname, date)
    return result


def derive_hook_deploy_dates(hook_names: set[str]) -> dict[str, str]:
    """Best-effort: match trigger-log hook names to hook filenames by token substring."""
    file_dates: dict[str, str] = {}
    for repo, sub in [(Path.home() / "Projects" / "skills", "hooks/"),
                      (Path.home() / ".claude", "hooks/")]:
        for fname, date in _git_first_commit_dates(repo, sub).items():
            # earliest wins if a hook file appears in both repos
            if fname not in file_dates or date < file_dates[fname]:
                file_dates[fname] = date

    result: dict[str, str] = {}
    for hook in hook_names:
        if not hook or hook == "?":
            continue
        hook_parts = hook.split("-")
        matches: list[tuple[str, str]] = []
        for fname, date in file_dates.items():
            stem = fname.rsplit(".", 1)[0].replace("_", "-")
            parts = stem.split("-")
            # Contiguous subsequence match: "dup-read" ⊂ "posttool-dup-read"
            for i in range(len(parts) - len(hook_parts) + 1):
                if parts[i:i + len(hook_parts)] == hook_parts:
                    matches.append((date, fname))
                    break
        if matches:
            matches.sort()
            result[hook] = matches[0][0]
    result.update(HOOK_DEPLOY_OVERRIDES)
    return result
