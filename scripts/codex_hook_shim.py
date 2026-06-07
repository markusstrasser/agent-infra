#!/usr/bin/env python3
"""codex_hook_shim.py — normalize Claude-dialect hook output to Codex's contract.

Claude Code and Codex CLI share a hook *firing* model but differ on the
*output/decision* contract. Our shared hooks (skills/hooks/*.sh + per-project
.claude/hooks) all speak Claude's dialect:

  - exit 2 with the block reason on EITHER stdout (as `{"decision":"block",...}`)
    or stderr (as plain text), and
  - advisory injection as a TOP-LEVEL `{"decision":"allow","additionalContext":"…"}`
    on stdout.

Codex (>=0.137) enforces a stricter shape, extracted from its binary's error
strings:

  - "PreToolUse hook exited with code 2 but did not write a blocking reason to
    stderr"  -> exit 2 REQUIRES a non-empty reason on STDERR.
  - "hook returned invalid pre-tool-use JSON output" -> any STDOUT on a
    JSON-parsed hook event must be valid Codex-schema JSON, i.e.
    `{"hookSpecificOutput": {"hookEventName": "<EVT>", "additionalContext": "…"}}`,
    NOT top-level `additionalContext`.
  - "decision:block without a non-empty reason" -> block needs a reason.

`codex_parity_sync.py` wraps every generated `.codex/hooks.json` command with
this shim (passing the event via CODEX_HOOK_EVENT). The Claude path and the hook
bodies stay untouched — translation happens only on the Codex side, at runtime.

Contract: read the hook payload on stdin, run the real command with that stdin,
capture (stdout, stderr, exit), re-emit in Codex's shape. Fail OPEN — if the
shim itself errors, pass the inner command's raw output/exit through unchanged.

Usage (as emitted by codex_parity_sync):
    CODEX_HOOK_EVENT=PreToolUse python3 codex_hook_shim.py '<full hook command>'
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

# Events whose stdout Codex parses as JSON.
JSON_STDOUT_EVENTS = {
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "PostCompact",
}
# Events where a non-JSON stdout line is accepted as plain advisory text.
PLAIN_TEXT_OK_EVENTS = {"SessionStart", "UserPromptSubmit", "SubagentStart"}
# Events where free-form advisory text is meaningful and can be lifted into
# additionalContext when a hook prints plain text instead of JSON.
ADDITIONAL_CONTEXT_EVENTS = {"PreToolUse", "PostToolUse", "UserPromptSubmit"}

REASON_KEYS = ("reason", "permissionDecisionReason", "additionalContext", "message", "stopReason")


def _extract_reason(stdout: str) -> str:
    """Best-effort block reason from a hook's stdout."""
    text = stdout.strip()
    if not text:
        return ""
    try:
        d = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(d, dict):
        for key in REASON_KEYS:
            val = d.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        hs = d.get("hookSpecificOutput")
        if isinstance(hs, dict):
            val = hs.get("additionalContext")
            if isinstance(val, str) and val.strip():
                return val.strip()
    return text


def _normalize_stdout(stdout: str, event: str) -> str:
    """Reshape Claude-dialect stdout into Codex's JSON contract.

    Returns the stdout string to emit (possibly empty to suppress).
    """
    if event not in JSON_STDOUT_EVENTS:
        return stdout
    text = stdout.strip()
    if not text:
        return ""

    try:
        d = json.loads(text)
    except json.JSONDecodeError:
        # Non-JSON stdout on a JSON-parsed event. Preserve as advisory where that
        # is meaningful; otherwise suppress (Codex would reject raw text, and a
        # stray echo is not worth a hard error).
        if event in PLAIN_TEXT_OK_EVENTS:
            return stdout
        if event in ADDITIONAL_CONTEXT_EVENTS:
            return json.dumps(
                {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
            )
        return ""

    if not isinstance(d, dict):
        return ""

    changed = False

    # Lift a top-level additionalContext into hookSpecificOutput (Codex's shape).
    if "additionalContext" in d:
        ac = d.pop("additionalContext")
        hs = d.get("hookSpecificOutput")
        if not isinstance(hs, dict):
            hs = {}
        hs.setdefault("hookEventName", event)
        hs["additionalContext"] = ac
        d["hookSpecificOutput"] = hs
        changed = True

    # Ensure any hookSpecificOutput carries the correct hookEventName.
    hs = d.get("hookSpecificOutput")
    if isinstance(hs, dict) and hs.get("hookEventName") != event:
        hs["hookEventName"] = event
        changed = True

    # A block decision must carry a non-empty reason.
    if d.get("decision") == "block" and not (d.get("reason") or "").strip():
        d["reason"] = _extract_reason(text) or "blocked"
        changed = True

    return json.dumps(d) if changed else stdout


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0
    command = argv[1]
    event = os.environ.get("CODEX_HOOK_EVENT", "")
    payload = sys.stdin.read()

    try:
        proc = subprocess.run(
            command,
            input=payload,
            text=True,
            capture_output=True,
            shell=True,
            executable="/bin/bash",
        )
    except Exception:
        # Could not even launch the inner hook — fail open, do not block.
        return 0

    stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode

    try:
        out_norm = _normalize_stdout(stdout, event)
        err_norm = stderr
        # exit 2 with empty stderr: Codex needs the reason on stderr.
        if rc == 2 and not stderr.strip():
            err_norm = _extract_reason(stdout) or "hook blocked (exit 2)"
    except Exception:
        # Normalizer bug must never break the agent — pass raw through.
        out_norm, err_norm = stdout, stderr

    if out_norm:
        sys.stdout.write(out_norm)
    if err_norm:
        sys.stderr.write(err_norm)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
