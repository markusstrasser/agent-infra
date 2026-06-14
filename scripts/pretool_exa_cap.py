#!/usr/bin/env python3
"""PreToolUse hook (pilot, agent-infra-local): cap exa full-text extraction.

# Gov-ID: hook:pretool-exa-cap
# goal: bound exa web_search_advanced context bloat — uncapped textMaxCharacters
#       produced 8.5M tok of >50KB results across 122 calls (the single biggest
#       controllable tool-output source after native-paginated Read).
# verifier: null
# blast_radius: local

Exa's `web_search_advanced_exa` returns UNCAPPED per-result text when
`textMaxCharacters` is unset. The `research-tool-gotchas` rule says to cap on
broad sweeps; it is ignored 122×. This enforces it (instruction -> architecture,
Constitution Principle 1) by injecting/clamping `textMaxCharacters` via the
PreToolUse `updatedInput` contract (best/claude-code-docs/docs/hooks.md:925).

Mechanism: read the stdin envelope (NO CLAUDE_TOOL_* vars — hook-input-contract);
if the call is web_search_advanced_exa and textMaxCharacters is unset or > CAP,
echo the FULL original input back with textMaxCharacters=CAP (full echo is safe
whether updatedInput merges or replaces) under permissionDecision:"allow".

Fails open on any error. Claude-only — Codex has no updatedInput; wire only in
.claude/settings.json, never .codex. Decision: decisions/2026-06-14-external-agent-appropriation.md
"""
import json
import os
import sys

TOOL = "mcp__exa__web_search_advanced_exa"
CAP = int(os.environ.get("EXA_TEXT_MAX_CHARS", "12000"))  # chars/result; tune down after measuring


def main() -> None:
    try:
        env = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # fail open — never block a tool on a parse error

    if env.get("tool_name") != TOOL:
        sys.exit(0)
    ti = env.get("tool_input")
    if not isinstance(ti, dict):
        sys.exit(0)

    cur = ti.get("textMaxCharacters")
    # Act only when unset OR explicitly larger than the cap. Leave a deliberate
    # smaller value untouched (the agent knows what it wants).
    if isinstance(cur, (int, float)) and not isinstance(cur, bool) and cur <= CAP:
        sys.exit(0)

    new_input = dict(ti)
    new_input["textMaxCharacters"] = CAP
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": (
                f"exa text capped to {CAP} chars/result (context-budget pilot; "
                "decisions/2026-06-14-external-agent-appropriation.md)"
            ),
            "updatedInput": new_input,
        }
    }
    print(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
