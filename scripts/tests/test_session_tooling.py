#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clean_vtt import clean_vtt
from session_automation_telemetry import classify_row


class TestCleanVtt(unittest.TestCase):
    def test_dedupes_rolling_captions(self):
        vtt = """WEBVTT

00:00:01.000 --> 00:00:02.000
Hello world

00:00:02.000 --> 00:00:03.000
Hello world this is

00:00:03.000 --> 00:00:04.000
Hello world this is a test
"""
        out = clean_vtt(vtt)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 3)
        self.assertNotIn("-->", out)


class TestSessionTelemetry(unittest.TestCase):
    def test_session_classify_stop_hook(self):
        self.assertEqual(
            classify_row({"first_message": "review an AI coding agent", "duration_min": 0.3, "is_subagent": 0}),
            "stop_hook",
        )


if __name__ == "__main__":
    unittest.main()
