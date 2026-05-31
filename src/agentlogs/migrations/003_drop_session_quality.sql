-- agentlogs migration 003 — drop the parked session_quality scorer.
--
-- The composite quality_score (0-1 from tool failures / backtracks /
-- reformulations) was built 2026-04-07 (agent-infra@ce4f331) alongside a
-- v_harness_correlation view, to score sessions and correlate quality against
-- harness versions. It was deliberately parked pending a calibration backfill
-- (see session-features.py compute_quality_score docstring) and never ran:
-- 0 / 3850 sessions scored as of 2026-06-01.
--
-- The harness-correlation half is already retired — migration 002 dropped the
-- harness_hash column and v_harness_correlation no longer exists. Build-then-undo
-- (the failure mode the scorer was meant to surface) is covered report-only by
-- scripts/buildthenundo.py (wired into gov.py) and the v_build_then_retire view.
-- We accept that report-only detection as sufficient and stop carrying the
-- never-populated scorer table.
--
-- Decision: retire (option #2), agent-infra session 2026-06-01. The scored gate
-- can be reintroduced by reverting this migration if a measured gap appears that
-- report-only detection misses.

DROP TABLE IF EXISTS session_quality;

PRAGMA user_version = 3;
