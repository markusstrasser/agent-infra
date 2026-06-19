#!/bin/bash
# refresh-codebase-maps.sh — regenerate per-repo codebase maps (+ summary caches)
# across configured projects (config/codebase-map-repos.json).
set -uo pipefail
export PATH="/Users/alien/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/alien/Projects/agent-infra || exit 1
exec uv run python3 scripts/refresh_all_codebase_maps.py "$@"
