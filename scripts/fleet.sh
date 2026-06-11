#!/usr/bin/env bash
# fleet.sh — one-shot dashboard of all live Claude Code sessions on this machine.
# Composes the statusline's per-agent state files (no API, no DB):
#   /tmp/claude-agent-<pid>      state|project|cost|ctx%|worktree|loop
#   /tmp/claude-tab-tool-<pid>   last tool action
#   /tmp/claude-tab-loop-<pid>   until_epoch|reason|prompt   (armed /loop wakeup)
#   /tmp/claude-tab-prompt-<pid> epoch of last user prompt
#   ~/.claude/sessions/<pid>.json  harness status (busy/idle)
set -uo pipefail

now=$(date +%s)
cutoff=$(( now - 21600 ))  # ignore state older than 6h

bold=$'\033[1m'; dim=$'\033[2m'; reset=$'\033[0m'
yellow=$'\033[33m'; red=$'\033[31m'; green=$'\033[32m'; cyan=$'\033[36m'

fmt_age() {
  local d=$1
  if (( d >= 3600 )); then echo "$((d / 3600))h$(( (d % 3600) / 60 ))m"
  elif (( d >= 60 )); then echo "$((d / 60))m"
  else echo "${d}s"; fi
}

rows=0
printf '%s%-3s %-14s %-10s %-8s %-6s %-5s %-28s %-24s %s%s\n' \
  "$bold" "" "PROJECT" "STATE" "BUSY" "COST" "CTX" "LOOP" "LAST TOOL" "IDLE" "$reset"

for f in /tmp/claude-agent-*; do
  [[ -f "$f" ]] || continue
  pid="${f#/tmp/claude-agent-}"
  [[ "$pid" =~ ^[0-9]+$ ]] || continue
  # Dead process or stale file → skip
  kill -0 "$pid" 2>/dev/null || continue
  fmtime=$(stat -f%m "$f" 2>/dev/null || echo 0)
  (( fmtime < cutoff )) && continue

  IFS='|' read -r state project cost pct wt loop_label < "$f" || true

  # Dot + color by state
  case "${state:-idle}" in
    working)   dot="🔵"; color="$dim" ;;
    attention) dot="🟡"; color="$yellow" ;;
    error)     dot="🔴"; color="$red" ;;
    done)      dot="🟢"; color="$green" ;;
    *)         dot="⚪"; color="$reset" ;;
  esac

  # Harness-level busy/idle (sessions/<pid>.json is the live harness heartbeat)
  busy=$(jq -r '.status // "?"' "$HOME/.claude/sessions/${pid}.json" 2>/dev/null || echo "?")

  # Armed /loop wakeup: show reason + time to fire
  loop_disp="${loop_label:-}"
  lf="/tmp/claude-tab-loop-$pid"
  if [[ -f "$lf" ]]; then
    IFS='|' read -r luntil lreason lprompt < "$lf" || true
    if [[ "${luntil:-0}" =~ ^[0-9]+$ ]] && (( luntil > now )); then
      if (( luntil >= 9999999999 )); then
        loop_disp="🔁 ${lreason:-cron}"
      else
        loop_disp="🔁 ${lreason:-${lprompt:-?}} (+$(fmt_age $(( luntil - now ))))"
      fi
    fi
  fi

  tool=$(/bin/cat "/tmp/claude-tab-tool-$pid" 2>/dev/null | tr '\n' ' ' | sed 's/  */ /g' || echo "")

  idle_age=""
  pf="/tmp/claude-tab-prompt-$pid"
  if [[ -f "$pf" ]]; then
    pt=$(/bin/cat "$pf" 2>/dev/null || echo 0)
    [[ "$pt" =~ ^[0-9]+$ ]] && (( pt > 0 )) && idle_age=$(fmt_age $(( now - pt )))
  fi

  proj_disp="$project"
  [[ -n "${wt:-}" ]] && proj_disp="${project}@${wt}"

  printf '%s %s%-14.14s %-10s %-8s %-6s %-5s %-28.28s %-24.24s %s%s\n' \
    "$dot" "$color" "$proj_disp" "${state:-idle}" "$busy" "$cost" "${pct}%" \
    "${loop_disp:--}" "${tool:--}" "${idle_age:--}" "$reset"
  (( rows++ )) || true
done

if (( rows == 0 )); then
  echo "${dim}no live Claude sessions found (state files in /tmp/claude-agent-*)${reset}"
else
  echo
  echo "${dim}🔵 working · 🟡 needs input · 🔴 error · 🟢 done · ⚪ idle · 🔁 armed loop · BUSY = harness heartbeat${reset}"
fi
