#!/usr/bin/env bash
# Cursor Agent CLI statusline — same pilot HUD grammar as Claude Code.
set -euo pipefail

COCKPIT_DIR="$(python3 -c "import os; print(os.path.dirname(os.path.realpath(os.path.expanduser('${BASH_SOURCE[0]}'))))")"
# shellcheck source=/dev/null
source "$COCKPIT_DIR/cockpit_common.sh"

input=$(cat)
now=$(date +%s)

model=$(echo "$input" | jq -r '.model.display_name // .model.id // "Cursor"')
pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
ctx_size=$(echo "$input" | jq -r '.context_window.context_window_size // 200000' | cut -d. -f1)
session_id=$(echo "$input" | jq -r '.session_id // ""')
workspace=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // "."')
render_w=$(echo "$input" | jq -r '.render_width_chars // empty' 2>/dev/null)
[[ -z "$render_w" || "$render_w" == "null" ]] && render_w=$(tput cols 2>/dev/null || echo 120)
rate_5h=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty' 2>/dev/null)
rate_7d=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty' 2>/dev/null)

project=$(basename "$workspace")
pct_int=${pct:-0}
current_tokens=$(( pct_int * ctx_size / 100 ))

reset='\033[0m'; dim='\033[2m'; bold='\033[1m'
cyan='\033[36m'; yellow='\033[33m'; red='\033[31m'; green='\033[32m'
if (( pct_int > 80 )); then ctx_color='\033[1;31m'
elif (( pct_int > 50 )); then ctx_color='\033[1;33m'
else ctx_color='\033[32m'; fi

filled=$(( pct_int / 10 )); empty=$(( 10 - filled ))
bar=""; (( filled > 0 )) && bar=$(printf '%0.s▓' $(seq 1 $filled))
(( empty > 0 )) && bar+=$(printf '%0.s░' $(seq 1 $empty))
in_k=$(cockpit_fmt_k "$current_tokens")
ctx_k=$(cockpit_fmt_k "$ctx_size")

tab_state="working"
[[ -f "/tmp/cursor-tab-state-$PPID" ]] && tab_state=$(cat "/tmp/cursor-tab-state-$PPID" 2>/dev/null || echo "working")
attn_tag=$(cockpit_attn_tag "$PPID" "$tab_state" "$pct_int")
case "$tab_state" in
  attention) state_glyph="◆"; state_color="$yellow" ;;
  error)     state_glyph="▲"; state_color="$red" ;;
  done)      state_glyph="●"; state_color="$green" ;;
  *)         state_glyph="◐"; state_color="$dim"; tab_state="working" ;;
esac

cockpit_loop_read "$PPID" "$now"
cockpit_prompt_idle "$PPID" "$now"
elapsed=""; (( COCKPIT_IDLE_SECS > 0 )) && elapsed=$(cockpit_fmt_age "$COCKPIT_IDLE_SECS")
cockpit_write_agent_state "cursor" "$PPID" "$tab_state" "$project" "—" "$pct_int" "" "${COCKPIT_LOOP_LABEL:-}"
cockpit_scan_aggregate "$PPID" "$now"

attn_disp=""; [[ -n "$attn_tag" ]] && attn_disp="${yellow}${attn_tag}${reset} "
left="${state_color}${state_glyph}${reset} ${attn_disp}${dim}◇${reset} ${bold}${project}${reset}"
left+=" ${dim}·${reset} ${ctx_color}${bar} ${pct_int}%${reset} ${dim}${in_k}/${ctx_k}${reset}"
(( pct_int > 80 )) && left+=" ${bold}${red}→/compact${reset}"
[[ -n "$elapsed" ]] && left+=" ${dim}${elapsed}${reset}"

right=$(cockpit_rate_limits_ansi "$rate_5h" "$rate_7d" "$dim" "$yellow" "$red" "$reset")
if [[ -n "$right" ]]; then cockpit_print_lr "$left" "$right" "$render_w"; else printf '%b' "$left"; fi
echo

parts=()
[[ -n "$COCKPIT_LOOP_BADGE" ]] && parts+=("${COCKPIT_LOOP_BADGE} ${cyan}${COCKPIT_LOOP_LABEL}${reset}")
cockpit_postcompact "$session_id" "$now" && parts+=("${yellow}↺compact${reset}")
dirty=$(cockpit_git_dirty "$workspace" "$now")
(( dirty > 0 )) && parts+=("${yellow}git:${dirty}${reset}")
cockpit_hutter_fleet "$project" "$now"
[[ -n "$COCKPIT_HUTTER" ]] && parts+=("${dim}fleet:${COCKPIT_HUTTER}${reset}")
if (( COCKPIT_AGG_ATTENTION > 0 || COCKPIT_AGG_WORKING > 0 )); then
  parts+=("${dim}others:${reset} [${COCKPIT_AGG_ATTENTION}◆ ${COCKPIT_AGG_WORKING}◐]")
fi
(( ${#parts[@]} > 0 )) && printf '%b\n' " $(cockpit_truncate_line "$(cockpit_join_parts "$dim" "$reset" "${parts[@]}")" "$render_w")"

if ! cockpit_tab_disabled; then
  tab="$(cockpit_tab_emoji "$tab_state" 0) ${project} · ${pct_int}%"
  attn_title=$(cockpit_attn_title "$attn_tag")
  [[ -n "$attn_title" ]] && tab="$(cockpit_tab_emoji "$tab_state" 0) ${project} · ${attn_title} · ${pct_int}%"
  cockpit_ghostty_title "$tab"
fi
