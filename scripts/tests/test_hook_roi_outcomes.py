"""Synthetic-data tests for hook-roi.py's outcome classifier (T2,
guard-forcerate-study / rescue-class-surface-closure-loop — arc-agi
loop/backlog.jsonl rows 906/909).

Deterministic fixture rows (not live log data) so the classification LOGIC
is verified independent of whatever happens to be in ~/.claude/hook-
triggers.jsonl on any given day. Live-data proof is T4, run separately.

hook-roi.py is a hyphenated filename (not a valid `import` target), loaded
via importlib.util — this repo's script-testing pattern for hyphenated
entrypoints (see scripts/tests/test_hooks_smoke.py's sibling-import style
for the same PYTHONPATH-relative convention, adapted here since hook-roi.py
specifically needs the hyphen-safe loader).
"""
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("hook_roi", SCRIPTS / "hook-roi.py")
hook_roi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook_roi)

classify_outcomes = hook_roi.classify_outcomes
EXPOSURE_ACTION = hook_roi.EXPOSURE_ACTION


def row(hook, action, session="s1", ts="2026-07-18T10:00:00Z", cmd_tok=None, cmd_fp=None):
    r = {"hook": hook, "action": action, "session": session, "ts": ts}
    if cmd_tok is not None:
        r["cmd_tok"] = cmd_tok
    if cmd_fp is not None:
        r["cmd_fp"] = cmd_fp
    return r


def test_comply_requires_exposure_row_with_different_fingerprint():
    """A block, then later an exposure-clean row for the SAME guard with a
    DIFFERENT fingerprint, same session, same token -> comply."""
    rows = [
        row("git-stash-guard", "block", ts="10:00:00", cmd_tok="git", cmd_fp="aaaaaaaa"),
        row("git-stash-guard", EXPOSURE_ACTION, ts="10:01:00", cmd_tok="git", cmd_fp="bbbbbbbb"),
    ]
    g = classify_outcomes(rows)["git-stash-guard"]
    assert g["fires"] == 1
    assert g["comply"] == 1
    assert g["repeated_attempt"] == 0
    assert g["abandoned"] == 0
    assert g["unknown"] == 0


def test_repeated_attempt_same_fingerprint_refires():
    """Identical fingerprint firing twice -> repeated-attempt, measurable
    with NO exposure instrumentation at all (unlike comply/abandoned)."""
    rows = [
        row("git-add-all-guard", "block", ts="10:00:00", cmd_tok="git", cmd_fp="cccccccc"),
        row("git-add-all-guard", "block", ts="10:00:05", cmd_tok="git", cmd_fp="cccccccc"),
    ]
    g = classify_outcomes(rows)["git-add-all-guard"]
    assert g["fires"] == 2
    assert g["repeated_attempt"] == 1
    assert g["comply"] == 0


def test_three_identical_fires_yield_two_transitions_not_three():
    rows = [
        row("git-add-all-guard", "block", ts="10:00:00", cmd_tok="git", cmd_fp="dddddddd"),
        row("git-add-all-guard", "block", ts="10:00:05", cmd_tok="git", cmd_fp="dddddddd"),
        row("git-add-all-guard", "block", ts="10:00:10", cmd_tok="git", cmd_fp="dddddddd"),
    ]
    g = classify_outcomes(rows)["git-add-all-guard"]
    assert g["fires"] == 3
    assert g["repeated_attempt"] == 2  # (1->2) and (2->3); the 3rd has no successor


def test_abandoned_requires_guard_to_be_exposure_instrumented():
    """No follow-up at all, but this guard HAS emitted an exposure row
    somewhere in the window (for a different session) -> abandoned, not
    unknown, because comply evidence is structurally possible here."""
    rows = [
        row("multiagent-commit", "block", session="s1", ts="10:00:00", cmd_tok="git", cmd_fp="ee"),
        row("multiagent-commit", EXPOSURE_ACTION, session="s2", ts="09:00:00", cmd_tok="git", cmd_fp="ff"),
    ]
    g = classify_outcomes(rows)["multiagent-commit"]
    assert g["fires"] == 1
    assert g["abandoned"] == 1
    assert g["unknown"] == 0


def test_no_exposure_instrumentation_is_unknown_not_guessed():
    """The core honesty requirement: a guard with ZERO exposure rows
    anywhere in the loaded window cannot distinguish comply from abandoned
    from silence alone -> unknown, never guessed as either."""
    rows = [
        row("cost-awareness", "warn", ts="10:00:00", cmd_tok="llmx", cmd_fp="11111111"),
    ]
    g = classify_outcomes(rows)["cost-awareness"]
    assert g["fires"] == 1
    assert g["unknown"] == 1
    assert g["comply"] == 0
    assert g["abandoned"] == 0


def test_preenrichment_row_without_cmd_tok_is_always_unknown():
    """A row with no cmd_tok (pre-2026-07-18, or not command-shaped) never
    gets adjacency logic applied, even if a later exposure row exists for
    the same guard."""
    rows = [
        row("git-stash-guard", "block", ts="10:00:00"),  # no cmd_tok at all
        row("git-stash-guard", EXPOSURE_ACTION, ts="10:01:00", cmd_tok="git", cmd_fp="22222222"),
    ]
    g = classify_outcomes(rows)["git-stash-guard"]
    assert g["fires"] == 1
    assert g["unknown"] == 1
    assert g["comply"] == 0


def test_different_session_does_not_pair():
    """Same guard, same token, different session -> no pairing; the guard IS
    exposure-instrumented (globally), but this specific fire's session has
    no follow-up of its own -> abandoned, not comply."""
    rows = [
        row("llmx-subscription-flag", "warn", session="s1", ts="10:00:00", cmd_tok="llmx", cmd_fp="33"),
        row("llmx-subscription-flag", EXPOSURE_ACTION, session="s2", ts="10:00:01", cmd_tok="llmx", cmd_fp="44"),
    ]
    g = classify_outcomes(rows)["llmx-subscription-flag"]
    assert g["fires"] == 1
    assert g["comply"] == 0
    assert g["abandoned"] == 1


def test_different_token_does_not_pair():
    """A later row for the SAME guard+session but a DIFFERENT first token
    (e.g. a different command shape entirely) must not be treated as a
    follow-up to this fire."""
    rows = [
        row("cost-guard", "warn", ts="10:00:00", cmd_tok="llmx", cmd_fp="55"),
        row("cost-guard", EXPOSURE_ACTION, ts="10:00:05", cmd_tok="modal", cmd_fp="66"),
    ]
    g = classify_outcomes(rows)["cost-guard"]
    assert g["comply"] == 0
    assert g["abandoned"] == 1  # cost-guard IS instrumented (has an exposure row) globally


def test_exposure_rows_not_counted_as_fires():
    rows = [
        row("git-stash-guard", EXPOSURE_ACTION, ts="10:00:00", cmd_tok="git", cmd_fp="77"),
    ]
    g = classify_outcomes(rows)["git-stash-guard"]
    assert g["fires"] == 0
    assert g["exposures"] == 1


def test_dominant_action_label_friction_vs_override():
    from collections import Counter
    assert hook_roi._outcome_label(Counter({"block": 5})) == "friction"
    assert hook_roi._outcome_label(Counter({"warn": 5})) == "override"
    assert hook_roi._outcome_label(Counter()) == "override"


def test_empty_triggers_returns_empty_dict():
    assert classify_outcomes([]) == {}


def test_rows_missing_hook_are_skipped_not_crashed():
    rows = [{"action": "block", "ts": "10:00:00"}]  # no "hook" key at all
    assert classify_outcomes(rows) == {}
