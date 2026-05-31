"""Golden regression tests for the deterministic session detectors.

Precision-first (the detectors are high-precision/low-recall by design). The
load-bearing test is `test_tail_compression_without_high_util_is_not_pressure`:
the mandatory high-utilization gate must prevent a benign long-then-short
session from being mislabeled context-pressure.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import session_detectors as sd  # noqa: E402

OPUS_1M = "claude-opus-4-8[1m]"  # → 1_000_000 ctx


def _texts(long_n, short_n, *, wrapup=False):
    """long_n long turns then short_n short turns (a declining session)."""
    texts = ["analysis " * 200 for _ in range(long_n)]  # ~1800 chars
    tail = ["ok done" for _ in range(short_n)]
    if wrapup and tail:
        tail[-1] = "I've covered the key points; the remaining items are similar."
    return texts + tail


class ContextPressure(unittest.TestCase):
    def test_high_util_plus_decline_plus_wrapup_flags(self):
        texts = _texts(5, 4, wrapup=True)
        occ = [100_000, 300_000, 600_000, 800_000, 900_000, 920_000, 930_000, 940_000, 950_000]
        r = sd.detect_context_pressure(texts, occ, OPUS_1M)
        self.assertGreater(r["peak_context_utilization"], 0.85)
        self.assertTrue(r["tail_compression_flag"])
        self.assertTrue(r["context_pressure_flag"])

    def test_tail_compression_without_high_util_is_not_pressure(self):
        # Same declining shape, but LOW occupancy → must NOT claim pressure.
        texts = _texts(5, 4, wrapup=True)
        occ = [50_000, 60_000, 70_000, 80_000, 90_000, 95_000, 96_000, 97_000, 98_000]
        r = sd.detect_context_pressure(texts, occ, OPUS_1M)
        self.assertLess(r["peak_context_utilization"], 0.85)
        self.assertTrue(r["tail_compression_flag"])      # tail compression is real
        self.assertFalse(r["context_pressure_flag"])     # but NOT context pressure

    def test_clean_uniform_session_no_flags(self):
        texts = ["a steady analysis turn " * 30 for _ in range(8)]  # uniform
        occ = [200_000] * 8
        r = sd.detect_context_pressure(texts, occ, OPUS_1M)
        self.assertFalse(r["tail_compression_flag"])
        self.assertFalse(r["context_pressure_flag"])

    def test_unknown_model_reports_missing_prereq(self):
        texts = _texts(5, 4)
        r = sd.detect_context_pressure(texts, [900_000] * 9, "some-future-model-x")
        self.assertIsNone(r["peak_context_utilization"])
        self.assertIn("unknown_model_ctx_limit", r["missing_prerequisites"])
        self.assertFalse(r["context_pressure_flag"])

    def test_occupancy_above_base_tier_escalates_not_overflows(self):
        # model string "claude-opus-4-8" resolves to 200k, but observed
        # occupancy 489k proves the [1m] tier is in use → util must be <=1.0.
        texts = _texts(5, 4)
        occ = [200_000, 300_000, 489_000]
        r = sd.detect_context_pressure(texts, occ, "claude-opus-4-8")
        self.assertIsNotNone(r["peak_context_utilization"])
        self.assertLessEqual(r["peak_context_utilization"], 1.0)
        self.assertAlmostEqual(r["peak_context_utilization"], 0.489, places=2)

    def test_too_few_turns_reports_missing_prereq(self):
        r = sd.detect_context_pressure(["a", "b", "c"], [900_000], OPUS_1M)
        self.assertIn("too_few_turns", r["missing_prerequisites"])
        self.assertFalse(r["context_pressure_flag"])


class PrematureCompletion(unittest.TestCase):
    def test_completion_claim_plus_todo_flags(self):
        r = sd.detect_premature_completion(
            "The implementation is complete and working. TODO: fix the parser edge case."
        )
        self.assertTrue(r["completion_claimed"])
        self.assertTrue(r["premature_completion_flag"])
        self.assertIn("incomplete_marker", r["completion_evidence"])

    def test_completion_plus_blocker_flags(self):
        r = sd.detect_premature_completion(
            "Task is done. I opened a ticket for the remaining infra access."
        )
        self.assertTrue(r["premature_completion_flag"])
        self.assertIn("blocker", r["completion_evidence"])

    def test_done_plus_next_steps_is_benign(self):
        # planned_work alone must NOT flag (critique: "done + next steps" benign).
        r = sd.detect_premature_completion(
            "Done! Next steps: I'll add more tests in a future iteration."
        )
        self.assertTrue(r["completion_claimed"])
        self.assertFalse(r["premature_completion_flag"])
        self.assertIn("planned_work", r["completion_evidence"])

    def test_honest_partial_suppresses(self):
        r = sd.detect_premature_completion(
            "The core task is complete. I completed 3 of 5 items; still working on the rest."
        )
        self.assertFalse(r["premature_completion_flag"])

    def test_no_completion_claim_no_flag(self):
        r = sd.detect_premature_completion(
            "Here is some analysis of the tradeoffs. There are several options to consider."
        )
        self.assertFalse(r["completion_claimed"])
        self.assertFalse(r["premature_completion_flag"])

    def test_false_success_on_explicit_failure(self):
        r = sd.detect_premature_completion(
            "The migration is complete. Note: the agent failed to finish the rollback step."
        )
        self.assertTrue(r["false_success_flag"])
        self.assertTrue(r["premature_completion_flag"])


class RateLimitCascade(unittest.TestCase):
    def test_three_hits_cascades(self):
        results = [
            {"stderr": "HTTP 429 Too Many Requests"},
            {"content": "rate limit exceeded, retry later"},
            {"stdout": "Error: 429"},
            {"content": "normal output"},
        ]
        r = sd.count_rate_limit_cascade(results)
        self.assertEqual(r["rate_limit_hit_count"], 3)
        self.assertTrue(r["rate_limit_cascade_flag"])

    def test_two_hits_no_cascade(self):
        results = [{"stderr": "429"}, {"content": "rate limit"}, {"content": "fine"}]
        r = sd.count_rate_limit_cascade(results)
        self.assertEqual(r["rate_limit_hit_count"], 2)
        self.assertFalse(r["rate_limit_cascade_flag"])


if __name__ == "__main__":
    unittest.main()
