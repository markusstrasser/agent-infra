"""Regression test for the automation-write attribution fix in the global Stop
hook (skills/hooks/stop-uncommitted-warn.sh).

Before the fix, files written by local automation (launchd jobs, fm.py, digest
generators) — which leave no per-session Edit/Write ledger — fell through to
"unattributable → most likely YOURS" on whatever interactive session was ending
(2026-06-20: agent-failure-modes.md + a sensor digest mis-flagged). The fix reads
a recency window of ~/.claude/automation-write-ledger.jsonl and excludes those
paths. This is the first test for this hook; it locks the differential:
  - a NEW untracked file is surfaced in the hook output (control), but
  - the SAME file, registered in the automation ledger, is EXCLUDED (treatment).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HOOK = Path.home() / "Projects/skills/hooks/stop-uncommitted-warn.sh"
LEDGER = Path.home() / ".claude/automation-write-ledger.jsonl"


def _mk_repo(tmp_path: Path) -> Path:
    d = tmp_path
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=d, check=True)
    (d / "base.txt").write_text("base\n")
    subprocess.run(["git", "add", "base.txt"], cwd=d, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=d, check=True)
    (d / "auto_file.md").write_text("NEW\n")  # untracked automation-style output
    return d


def _run_hook(repo: Path, sid: str) -> str:
    payload = json.dumps({"cwd": str(repo), "session_id": sid, "stop_hook_active": False})
    r = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True, timeout=30)
    return (r.stdout or "") + (r.stderr or "")


def test_unregistered_file_is_surfaced(tmp_path):
    if not HOOK.exists():
        import pytest
        pytest.skip("global stop hook not present")
    out = _run_hook(_mk_repo(tmp_path), f"e2e-ctrl-{int(time.time())}")
    assert "auto_file.md" in out, "control: an unregistered new file must be surfaced"


def test_automation_registered_file_is_excluded(tmp_path):
    if not HOOK.exists():
        import pytest
        pytest.skip("global stop hook not present")
    repo = _mk_repo(tmp_path)
    sys.path.insert(0, str(Path.home() / "Projects/agent-infra/scripts"))
    from common.automation_ledger import register
    register(repo / "auto_file.md", "test")  # recent → inside the hook window
    out = _run_hook(repo, f"e2e-treat-{int(time.time())}")
    assert "auto_file.md" not in out, "treatment: a registered automation file must be excluded"
