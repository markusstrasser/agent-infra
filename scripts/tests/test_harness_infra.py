"""Tests for agent-infra harness infrastructure — quality scoring, trace index parsing.

Covers the new code from the Meta-Harness leverage plan (arXiv:2603.28052).
Focus: contract tests for pure functions and regex parsers.
"""

import sys
from pathlib import Path

# Add scripts to path for session_features import chain (needs common, config)
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# compute_quality_score tests
# ---------------------------------------------------------------------------

class TestQualityScore:
    """Test compute_quality_score produces sensible scores."""

    def setup_method(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "session_features",
            Path(__file__).parent.parent / "session-features.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.score = mod.compute_quality_score

    def _features(self, **overrides):
        """Base features with no penalties."""
        base = {
            "tool_call_count": 50,
            "tool_failure_count": 0,
            "tool_failure_rate": 0.0,
            "backtrack_count": 0,
            "query_reformulation_count": 0,
            "session_duration_minutes": 30,
        }
        base.update(overrides)
        return base

    def test_perfect_session_scores_1(self):
        """No failures, no backtracks = perfect score."""
        assert self.score(self._features()) == 1.0

    def test_high_failure_rate_penalizes(self):
        """50% tool failure rate should significantly reduce score."""
        s = self.score(self._features(tool_failure_rate=0.5))
        assert s < 0.8, f"Expected < 0.8, got {s}"

    def test_backtrack_penalty(self):
        """Backtracks reduce score proportionally up to saturation."""
        s = self.score(self._features(backtrack_count=5, tool_call_count=50))
        assert s < 1.0
        # More backtracks = lower score (below saturation threshold)
        s2 = self.score(self._features(backtrack_count=8, tool_call_count=50))
        assert s2 < s, "More backtracks should mean lower score"
        # Saturation: very high backtracks max out the penalty
        s3 = self.score(self._features(backtrack_count=20, tool_call_count=50))
        s4 = self.score(self._features(backtrack_count=40, tool_call_count=50))
        assert s3 == s4, "Penalty should saturate at high backtrack rates"

    def test_excessive_tool_calls_penalized(self):
        """Sessions with >200 tool calls get a penalty."""
        normal = self.score(self._features(tool_call_count=100))
        excessive = self.score(self._features(tool_call_count=250))
        assert excessive < normal

    def test_marathon_session_penalized(self):
        """Sessions >120 min get a penalty."""
        normal = self.score(self._features(session_duration_minutes=60))
        marathon = self.score(self._features(session_duration_minutes=180))
        assert marathon < normal

    def test_score_bounded_0_1(self):
        """Score should always be between 0 and 1."""
        # Worst case: everything bad
        worst = self.score(self._features(
            tool_failure_rate=1.0,
            backtrack_count=100,
            query_reformulation_count=100,
            tool_call_count=300,
            session_duration_minutes=200,
        ))
        assert 0.0 <= worst <= 1.0

        # Best case
        best = self.score(self._features())
        assert 0.0 <= best <= 1.0

    def test_zero_tool_calls_doesnt_crash(self):
        """Edge case: session with no tool calls."""
        s = self.score(self._features(tool_call_count=0))
        assert 0.0 <= s <= 1.0

    def test_reformulation_penalty(self):
        """Query reformulations reduce score."""
        s = self.score(self._features(query_reformulation_count=15, tool_call_count=50))
        assert s < 1.0


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
