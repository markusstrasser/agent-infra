"""Harness envelopes are labeled without swallowing real operator taste."""

from __future__ import annotations

from pathlib import Path

import agentlogs
from agentlogs import authorship_reindex as ar
from agentlogs.authorship import is_injected_user_text


def _db(path: Path):
    db = agentlogs.connect(path)
    db.execute(
        "INSERT INTO sessions (session_pk, vendor, client, vendor_session_id, "
        "session_uuid, first_message) "
        "VALUES (1, 'codex', 'codex-cli', 's1', 'codex:s1', '<recommended_plugins>')"
    )
    db.execute(
        "INSERT INTO runs (run_id, session_pk, vendor, client, started_at) "
        "VALUES ('r1', 1, 'codex', 'codex-cli', '2026-08-20T00:00:00Z')"
    )
    db.executemany(
        "INSERT INTO events (event_id, run_id, seq, kind, vendor_kind, role, text) "
        "VALUES (?, 'r1', ?, 'user_message', 'message', 'user', ?)",
        (
            ("meta", 1, "<recommended_plugins>\n# AGENTS.md instructions for /tmp/x"),
            ("operator", 2, "Keep the exact taste-bearing input."),
        ),
    )
    return db


def test_injected_prefix_classifier_does_not_match_mid_message_quote() -> None:
    assert is_injected_user_text("<environment_context>generated</environment_context>")
    assert not is_injected_user_text(
        "My request quotes <environment_context>, but this sentence is mine."
    )


def test_backfill_labels_envelope_and_refreshes_first_message(tmp_path: Path) -> None:
    db = _db(tmp_path / "a.db")
    assert ar.plan_reindex(db) == ar.AuthorshipPlan(rows=1, sessions=1)

    result = ar.apply_reindex(db)

    assert result == ar.AuthorshipPlan(rows=1, sessions=1)
    assert dict(db.execute(
        "SELECT event_id, vendor_kind FROM events ORDER BY seq"
    ).fetchall()) == {"meta": "meta_injected", "operator": "message"}
    assert db.execute("SELECT first_message FROM sessions").fetchone()[0] == (
        "Keep the exact taste-bearing input."
    )
    assert ar.apply_reindex(db) == ar.AuthorshipPlan(rows=0, sessions=0)
    db.close()



def test_codex_and_cursor_runtime_envelopes_are_injected() -> None:
    # Measured 2026-09-26: these reached taste mining as operator text.
    for text in (
        '<subagent_notification>\n{"agent_path":"019f","status":{"completed":"done"}}',
        "<heartbeat>\n  <automation_id>arc3-v11-submission-window</automation_id>",
        '<codex_internal_context source="goal">\nContinue working toward the goal.',
        "<skill>\n<name>research</name>\n<path>/x/SKILL.md</path>",
        '<in-app-browser-context source="ambient-ui-state">',
        '<hook_prompt hook_run_id="stop:138:/x/hooks.json">BLOCKED: ...',
        "<turn_aborted>\nThe user interrupted the previous turn on purpose.",
        "Briefly inform the user about the task result and perform any follow-up actions",
        "<available_subagent_types>\nAvailable subagent_types and a quick description",
    ):
        assert is_injected_user_text(text), text[:40]
    assert not is_injected_user_text(
        '<send_user_message_question_reply> [{"question":"Does X?","answer":"yes"}]'
    )


def test_backfill_labels_cursor_envelope(tmp_path: Path) -> None:
    db = agentlogs.connect(tmp_path / "c.db")
    db.execute(
        "INSERT INTO sessions (session_pk, vendor, client, vendor_session_id, session_uuid) "
        "VALUES (1, 'cursor', 'cursor-agent', 'c1', 'cursor:c1')"
    )
    db.execute(
        "INSERT INTO runs (run_id, session_pk, vendor, client, started_at) "
        "VALUES ('r1', 1, 'cursor', 'cursor-agent', '2026-09-22T00:00:00Z')"
    )
    db.executemany(
        "INSERT INTO events (event_id, run_id, seq, kind, vendor_kind, role, text) "
        "VALUES (?, 'r1', ?, 'user_message', 'user', 'user', ?)",
        (
            ("meta", 1, "Briefly inform the user about the task result and perform any follow-up"),
            ("operator", 2, "<user_query>Are these metrics right?</user_query>"),
        ),
    )
    assert ar.plan_reindex(db) == ar.AuthorshipPlan(rows=1, sessions=1)
    ar.apply_reindex(db)
    assert dict(db.execute(
        "SELECT event_id, vendor_kind FROM events ORDER BY seq"
    ).fetchall()) == {"meta": "meta_injected", "operator": "user"}
    db.close()
