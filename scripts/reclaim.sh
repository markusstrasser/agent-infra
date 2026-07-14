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
# Usage:  reclaim [report|preview|sweep|caches|rotate|venvs|big|rosetta|ssd|tm-off|sudo-items|all] [--yes] [--days N] [--gb N]
#         sweep = whole-disk top-N per root (read-only) — the report's known-hogs list is not a full scan.
#         rotate = prune agentlogs.db to last ALOG_KEEP_DAYS (21) of sessions + VACUUM (the unbounded append-only store).
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

  # Append-only snapshot → cross-OS RAM baseline (wired is the kernel/OS-footprint
  # signal; "used" is ~constant by design, compressor/swap are workload-driven).
  # Tag os+build so an OS bump is a queryable before/after, not lost to stdout.
  {
    local _wired _compr _swap _la
    _wired=$(vm_stat 2>/dev/null | awk '/Pages wired down/{gsub(/\./,"",$NF);printf "%.0f",$NF*16384/1048576}')
    _compr=$(vm_stat 2>/dev/null | awk '/Pages occupied by compressor/{gsub(/\./,"",$NF);printf "%.0f",$NF*16384/1048576}')
    _swap=$(sysctl -n vm.swapusage 2>/dev/null | awk '{for(i=1;i<=NF;i++)if($i=="used"){print $(i+2);break}}')
    _la=$(sysctl -n vm.loadavg 2>/dev/null | awk '{print $2}')
    printf '{"ts":"%s","os":"%s","build":"%s","wired_mb":%s,"compressor_mb":%s,"swap_used":"%s","load1":"%s"}\n' \
      "$(date -u +%FT%TZ)" "$(sw_vers -productVersion 2>/dev/null)" "$(sw_vers -buildVersion 2>/dev/null)" \
      "${_wired:-0}" "${_compr:-0}" "${_swap:-?}" "${_la:-?}" \
      >> "$LOG_DIR/mem-history.jsonl" 2>/dev/null || true
  }

  sect "SSD wear"
  local ssd; ssd=$(smartctl -a disk0 2>/dev/null)
  if [ -n "$ssd" ]; then printf '%s\n' "$ssd" | awk -F: '/Percentage Used|Data Units Written|Available Spare:/{gsub(/^ +/,"",$2);print "    "$1": "$2}'
  else info "install smartmontools, or run: sudo smartctl -a disk0"; fi

  sect "Sleep / power"
  local nca; nca=$(pgrep -x caffeinate 2>/dev/null | wc -l | tr -d ' ')
  pmset -g assertions 2>/dev/null | awk '/PreventUserIdleSystemSleep +1/{print "    idle-sleep is BLOCKED"}'
  info "$nca caffeinate holds, $(pgrep -x claude 2>/dev/null | wc -l | tr -d ' ') claude agents alive"

  sect "Backup"
  local tmauto; tmauto=$(defaults read /Library/Preferences/com.apple.TimeMachine.plist AutoBackup 2>/dev/null || echo 0)
  if [ "$tmauto" = "1" ]; then
    local last; last=$(tmutil latestbackup 2>/dev/null | tail -1)
    if [ -n "$last" ]; then info "Time Machine on — latest: ${last##*/}"; else warn "Time Machine ON but no completed backup reachable"; fi
  else
    warn "Time Machine auto-backup OFF — machine has NO working backup"
  fi

  sect "Reclaim hints"
  info "preview ALL → reclaim preview     (dry-run everything; deletes nothing)"
  info "caches      → reclaim caches      (uv/brew/hf/playwright/quicklook/crashes)"
  info "rotate logs → RETIRED             (agentlogs.db retention: weekly 'just agentlogs-archive')"
  info "stale venvs → reclaim venvs       (git-dormant > ${DAYS}d, skips live agents)"
  info "big files   → reclaim big --gb 2"
  info "sudo queue  → reclaim sudo-items  (relocated items, Claude vm_bundles, texlive, powerlog)"
  info "kill TM     → reclaim tm-off"
}

