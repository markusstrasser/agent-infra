#!/usr/bin/env bash
# fleet.sh — view live Claude Code sessions on this machine.
#   fleet.sh                 one-shot roster of all live sessions (default)
#   fleet.sh watch [filters] roster snapshot, then a live filtered event stream
#
# Composes the statusline's per-agent state files (no API, no DB):
#   /tmp/claude-agent-<pid>      state|project|cost|ctx%|worktree|loop
#   /tmp/claude-tab-tool-<pid>   last tool action
#   /tmp/claude-tab-loop-<pid>   until_epoch|reason|prompt   (armed /loop wakeup)
#   /tmp/claude-tab-prompt-<pid> epoch of last user prompt
#   ~/.claude/sessions/<pid>.json  harness status (busy/idle)
# watch mode tails the cross-repo event firehose: ~/.claude/event-log.jsonl
#   (fields: ts, project, hook, tool, action, detail, session)
set -uo pipefail

bold=$'\033[1m'; dim=$'\033[2m'; reset=$'\033[0m'
yellow=$'\033[33m'; red=$'\033[31m'; green=$'\033[32m'; cyan=$'\033[36m'

fmt_age() {
  local d=$1
  if (( d >= 3600 )); then echo "$((d / 3600))h$(( (d % 3600) / 60 ))m"
  elif (( d >= 60 )); then echo "$((d / 60))m"
  else echo "${d}s"; fi
}

render_roster() {
  local now cutoff rows=0
  now=$(date +%s)
  cutoff=$(( now - 21600 ))  # ignore state older than 6h

  printf '%s%-3s %-14s %-10s %-8s %-6s %-5s %-28s %-24s %s%s\n' \
    "$bold" "" "PROJECT" "STATE" "BUSY" "COST" "CTX" "LOOP" "LAST TOOL" "IDLE" "$reset"

  local f pid fmtime state project cost pct wt loop_label dot color busy
  local loop_disp lf luntil lreason lprompt tool idle_age pf pt proj_disp
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
}

watch_usage() {
  cat >&2 <<'EOF'
fleet.sh watch — roster snapshot, then a live filtered event stream (Ctrl-C to stop).
  --project P      only events from project P (exact)
  --hook REGEX     only hooks matching REGEX
  --tool  T        only events with tool == T (exact; note: failures often record the
                   tool in `detail`, not `tool` — use --detail there)
  --detail REGEX   only events whose detail matches REGEX
  --errors-only    only action==block or hook==tool-failure
Source: ~/.claude/event-log.jsonl (local agent firehose, all repos). Does NOT include
Modal-cloud launches or remote SSH-box dispatches — those live in separate streams.
EOF
}

watch_stream() {
  local proj="" hook_re="" tool="" detail_re="" errors_only=0
  while (( $# )); do
    case "$1" in
      --project) proj="${2:-}"; shift 2 ;;
      --hook)    hook_re="${2:-}"; shift 2 ;;
      --tool)    tool="${2:-}"; shift 2 ;;
      --detail)  detail_re="${2:-}"; shift 2 ;;
      --errors-only) errors_only=1; shift ;;
      -h|--help) watch_usage; return 0 ;;
      *) echo "fleet watch: unknown argument '$1'" >&2; watch_usage; return 2 ;;
    esac
  done

  command -v jq >/dev/null 2>&1 || { echo "fleet watch: jq is required" >&2; return 1; }
  local log="$HOME/.claude/event-log.jsonl"
  [[ -f "$log" ]] || { echo "fleet watch: no event log at $log" >&2; return 1; }

  render_roster
  echo
  echo "${dim}── live events (Ctrl-C to stop) — TIME PROJECT HOOK ACTION TOOL DETAIL ──${reset}"

  # tail -n 0  → live only, no startup backlog
  # jq -R + fromjson?//empty → survive partial/corrupt lines (never exit)
  # --unbuffered → real-time; regexes via --arg → no shell injection; // "" → no null crash
  tail -n 0 -F "$log" 2>/dev/null | jq -Rr --unbuffered \
    --arg p "$proj" --arg h "$hook_re" --arg t "$tool" --arg d "$detail_re" \
    --argjson eo "$errors_only" '
    def pad($n): (tostring | .[:$n]) as $s | $s + ((" " * ($n - ($s|length))) // "");
    fromjson? // empty
    | select($p == "" or .project == $p)
    | select($h == "" or ((.hook // "") | test($h)))
    | select($t == "" or (.tool // "") == $t)
    | select($d == "" or ((.detail // "") | test($d)))
    | select($eo == 0 or ((.action // "") == "block" or (.hook // "") == "tool-failure"))
    | ((.ts // "")[11:19]) + "  "
      + ((.project // "") | pad(12)) + " "
      + ((.hook // "-") | pad(18)) + " "
      + ((.action // "-") | pad(6)) + " "
      + ((.tool // "-") | pad(10)) + " "
      + ((.detail // "") | gsub("[[:cntrl:]]"; " ") | .[0:50])'
}

main() {
  case "${1:-}" in
    ""|roster) render_roster ;;
    watch)     shift; watch_stream "$@" ;;
    -h|--help)
      echo "usage: fleet.sh [roster | watch [filters]]   (default: roster)" >&2
      watch_usage ;;
    *) echo "fleet.sh: unknown command '$1' (try: roster | watch)" >&2; exit 2 ;;
  esac
}

main "$@"
