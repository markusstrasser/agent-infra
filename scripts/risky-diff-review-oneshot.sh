#!/usr/bin/env bash
# One-shot launchd runner for the risky-diff-review SHADOW promote/cut review
# (improvement-log 2026-06-07). Local, zero-API, zero-quota. Idempotent via a
# sentinel; SELF-UNLOADS after running so the StartCalendarInterval (no year
# field) doesn't recur next June.
#
# The detector is git-history-based, so this single run reconstructs the whole
# 2-week window retroactively (scan --days 16 covers 2026-06-07 → 2026-06-21).
# It COMPUTES + SURFACES the report; the promote/cut call stays the human's.
# Replaces a remote-CCR routine, which can't see local git history / the local
# ~/.claude shadow log.
set +e
SENTINEL="$HOME/.claude/risky-diff-review-done"
REPO="$HOME/Projects/agent-infra"
[ -f "$SENTINEL" ] && exit 0   # already ran — do nothing

PY="$REPO/.venv/bin/python3"
[ -x "$PY" ] || PY="python3"

# Capture the full window into the shadow log, then summarize.
"$PY" "$REPO/scripts/risky_diff_review_shadow.py" --days 16 --log >/dev/null 2>&1
REPORT="$("$PY" "$REPO/scripts/risky_diff_review_shadow.py" --report 2>&1)"
echo "$REPORT"

# Surface for the human: append to checkpoint + desktop notification.
{
  echo ""
  echo "## [$(date +%Y-%m-%d)] DECISION NEEDED — risky-diff-review SHADOW promote/cut"
  echo "$REPORT"
  echo ""
  echo "PROMOTE to an auto-review gate (fresh-eyes-review / /critique on risky diffs)"
  echo "only if it fired OFTEN and unreviewed-risky commits correlate with LATER fixes."
  echo "CUT if rare (the live hypothesis — Opus 4.8 self-review-degeneracy did not"
  echo "reproduce, decisions/2026-06-03-verifier-bound-autonomy.md)."
  echo "Calibration caveat: path-based reasons over-flag doc/record edits to"
  echo "governance files vs. real behavior/code changes — weight the genuine ones."
  echo "Detail: \`just risky-diff-report\`; improvement-log [2026-06-07] SHADOW entry."
} >> "$REPO/.claude/checkpoint.md" 2>/dev/null

osascript -e 'display notification "risky-diff-review shadow ready — decide promote/cut (checkpoint.md)" with title "agent-infra"' 2>/dev/null

touch "$SENTINEL"
launchctl bootout "gui/$(id -u)/com.agent-infra.risky-diff-review" 2>/dev/null  # one-shot: never recur
exit 0
