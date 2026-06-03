#!/usr/bin/env bash
# One-shot launchd runner for the reflect-loop 2-week evaluation (plan 4d40085a).
# Local, zero-API. Idempotent via a sentinel; SELF-UNLOADS after running so the
# StartCalendarInterval (which has no year field) doesn't recur next June. It
# COMPUTES metrics + runs the classify pass and SURFACES results — go/cut and any
# omission-surface enablement remain the human's call.
set +e
SENTINEL="$HOME/.claude/reflect-eval-done"
REPO="$HOME/Projects/agent-infra"
[ -f "$SENTINEL" ] && exit 0   # already ran — do nothing

PY="$REPO/.venv/bin/python3"
[ -x "$PY" ] || PY="python3"
REPORT="$("$PY" "$REPO/scripts/reflect_eval.py" --report 2>&1)"
echo "$REPORT"

# Surface for the human: append to checkpoint + desktop notification.
{
  echo ""
  echo "## [$(date +%Y-%m-%d)] DECISION NEEDED — reflect-loop 2-week evaluation"
  echo "$REPORT" | sed -n '1,22p'
  echo "Full report: artifacts/reflect-eval/$(date +%Y-%m-%d).md — decide go/cut per plan 4d40085a."
} >> "$REPO/.claude/checkpoint.md" 2>/dev/null

osascript -e 'display notification "reflect-loop 2-week eval ready — decide go/cut (checkpoint.md)" with title "agent-infra"' 2>/dev/null

touch "$SENTINEL"
launchctl bootout "gui/$(id -u)/com.agent-infra.reflect-eval" 2>/dev/null  # one-shot: never recur
exit 0
