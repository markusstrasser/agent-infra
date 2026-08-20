"""Canonical authorship classification for user-role transcript records."""

from __future__ import annotations


# Codex emits these harness envelopes with role="user" even though the operator
# did not author them. This is a correctness boundary for taste/prior-context
# mining, so adapters and exporters load one definition rather than restating it.
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
)


def is_injected_user_text(text: str | None) -> bool:
    """True only for a recognized harness envelope at the start of the row."""
    return (text or "").lstrip().startswith(INJECTED_USER_PREFIXES)

