#!/usr/bin/env python3
"""userprompt-clash-capture.py — capture directive-class user messages for OFFLINE
governance clash-detection (ADR 2026-06-16-governance-clash-detection, Phase 2 shadow).

UserPromptSubmit hook. Deliberately does NO LLM work and emits NO output: it only
appends the message to a capture log. The clash-detection itself runs OFFLINE
(scripts/clash_detect.py) so it adds ZERO latency to the turn and never interrupts —
which is also the right shape for the async "back-queue" (detect offline → queue a
question → human reviews when they want), not an inline nag.

Why a hook, not an instruction: "flag my request when it clashes with a goal/principle/
veto" is the pushback discipline (<technical_pushback>, provisional-by-construction) made
architectural — instructions for it are ~0% reliable (Principle 1). The probe
(gemini-flash on the governance-index) showed 5/5 precision on concrete clashes.

Contract (Claude Code 2.1.x): UserPromptSubmit envelope on stdin — `.user_message`,
`.cwd`, `.session_id`. Fails OPEN (any error → exit 0, no output). Captures only
directive-class messages (a cheap regex gate); the offline detector judges clash-or-not.
"""
# Gov-ID: hook:clash-capture
# goal: capture directive-class user messages so offline clash-detection can flag a
#       request clashing with a goal/principle/veto (pushback made architectural)
# verifier: null  # shadow-mode; precision measured from ~/.claude/clash-shadow.jsonl
# blast_radius: local  # agent-infra .claude/settings.json only; capture-only, fail-open
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CAPTURE_LOG = Path.home() / ".claude" / "clash-capture.jsonl"

# Directive-class gate: the message PROPOSES building / changing / deciding something —
# the surface where a request can clash with a principle or a vetoed decision. Broad on
# purpose (the offline detector judges precisely); a non-directive pays one regex + exits.
DIRECTIVE = re.compile(
    # mid-sentence directive verbs (the less-ambiguous ones — avoid bare make/use here)
    r"\b(build|add|create|implement|adopt|switch|replace|remove|delete|drop|rebuild|"
    r"extract|introduce|set up|wire|migrate|refactor|rewrite|redesign|generalize|"
    r"let'?s|should (we|i)|can (we|i)|why don'?t (we|i)|go with|deprecate|retire|"
    r"consolidate|unify|standardi[sz]e|rethink|enable|disable|spin up|stand up|"
    r"scaffold|expose)\b"
    # OR a sentence-initial imperative ("Make the tooling …", "Use X …")
    r"|^\s*\W*(make|use|build|add|create|switch|replace|remove|drop|adopt|design|"
    r"change|update|do|spin|start)\b",
    re.I,
)


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        env = json.loads(raw)
        msg = (env.get("user_message") or "").strip()
        # too short or no build/change/decide intent → not a clash surface, skip
        if len(msg) < 16 or not DIRECTIVE.search(msg):
            return
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": env.get("session_id") or "",
            "cwd": env.get("cwd") or "",
            "message": msg[:4000],
            "processed": False,
        }
        CAPTURE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CAPTURE_LOG.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:
        return  # fail open — capture is best-effort, never blocks a turn


if __name__ == "__main__":
    main()
