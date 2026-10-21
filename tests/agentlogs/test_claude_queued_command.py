"""Prompts typed while a turn runs are queued_command attachments, mostly with no
type=user line (487 of 494 in 32 operator sessions, 2026-10-21). The adapter, the
authorship rule and the raw-transcript reader must all count the human ones.

Fixtures are real genomics records (1cce6699, 2026-10-18) with prompts shortened.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from agentlogs.adapters import claude as claude_adapter  # noqa: E402
from agentlogs.adapters.common import DiscoveredSource  # noqa: E402
from agentlogs.authorship import claude_line_author  # noqa: E402
from common.transcript_text import is_operator_authored, iter_user_texts, user_texts  # noqa: E402

SID = "1cce6699-dd28-4115-b427-53274782020c"


def _queued(prompt, uuid, origin, mode="prompt"):
    return {
        "parentUuid": "cb221841-a6ba-4850-9961-91d9c86c5843", "isSidechain": False,
        "attachment": {"type": "queued_command", "prompt": prompt,
                       "source_uuid": "59e5eb62-1a04-4c50-88fe-9f7ea5e73288",
                       "commandMode": mode, "origin": origin,
                       "timestamp": "2026-10-18T11:59:33.767Z", "humanTurn": True},
        "type": "attachment", "uuid": uuid, "timestamp": "2026-10-18T11:59:33.767Z",
        "sessionId": SID,
    }


HUMAN = _queued("there's an agent currently trying to clear worktrees", "q-human", {"kind": "human"})
TASK = _queued("<task-notification>\n<task-id>b92m962rz</task-id>\n<status>completed</status>",
               "q-task", {"kind": "task-notification", "producer": "session-task"}, "task-notification")
RELAY = _queued("<cross-session-message from=\"uds:/tmp/x.sock\">\nI didn't empty it", "q-relay", {"kind": "human"})
ECHOED = _queued("parallelize", "q-echo", {"kind": "human"})
ECHO_LINE = {"type": "user", "uuid": "u-echo", "timestamp": "2026-10-18T11:59:40.000Z", "sessionId": SID,
             "origin": {"kind": "human"}, "message": {"role": "user", "content": "parallelize"}}


def test_claude_line_author_reads_the_attachment_stamp() -> None:
    assert claude_line_author(HUMAN, HUMAN["attachment"]["prompt"]) == "operator"
    assert claude_line_author(TASK, TASK["attachment"]["prompt"]) == "harness"
    assert claude_line_author(RELAY, RELAY["attachment"]["prompt"]) == "harness"


def test_user_texts_counts_human_queued_prompts() -> None:
    assert user_texts(HUMAN) == ["there's an agent currently trying to clear worktrees"]
    assert user_texts(TASK) == []
    assert is_operator_authored(HUMAN)
    assert not is_operator_authored(TASK)
    assert not is_operator_authored(RELAY)
    assert user_texts({"type": "attachment", "attachment": {"type": "deferred_tools_delta"}}) == []


def test_iter_user_texts_drops_an_echoed_queued_prompt() -> None:
    got = [(o["uuid"], t) for o, t in iter_user_texts([HUMAN, ECHOED, TASK, ECHO_LINE]) if t]
    assert got == [("q-human", [HUMAN["attachment"]["prompt"]]), ("u-echo", ["parallelize"])]


def test_adapter_emits_queued_commands_as_labeled_user_rows(tmp_path: Path) -> None:
    p = tmp_path / f"{SID}.jsonl"
    p.write_text("\n".join(json.dumps(o) for o in [HUMAN, TASK, RELAY, ECHOED, ECHO_LINE]))
    bundle = claude_adapter.parse_source(DiscoveredSource(vendor="claude", source_kind="transcript_jsonl", path=p))
    kinds = {e.vendor_event_id: e.vendor_kind for e in bundle.events if e.kind == "user_message"}
    assert kinds == {"q-human": "user", "q-task": "meta_injected", "q-relay": "meta_injected",
                     "q-echo": "queued_echo", "u-echo": "user"}
    assert all(e.role == "user" for e in bundle.events if e.kind == "user_message")
