#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from session_automation_telemetry import classify_row


class TestSessionClassify(unittest.TestCase):
    def test_stop_hook(self):
        self.assertEqual(
            classify_row({"first_message": "review an AI coding agent session", "duration_min": 0.3, "is_subagent": 0}),
            "stop_hook",
        )

    def test_cursor_scout(self):
        self.assertEqual(
            classify_row({
                "vendor": "cursor", "duration_min": 0, "is_subagent": 0,
                "first_message": "You are a code reviewer. Be concrete",
            }),
            "cursor_scout",
        )

    def test_operator(self):
        self.assertEqual(
            classify_row({"vendor": "claude", "duration_min": 45, "is_subagent": 0, "first_message": "plan this"}),
            "operator",
        )


if __name__ == "__main__":
    unittest.main()
