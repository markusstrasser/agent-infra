#!/usr/bin/env bash
# priorities-surface.sh — SessionStart surface for the loop's Top-N priorities.
# Prints PRIORITIES.md at session start IFF it's fresh (<24h), so the ranked
# "what to plan next" digest shows up in sessions that ALREADY happen — with zero
# dependence on a human typing /loop. This is the demand-test's load-bearing
# insight (decisions 2026-06-12-demand-test-the-conductor, resolved 2026-06-14):
# surface where attention already is, don't wait for the conductor to be invoked.
# Stale digest = loop + daily regen both down → silent rather than show stale.
# Fail-open, never blocks.
PRIO="/Users/alien/Projects/agent-infra/PRIORITIES.md"
[ -f "$PRIO" ] || exit 0
age=$(( ( $(date +%s) - $(stat -f %m "$PRIO" 2>/dev/null || echo 0) ) / 3600 ))
[ "$age" -lt 24 ] || exit 0
echo "▸ agent-infra top priorities (${age}h old) — ranked 'what to plan next' (full: PRIORITIES.md):"
cat "$PRIO"
exit 0
