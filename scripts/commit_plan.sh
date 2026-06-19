#!/usr/bin/env bash
# commit_plan.sh — cluster diff → plan; deterministic apply
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec uv run python3 "$REPO/scripts/commit_plan.py" --repo "$REPO" "$@"
