#!/usr/bin/env bash
# pretool-terse-bash.sh — Suggest terse command alternatives to reduce token output
# PreToolUse:Bash hook. Advisory only (exit 0, never exit 2).
trap 'exit 0' ERR

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -z "$CMD" ] && exit 0

SUGGESTION=""

# git status without -s/--short
if echo "$CMD" | grep -qE '\bgit\s+status\b'; then
    echo "$CMD" | grep -qE -- '\-[a-zA-Z]*s|--short' || SUGGESTION="Consider 'git status -s' for shorter output"
fi

# git diff without --stat/--name-only/--name-status
if [ -z "$SUGGESTION" ] && echo "$CMD" | grep -qE '\bgit\s+diff\b'; then
    echo "$CMD" | grep -qE -- '--stat|--name-only|--name-status' || SUGGESTION="Consider 'git diff --stat' or '--name-only' for shorter output"
fi

# git log without --oneline/--format/--pretty
if [ -z "$SUGGESTION" ] && echo "$CMD" | grep -qE '\bgit\s+log\b'; then
    echo "$CMD" | grep -qE -- '--oneline|--format|--pretty' || SUGGESTION="Consider 'git log --oneline' for shorter output"
fi

# ls -la or ls -al (but not targeting a specific file)
if [ -z "$SUGGESTION" ] && echo "$CMD" | grep -qE '\bls\s+-(la|al)\b'; then
    echo "$CMD" | grep -qE '\bls\s+-(la|al)\s+\S' || SUGGESTION="Consider bare 'ls' — -la output is verbose"
fi

# pip list/freeze without piping
if [ -z "$SUGGESTION" ] && echo "$CMD" | grep -qE '\bpip\s+(list|freeze)\b'; then
    echo "$CMD" | grep -qE '[|>]' || SUGGESTION="Consider 'pip list --format=columns | head' to limit output"
fi

# cat <file> without piping — suggest Read tool
if [ -z "$SUGGESTION" ] && echo "$CMD" | grep -qE '^\s*cat\s+\S'; then
    echo "$CMD" | grep -qE '[|>]' || SUGGESTION="Use the Read tool instead of cat — it has line numbers and pagination"
fi

# npm list without --depth
if [ -z "$SUGGESTION" ] && echo "$CMD" | grep -qE '\bnpm\s+list\b'; then
    echo "$CMD" | grep -q -- '--depth' || SUGGESTION="Consider 'npm list --depth=0' to limit output"
fi

if [ -n "$SUGGESTION" ]; then
    TRIGGER="$HOME/Projects/skills/hooks/hook-trigger-log.sh"
    [ -x "$TRIGGER" ] && "$TRIGGER" "terse-bash" "suggest" "$(echo "$CMD" | head -c 60)" 2>/dev/null || true
    SAFE=$(echo "$SUGGESTION" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
    echo "{\"additionalContext\": ${SAFE:-\"$SUGGESTION\"}}"
fi
exit 0
