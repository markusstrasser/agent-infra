"""Tests for cross-harness shell env loop gate."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import shell_env_loop_gate as gate  # noqa: E402


class TestShellEnvLoopGate(unittest.TestCase):
    def test_assess_promote_when_unhealthy_and_volume(self):
        failures = [
            {"cluster": "zsh-env:nomatch", "fails": 60, "distinct_days": 5, "last_seen": "2026-06-28T10:00"},
        ]
        orig = gate._cross_harness_status
        try:
            gate._cross_harness_status = lambda: (False, ["missing cursor hooks"])
            out = gate.assess(days=30, failures=failures)
            self.assertTrue(out["promote_actionable"])
            self.assertEqual(out["total_fails"], 60)
        finally:
            gate._cross_harness_status = orig

    def test_assess_no_promote_when_healthy(self):
        failures = [
            {"cluster": "zsh-env:nomatch", "fails": 60, "distinct_days": 5, "last_seen": "2026-06-28T10:00"},
        ]
        orig = gate._cross_harness_status
        try:
            gate._cross_harness_status = lambda: (True, [])
            out = gate.assess(days=30, failures=failures)
            self.assertFalse(out["promote_actionable"])
        finally:
            gate._cross_harness_status = orig

    def test_cross_harness_status_accepts_pass(self):
        """doctor Check.ok() sets status='pass', not 'ok'."""
        import doctor as doc

        orig_checks = doc.check_cross_harness_shell_env
        try:
            doc.check_cross_harness_shell_env = lambda: [
                doc.Check("t", "global").ok("wired"),
            ]
            healthy, issues = gate._cross_harness_status()
            self.assertTrue(healthy)
            self.assertEqual(issues, [])
        finally:
            doc.check_cross_harness_shell_env = orig_checks

    def test_stage_candidate_writes_artifacts(self):
        g = {
            "promote_actionable": True,
            "assessed_at": "2026-06-28T12:00:00Z",
            "total_fails": 55,
            "window_days": 30,
            "cross_harness_issues": ["missing hooks"],
            "shell_env_clusters": [{"cluster": "zsh-env:nomatch", "fails": 55}],
            "fix_hint": "fix it",
        }
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = gate.stage_candidate(g, Path(td))
            self.assertTrue(path and path.is_file())
            cand = json.loads((Path(td) / "shell-env-candidate.jsonl").read_text())
            self.assertTrue(cand["checkable"])


if __name__ == "__main__":
    unittest.main()
