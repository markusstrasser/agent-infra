#!/usr/bin/env bash
# cockpit_common.sh — shared Ghostty/cockpit helpers (Claude, Codex, Cursor).
[[ -n "${COCKPIT_COMMON_LOADED:-}" ]] && return 0
COCKPIT_COMMON_LOADED=1

COCKPIT_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cockpit_tab_disabled() {
  local conf="$HOME/.claude/cockpit.conf"
  [[ -f "$conf" ]] && [[ "$(grep "^tab_colors=" "$conf" 2>/dev/null | head -1 | cut -d= -f2-)" == "off" ]]
}

cockpit_fmt_k() {
  local n=${1:-0}
  (( n >= 1000 )) && echo "$((n / 1000))K" || echo "$n"
}

cockpit_fmt_age() {
  local s=${1:-0}
  if (( s >= 3600 )); then echo "$((s / 3600))h$(( (s % 3600) / 60 ))m"
  elif (( s >= 60 )); then echo "$((s / 60))m"
  else echo "${s}s"; fi
}

cockpit_vis_len() {
  local n
  n=$(printf '%b' "$1" | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g' | wc -c | tr -d ' ')
  echo "$(( n > 0 ? n - 1 : 0 ))"
}

cockpit_print_lr() {
  local left="$1" right="$2" width="${3:-0}"
  local llen rlen pad
  llen=$(cockpit_vis_len "$left")
  rlen=$(cockpit_vis_len "$right")
  if (( width <= 0 )); then
    width=$(tput cols 2>/dev/null || echo 120)
  fi
  pad=$(( width - llen - rlen ))
  (( pad < 1 )) && pad=1
  printf '%b%*s%b' "$left" "$pad" "" "$right"
}

cockpit_attn_tag() {
  local pid="$1" state="$2" pct="${3:-0}"
  if [[ "$state" == "error" ]]; then echo "fail"; return; fi
  if [[ -f "/tmp/claude-tab-perm-$pid" ]]; then echo "perm"; return; fi
  if [[ "$state" == "attention" ]]; then
    local ev=""
    ev=$(cat "/tmp/claude-last-notify-$pid" 2>/dev/null || true)
    [[ "$ev" == "needs_input" ]] && echo "input" && return
    echo "input"; return
  fi
  if (( pct > 80 )); then echo "ctx"; fi
}

cockpit_loop_read() {
  local pid="$1" now="$2"
  COCKPIT_LOOP_BADGE=""; COCKPIT_LOOP_LABEL=""; COCKPIT_LOOP_COUNTDOWN=""
  local lf="/tmp/claude-tab-loop-$pid"
  [[ -f "$lf" ]] || return 0
  local loop_until loop_reason loop_prompt
  IFS='|' read -r loop_until loop_reason loop_prompt < "$lf" || true
  [[ "${loop_until:-0}" =~ ^[0-9]+$ ]] || return 0
  (( loop_until > now )) || return 0
  COCKPIT_LOOP_BADGE="🔁"
  COCKPIT_LOOP_LABEL="${loop_reason:-$loop_prompt}"
  COCKPIT_LOOP_LABEL="${COCKPIT_LOOP_LABEL:0:32}"
  if (( loop_until < 9999999999 )); then
    COCKPIT_LOOP_COUNTDOWN=$(cockpit_fmt_age $(( loop_until - now )))
  fi
}

cockpit_prompt_idle() {
  local pid="$1" now="$2"
  COCKPIT_IDLE_SECS=0
  local pf="/tmp/claude-tab-prompt-$pid"
  [[ -f "$pf" ]] || return 0
  local pt
  pt=$(cat "$pf" 2>/dev/null || echo 0)
  [[ "$pt" =~ ^[0-9]+$ ]] && (( pt > 0 )) && COCKPIT_IDLE_SECS=$(( now - pt ))
}

cockpit_git_dirty() {
  local ws="$1" now="$2"
  local hash cache
  hash=$(printf '%s' "$ws" | shasum | cut -c1-8)
  cache="/tmp/cockpit-git-dirty-$hash"
  if [[ -f "$cache" ]] && (( now - $(stat -f%m "$cache" 2>/dev/null || echo 0) < 12 )); then
    cat "$cache"; return
  fi
  local n
  n=$(git -C "$ws" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  echo "${n:-0}" > "$cache"
  echo "${n:-0}"
}

cockpit_postcompact() {
  local sid="$1" now="$2"
  [[ -n "$sid" ]] || return 1
  local f="/tmp/claude-postcompact-$sid"
  [[ -f "$f" ]] || return 1
  local ts
  ts=$(cat "$f" 2>/dev/null || echo 0)
  [[ "$ts" =~ ^[0-9]+$ ]] && (( now - ts < 1800 ))
}

cockpit_hutter_fleet() {
  local project="$1" now="$2"
  COCKPIT_HUTTER=""
  [[ "$project" == "hutter" ]] || return 0
  local cache_f="/tmp/hutter-fleet-cache" refresh_lock="/tmp/hutter-fleet-cache.refresh"
  if [[ -f "$cache_f" ]]; then
    local ts idle busy unreach
    IFS='|' read -r idle busy unreach ts < "$cache_f" || true
    if [[ "${ts:-0}" =~ ^[0-9]+$ ]] && (( now - ts < 180 )); then
      if (( idle > 0 )); then COCKPIT_HUTTER="${idle}idle"
      elif (( unreach > 0 )); then COCKPIT_HUTTER="${unreach}unreach"
      else COCKPIT_HUTTER="${busy:-0}busy"; fi
      return 0
    fi
  fi
  if [[ ! -f "$refresh_lock" ]] || (( now - $(stat -f%m "$refresh_lock" 2>/dev/null || echo 0) > 300 )); then
    touch "$refresh_lock" 2>/dev/null || true
    ( bash "$COCKPIT_COMMON_DIR/hutter-fleet-cache.sh"; rm -f "$refresh_lock" ) &>/dev/null &
  fi
}

cockpit_rate_limits_ansi() {
  local r5="$1" r7="$2" dim="$3" yellow="$4" red="$5" reset="$6"
  local parts=() col
  if [[ -n "$r5" && "$r5" != "null" ]]; then
    local v=${r5%.*}
    if (( v > 80 )); then col="$red"
    elif (( v > 50 )); then col="$yellow"
    else col="$dim"; fi
    parts+=("${col}5h ${v}%${reset}")
  fi
  if [[ -n "$r7" && "$r7" != "null" ]]; then
    local v=${r7%.*}
    if (( v > 90 )); then col="$red"
    elif (( v > 70 )); then col="$yellow"
    else col="$dim"; fi
    parts+=("${col}7d ${v}%${reset}")
  fi
  (IFS=' · '; echo "${parts[*]}")
}

cockpit_scan_aggregate() {
  local mypid="$1" now="$2"
  COCKPIT_AGG_WORKING=0 COCKPIT_AGG_ATTENTION=0 COCKPIT_AGG_ERROR=0
  COCKPIT_AGG_ATT_NAMES=() COCKPIT_AGG_ERR_NAMES=()
  local cutoff=$(( now - 21600 )) f fname fpid fmtime astate aproj
  for f in /tmp/claude-agent-* /tmp/cockpit-agent-*; do
    [[ -f "$f" ]] || continue
    fname=$(basename "$f")
    if [[ "$fname" == claude-agent-* ]]; then fpid="${fname#claude-agent-}"
    else fpid="${fname##*-}"; fi
    [[ "$fpid" =~ ^[0-9]+$ ]] || continue
    [[ "$fpid" == "$mypid" ]] && continue
    kill -0 "$fpid" 2>/dev/null || { rm -f "$f" 2>/dev/null; continue; }
    fmtime=$(stat -f%m "$f" 2>/dev/null || echo 0)
    (( fmtime < cutoff )) && continue
    astate=$(cut -d'|' -f1 "$f" 2>/dev/null || echo "idle")
    aproj=$(cut -d'|' -f2 "$f" 2>/dev/null || echo "?")
    case "$astate" in
      working)   (( COCKPIT_AGG_WORKING++ )) || true ;;
      attention) (( COCKPIT_AGG_ATTENTION++ )) || true; COCKPIT_AGG_ATT_NAMES+=("$aproj") ;;
      error)     (( COCKPIT_AGG_ERROR++ )) || true; COCKPIT_AGG_ERR_NAMES+=("$aproj") ;;
    esac
  done
}

