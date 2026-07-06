#!/usr/bin/env bash
# spend-alarm.sh — periodic metered-spend alarm (option B of the spend-block build).
#
# Runs usage-check.py --metered-today --alarm $CAP over the funnel ledger
# (~/.claude/llmx-usage.jsonl). On breach (usage-check exits 1) it fires a macOS
# notification so an over-cap day is visible even between doctor.py runs. This is
# the SAFETY NET behind the in-llmx hard block (spend_guard): the block prevents
# the NEXT metered call, this alarm catches spend already accrued by a long job
# that started under the cap.
#
# Native-First: launchd (StartInterval) is the scheduled-execution primitive; this
# is the thin wrapper that turns usage-check's exit-1 into an operator-visible alarm.
#
# Anchor: agent-infra decisions/2026-06-25-metered-spend-funnel-enforcement.md.
set -uo pipefail

CAP="${SPEND_ALARM_CAP:-25}"
REPO="$HOME/Projects/agent-infra"
LOG="$HOME/.claude/logs/spend-alarm.log"
mkdir -p "$(dirname "$LOG")"

cd "$REPO" || exit 0
JSON="$(uv run python3 scripts/usage-check.py --metered-today --alarm "$CAP" --json 2>/dev/null)"
STATUS=$?
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Pull the total for the log line (best-effort; python is available under uv).
# Shell double-quotes, python single-quotes → no nested-quote escaping.
TOTAL="$(printf '%s' "$JSON" | uv run python3 -c "import sys,json;print('%.2f'%json.load(sys.stdin).get('metered_total_usd',0))" 2>/dev/null || echo "?")"

if [ "$STATUS" -eq 1 ]; then
    MSG="Metered llmx spend \$$TOTAL today >= \$$CAP cap. Hard block active in llmx; set LLMX_SPEND_OVERRIDE=1 only for an intended large job."
    osascript -e "display notification \"$MSG\" with title \"llmx spend cap\" sound name \"Basso\"" >/dev/null 2>&1 || true
    echo "$TS ALARM metered=\$$TOTAL cap=\$$CAP" >> "$LOG"
else
    echo "$TS ok metered=\$$TOTAL cap=\$$CAP" >> "$LOG"
fi
exit 0