# ============================================================ caches (safe, reversible)
cmd_caches() {
  printf "${B}reclaim caches${N}  "; mode_banner
  local before; before=$(free_gb)

  sect "Package-manager caches"
  if [ "$(pgrep -x claude 2>/dev/null | wc -l | tr -d ' ')" -gt 0 ] || pgrep -qx uv 2>/dev/null; then
    warn "agents/uv running — 'uv cache prune' may be lock-blocked; never force past the lock (3 sessions re-derived this 2026-07-14), rerun when idle"
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

  sect "Project build caches (rederivable — regenerate on next run)"
  local pyc; pyc=$(find "$HOME/Projects" -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache \) -prune 2>/dev/null)
  if [ -n "$pyc" ]; then
    local pn; pn=$(printf '%s\n' "$pyc" | grep -c .)
    if [ "$YES" = 1 ]; then printf '%s\n' "$pyc" | xargs rm -rf 2>/dev/null; ok "removed $pn Python build-cache dirs under ~/Projects"
    else printf "  ${D}[dry-run]${N} would remove %s Python build-cache dirs under ~/Projects\n" "$pn"; fi
  else info "none"; fi

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
  # venvs with a live process (MCP servers, dev servers, launchd jobs) — deleting breaks them
  local inuse; inuse=$(ps -axww -o command= 2>/dev/null | grep -oE "$HOME/Projects/[A-Za-z0-9_.-]+/\.venv" | sort -u)
  local d n lc ts
  for d in "$HOME"/Projects/*/; do
    n=$(basename "$d"); [ -d "${d}.venv" ] || continue
    case "$active" in *" $n "*) info "skip $n (live agent)"; continue ;; esac
    case "$inuse" in *"${d}.venv"*) info "skip $n (venv in use by a running process)"; continue ;; esac
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
  sect "TeX Live (root-owned, ~9 GB; operator confirmed unused 2026-07-14)"
  if [ -d /usr/local/texlive ]; then
    if [ "$YES" = 1 ]; then sudo rm -rf /usr/local/texlive /Library/TeX && ok "removed TeX Live + /Library/TeX"; \
    else info "[dry-run] sudo rm -rf /usr/local/texlive /Library/TeX"; fi
  else info "already gone"; fi
  sect "Mono.framework (root-owned, ~1 GB; operator confirmed unused 2026-07-14)"
  if [ -d /Library/Frameworks/Mono.framework ]; then
    if [ "$YES" = 1 ]; then sudo rm -rf /Library/Frameworks/Mono.framework && sudo find /usr/local/bin -type l -lname '*Mono.framework*' -delete; ok "removed Mono + symlinks"; \
    else info "[dry-run] sudo rm -rf /Library/Frameworks/Mono.framework  (+ /usr/local/bin symlinks)"; fi
  else info "already gone"; fi
  sect "python.org Framework Python 3.12/3.13/3.14 (root-owned, ~1 GB; uv owns Python — operator confirmed 2026-07-14; evo=Clojure keeps JVM, NOT this)"
  if [ -d /Library/Frameworks/Python.framework ]; then
    if [ "$YES" = 1 ]; then sudo rm -rf /Library/Frameworks/Python.framework "/Applications/Python 3.12" "/Applications/Python 3.13" "/Applications/Python 3.14" && sudo find /usr/local/bin -type l -lname '*Python.framework*' -delete; ok "removed Framework Python + app folders + symlinks"; \
    else info "[dry-run] sudo rm -rf /Library/Frameworks/Python.framework '/Applications/Python 3.1[2-4]'  (+ /usr/local/bin symlinks)"; fi
  else info "already gone"; fi
  sect "powerlog PerfPowerTelemetry (root-owned; ballooned to 12 GB on macOS 27 beta — regenerates)"
  local ppt="/private/var/db/powerlog/Library/PerfPowerTelemetry"
  if [ -d "$ppt" ]; then
    if [ "$YES" = 1 ]; then sudo rm -rf "$ppt" && ok "removed PerfPowerTelemetry (powerd recreates the dir)"; \
    else info "[dry-run] sudo rm -rf $ppt   # $(du -sh "$ppt" 2>/dev/null | cut -f1) now"; fi
  else info "already gone"; fi
}

# ============================================================ sweep (whole-disk top-N)
# The report's known-hogs list is NOT a full scan: it missed TeX Live (9.1G) and
# powerlog PerfPowerTelemetry (12G) until the operator asked "what did you miss?"
# (2026-07-14). Sweep walks the roots where forgotten installs and system balloons
# actually live. Read-only; ~1-2 min under load.
cmd_sweep() {
  printf "${B}reclaim sweep${N} — top consumers per root (read-only)\n"
  local r
  for r in /usr/local /opt "$HOME" "$HOME/Library" /Library /private/var/db /private/var/folders /private/tmp /Applications; do
    sect "$r"
    du -xsh "$r"/* 2>/dev/null | sort -rh | head -6
  done
  sect "agent worktrees (16.8G freed from this class 2026-07-14; prune ONLY with lsof/content checks — research/2026-07-14-cleanup-campaign-ledger.md)"
  local w; for w in "$HOME"/Projects/*/.claude/worktrees; do
    [ -d "$w" ] && du -xsh "$w" 2>/dev/null
  done | sort -rh | head -8
  sect "superseded backups (>100M, >14d, backup/bak/prev-named — check for a live sibling before touching)"
  find "$HOME/Projects" -maxdepth 4 \( -name '*backup*' -o -name '*.bak*' -o -name '*.prev.*' \) \
    -size +100M -mtime +14 -not -path '*/.git/*' 2>/dev/null | head -8
  info "root-owned finds (texlive, powerlog, …) → add to 'reclaim sudo-items'; caches → 'reclaim caches'"
}

