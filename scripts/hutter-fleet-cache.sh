#!/usr/bin/env bash
# Refresh /tmp/hutter-fleet-cache for statusline (hutter project only).
# Parses loop_health output — too heavy for statusline hot path; run async when cache stale.
set -uo pipefail
ROOT="${HOME}/Projects/hutter"
OUT="/tmp/hutter-fleet-cache"
[ -d "$ROOT" ] || exit 0
out=$(cd "$ROOT" && timeout 90 uv run python3 scripts/loop_health.py 2>&1) || exit 0
idle=$(printf '%s\n' "$out" | awk '$3=="IDLE"{c++} END{print c+0}')
busy=$(printf '%s\n' "$out" | awk '$1 ~ /^hutter-x86-box/ && $3!="IDLE" && $3!="UNREACH"{c++} END{print c+0}')
unreach=$(printf '%s\n' "$out" | awk '$3=="UNREACH"{c++} END{print c+0}')
printf '%s|%s|%s|%s\n' "$idle" "$busy" "$unreach" "$(date +%s)" > "$OUT"
