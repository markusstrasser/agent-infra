#!/usr/bin/env python3
"""continuation-directive-guard.py — a continuation prompt is NOT a no-op.

UserPromptSubmit hook. The blindspot-miner + steer-mine measured a recurring
agent_miss cluster (4+ sessions, research/2026-06-19-steering-vectors.md): a bare
continuation directive — "Continue from where you left off", "resume", "keep
going" — gets misread as "no new request" and the agent replies with a no-op
("No response requested" / "no response needed" / nothing actionable) instead of
RESUMING the prior task. The fix is to inject context, at prompt time, that a
continuation directive means *pick up the prior work*, not *acknowledge and stop*.

Why a hook, not an instruction: per Constitution Principle 1, "treat a
continuation as resume" is exactly the kind of behavioral predicate instructions
fail at (~0% reliable) — the miss recurred across 4+ sessions despite the global
checkpoint/continuation rules already existing in CLAUDE.md. This supplies the
recoverable cue at the moment it's needed (state-externalization lens).

Contract (Claude Code 2.1.x), mirrors the sibling userprompt-prior-context.py:
  - UserPromptSubmit envelope on stdin: `.prompt` (CC renamed it from
    `.user_message` ~2026-06-16), `.cwd`, `.session_id`; `.user_message` fallback.
  - Advisory ONLY: emits hookSpecificOutput.additionalContext, never blocks.
  - Fails OPEN: any error -> exit 0, no output.
  - Cheap: a single regex; on a non-continuation prompt it exits immediately.
  - Tight gate: fires ONLY when the prompt is *essentially nothing but* a
    continuation directive (short, no substantive new request riding along), so a
    prompt like "continue, but first fix the import in foo.py" — which carries its
    own actionable content — does NOT get the nudge (no misread risk there).

Scope decision (recorded): this is the AGENT-INFRA-LOCAL build. Registering it in
the GLOBAL ~/.claude/settings.json (so it fires in every project) is a SEPARATE,
shared-tier action that needs operator sign-off — see the builder manifest. The
.claude/settings.json snippet to wire it agent-infra-locally is in the manifest;
this file does not wire itself.
"""
# Gov-ID: hook:continuation-directive-guard
# goal: stop the agent reading a bare continuation directive ("continue from
#       where you left off") as a no-op instead of resuming the prior task —
#       a 4+-session blindspot-miner cluster
# verifier: null  # semantic (did the agent resume vs reply no-op?) — on the
#                 # generative backlog; ROI tracked via hook-trigger-log
# blast_radius: local  # agent-infra-local registration (this build). GLOBAL
#               # deploy = shared-tier, operator-gated (see manifest).
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# A bare continuation directive. Anchored so it matches the prompt that is
# *essentially only* "continue / resume / keep going" (optionally with trivial
# framing like "please" / "from where you left off" / "with the task"). The
# substantive-content guard below is what keeps this from firing on a prompt that
# says "continue" AND then asks for something concrete.
CONTINUATION = re.compile(
    r"^\s*(?:please\s+|ok(?:ay)?[,\s]+|now\s+|go\s+ahead[,\s]+|"
    r"yes[,\s]+|alright[,\s]+)?"
    r"(?:"
    r"continue|resume|carry\s+on|keep\s+going|proceed|"
    r"pick\s+up\s+(?:where|from)|go\s+on|"
    r"finish\s+(?:up|it|that|the\s+task)|"
    r"continue\s+(?:from\s+)?where\s+you\s+(?:left\s+off|were)"
    r")"
    r"\b",
    re.I,
)

# If the prompt, after stripping the continuation directive, still contains a
# concrete new ask (an imperative verb + object, a path, code, a question that's
# not just "where were we"), it carries its own actionable content and does NOT
# need the nudge. Keep this list small + high-signal — false negatives here just
# mean we skip a nudge (safe), false positives mean we nudge over a real request
# (mildly noisy). We bias toward NOT firing when substantive content is present.
SUBSTANTIVE = re.compile(
    r"\b(fix|add|remove|delete|change|refactor|implement|build|create|write|"
    r"run|test|debug|investigate|read|edit|update|rename|move|check|deploy|"
    r"why|how|what|where(?!\s+you)|when|which|should\s+(?:we|i)|can\s+(?:we|i))\b"
    r"|[/`]|\.py\b|\.md\b|\.json\b|\.sh\b",
    re.I,
)

# Hard length ceiling: a genuine "just continue" nudge is short. A long prompt is
# carrying content even if it opens with "continue", so we don't fire on it.
MAX_CHARS = 120


def _is_bare_continuation(prompt: str) -> bool:
    p = prompt.strip()
    if not p or len(p) > MAX_CHARS:
        return False
    if not CONTINUATION.search(p):
        return False
    # Strip the leading continuation phrase, then check what's left for a real ask.
    remainder = CONTINUATION.sub("", p, count=1)
    # Drop trivial trailing framing so "continue from where you left off." reduces
    # to empty rather than tripping the substantive check on "off".
    remainder = re.sub(
        r"\b(from\s+)?where\s+you\s+(left\s+off|were)\b|"
        r"\bwith\s+(the\s+)?(task|work|plan|it)\b|"
        r"\bon\s+(the\s+)?(task|work|plan)\b|"
        r"\bplease\b|\bthe\s+task\b|\bthat\b|\bit\b|\bnow\b",
        "", remainder, flags=re.I,
    )
    remainder = re.sub(r"[^\w]", "", remainder)
    if remainder:  # leftover word(s) → might be a real ask; require the guard
        if SUBSTANTIVE.search(p):
            return False
    return True


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return
    env = json.loads(raw)
    # CC 2.1.x envelope field is `.prompt` (renamed from `.user_message`
    # ~2026-06-16); read the new field, fall back to the old, flag missing-both.
    prompt = (env.get("prompt") or env.get("user_message") or "").strip()
    if not prompt:
        if "prompt" not in env and "user_message" not in env:
            print("[DEGRADED] continuation-directive-guard: envelope has neither "
                  ".prompt nor .user_message — CC UserPromptSubmit contract drifted",
                  file=sys.stderr)
        return
    if not _is_bare_continuation(prompt):
        return

    msg = (
        "CONTINUATION DIRECTIVE (harness-supplied): this prompt is a request to "
        "RESUME the prior task, NOT a no-op. Do not reply 'no response needed' / "
        "'no action required' / acknowledge-and-stop. Re-orient from "
        "`.claude/checkpoint.md` (if present) plus the recent conversation + git "
        "state, then CONTINUE the in-flight work where it left off. If you "
        "genuinely cannot tell what to resume, say so and ask — but do not treat "
        "a continuation as 'nothing to do'. "
        "(blindspot-miner cluster: continuation-misread, 4+ sessions; "
        "research/2026-06-19-steering-vectors.md)"
    )

    # Best-effort ROI trigger log (Constitution Principle 3 — measure to promote/demote).
    try:
        import subprocess
        subprocess.run(
            [str(Path.home() / "Projects/skills/hooks/hook-trigger-log.sh"),
             "continuation-directive-guard", "warn", "fired"],
            timeout=1.0, capture_output=True,
        )
    except Exception:
        pass

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": msg,
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
