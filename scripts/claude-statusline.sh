#!/usr/bin/env bash
# Claude Code statusline — pilot HUD + Ghostty tab title.
# Line 1: steer signals · cost · context · tool · elapsed ········· 5h% · 7d%
# Line 2: loop · compact · git · fleet · others (width-capped — no wrap garbage)
set -euo pipefail

COCKPIT_DIR="$(python3 -c "import os; print(os.path.dirname(os.path.realpath(os.path.expanduser('${BASH_SOURCE[0]}'))))")"
# shellcheck source=/dev/null
source "$COCKPIT_DIR/cockpit_common.sh"

input=$(cat)
now=$(date +%s)

model=$(echo "$input" | jq -r '.model.display_name // "?"')
cost=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
duration_ms=$(echo "$input" | jq -r '.cost.total_duration_ms // 0' | cut -d. -f1)
session_id=$(echo "$input" | jq -r '.session_id // ""')
effort=$(echo "$input" | jq -r '.effort.level // ""')
fast_mode=$(echo "$input" | jq -r '.fast_mode // false')
bg_tasks=$(echo "$input" | jq -r '.background_tasks | length // 0' 2>/dev/null || echo 0)
subagent_n=$(echo "$input" | jq -r '.subagents | length // 0' 2>/dev/null || echo 0)
cron_n=$(echo "$input" | jq -r '.session_crons | length // 0' 2>/dev/null || echo 0)
workspace=$(echo "$input" | jq -r '.workspace.current_dir // "."')
git_worktree=$(echo "$input" | jq -r '.workspace.git_worktree // ""')
ctx_size=$(echo "$input" | jq -r '.context_window.context_window_size // 200000' | cut -d. -f1)
lines_add=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
lines_rm=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')
total_out=$(echo "$input" | jq -r '.context_window.total_output_tokens // 0' | cut -d. -f1)
rate_5h=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty' 2>/dev/null)
rate_7d=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty' 2>/dev/null)
render_w=$(echo "$input" | jq -r '.render_width_chars // empty' 2>/dev/null)
[[ -z "$render_w" || "$render_w" == "null" ]] && render_w=$(tput cols 2>/dev/null || echo 120)

project=$(basename "$workspace")
pct_int=${pct:-0}
current_tokens=$(( pct_int * ctx_size / 100 ))

CONF="$HOME/.claude/cockpit.conf"
# shellcheck disable=SC1090
[[ -f "$CONF" ]] && source "$CONF" 2>/dev/null || true

# --- effort (abbrev) ---
effort_tag=""
[[ "$fast_mode" == "true" ]] && effort_tag="fast"
if [[ -z "$effort_tag" && -n "$effort" ]]; then
  case "$effort" in medium) effort_tag="med" ;; *) effort_tag="$effort" ;; esac
fi

# --- branch / worktree ---
branch_tag=""
if [[ -n "$git_worktree" ]]; then
  branch_tag="wt:$(basename "$git_worktree") "
else
  cache="/tmp/statusline-git-cache-$project"
  branch=""
  if [[ -f "$cache" ]] && (( now - $(stat -f%m "$cache" 2>/dev/null || echo 0) < 8 )); then
    branch=$(cat "$cache")
  else
    branch=$(git -C "$workspace" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "—")
    echo "$branch" > "$cache" 2>/dev/null || true
  fi
  [[ "$branch" != "main" && "$branch" != "—" ]] && branch_tag="(${branch}) "
fi

# --- bar ---
filled=$(( pct_int / 10 )); empty=$(( 10 - filled ))
bar=""; (( filled > 0 )) && bar=$(printf '%0.s▓' $(seq 1 $filled))
(( empty > 0 )) && bar+=$(printf '%0.s░' $(seq 1 $empty))

in_k=$(cockpit_fmt_k "$current_tokens")
ctx_k=$(cockpit_fmt_k "$ctx_size")
cost_fmt=$(printf '$%.2f' "$cost")

cost_vel=""; cost_alert=0
if (( duration_ms > 60000 )); then
  vel=$(echo "scale=2; $cost * 60000 / $duration_ms" | bc -l 2>/dev/null || echo "")
  [[ "$vel" == .* ]] && vel="0${vel}"
  if [[ -n "$vel" && "$vel" != "0" && "$vel" != "0.00" ]]; then
    cost_vel="\$${vel}/m"
    cost_alert=$(echo "$vel > ${COST_VEL_ALERT:-1.0}" | bc -l 2>/dev/null || echo 0)
  fi
fi

ctx_eta=""
if (( duration_ms > 60000 && pct_int > 40 )); then
  rate_per_min=$(echo "scale=1; $pct_int * 60000 / $duration_ms" | bc -l 2>/dev/null || echo "")
  if [[ -n "$rate_per_min" && "$rate_per_min" != "0" && "$rate_per_min" != "0.0" ]]; then
    remaining=$(( 100 - pct_int ))
    eta_min=$(echo "scale=0; $remaining / $rate_per_min" | bc -l 2>/dev/null || echo "")
    if [[ -n "$eta_min" && "$eta_min" -gt 0 ]] 2>/dev/null; then
      if (( eta_min > 60 )); then ctx_eta="~$((eta_min / 60))h"
      else ctx_eta="~${eta_min}m"; fi
    fi
  fi
