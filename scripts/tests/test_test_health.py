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
