#!/usr/bin/env bash
#
# reclaim — macOS space & memory hygiene for an 18 GB M3 Pro dev machine.
#
# Supersedes the scattered cleanup scripts (enhanced-macos-cleanup.sh,
# macos-cleanup.sh, deep-cleanup.py, cleanup_scripts_backup/*). Carries forward
# only the good ideas from those:
#   - dry-run by default; --yes to execute
#   - prefer `trash` (recoverable) over `rm -rf`
#   - before/after free-space accounting + run log
#   - sleep-assertion / pmset reporting
# Drops the dangerous slop they contained (rm -rf /System caches, font-DB reset,
# LaunchServices reset, ~/.zsh_history wipe, Notes SQLite surgery, Spotlight
# *rebuild*, DNS/print/Siri kitchen-sink).
#
# Aware of THIS machine's real hogs: uv cache (~50 GB), HuggingFace, datalab,
# the sudo-gated queue (Previously Relocated Items, Claude vm_bundles).
#
# Usage:  reclaim [report|preview|caches|venvs|big|rosetta|ssd|tm-off|sudo-items|all] [--yes] [--days N] [--gb N]
#         preview = force dry-run of every destructive action (caches+venvs+sudo-items); never deletes.
# Safe by default — destructive subcommands print a dry-run unless you pass --yes (alias --force, -y).

set -uo pipefail   # NOT -e on purpose: one missing path must not abort the whole run.
[[ "$(uname)" == "Darwin" ]] || { echo "reclaim: macOS only"; exit 1; }

# ---- args ----
SUB=""; YES=0; DAYS=90; GB=2
while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes|--force) YES=1 ;;
    --days) DAYS="${2:-90}"; shift ;;
    --gb)   GB="${2:-2}";  shift ;;
    -h|--help|help) SUB="help" ;;
    *) [ -z "$SUB" ] && SUB="$1" ;;
  esac
  shift
done
SUB="${SUB:-report}"