fi

reset='\033[0m'; dim='\033[2m'; bold='\033[1m'
cyan='\033[36m'; yellow='\033[33m'; red='\033[31m'; green='\033[32m'
if (( pct_int > 80 )); then ctx_color='\033[1;31m'
elif (( pct_int > 50 )); then ctx_color='\033[1;33m'
else ctx_color='\033[32m'; fi

tool_action=""
[[ -f "/tmp/claude-tab-tool-$PPID" ]] && tool_action=$(cat "/tmp/claude-tab-tool-$PPID" 2>/dev/null || true)

cockpit_loop_read "$PPID" "$now"
if [[ -z "$COCKPIT_LOOP_BADGE" ]] && (( cron_n > 0 )); then
  COCKPIT_LOOP_BADGE="🔁"; COCKPIT_LOOP_LABEL="${cron_n} cron"
fi

cockpit_prompt_idle "$PPID" "$now"
elapsed=""
(( COCKPIT_IDLE_SECS > 0 )) && elapsed=$(cockpit_fmt_age "$COCKPIT_IDLE_SECS")

spinners=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
spinner_file="/tmp/claude-tab-spinner-$PPID"
spinner_idx=0; [[ -f "$spinner_file" ]] && spinner_idx=$(cat "$spinner_file" 2>/dev/null || echo 0)
spinner="${spinners[$((spinner_idx % 10))]}"
echo $(( (spinner_idx + 1) % 10 )) > "$spinner_file" 2>/dev/null || true

[[ -n "$session_id" ]] && printf '%s|%s|%s' "$pct_int" "$current_tokens" "$ctx_size" > "/tmp/claude-ctxpct-${session_id}" 2>/dev/null || true

tab_state=""
[[ -f "/tmp/claude-tab-state-$PPID" ]] && tab_state=$(cat "/tmp/claude-tab-state-$PPID" 2>/dev/null || true)
error_val=0
[[ -f "/tmp/claude-tab-error-$PPID" ]] && error_val=$(cat "/tmp/claude-tab-error-$PPID" 2>/dev/null || echo 0)
(( error_val > 0 )) && tab_state="error"
(( pct_int > 80 )) && [[ "$tab_state" != "error" && "$tab_state" != "done" ]] && tab_state="attention"

attn_tag=$(cockpit_attn_tag "$PPID" "${tab_state:-idle}" "$pct_int")
case "${tab_state:-idle}" in
  working)   state_glyph="◐"; state_color="$dim" ;;
  attention) state_glyph="◆"; state_color="$yellow" ;;
  error)     state_glyph="▲"; state_color="$red" ;;
  done)      state_glyph="●"; state_color="$green" ;;
  *)         state_glyph="·"; state_color="$dim" ;;
esac

wt_id=""; [[ -n "$git_worktree" ]] && wt_id=$(basename "$git_worktree")
cockpit_write_agent_state "claude" "$PPID" "${tab_state:-idle}" "$project" "$cost_fmt" "$pct_int" "$wt_id" "${COCKPIT_LOOP_LABEL:-}"
cockpit_scan_aggregate "$PPID" "$now"

agg_badge=""
(( COCKPIT_AGG_ATTENTION > 0 || COCKPIT_AGG_ERROR > 0 || COCKPIT_AGG_WORKING > 0 )) && {
  agg_badge=" ["
  (( COCKPIT_AGG_ATTENTION > 0 )) && agg_badge+="${COCKPIT_AGG_ATTENTION}◆ "
  (( COCKPIT_AGG_ERROR > 0 )) && agg_badge+="${COCKPIT_AGG_ERROR}▲ "
  (( COCKPIT_AGG_WORKING > 0 )) && agg_badge+="${COCKPIT_AGG_WORKING}◐"
  agg_badge="${agg_badge% }]"
}

# === LINE 1 ===
model_short=""
[[ "$model" != "Opus 4.6" && "$model" != "?" ]] && model_short="${model%% (*} "
attn_disp=""
[[ -n "$attn_tag" ]] && attn_disp="${yellow}${attn_tag}${reset} "
effort_disp=""; [[ -n "$effort_tag" ]] && effort_disp="${dim}${effort_tag}${reset} "

left="${state_color}${state_glyph}${reset} ${attn_disp}${dim}${model_short}${reset}${effort_disp}${branch_tag}${bold}${project}${reset}"
left+=" ${dim}·${reset} ${yellow}${cost_fmt}${reset}"
[[ -n "$cost_vel" ]] && left+=" ${dim}${cost_vel}${reset}"
left+=" ${dim}·${reset} ${ctx_color}${bar} ${pct_int}%${reset} ${dim}${in_k}/${ctx_k}${reset}"
(( pct_int > 80 )) && left+=" ${bold}${red}→/compact${reset}"
[[ -n "$tool_action" ]] && left+=" ${dim}·${reset} ${tool_action}"
[[ -n "$elapsed" ]] && left+=" ${dim}${elapsed}${reset}"

