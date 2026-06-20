#!/usr/bin/env bash
# pulse-tick.sh — launchd entry for the unified RSI motor.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec uv run python3 "$REPO/scripts/pulse.py" tick "$@"