# ============================================================ rotate (RETIRED 2026-07-14)
# agentlogs.db retention has ONE owner: the weekly snapshot-gated
# `just agentlogs-archive` (prune 30d ONLY after a verified 2TBPNY snapshot —
# keep-everything-via-archive, decision 2026-07-05). This nightly ungated 21d
# prune predated that pipeline ("no prune path" above was true on 2026-06-12),
# silently overrode the operator's 30d call, and paid FTS-rebuild+VACUUM on a
# 10GB DB every night. Dual-owner drift caught 2026-07-14.
cmd_rotate() {
  printf "${B}reclaim rotate${N}  "; mode_banner
  warn "retired: agentlogs.db retention moved to weekly 'just agentlogs-archive'"
  warn "(snapshot-gated 30d prune; agent-infra@fd2da3f). Nothing to rotate here."
}

# ============================================================ dispatch
case "$SUB" in
  report)      cmd_report ;;
  caches)      cmd_caches ;;
  rotate)      cmd_rotate ;;
  venvs)       cmd_venvs ;;
  big)         cmd_big ;;
  rosetta)     cmd_rosetta ;;
  ssd)         cmd_ssd ;;
  tm-off)      cmd_tm_off ;;
  sudo-items)  cmd_sudo_items ;;
  sweep)       cmd_sweep ;;
  preview)     YES=0
               printf "${B}reclaim preview${N} — everything that WOULD run/delete across caches+venvs+sudo-items.\n"
               printf "${C}● nothing is touched${N} (preview ignores --yes; run a specific subcommand with --yes to apply)\n"
               cmd_caches; cmd_venvs; cmd_sudo_items ;;
  all)         cmd_report; printf "\n"; cmd_caches ;;
  help|*)
    sed -n '2,30p' "$0" | sed 's/^#\{0,1\} \{0,1\}//'
    ;;
esac
