"""Contract tests for the test-health sentinel's pure logic.

The classifier is the heart: it decides COMPLETED (real verdict) vs
DID-NOT-COMPLETE (the high-signal alarm). A wrong classification here would
either mask a dead suite (the failure this tool exists to catch) or cry wolf.
"""

import test_health as th


class TestClassifyOutcome:
    def test_passed_and_failed_are_completed(self):
        assert th.classify_outcome(0, timed_out=False) == "passed"
        assert th.classify_outcome(1, timed_out=False) == "failed"
        # both are real verdicts
        assert "passed" in th._COMPLETED and "failed" in th._COMPLETED

    def test_collection_and_internal_errors_are_not_completed(self):
        for rc, outcome in [(2, "collection_error"), (3, "internal_error"),
                            (4, "usage_error"), (5, "no_tests")]:
            assert th.classify_outcome(rc, timed_out=False) == outcome
            assert outcome not in th._COMPLETED

    def test_signal_crash_is_crashed(self):
        # 139 = 128 + SIGSEGV(11) — the exact certificates failure that masked
        # 4 clusters of drift for ~6 days; 134 = SIGABRT.
        assert th.classify_outcome(139, timed_out=False) == "crashed"
        assert th.classify_outcome(134, timed_out=False) == "crashed"
        assert th.classify_outcome(-11, timed_out=False) == "crashed"
        assert "crashed" not in th._COMPLETED

    def test_timeout_wins_over_returncode(self):
        assert th.classify_outcome(0, timed_out=True) == "timeout"
        assert "timeout" not in th._COMPLETED


class TestIsRegression:
    def _rec(self, completed, passed=0, failed=0, errors=0, outcome="passed"):
        return {"completed": completed, "outcome": outcome,
                "counts": {"passed": passed, "failed": failed, "errors": errors}}

    def test_no_previous_is_never_regression(self):
        assert th.is_regression(self._rec(True, passed=10), None) == (False, "")

    def test_stopped_completing_is_regression(self):
        cur = self._rec(False, outcome="crashed")
        prev = self._rec(True, passed=10)
        regressed, note = th.is_regression(cur, prev)
        assert regressed and "stopped completing" in note

    def test_more_failures_is_regression(self):
        cur = self._rec(True, passed=120, failed=3)
        prev = self._rec(True, passed=123, failed=0)
        regressed, note = th.is_regression(cur, prev)
        assert regressed and "0→3" in note

    def test_same_failures_not_regression(self):
        # chronic-but-stable failures must NOT alarm every run (report-only)
        cur = self._rec(True, passed=121, failed=13)
        prev = self._rec(True, passed=121, failed=13)
        assert th.is_regression(cur, prev) == (False, "")

    def test_fewer_failures_is_improvement_not_regression(self):
        cur = self._rec(True, passed=134, failed=0)
        prev = self._rec(True, passed=121, failed=13)
        assert th.is_regression(cur, prev)[0] is False

    def test_recovery_after_crash_not_regression(self):
        cur = self._rec(True, passed=100)
        prev = self._rec(False, outcome="crashed")
        assert th.is_regression(cur, prev)[0] is False

    def test_fewer_passes_alone_not_flagged(self):
        # tests can be legitimately removed — fewer passes with no new failures
        # is not a regression
        cur = self._rec(True, passed=90, failed=0)
        prev = self._rec(True, passed=120, failed=0)
        assert th.is_regression(cur, prev) == (False, "")


class TestParseCounts:
    def test_typical_summary(self):
        c = th.parse_counts("814 passed, 15 skipped, 2 xfailed in 155.71s (0:02:35)")
        assert c == {"passed": 814, "skipped": 15, "xfailed": 2}

    def test_failures_and_errors(self):
        c = th.parse_counts("5 failed, 809 passed, 11 skipped, 4 errors in 1162s")
        assert c["failed"] == 5 and c["passed"] == 809 and c["errors"] == 4

    def test_error_singular_normalizes_to_errors(self):
        assert th.parse_counts("1 error in 0.5s") == {"errors": 1}

    def test_empty(self):
        assert th.parse_counts("") == {}
