"""Fail-closed contracts for the continuous code-review dispatcher."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "code-review-scout.py"
SPEC = importlib.util.spec_from_file_location("code_review_scout", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
scout = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scout)


PROVIDER = {
    "name": "test-provider",
    "model_flag": "-m test-model",
    "extra": "",
}


def test_dispatch_returns_nonempty_reviewer_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scout.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "NO_ISSUES\n", ""),
    )

    assert scout.dispatch_review("code", "patterns", PROVIDER, "test:batch-1") == "NO_ISSUES"


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "match"),
    [
        (1, "", "authentication failed", "exited 1"),
        (0, "", "", "without a verdict"),
    ],
)
def test_dispatch_failure_cannot_be_reported_as_zero_findings(
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    stderr: str,
    match: str,
) -> None:
    monkeypatch.setattr(
        scout.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], returncode, stdout, stderr
        ),
    )

    with pytest.raises(scout.DispatchError, match=match):
        scout.dispatch_review("code", "patterns", PROVIDER, "test:batch-1")


def test_dispatch_timeout_is_a_hard_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], timeout=300)

    monkeypatch.setattr(scout.subprocess, "run", timeout)

    with pytest.raises(scout.DispatchError, match="timed out"):
        scout.dispatch_review("code", "patterns", PROVIDER, "test:batch-1")


def test_parse_accepts_only_exact_no_issues() -> None:
    assert scout.parse_findings("NO_ISSUES\n", "test", [], Path(".")) == []
    with pytest.raises(scout.DispatchError, match="output contract"):
        scout.parse_findings("preface\nNO_ISSUES", "test", [], Path("."))


def test_parse_rejects_async_session_receipt_as_a_verdict() -> None:
    with pytest.raises(scout.DispatchError, match="output contract"):
        scout.parse_findings("SESSION_ID=28860", "composer", [], Path("."))


def test_parse_accepts_a_structured_finding() -> None:
    parsed = scout.parse_findings(
        "scripts/example.py:7 HIGH patterns unchecked terminal state",
        "composer",
        [],
        Path("."),
    )
    assert parsed == [
        {
            "file": "scripts/example.py",
            "line": 7,
            "severity": "HIGH",
            "category": "patterns",
            "description": "unchecked terminal state",
            "source": "composer",
        }
    ]
