"""Tiny hook-policy scorer for autoresearch experiments."""

from __future__ import annotations


def recommend(features: dict) -> str:
    """Return one of keep, narrow, promote, demote.

    This is deliberately small: it gives autoresearch a mutable policy surface
    while the case file owns the labels.
    """
    action = str(features.get("action", "warn"))
    phase = str(features.get("phase", "PostToolUse"))
    fires = int(features.get("fires_7d", 0))
    blocks = int(features.get("blocks_7d", 0))
    correction_rate = float(features.get("correction_rate", 0.0))
    override_rate = float(features.get("override_rate", 0.0))
    missed_incident = bool(features.get("missed_incident", False))
    high_stakes = bool(features.get("high_stakes", False))

    if missed_incident and high_stakes and phase == "PreToolUse":
        return "promote"
    if action == "block" and blocks >= 5 and override_rate >= 0.35:
        return "demote"
    if action != "block" and fires >= 50 and correction_rate < 0.05:
        return "narrow"
    if action != "block" and phase == "PreToolUse" and correction_rate >= 0.35:
        return "promote"
    return "keep"
