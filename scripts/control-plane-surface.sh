#!/usr/bin/env bash
# control-plane-surface.sh — sole SessionStart RSI surface.
# Prints a DIGEST of the fresh (<48h) control-plane inbox: section headings with
# their counts, the stale-drain line, and the first two bullets per section.
# The former full dump was ~43 KB (~11K tokens) on EVERY session start and
# compaction, and no session acted on it (tabula rasa 2026-09-02). Fail-open.
INBOX="$HOME/.claude/control-plane-inbox.md"
[ -f "$INBOX" ] || exit 0
age=$(( ( $(date +%s) - $(stat -f %m "$INBOX" 2>/dev/null || echo 0) ) / 3600 ))
[ "$age" -lt 48 ] || exit 0
echo "▸ agent-infra control plane (${age}h old) — digest; full: $INBOX"
awk -v per=2 '
  /^# /   { next }
  /^## /  { print; n = 0; next }
  /^### / { print "  " $0; n = 0; next }
  /^_→/   { print "  " $0; next }
  /^- /   { if (n < per) { line = $0; if (length(line) > 160) line = substr(line, 1, 157) "…"; print "  " line; n++ }; next }
' "$INBOX" | head -60
exit 0
