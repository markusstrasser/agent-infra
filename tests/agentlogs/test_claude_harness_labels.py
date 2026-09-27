"""Claude adapter labels harness-injected user lines (label, never drop).

Compaction summaries (isCompactSummary) and meta expansions (isMeta) re-quote
old user text; downstream miners filter on vendor_kind instead of each
re-implementing transcript parsing (improvement-log 2026-07-05 harness-requote
class: 3 miners diverged, all wrong).
"""

import json
from pathlib import Path

from agentlogs.adapters import claude as claude_adapter
from agentlogs.adapters.common import DiscoveredSource


def _line(text, **extra):
    d = {
        "type": "user",
        "uuid": f"u-{abs(hash(text)) % 10**8}",
        "timestamp": "2026-07-05T10:00:00.000Z",
        "sessionId": "aaaaaaaa-bbbb-cccc-dddd-eeeeffff0000",
        "message": {"role": "user", "content": text},
    }
    d.update(extra)
    return json.dumps(d)


def test_harness_injected_user_lines_labeled(tmp_path: Path) -> None:
    p = tmp_path / "aaaaaaaa-bbbb-cccc-dddd-eeeeffff0000.jsonl"
    p.write_text(
        "\n".join(
            [
                _line("This session is being continued ... #f old", isCompactSummary=True),
                _line("skill expansion text", isMeta=True),
                _line("a genuine user message"),
            ]
        )
    )
    bundle = claude_adapter.parse_source(
        DiscoveredSource(vendor="claude", source_kind="transcript_jsonl", path=p)
    )
    user_events = [e for e in bundle.events if e.kind == "user_message"]
    kinds = {e.text[:10]: e.vendor_kind for e in user_events}
    assert len(user_events) == 3, "label, never drop — all three lines stored"
    assert kinds["This sessi"] == "compact_summary"
    assert kinds["skill expa"] == "meta_injected"
    assert kinds["a genuine "] == "user"


def test_unflagged_harness_frames_labeled(tmp_path: Path) -> None:
    """Task notifications, peer relays and local-command echoes carry no isMeta flag;
    Claude Code's origin stamp or the frame itself marks them (2026-09-27)."""
    p = tmp_path / "aaaaaaaa-bbbb-cccc-dddd-eeeeffff0000.jsonl"
    p.write_text(
        "\n".join(
            [
                _line("2 background agents were stopped by the user",
                      origin={"kind": "task-notification"}),
                _line("Another Claude session sent a message: rebase done"),
                _line("<local-command-stdout>Goal set</local-command-stdout>", origin={"kind": "human"}),
                _line("why is the backfill slow?", origin={"kind": "human"}, entrypoint="cli"),
                _line("Watch tick: read loop/WATCH.md", entrypoint="sdk-cli"),
            ]
        )
    )
    bundle = claude_adapter.parse_source(
        DiscoveredSource(vendor="claude", source_kind="transcript_jsonl", path=p)
    )
    kinds = [e.vendor_kind for e in bundle.events if e.kind == "user_message"]
    # the dispatch-stamped line stays "user": its session is session_role 'dispatch'
    assert kinds == ["meta_injected", "meta_injected", "meta_injected", "user", "user"]
