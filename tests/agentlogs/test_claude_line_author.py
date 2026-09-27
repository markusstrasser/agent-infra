"""agentlogs.authorship.claude_line_author: one rule for the adapter and raw miners."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentlogs.authorship import claude_line_author


@pytest.mark.parametrize(
    ("obj", "text", "author"),
    [
        ({"origin": {"kind": "human"}, "entrypoint": "cli"}, "plan the backfill", "operator"),
        ({"origin": {"kind": "task-notification"}}, "2 background agents were stopped", "harness"),
        ({"origin": {"kind": "human"}}, "<local-command-stdout>Goal set</local-command-stdout>", "harness"),
        ({}, "[Request interrupted by user for tool use]", "harness"),
        ({}, "<system-reminder>x</system-reminder>\n<task-notification>done", "harness"),
        ({"entrypoint": "sdk-cli"}, "Watch tick: read loop/WATCH.md", "dispatch"),
        ({"entrypoint": "cli", "promptSource": "system"}, "Fallback tick for session", "dispatch"),
        # the origin stamp outranks the dispatch stamps
        ({"origin": {"kind": "human"}, "entrypoint": "sdk-cli"}, "typed via the SDK app", "operator"),
    ],
)
def test_claude_line_author(obj, text, author) -> None:
    assert claude_line_author(obj, text) == author


def test_raw_miner_predicate_loads_the_same_rule() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from common.transcript_text import is_operator_authored

    line = {"type": "user", "message": {"role": "user", "content": "<task-notification> done"}}
    assert not is_operator_authored(line)
    assert is_operator_authored({**line, "message": {"role": "user", "content": "keep going"}})