cockpit_write_agent_state() {
  local vendor="$1" pid="$2" state="$3" project="$4" cost="$5" pct="$6" wt="$7" loop="$8"
  echo "${state:-idle}|${project}|${cost}|${pct}|${wt}|${loop}|${vendor}" > "/tmp/cockpit-agent-${vendor}-${pid}" 2>/dev/null || true
  echo "${state:-idle}|${project}|${cost}|${pct}|${wt}|${loop}" > "/tmp/claude-agent-${pid}" 2>/dev/null || true
}

cockpit_tab_emoji() {
  local state="$1" cost_alert="${2:-0}"
  if [[ "$cost_alert" == "1" && "$state" != "attention" && "$state" != "error" ]]; then
    echo "🟠"; return
  fi
  case "$state" in
    working)   echo "🔵" ;;
    attention) echo "🟡" ;;
    error)     echo "🔴" ;;
    done)      echo "🟢" ;;
    *)         echo "⚪" ;;
  esac
}

cockpit_truncate_line() {
  python3 - "$1" "$2" <<'PY'
import re, sys
line, w = sys.argv[1], int(sys.argv[2])
plain = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
if len(plain) <= w:
    sys.stdout.write(line)
else:
    sys.stdout.write(plain[: max(0, w - 1)] + '…')
PY
}

cockpit_attn_title() {
  case "$1" in
    input) echo "NEEDS INPUT" ;;
    perm)  echo "PERM" ;;
    ctx)   echo "CTX" ;;
    fail)  echo "ERROR" ;;
    *)     echo "" ;;
  esac
}

cockpit_agent_pid() {
  echo "${COCKPIT_AGENT_PID:-${CLAUDE_PID:-$PPID}}"
}

cockpit_ghostty_title() {
  local title="$1"
  local apid tty_dev
  apid=$(cockpit_agent_pid)
  tty_dev="${COCKPIT_TTY:-}"
  if [[ -z "$tty_dev" && -n "${TTY:-}" && "${TTY}" != "?" && "${TTY}" != "not a tty" ]]; then
    tty_dev="/dev/${TTY#\/dev/}"
  fi
  # Never test -w /dev/tty (can block); attempt write and fail fast.
  if [[ -n "$tty_dev" ]]; then
    printf '\033]2;%s\007' "$title" > "$tty_dev" 2>/dev/null || true
  else
    printf '\033]2;%s\007' "$title" > /dev/tty 2>/dev/null || true
  fi
  # Codex hooks lack a tty — shim flushes this file post-hook.
  [[ -n "$apid" ]] && printf '%s' "$title" > "/tmp/cockpit-tab-pending-${apid}" 2>/dev/null || true
}

cockpit_join_parts() {
  local dim="$1" reset="$2"
  shift 2
  local line="" part
  for part in "$@"; do
    [[ -z "$part" ]] && continue
    [[ -n "$line" ]] && line+=" ${dim}·${reset} "
    line+="$part"
  done
  printf '%b' "$line"
}
