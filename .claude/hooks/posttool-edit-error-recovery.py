#!/usr/bin/env python3
"""PostToolUse:Edit|Write|MultiEdit — corrective nudge when an Edit fails.

Why this exists (incident-backed, 2026-06-20):
  agentlogs shows Edit at a 7.1% error rate (1651 errors / 23 days). ~155 runs
  carry >=3 Edit errors with a long tail to 47 in one run — i.e. the model
  THRASHES on the same failure instead of recovering. The worst offenders are
  already-documented bad sessions (genomics 1c094e24 = the 9x-compact
  correction case, 21 Edit errors; hutter 897a2209, 30). A single advisory
  injection on the first failure — "re-Read, your assumption about the file is
  stale" — targets the thrash at its root.

  Ported idea (NOT code) from oh-my-openagent's edit-error-recovery hook; see
  research/2026-06-20-oh-my-openagent-primitives.md. The 3 matched substrings
  are VERIFIED from real Claude Code transcripts (~/.claude/projects/*.jsonl),
  not guessed — a guessed string is how posttool-subagent-output-check.sh once
  never fired (see its header).

Posture: advisory only (additionalContext), fail-open, hook-trigger-logged so
the false-positive / firing rate is measurable before any escalation (P3
measure-before-enforcing). Never blocks.

Input contract: Claude passes a stdin JSON envelope (no CLAUDE_TOOL_* vars).
"""
import json
import os
import subprocess
import sys

# Verified Claude Code Edit-error substrings -> tailored corrective guidance.
# (substring, message). Order = priority; first match wins.
PATTERNS = [
    (
        "String to replace not found",
        "oldString is NOT present in the file as written — almost always a "
        "whitespace/indentation mismatch, or the file changed since you last "
        "read it. Do NOT retry the same oldString. Re-Read the exact target "
        "region and copy its literal current text (including leading spaces) "
        "before constructing the edit.",
    ),
    (
        "String not found",
        "oldString is NOT present as written — whitespace/indentation mismatch "
        "or the file changed. Re-Read the target region and copy its exact "
        "current text before retrying.",
    ),
    (
        "replace_all is false",  # "Found N matches of the string to replace, but replace_all is false"
        "oldString matches MULTIPLE locations. Either add surrounding lines to "
        "make the match unique, or pass replace_all=true if you truly intend "
        "every occurrence. Retrying the same non-unique oldString will fail "
        "again.",
    ),
    (
        "must be different",
        "oldString and newString are IDENTICAL — your intended change isn't "
        "expressed. Re-derive newString so it actually differs from the "
        "current text.",
    ),
]

MARKER = "[EDIT FAILED — re-Read before retrying]"


def _response_text(resp) -> str:
    """tool_response may be a str, a dict, or a list of parts. Flatten to text."""
    if resp is None:
        return ""
    if isinstance(resp, str):
        return resp
    try:
        return json.dumps(resp)
    except Exception:
        return str(resp)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool = (data.get("tool_name") or "")
    if tool not in ("Edit", "Write", "MultiEdit"):
        return 0

    text = _response_text(data.get("tool_response"))
    if not text or MARKER in text:
        return 0

    # CC marks tool errors; require an error signal AND a known pattern so we
    # don't fire on successful edits whose content happens to contain a phrase.
    lowered = text.lower()
    looks_error = ('"is_error"' in lowered or "error" in lowered
                   or "not found" in lowered or "must be different" in lowered
                   or "replace_all is false" in lowered)
    if not looks_error:
        return 0

    msg = None
    matched = None
    for needle, guidance in PATTERNS:
        if needle in text:
            msg, matched = guidance, needle
            break
    if msg is None:
        return 0

    log = os.path.expanduser("~/Projects/skills/hooks/hook-trigger-log.sh")
    try:
        subprocess.run([log, "edit-error-recovery", "warn",
                        f"tool={tool} pat={(matched or '')[:24]}"],
                       timeout=3, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    out = {"additionalContext": f"{MARKER} {msg}"}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
