#!/usr/bin/env bash
# blindspot-surface.sh — SessionStart surface for the RSI blindspot miner's digest.
# Shows the summary + top few misses the human had to catch (NOT the whole digest —
# context budget); points at the full file. Fresh (<48h) only: a stale digest means
# the miner (launchd) is down → silent rather than show stale. Fail-open, never blocks.
DIGEST="/Users/alien/Projects/agent-infra/.claude/blindspot-digest.md"
[ -f "$DIGEST" ] || exit 0
age=$(( ( $(date +%s) - $(stat -f %m "$DIGEST" 2>/dev/null || echo 0) ) / 3600 ))
[ "$age" -lt 48 ] || exit 0
echo "▸ agent-infra blindspot digest (${age}h old) — loop misses the human had to catch (RSI signal). Convert recurring clusters to detectors. Full: .claude/blindspot-digest.md"
# summary line + by-project + top 6 flags only
sed -n '3,5p' "$DIGEST"
grep '^- ' "$DIGEST" | head -6
exit 0
