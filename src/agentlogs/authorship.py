"""Canonical authorship classification for user-role transcript records."""

from __future__ import annotations


# Codex and Cursor emit these harness envelopes with role="user" even though the
# operator did not author them. This is a correctness boundary for taste/prior-context
# mining, so adapters and exporters load one definition rather than restating it.
# Measured 2026-09-26 over research-project rollouts (June-September): subagent
# notifications (782), automation heartbeats (481), goal continuations (31), skill
# bodies (20), in-app browser state (13), hook prompts (7), interrupt notices (4).
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
)


def is_injected_user_text(text: str | None) -> bool:
    """True only for a recognized harness envelope at the start of the row."""
    return (text or "").lstrip().startswith(INJECTED_USER_PREFIXES)