# ---- output (TTY-aware, NO_COLOR-aware; unicode markers per console-output rules) ----
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  B=$'\033[1m'; D=$'\033[2m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; C=$'\033[36m'; N=$'\033[0m'
else B=""; D=""; G=""; Y=""; R=""; C=""; N=""; fi
ok()   { printf "  ${G}✓${N} %s\n" "$*"; }
warn() { printf "  ${Y}!${N} %s\n" "$*"; }
err()  { printf "  ${R}✗${N} %s\n" "$*"; }
sect() { printf "\n${B}▸ %s${N}\n" "$*"; }
info() { printf "    %s\n" "$*"; }

# ---- deletion: prefer `trash` (recoverable) over rm ----
HAS_TRASH=0; command -v trash >/dev/null 2>&1 && HAS_TRASH=1
LOG_DIR="$HOME/.cache/reclaim"; mkdir -p "$LOG_DIR" 2>/dev/null || true
LOG="$LOG_DIR/history.log"

del() { # del <path...>  — trash/rm each existing path, or dry-run preview
  local p sz
  for p in "$@"; do
    [ -e "$p" ] || continue
    sz=$(du -sh "$p" 2>/dev/null | cut -f1)
    if [ "$YES" = 1 ]; then
      if [ "$HAS_TRASH" = 1 ]; then trash "$p" 2>/dev/null || rm -rf "$p"; else rm -rf "$p"; fi
      ok "removed $p ($sz)"
      printf '%s\tdel\t%s\t%s\n' "$(date +%FT%T)" "$sz" "$p" >> "$LOG" 2>/dev/null || true
    else
      printf "  ${D}[dry-run]${N} would remove %s (%s)\n" "$p" "$sz"
    fi
  done
}
runcmd() { # runcmd "<label>" cmd args...
  local label="$1"; shift
  if [ "$YES" = 1 ]; then
    if "$@" >/dev/null 2>&1; then ok "$label"; printf '%s\trun\t%s\n' "$(date +%FT%T)" "$label" >> "$LOG" 2>/dev/null || true
    else warn "$label — skipped/failed"; fi
  else printf "  ${D}[dry-run]${N} %s\n" "$label"; fi
}
free_gb() { df -g / 2>/dev/null | awk 'NR==2{print $4}'; }
mode_banner() { [ "$YES" = 1 ] && printf "${R}● EXECUTING${N} (--yes)\n" || printf "${C}● dry-run${N} (pass --yes to apply)\n"; }

# ============================================================ report
cmd_report() {
  printf "${B}reclaim report${N}  —  %s\n" "$(date '+%a %d %b %Y, %H:%M')"

  sect "Disk (shared APFS container)"
  df -h / | awk 'NR==2{print "    "$4" free of "$2"   ("$5" on system vol)"}'
  info "biggest caches:  uv $(du -sh ~/.cache/uv 2>/dev/null|cut -f1)   hf $(du -sh ~/.cache/huggingface 2>/dev/null|cut -f1)"

  sect "Memory"
  top -l 1 -n 0 2>/dev/null | awk '/PhysMem/{print "    "$0}'
  sysctl -n vm.swapusage 2>/dev/null | awk '{print "    swap: "$0}'
  info "top RAM:"
  ps axo rss=,comm= 2>/dev/null | sort -rn | head -5 | awk '{rss=$1;$1="";printf "      %5.0f MB %s\n",rss/1024,$0}'

  sect "SSD wear"
  local ssd; ssd=$(smartctl -a disk0 2>/dev/null)
  if [ -n "$ssd" ]; then printf '%s\n' "$ssd" | awk -F: '/Percentage Used|Data Units Written|Available Spare:/{gsub(/^ +/,"",$2);print "    "$1": "$2}'
  else info "install smartmontools, or run: sudo smartctl -a disk0"; fi

  sect "Sleep / power"
  local nca; nca=$(pgrep -x caffeinate 2>/dev/null | wc -l | tr -d ' ')
  pmset -g assertions 2>/dev/null | awk '/PreventUserIdleSystemSleep +1/{print "    idle-sleep is BLOCKED"}'
  info "$nca caffeinate holds, $(pgrep -x claude 2>/dev/null | wc -l | tr -d ' ') claude agents alive"

  sect "Reclaim hints"
  info "preview ALL → reclaim preview     (dry-run everything; deletes nothing)"
  info "caches      → reclaim caches      (uv/brew/hf/playwright/quicklook/crashes)"
  info "stale venvs → reclaim venvs       (git-dormant > ${DAYS}d, skips live agents)"
  info "big files   → reclaim big --gb 2"
  info "sudo queue  → reclaim sudo-items  (relocated items, Claude vm_bundles)"
  info "kill TM     → reclaim tm-off"
}

# ============================================================ caches (safe, reversible)
cmd_caches() {
  printf "${B}reclaim caches${N}  "; mode_banner
  local before; before=$(free_gb)

  sect "Package-manager caches"
  if [ "$(pgrep -x claude 2>/dev/null | wc -l | tr -d ' ')" -gt 0 ]; then
    warn "claude agents are running — 'uv cache prune' may be lock-blocked; run again when idle"
  fi
  runcmd "uv cache prune (unreferenced wheels)" env UV_LOCK_TIMEOUT=30 uv cache prune
  runcmd "brew cleanup -s" brew cleanup -s
  command -v pip3 >/dev/null 2>&1 && runcmd "pip cache purge" pip3 cache purge
  command -v npm  >/dev/null 2>&1 && runcmd "npm cache clean" npm cache clean --force

  sect "ML model caches (HuggingFace, accessed > ${DAYS}d ago)"
  local hub="$HOME/.cache/huggingface/hub" d
  if [ -d "$hub" ]; then
    while IFS= read -r d; do [ -n "$d" ] && del "$d"; done \
      < <(find "$hub" -maxdepth 1 -type d -name 'models--*' -atime +"$DAYS" 2>/dev/null)
  fi
  del "$HOME/Library/Caches/datalab"   # marker runs on Modal, not local

  sect "Browser-automation builds (Playwright — keep newest)"
  local base="$HOME/Library/Caches/ms-playwright" fam newest v
  if [ -d "$base" ]; then
    for fam in chromium chromium_headless_shell; do
      newest=$(ls -d "$base/$fam"-* 2>/dev/null | sed "s|.*/$fam-||" | sort -n | tail -1)
      [ -n "$newest" ] || continue
      for d in "$base/$fam"-*; do
        [ -d "$d" ] || continue; v="${d##*-}"
        [ "$v" != "$newest" ] && del "$d"
      done
    done
  fi

  sect "System caches (safe / regenerable)"
  runcmd "QuickLook thumbnail cache" qlmanage -r cache
  del "$HOME/Library/Logs/DiagnosticReports"          # crash reports
  del "$HOME/Library/Developer/Xcode/DerivedData"     # no-op if no Xcode
  # Mail Downloads can hold stale attachments:
  del "$HOME/Library/Containers/com.apple.mail/Data/Library/Mail Downloads"

  sect "App & browser caches (regenerable — NOT profiles/history)"
  del "$HOME/Library/Caches/Google"                    # Chrome HTTP cache
  del "$HOME/Library/Caches/com.apple.Safari"
  del "$HOME/Library/Caches/BraveSoftware"
  del "$HOME/Library/Caches/ru.keepcoder.Telegram"     # Telegram media cache (re-downloads)
  del "$HOME/Library/Caches/CloudKit"                  # re-syncs from iCloud
  del "$HOME/.cache/codex-runtimes"                    # Codex CLI runtimes (re-fetched)
  del "$HOME/.cache/chrome-devtools-mcp"               # MCP chrome download (re-fetched)

  if [ "$YES" = 1 ]; then
    local after; after=$(free_gb)
    sect "Result"; ok "free space: ${before} GB → ${after} GB  (Δ $((after-before)) GB)"
  else
    printf "\n${D}  dry-run — nothing deleted. Re-run with --yes to apply.${N}\n"
  fi
}

# ============================================================ venvs (git-dormancy)
cmd_venvs() {
  printf "${B}reclaim venvs${N}  (dormant > ${DAYS}d)  "; mode_banner
  local cutoff; cutoff=$(date -v-"${DAYS}"d +%s)
  local active=" intel genomics phenome publishing "   # live-agent cwds — never touch
  local d n lc ts
  for d in "$HOME"/Projects/*/; do
    n=$(basename "$d"); [ -d "${d}.venv" ] || continue
    case "$active" in *" $n "*) info "skip $n (live agent)"; continue ;; esac
    lc=$(git -C "$d" log -1 --format=%ct 2>/dev/null || echo 0)
    if [ "${lc:-0}" -lt "$cutoff" ]; then
      ts=$(git -C "$d" log -1 --format=%cd --date=short 2>/dev/null || echo "no-git")
      printf "  %-16s last commit %s — " "$n" "$ts"; del "${d}.venv"
    fi
  done
  info "recreate any with: (cd <proj> && uv sync)"
}

# ============================================================ big files
cmd_big() {
  printf "${B}reclaim big${N}  (files > %s GB, via Spotlight)\n" "$GB"
  local bytes=$((GB*1073741824)) f sz
  mdfind "kMDItemFSSize > $bytes" 2>/dev/null | head -60 | while IFS= read -r f; do
    sz=$(stat -f%z "$f" 2>/dev/null); [ -n "$sz" ] && printf "%.2f\t%s\n" "$(echo "$sz/1073741824"|bc -l)" "$f"
  done | sort -rn | head -25 | awk -F'\t' '{printf "  %6.1f GB  %s\n",$1,$2}'
  info "(review-only; delete intentionally with: reclaim … or trash <file>)"
}

# ============================================================ rosetta
cmd_rosetta() {
  printf "${B}reclaim rosetta${N}\n"
  sect "x86-only processes currently running (need emulation)"
  local found=0 p a
  while IFS= read -r p; do
    case "$p" in /*) [ -f "$p" ] || continue; a=$(lipo -archs "$p" 2>/dev/null)
      case "$a" in *arm64*) : ;; *x86_64*) info "$p [$a]"; found=1 ;; esac ;;
    esac
  done < <(ps -axo comm= 2>/dev/null | sort -u)
  [ "$found" = 0 ] && info "none — nothing actually needs Rosetta right now"
  sect "oahd daemon"
  if pgrep -x oahd >/dev/null 2>&1; then
    runcmd "stop oahd (respawns on next x86 launch)" sudo pkill -x oahd
    info "permanent removal (may reinstall on demand): sudo rm -rf /Library/Apple/usr/{share/rosetta,libexec/oah}"
  else info "oahd not running"; fi
}

# ============================================================ ssd
cmd_ssd() {
  printf "${B}reclaim ssd${N}\n"
  local out; out=$(smartctl -a disk0 2>/dev/null)
  if [ -n "$out" ]; then printf '%s\n' "$out" | grep -iE "model number|percentage used|data units written|available spare|power on hours|unsafe shutdown" | sed 's/^/  /'
  else warn "needs privileges"; info "run: sudo smartctl -a disk0"; fi
}

# ============================================================ tm-off
cmd_tm_off() {
  printf "${B}reclaim tm-off${N}  "; mode_banner
  warn "Disabling Time Machine = NO automatic backups. (Your code is in git; Media syncs to gdrive.)"
  sect "current status"; tmutil status 2>/dev/null | sed 's/^/  /' | head -4
  tmutil destinationinfo 2>/dev/null | sed 's/^/  /' | head -6
  sect "actions"
  runcmd "disable automatic backups" sudo tmutil disable
  local s
  for s in $(tmutil listlocalsnapshots / 2>/dev/null | sed 's/.*com.apple.TimeMachine.//'); do
    runcmd "delete local snapshot $s" sudo tmutil deletelocalsnapshots "$s"
  done
}

# ============================================================ sudo-items (the gated queue)
cmd_sudo_items() {
  printf "${B}reclaim sudo-items${N}  "; mode_banner
  info "(these need sudo / touch app internals; run in your terminal so sudo can prompt)"
  sect "macOS install leftover (root-owned, ~11 GB)"
  if [ -e "/Users/Shared/Previously Relocated Items 18" ]; then
    if [ "$YES" = 1 ]; then sudo rm -rf "/Users/Shared/Previously Relocated Items 18" && ok "removed relocated-items"; \
    else info "[dry-run] sudo rm -rf '/Users/Shared/Previously Relocated Items 18'"; fi
  else info "already gone"; fi
  sect "Claude Desktop sandbox VM image (~10 GB, rebuilds from .zst)"
  local img="$HOME/Library/Application Support/Claude/vm_bundles/claudevm.bundle/rootfs.img"
  if [ -e "$img" ]; then info "quit Claude Desktop first."; del "$img"; else info "already gone"; fi
}

# ============================================================ dispatch
case "$SUB" in
  report)      cmd_report ;;
  caches)      cmd_caches ;;
  venvs)       cmd_venvs ;;
  big)         cmd_big ;;
  rosetta)     cmd_rosetta ;;
  ssd)         cmd_ssd ;;
  tm-off)      cmd_tm_off ;;
  sudo-items)  cmd_sudo_items ;;
  preview)     YES=0
               printf "${B}reclaim preview${N} — everything that WOULD run/delete across caches+venvs+sudo-items.\n"
               printf "${C}● nothing is touched${N} (preview ignores --yes; run a specific subcommand with --yes to apply)\n"
               cmd_caches; cmd_venvs; cmd_sudo_items ;;
  all)         cmd_report; printf "\n"; cmd_caches ;;
  help|*)
    sed -n '2,30p' "$0" | sed 's/^#\{0,1\} \{0,1\}//'
    ;;
esac