right=$(cockpit_rate_limits_ansi "$rate_5h" "$rate_7d" "$dim" "$yellow" "$red" "$reset")
if [[ -n "$right" ]]; then
  cockpit_print_lr "$left" "$right" "$render_w"
else
  printf '%b' "$left"
fi
echo

# === LINE 2 (steering only, width-capped) ===
parts=()
[[ -n "$COCKPIT_LOOP_BADGE" ]] && {
  lp="${COCKPIT_LOOP_BADGE} ${cyan}${COCKPIT_LOOP_LABEL}${reset}"
  [[ -n "$COCKPIT_LOOP_COUNTDOWN" ]] && lp+=" ${dim}·${COCKPIT_LOOP_COUNTDOWN}${reset}"
  parts+=("$lp")
}
cockpit_postcompact "$session_id" "$now" && parts+=("${yellow}↺compact${reset}")
(( subagent_n > 0 )) && parts+=("${cyan}sub:${subagent_n}${reset}")
(( bg_tasks > 0 )) && parts+=("${cyan}bg:${bg_tasks}${reset}")
dirty=$(cockpit_git_dirty "$workspace" "$now")
(( dirty > 0 )) && parts+=("${yellow}git:${dirty}${reset}")
[[ "$tab_state" == "working" && "$COCKPIT_IDLE_SECS" -ge 300 ]] && parts+=("${yellow}stale?${reset}")
[[ -n "$ctx_eta" && "$pct_int" -ge 50 ]] && parts+=("${dim}${ctx_eta}${reset}")
cockpit_hutter_fleet "$project" "$now"
[[ -n "$COCKPIT_HUTTER" ]] && {
  if [[ "$COCKPIT_HUTTER" == *idle* || "$COCKPIT_HUTTER" == *unreach* ]]; then parts+=("${yellow}fleet:${COCKPIT_HUTTER}${reset}")
  else parts+=("${dim}fleet:${COCKPIT_HUTTER}${reset}"); fi
}
if (( COCKPIT_AGG_ATTENTION > 0 || COCKPIT_AGG_ERROR > 0 || COCKPIT_AGG_WORKING > 0 )); then
  oc=""; (( COCKPIT_AGG_ATTENTION > 0 )) && oc+="${yellow}${COCKPIT_AGG_ATTENTION}◆${reset} "
  (( COCKPIT_AGG_ERROR > 0 )) && oc+="${red}${COCKPIT_AGG_ERROR}▲${reset} "
  (( COCKPIT_AGG_WORKING > 0 )) && oc+="${dim}${COCKPIT_AGG_WORKING}◐${reset}"
  parts+=("${dim}others:${reset} [${oc% }]")
fi
if (( ${#COCKPIT_AGG_ATT_NAMES[@]} > 0 )); then
  att_list=$(printf '%s\n' "${COCKPIT_AGG_ATT_NAMES[@]}" | sort -u | paste -sd, -)
  parts+=("${yellow}⚑ ${att_list}${reset}")
fi

if (( ${#parts[@]} > 0 )); then
  line2=$(cockpit_join_parts "$dim" "$reset" "${parts[@]}")
  line2=" $(cockpit_truncate_line "$line2" "$render_w")"
  printf '%b\n' "$line2"
fi

# === GHOSTTY TAB ===
if ! cockpit_tab_disabled; then
  tab_dot=$(cockpit_tab_emoji "${tab_state:-idle}" "$cost_alert")
  attn_title=$(cockpit_attn_title "$attn_tag")
  tab="${tab_dot}"
  [[ -n "$COCKPIT_LOOP_BADGE" ]] && tab+="${COCKPIT_LOOP_BADGE}"
  if [[ "$tab_state" == "working" ]]; then
    tab+=" ${spinner} ${project}"
    [[ -n "$tool_action" ]] && tab+=": ${tool_action}"
    [[ -n "$COCKPIT_LOOP_COUNTDOWN" ]] && tab+=" · 🔁${COCKPIT_LOOP_COUNTDOWN}"
    tab+="${agg_badge} · ${cost_fmt} ${pct_int}%"
    [[ -n "$elapsed" ]] && tab+=" ${elapsed}"
  elif [[ -n "$attn_title" ]]; then
    tab+=" ${project} · ${attn_title}${agg_badge} · ${cost_fmt} ${pct_int}%"
  else
    tab+=" ${project}${agg_badge} · ${cost_fmt} ${pct_int}%"
  fi
  cockpit_ghostty_title "$tab"
fi

[[ -n "$session_id" ]] && jq -n \
  --arg cost "$cost" --arg pct "$pct_int" --arg dur "$duration_ms" \
  --arg la "$lines_add" --arg lr "$lines_rm" --arg model "$model" \
  --arg branch "${branch:-}" --arg project "$project" --arg out_tok "$total_out" \
  '{cost:$cost,context_pct:$pct,duration_ms:$dur,lines_added:$la,lines_removed:$lr,model:$model,branch:$branch,project:$project,output_tokens:$out_tok}' \
  > "/tmp/claude-cockpit-${session_id}" 2>/dev/null || true
