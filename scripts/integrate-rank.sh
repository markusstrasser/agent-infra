#!/usr/bin/env bash
# integrate-rank.sh — daily RSI sensor synthesis → research/YYYY-MM-DD-auto-integration-rank.md
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec uv run python3 "$REPO/scripts/sensor_integration_ranking.py" "$@"
