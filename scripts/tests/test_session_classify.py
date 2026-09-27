#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from session_automation_telemetry import classify_row, summarize


class TestSessionClassify(unittest.TestCase):
    def test_stop_hook(self):
        self.assertEqual(
            classify_row({"first_message": "review an AI coding agent session", "duration_min": 0.3,
                          "session_role": "dispatch"}),
            "stop_hook",
        )

    def test_cursor_scout(self):
        self.assertEqual(
            classify_row({
                "vendor": "cursor", "duration_min": 0, "session_role": "dispatch",
                "first_message": "You are a code reviewer. Be concrete",
            }),
            "cursor_scout",
        )

    def test_operator(self):
        self.assertEqual(
            classify_row({"vendor": "claude", "duration_min": 45, "session_role": "operator",
                          "first_message": "plan this"}),
            "operator",
        )

    def test_role_outranks_duration_and_text(self):
        # a long launchd tick is still a dispatch; a quick question is still the operator's
        self.assertEqual(classify_row({"duration_min": 30, "session_role": "dispatch",
                                       "first_message": "Watch tick — read loop/WATCH.md"}), "dispatch")
        self.assertEqual(classify_row({"duration_min": 1, "session_role": "operator",
                                       "first_message": "review an AI coding agent"}), "operator")
        self.assertEqual(classify_row({"duration_min": 9, "session_role": None}), "undetermined")
        self.assertEqual(classify_row({"duration_min": 9, "session_role": "subagent"}), "subagent")

    def test_summary_reports_undetermined_outside_the_automation_share(self):
        summary = summarize([
            {"session_role": "operator"},
            {"session_role": "dispatch"},
            {"session_role": "dispatch"},
            {"session_role": None},
        ])
        self.assertEqual((summary["operator"], summary["automation"], summary["undetermined"]), (1, 2, 1))
        self.assertEqual(summary["automation_pct"], 66.7)


if __name__ == "__main__":
    unittest.main()
