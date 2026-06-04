#!/bin/bash
# refresh-codebase-maps.sh — regenerate per-repo codebase maps (+ summary caches)
# across the 5 indexed projects.
#
# Zero-API: repo-summary runs with --no-llm (descriptions from AST/docstrings,
# cached in ~/.cache/repo-summary, OUTSIDE the repos — no git churn).
# Idempotent: codebase-map.py skips no-op writes (only the date would change),
# so a repo whose code is unchanged is NOT dirtied.
#
# Single source of truth for the refresh. Invoked by:
#   - `just refresh-maps`                                   (interactive)
#   - com.agent-infra.codebase-map-refresh launchd job      (daily ~06:30, local)
# Supersedes pipelines/repo-index-refresh.json — the orchestrator that ran it was
# archived 2026-04-24, which is why the maps drifted stale.
set -uo pipefail
export PATH="/Users/alien/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/alien/Projects/agent-infra || exit 1

fail=0
run() {
  echo "▸ $*"
  if ! uv run python3 "$@"; then
    echo "  ✗ failed: $*"
    fail=1
  fi
}

echo "[summaries] --no-llm (zero-API), cache in ~/.cache/repo-summary"
run scripts/repo-summary.py "$HOME/Projects/agent-infra/scripts" --refresh --no-llm
run scripts/repo-summary.py "$HOME/Projects/intel/tools"          --refresh --no-llm --compact
run scripts/repo-summary.py "$HOME/Projects/research-mcp/src"     --refresh --no-llm
run scripts/repo-summary.py "$HOME/Projects/genomics"            --refresh --no-llm --compact
run scripts/repo-summary.py "$HOME/Projects/phenome/scripts"     --refresh --no-llm
run scripts/repo-summary.py "$HOME/Projects/phenome/src"         --refresh --no-llm

echo "[maps] idempotent (writes only on real change)"
run scripts/codebase-map.py "$HOME/Projects/agent-infra" --source-dirs scripts
run scripts/codebase-map.py "$HOME/Projects/intel"       --source-dirs tools,analysis
run scripts/codebase-map.py "$HOME/Projects/research-mcp" --source-dirs src
run scripts/codebase-map.py "$HOME/Projects/genomics"    --source-dirs scripts
run scripts/codebase-map.py "$HOME/Projects/phenome"     --source-dirs scripts,src

echo "[done] fail=$fail"
exit $fail
