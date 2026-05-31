"""Tests for agent-infra harness infrastructure — trace index parsing, correction detection.

Focus: contract tests for pure functions and regex parsers. The composite
quality_score tests were retired 2026-06-01 with the scorer itself (never
populated; see migration 003).
"""


# ---------------------------------------------------------------------------
# Trace index regex tests
# ---------------------------------------------------------------------------

class TestTraceIndexParsing:
    """Test that improvement-log entry regex captures expected patterns."""

    def setup_method(self):
        import re
        self.pattern = re.compile(
            r"### \[(\d{4}-\d{2}-\d{2})\] (\w[\w\s]*?):\s*(.+?)$\s*"
            r"- \*\*Session:\*\*\s*(\S+)\s+(\w+)",
            re.MULTILINE,
        )

    def test_standard_entry(self):
        """Parse a standard improvement-log entry."""
        text = """### [2026-04-07] TOKEN WASTE: 13 sequential WebFetch calls
- **Session:** agent-infra abc12345
- **Evidence:** blah blah"""
        m = self.pattern.search(text)
        assert m is not None
        date, category, summary, project, session = m.groups()
        assert date == "2026-04-07"
        assert category == "TOKEN WASTE"
        assert "13 sequential" in summary
        assert project == "agent-infra"
        assert session == "abc12345"

    def test_multi_word_category(self):
        """Categories with spaces should parse correctly."""
        text = """### [2026-04-01] MISSING PUSHBACK: Agent complied without questioning
- **Session:** genomics def45678"""
        m = self.pattern.search(text)
        assert m is not None
        assert m.group(2) == "MISSING PUSHBACK"

    def test_single_word_category(self):
        """Single-word categories like RECURRENCE should work."""
        text = """### [2026-04-05] RECURRENCE: Token waste pattern repeats
- **Session:** phenome aaa11111"""
        m = self.pattern.search(text)
        assert m is not None
        assert m.group(2) == "RECURRENCE"

    def test_no_match_on_malformed(self):
        """Don't match entries without Session line."""
        text = """### [2026-04-07] TOKEN WASTE: something
- **Evidence:** no session line here"""
        m = self.pattern.search(text)
        assert m is None


# ---------------------------------------------------------------------------
# extract_transcript --full correction detection
# ---------------------------------------------------------------------------

class TestCorrectionDetection:
    """Test the likely_correction tagging in --full mode."""

    def test_short_user_message_after_assistant_is_correction(self):
        """A short user message following assistant tool use is flagged."""
        # Simulate the logic from extract_transcript.py
        # User message < 500 chars, not system-reminder, after assistant = correction
        msg = "no, use the other approach"
        is_correction = (
            len(msg.strip()) < 500
            and not msg.strip().startswith("<system-reminder>")
        )
        assert is_correction

    def test_system_reminder_not_flagged(self):
        """System reminders should NOT be flagged as corrections."""
        msg = "<system-reminder>hook output here</system-reminder>"
        is_correction = (
            len(msg.strip()) < 500
            and not msg.strip().startswith("<system-reminder>")
        )
        assert not is_correction

    def test_long_message_not_flagged(self):
        """Long messages (new prompts, not corrections) should not be flagged."""
        msg = "x" * 600
        is_correction = len(msg.strip()) < 500
        assert not is_correction
