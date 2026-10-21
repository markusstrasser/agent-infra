"""Canonical authorship classification for user-role transcript records.

Stdlib-only and free of package-relative imports: scripts/common/transcript_text.py
loads this file by path, so raw-transcript miners and the adapters share it.
"""

from __future__ import annotations


# Codex, Cursor and Claude Code emit these harness envelopes with role="user" even
# though the operator did not author them. This is a correctness boundary for
# taste/prior-context mining, so adapters and exporters load one definition rather
# than restating it. Measured 2026-09-26 over research-project rollouts
# (June-September): subagent notifications (782), automation heartbeats (481), goal
# continuations (31), skill bodies (20), in-app browser state (13), hook prompts (7),
# interrupt notices (4).
INJECTED_USER_PREFIXES = (
    "# AGENTS.md instructions for ",
    "<codex_delegation>",
    "<permissions instructions>",
    "<app-context>",
    "<collaboration_mode>",
    "<skills_instructions>",
    "<apps_instructions>",
    "<plugins_instructions>",
    "<environment_context>",
    "<recommended_plugins>",
    "<subagent_notification>",
    "<heartbeat>",
    "<codex_internal_context",
    "<skill>",
    "<in-app-browser-context",
    "<hook_prompt",
    "<turn_aborted>",
    # Cursor background-task completion and subagent roster
    "Briefly inform the user about the task result",
    "<available_subagent_types>",
    # Claude Code frames written without a harness flag (isMeta / isCompactSummary).
    # Measured 2026-09-23 over 489 transcripts: peer/teammate relays (395 lines),
    # interrupt markers (70), local-command stdout (60); in operator sessions on
    # 2026-09-27, 1,210 of 2,100 user text lines were these frames.
    "Another Claude session sent a message",  # peer / teammate relay wrapper
    "<teammate-message",
    "<cross-session-message",
    "<agent-message",
    "<local-command-",  # -stdout / -stderr / -caveat
    "[Request interrupted by user",
    "<task-notification>",
    "<system-reminder>",
    "[SYSTEM NOTIFICATION",
)


def is_injected_user_text(text: str | None) -> bool:
    """True only for a recognized harness envelope at the start of the row."""
    return (text or "").lstrip().startswith(INJECTED_USER_PREFIXES)


def is_claude_harness_text(text: str | None) -> bool:
    """A Claude Code harness frame by its text alone: an envelope at the start, or a
    task notification that another frame precedes within the first 200 characters."""
    head = (text or "").lstrip()
    return head.startswith(INJECTED_USER_PREFIXES) or "<task-notification>" in head[:200]


def queued_command(obj: dict) -> dict | None:
    """The queued_command attachment of one Claude Code record, else None.

    A prompt typed while a turn runs is stored as {"type": "attachment",
    "attachment": {"type": "queued_command", "prompt": ..., "origin": {...},
    "commandMode": "prompt" | "task-notification"}} and usually never appears as a
    type=user line (measured 2026-10-21: 487 of 494 in 32 operator sessions).
    Task notifications are queued the same way with origin.kind "task-notification".
    """
    if obj.get("type") != "attachment":
        return None
    att = obj.get("attachment")
    if isinstance(att, dict) and att.get("type") == "queued_command":
        return att
    return None


def queued_command_text(att: dict) -> str:
    prompt = att.get("prompt")
    if isinstance(prompt, str):
        return prompt
    if isinstance(prompt, list):
        return "\n".join(b.get("text", "") for b in prompt if isinstance(b, dict) and b.get("type") == "text")
    return ""


def is_human_queued_command(obj: dict) -> bool:
    """A queued_command whose stamp says a human typed it (origin.kind "human",
    commandMode "prompt"); the text may still be a relay frame — see claude_line_author."""
    att = queued_command(obj)
    if att is None:
        return False
    origin = att.get("origin")
    kind = origin.get("kind") if isinstance(origin, dict) else None
    return kind in (None, "human") and att.get("commandMode", "prompt") == "prompt"


def claude_line_author(obj: dict, text: str) -> str:
    """Who wrote one Claude Code user line: "operator", "harness" or "dispatch".

    `text` is the line's user-authored text; the harness flags isMeta and
    isCompactSummary are the caller's first screen. Evidence, strongest first:
      1. Claude Code's origin stamp decides when present: a kind other than "human"
         (task-notification, peer, auto-continuation) is the harness;
      2. without one, entrypoint "sdk-*" (`claude -p`) or promptSource "sdk"/"system"
         means a program wrote the prompt;
      3. a harness frame is the harness, stamped or not: Claude Code stamps
         local-command stdout echoes ("Goal set: …", "Compacted …") origin.kind
         "human" (measured 2026-09-26, arc-agi c0549792 and 3 more sessions).
    A queued_command attachment is judged by its own stamp (attachment.origin,
    commandMode); a non-"prompt" commandMode is the harness.
    """
    att = queued_command(obj)
    if att is not None and att.get("commandMode", "prompt") != "prompt":
        return "harness"
    origin = (att if att is not None else obj).get("origin")
    if isinstance(origin, dict) and origin.get("kind"):
        if origin["kind"] != "human":
            return "harness"
    elif str(obj.get("entrypoint") or "").startswith("sdk") or obj.get("promptSource") in ("sdk", "system"):
        return "dispatch"
    return "harness" if is_claude_harness_text(text) else "operator"
