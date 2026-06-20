#!/usr/bin/env bash
# control-plane-surface.sh — sole SessionStart RSI surface.
# Fresh (<48h) control-plane inbox only. Fail-open.
INBOX="$HOME/.claude/control-plane-inbox.md"
[ -f "$INBOX" ] || exit 0
age=$(( ( $(date +%s) - $(stat -f %m "$INBOX" 2>/dev/null || echo 0) ) / 3600 ))
[ "$age" -lt 48 ] || exit 0
echo "▸ agent-infra control plane (${age}h old):"
cat "$INBOX"
exit 0
