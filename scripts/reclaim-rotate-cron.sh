#!/usr/bin/env bash
#
# reclaim-rotate-cron — nightly retention for the UNBOUNDED local stores that
# the cache subcommands don't touch. Loaded by com.agent-infra.reclaim-rotate
# at 04:10, deliberately in the quiet window:
#   - `uv cache prune` is a no-op while agents hold the cache lock (confirmed
#     2026-06-10: prune freed 0 with 9 live `uv` procs). 04:10 is the best shot
#     at an uncontended run.
#   - `reclaim rotate` (agentlogs.db prune) takes the indexer single-writer
#     lock; the 2h indexer is least likely to be mid-run at night.
# Codex sessions are intentionally NOT rotated (only copy, not re-derivable).
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin"
LOG="$HOME/.cache/reclaim/rotate-cron.log"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
{
  printf '\n===== %s =====\n' "$(date '+%F %T')"
  "$HOME/.local/bin/reclaim" rotate --yes
  printf -- '--- uv cache prune ---\n'
  "$HOME/.local/bin/uv" cache prune
} >> "$LOG" 2>&1
