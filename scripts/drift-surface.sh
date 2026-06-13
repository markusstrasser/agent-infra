#!/usr/bin/env bash
# drift-surface.sh — SessionStart surface for the drift sentinel's digest.
# Prints the digest to the agent at session start IFF it exists and is fresh
# (<48h). Absent digest = all-green = silent. Stale digest = sentinel hasn't run
# (launchd down) → silent rather than show stale drift. Fail-open, never blocks.
DIGEST="/Users/alien/Projects/agent-infra/.claude/drift-digest.md"
[ -f "$DIGEST" ] || exit 0
age=$(( ( $(date +%s) - $(stat -f %m "$DIGEST" 2>/dev/null || echo 0) ) / 3600 ))
[ "$age" -lt 48 ] || exit 0
echo "▸ agent-infra drift digest (${age}h old) — deterministic self-monitor flagged items:"
cat "$DIGEST"
echo "(triage in a /improve tick; auto-clears when green)"
exit 0
