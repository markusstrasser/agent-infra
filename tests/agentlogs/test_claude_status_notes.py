"""Claude adapter indexes status notes stored as thinking blocks (label, never drop).

Since late Aug 2026 the narration Claude Code shows the operator between tool
calls arrives as `thinking` blocks with non-empty text; empty thinking blocks
carry nothing. Before parser 2026-09-22.1 only `text` blocks were indexed, so
2,508 of these notes (30-day count) never reached search.
"""

import json
from pathlib import Path

from agentlogs.adapters import claude as claude_adapter
from agentlogs.adapters.common import DiscoveredSource

SESSION = "aaaaaaaa-bbbb-cccc-dddd-eeeeffff0001"


def _assistant(uuid, content):
    return json.dumps(
        {
            "type": "assistant",
            "uuid": uuid,
            "timestamp": "2026-09-22T17:00:00.000Z",
            "sessionId": SESSION,
            "message": {"role": "assistant", "model": "claude-opus-5-5", "content": content},
        }
    )


def _parse(tmp_path: Path, lines):
    p = tmp_path / f"{SESSION}.jsonl"
    p.write_text("\n".join(lines))
    return claude_adapter.parse_source(
        DiscoveredSource(vendor="claude", source_kind="transcript_jsonl", path=p)
    )


def test_non_empty_thinking_becomes_one_status_note(tmp_path: Path) -> None:
    bundle = _parse(
        tmp_path,
        [
            _assistant(
                "a1",
                [
                    {"type": "thinking", "thinking": "", "signature": "sig-empty"},
                    {"type": "thinking", "thinking": "Checked the diff; next I'll run tests.", "signature": "sig-1"},
                    {"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {"command": "pytest -q"}},
                ],
            ),
            _assistant(
                "a2",
                [
                    {"type": "thinking", "thinking": "Found the bug.", "signature": "sig-2"},
                    {"type": "text", "text": "done"},
                ],
            ),
        ],
    )
    updates = [e for e in bundle.events if e.kind == "assistant_update"]
    assert [e.text for e in updates] == ["Checked the diff; next I'll run tests.", "Found the bug."]
    assert all(e.role == "assistant" and e.vendor_kind == "thinking" for e in updates)
    assert all(e.payload == {"type": "assistant_update"} for e in updates), "never store signatures"
    messages = [e for e in bundle.events if e.kind == "assistant_message"]
    assert [e.text for e in messages] == ["done"], "text-block handling unchanged"


def test_empty_thinking_emits_nothing(tmp_path: Path) -> None:
    bundle = _parse(
        tmp_path,
        [_assistant("a3", [{"type": "thinking", "thinking": "", "signature": "sig"}, {"type": "text", "text": "ok"}])],
    )
    assert not [e for e in bundle.events if e.kind == "assistant_update"]
    assert [e.text for e in bundle.events if e.kind == "assistant_message"] == ["ok"]
