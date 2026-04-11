"""Phase 1 unit tests for claim-bench.

Covers the pure-logic parts of scorer.py and tools.py:
- _normalize (verdict string canonicalization)
- _parse_groundedness_verdict (judge output parsing)
- _format_tool_trace (state.messages walking)
- exa_search budget counter
- _format_result (Exa result trimming)

Integration tests (actual Exa calls, actual judge calls) are NOT covered
here — they require network and API keys. Run the inspect eval itself
as the integration test.

Run:
    uv run pytest experiments/claim-bench/test_phase1.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Add this directory to sys.path so sibling imports (scorer, tools) resolve
# the same way inspect_ai's task loader does.
THIS_DIR = str(Path(__file__).resolve().parent)
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

import tools  # noqa: E402
from scorer import (  # noqa: E402
    _extract_verdict,
    _format_tool_trace,
    _normalize,
    _parse_groundedness_verdict,
)
from tools import _check_budget, _format_result, exa_call_count  # noqa: E402


# ---------- _normalize ----------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("supported", "supported"),
        ("Supported", "supported"),
        ("  SUPPORTED  ", "supported"),
        ("insufficient-evidence", "insufficient_evidence"),
        ("insufficient evidence", "insufficient_evidence"),
        ("Not Verifiable", "not_verifiable"),
        ("", ""),
    ],
)
def test_normalize_handles_common_shapes(raw: str, expected: str) -> None:
    assert _normalize(raw) == expected


# ---------- _extract_verdict ----------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Two-line format — the prompt's intended shape
        ("supported\nEvidence directly backs the claim", "supported"),
        # Single-line colon-separated — observed on case 002, stochastic
        ("contradicted: Evidence indicates the claim is false", "contradicted"),
        # Trailing whitespace then newline
        ("supported  \nExplanation follows", "supported"),
        # Markdown emphasis wrapping
        ("**supported** Evidence for the claim", "supported"),
        # All-caps with colon
        ("NOT_VERIFIABLE: rhetorical claim", "not_verifiable"),
        # Verdict with hyphenation spelling
        ("insufficient-evidence\nNothing found", "insufficient_evidence"),
        # Edge: empty output
        ("", ""),
        # Edge: only whitespace
        ("   \n  ", ""),
    ],
)
def test_extract_verdict_handles_observed_formats(raw: str, expected: str) -> None:
    """Regression for the case-002 plan-close finding.

    The Phase 1 commit used `_normalize(raw_output.split('\\n')[0])` which
    failed on single-line 'verdict: explanation' outputs. _extract_verdict
    must return the verdict token regardless of format.
    """
    assert _extract_verdict(raw) == expected


# ---------- _parse_groundedness_verdict ----------


def test_parse_grounded() -> None:
    label, value = _parse_groundedness_verdict(
        "grounded\nRetrieval trace clearly supports the verdict."
    )
    assert label == "grounded"
    assert value == 1.0


def test_parse_partial() -> None:
    label, value = _parse_groundedness_verdict(
        "partial\nSome relevant evidence but verdict overclaims."
    )
    assert label == "partial"
    assert value == 0.5


def test_parse_ungrounded() -> None:
    label, value = _parse_groundedness_verdict(
        "ungrounded\nTrace is empty and model confabulated."
    )
    assert label == "ungrounded"
    assert value == 0.0


def test_parse_not_grounded_variant() -> None:
    label, value = _parse_groundedness_verdict("not grounded\nNo real evidence.")
    assert label == "ungrounded"
    assert value == 0.0


def test_parse_strips_decoration() -> None:
    # Judge might wrap the label in markdown emphasis.
    label, value = _parse_groundedness_verdict("**grounded**\njustification")
    assert label == "grounded"
    assert value == 1.0


def test_parse_error_returns_zero_not_partial() -> None:
    """Regression for the fix where parse_error silently scored as 0.5.

    Treating an unparseable judge output as half-grounded inflates the
    mean groundedness by +0.5 per sample every time the judge goes
    off-format. The post-fix behavior is 0.0 — we do NOT have evidence
    of grounding if we cannot read the judge. A cross-model review
    (Gemini arch + GPT-5.4 formal) flagged this on 2026-04-11 Phase 1
    plan-close review.
    """
    label, value = _parse_groundedness_verdict("maybe?\nunclear")
    assert label == "parse_error"
    assert value == 0.0, (
        "parse_error must return 0.0 — returning 0.5 silently inflates "
        "the metric mean when the judge violates output format"
    )


# ---------- _format_tool_trace ----------


def _fake_assistant(tool_calls: list | None = None) -> SimpleNamespace:
    """Minimal stand-in for ChatMessageAssistant."""
    return SimpleNamespace(role="assistant", tool_calls=tool_calls)


def _fake_tool_result(
    function: str, content: str, error: object | None = None
) -> object:
    """Create a real ChatMessageTool so isinstance checks pass."""
    from inspect_ai.model import ChatMessageTool

    return ChatMessageTool(
        role="tool", function=function, content=content, tool_call_id="x", error=error
    )


def _fake_state(messages: list) -> SimpleNamespace:
    return SimpleNamespace(messages=messages)


def test_format_tool_trace_no_calls() -> None:
    state = _fake_state([_fake_assistant(tool_calls=None)])
    trace = _format_tool_trace(state)
    assert trace.startswith("(no tool calls")


def test_format_tool_trace_with_call_and_result() -> None:
    tc = SimpleNamespace(
        function="exa_search", arguments={"query": "pair instability gap"}
    )
    messages = [
        _fake_assistant(tool_calls=[tc]),
        _fake_tool_result("exa_search", "result content about pair instability"),
    ]
    trace = _format_tool_trace(_fake_state(messages))
    assert "Tool call: exa_search" in trace
    assert "pair instability gap" in trace
    assert "Tool result from exa_search" in trace
    assert "result content" in trace


def test_format_tool_trace_truncates_long_result() -> None:
    long_content = "x" * 5000
    messages = [_fake_tool_result("exa_search", long_content)]
    trace = _format_tool_trace(_fake_state(messages))
    # Truncation happens at 2500 + "...[truncated]" suffix
    assert "[truncated]" in trace
    assert len(trace) < 4000


def test_format_tool_trace_non_dict_arguments_survive() -> None:
    # Defensive: arguments might not be a dict; shouldn't crash.
    tc = SimpleNamespace(function="exa_search", arguments="raw string args")
    messages = [_fake_assistant(tool_calls=[tc])]
    trace = _format_tool_trace(_fake_state(messages))
    assert "exa_search" in trace


# ---------- tools.py: budget counter ----------


def test_budget_counter_increments_and_exceeds() -> None:
    # Reset the module-global counter and lower the cap for the test.
    with patch.object(tools, "_exa_call_count", 0), patch.object(
        tools, "MAX_EXA_CALLS_PER_PROCESS", 3
    ):
        _check_budget()
        _check_budget()
        _check_budget()
        with pytest.raises(tools.ToolError, match="budget exhausted"):
            _check_budget()


def test_exa_call_count_readable() -> None:
    # exa_call_count is a getter — should return an int.
    assert isinstance(exa_call_count(), int)


# ---------- tools.py: _format_result ----------


def test_format_result_trims_long_text() -> None:
    result = SimpleNamespace(
        title="t", url="u", published_date="2026-01-01", author="a", text="y" * 3000
    )
    out = _format_result(result, max_chars=1500)
    assert len(out["text"]) == 1500 + len("...")
    assert out["text"].endswith("...")


def test_format_result_handles_missing_fields() -> None:
    result = SimpleNamespace()  # no attributes at all
    out = _format_result(result, max_chars=1500)
    assert out["title"] is None
    assert out["url"] is None
    assert out["published_date"] is None
    assert out["author"] is None
    assert out["text"] == ""


def test_format_result_none_text_coerced_to_empty() -> None:
    result = SimpleNamespace(text=None)
    out = _format_result(result, max_chars=1500)
    assert out["text"] == ""


def test_num_results_bounds_exist() -> None:
    """The tool module must expose MIN/MAX num_results constants so a
    confused model can't request 100 results per query and blow up cost.
    """
    assert tools.MIN_NUM_RESULTS >= 1
    assert tools.MAX_NUM_RESULTS <= 50  # generous upper bound on the bound
    assert tools.MIN_NUM_RESULTS < tools.MAX_NUM_RESULTS


def test_gemini_to_google_key_bridge_in_scorer_module() -> None:
    """Regression: importing scorer.py with only GEMINI_API_KEY set must
    populate GOOGLE_API_KEY at module load so the google-genai SDK
    authenticates without an operator-side export.
    """
    import importlib
    import os as _os

    saved = {
        "GOOGLE_API_KEY": _os.environ.get("GOOGLE_API_KEY"),
        "GEMINI_API_KEY": _os.environ.get("GEMINI_API_KEY"),
    }
    try:
        _os.environ.pop("GOOGLE_API_KEY", None)
        _os.environ["GEMINI_API_KEY"] = "test-sentinel-value"
        import scorer as scorer_mod  # noqa: F401

        importlib.reload(scorer_mod)
        assert _os.environ.get("GOOGLE_API_KEY") == "test-sentinel-value"
    finally:
        # Restore original env so other tests aren't affected.
        for k, v in saved.items():
            if v is None:
                _os.environ.pop(k, None)
            else:
                _os.environ[k] = v


# ---------- regression: the bug fixed during plan-close ----------


def test_tool_calls_seen_is_not_inverted() -> None:
    """Regression for the bug where `tool_calls_seen` metadata was inverted.

    Before the fix, `tool_calls_seen` was True exactly when there were NO
    tool calls (it compared `_format_tool_trace(state).startswith('(no tool')`
    without negation). This test reproduces the semantic and ensures the
    field reports what its name claims.
    """
    tc = SimpleNamespace(function="exa_search", arguments={"query": "x"})
    state_with_calls = _fake_state(
        [_fake_assistant(tool_calls=[tc]), _fake_tool_result("exa_search", "hit")]
    )
    state_empty = _fake_state([_fake_assistant(tool_calls=None)])

    trace_with = _format_tool_trace(state_with_calls)
    trace_empty = _format_tool_trace(state_empty)

    # This is the logic the scorer uses post-fix.
    assert not trace_with.startswith("(no tool")  # tool_calls_seen should be True
    assert trace_empty.startswith("(no tool")  # tool_calls_seen should be False
