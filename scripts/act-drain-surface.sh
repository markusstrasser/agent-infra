#!/usr/bin/env bash
# act-drain-surface.sh — SessionStart surface for the ACT drain digest.
# Fresh (<48h) only; absent digest = all green = silent. Fail-open.
DIGEST="$HOME/.claude/act-drain-digest.md"
[ -f "$DIGEST" ] || exit 0
age=$(( ( $(date +%s) - $(stat -f %m "$DIGEST" 2>/dev/null || echo 0) ) / 3600 ))
[ "$age" -lt 48 ] || exit 0
echo "▸ agent-infra ACT drain (${age}h old) — disposition queue needs attention:"
cat "$DIGEST"
exit 0
