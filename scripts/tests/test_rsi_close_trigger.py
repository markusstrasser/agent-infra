#!/usr/bin/env python3
"""Pins the Tier-1 close trigger: REAL empirical issues fire, correction volume does NOT.

Regression guard for the false-positive class retired 2026-06-18 (improvement-log): the old
`len(corrects) >= 3` floor fired the close on every iterative-but-recovered session.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from goal_state import tier1_eligible  # noqa: E402
from reflect_capture import real_issue_signal  # noqa: E402


class TestRealIssueSignal(unittest.TestCase):
    def test_operator_flag_fires(self):
        ok, kinds = real_issue_signal([{"subtype": "f_tag", "strength": "strong"}])
        self.assertTrue(ok)
        self.assertIn("operator_flag", kinds)

    def test_strong_correction_fires(self):
        ok, kinds = real_issue_signal([{"subtype": "negation", "strength": "strong"}])
        self.assertTrue(ok)
        self.assertIn("strong_correction", kinds)

    def test_user_rescued_failure_fires(self):
        ok, kinds = real_issue_signal([{"subtype": "fail_then_user", "strength": "medium"}])
        self.assertTrue(ok)
        self.assertIn("user_rescued_failure", kinds)

    def test_correction_volume_does_not_fire(self):
        # The false-positive class: many weak corrections, none real → NO trigger (was: len>=3).
        rows = [{"subtype": "retry_run", "strength": "medium"}] * 5 + \
               [{"subtype": "negation", "strength": "medium"}] * 4
        ok, kinds = real_issue_signal(rows)
        self.assertFalse(ok)
        self.assertEqual(kinds, [])

    def test_empty(self):
        self.assertEqual(real_issue_signal([]), (False, []))


class TestTier1Gate(unittest.TestCase):
    def test_real_issue_eligible(self):
        ok, reason = tier1_eligible({"status": "unknown"}, real_issue=True)
        self.assertTrue(ok)
        self.assertEqual(reason, "real_issue_signal")

    def test_goal_achieved_still_fires_without_issue(self):
        # Fabrication defense: a claimed achievement is verify-worthy even with no correction.
        ok, reason = tier1_eligible({"status": "achieved"}, real_issue=False)
        self.assertTrue(ok)
        self.assertEqual(reason, "goal_achieved")

    def test_explicit_close_fires(self):
        ok, reason = tier1_eligible({"source": "explicit_rsi_close"}, real_issue=False)
        self.assertTrue(ok)
        self.assertEqual(reason, "explicit_rsi_close")

    def test_recovered_session_not_eligible(self):
        # unknown goal + no real issue → the close no longer fires (was the noise source).
        self.assertFalse(tier1_eligible({"status": "unknown"}, real_issue=False)[0])


if __name__ == "__main__":
    unittest.main()
