from __future__ import annotations

import importlib.util
import os
from datetime import datetime, timedelta, timezone
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "agent_maintainability.py"


def load_module():
    spec = importlib.util.spec_from_file_location("agent_maintainability", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


class AgentMaintainabilityTest(unittest.TestCase):
    def test_metrics_use_session_id_for_conservative_agent_cohort(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            git(repo, "init")
            git(repo, "config", "user.name", "Test User")
            git(repo, "config", "user.email", "test@example.com")

            file_path = repo / "note.txt"
            file_path.write_text("base\n", encoding="utf-8")
            git(repo, "add", "note.txt")
            git(
                repo,
                "commit",
                "-m",
                "seed",
                env=_commit_env(_days_ago(45)),
            )

            file_path.write_text("base\nagent line\n", encoding="utf-8")
            git(repo, "add", "note.txt")
            git(
                repo,
                "commit",
                "-m",
                "agent change",
                "-m",
                "Session-ID: abc123",
                env=_commit_env(_days_ago(40)),
            )
            agent_hash = (
                subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            )

            file_path.write_text("base\nagent line\nfix line\n", encoding="utf-8")
            git(repo, "add", "note.txt")
            git(
                repo,
                "commit",
                "-m",
                "fix followup",
                env=_commit_env(_days_ago(38)),
            )

            file_path.write_text("base\n", encoding="utf-8")
            git(repo, "add", "note.txt")
            git(
                repo,
                "commit",
                "-m",
                f"Revert \"agent change\"",
                "-m",
                f"This reverts commit {agent_hash}.",
                env=_commit_env(_days_ago(27)),
            )

            report = module.build_report([("repo", repo)], days=120, windows=[7, 30])
            rows = report["repos"][0]["summary"]
            row_7 = next(row for row in rows if row["cohort"] == "agent_high" and row["window_days"] == 7)
            row_30 = next(row for row in rows if row["cohort"] == "agent_high" and row["window_days"] == 30)

            self.assertEqual(row_7["eligible_commits"], 1)
            self.assertEqual(row_7["followup_fix_rate"], 1.0)
            self.assertEqual(row_30["revert_rate"], 1.0)


def _days_ago(days: int) -> str:
    """Commit dates are derived from now(): hardcoded date literals aged out of
    the days=120 lookback and silently flipped this test red (found 2026-07-06).
    The agent commit sits at -40d (>=30d old, inside the lookback); followup +2d,
    revert +13d preserve the original gaps."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _commit_env(ts: str) -> dict[str, str]:
    env = dict(os.environ)
    env["GIT_AUTHOR_DATE"] = ts
    env["GIT_COMMITTER_DATE"] = ts
    return env


if __name__ == "__main__":
    unittest.main()
