#!/usr/bin/env bash
#
# reclaim-rotate-cron — nightly uv cache prune in the 04:10 quiet window
# (`uv cache prune` is a no-op while agents hold the cache lock; confirmed
# 2026-06-10: prune freed 0 with 9 live `uv` procs).
#
# agentlogs.db retention REMOVED 2026-07-14: single owner is the weekly
# snapshot-gated `just agentlogs-archive` (keep-everything-via-archive,
# decision 2026-07-05). The nightly ungated 21d prune here silently overrode
# the operator's 30d retention and churned FTS-rebuild+VACUUM on 10GB nightly.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin"
LOG="$HOME/.cache/reclaim/rotate-cron.log"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
{
  printf '\n===== %s =====\n' "$(date '+%F %T')"
  "$HOME/.local/bin/uv" cache prune
} >> "$LOG" 2>&1
