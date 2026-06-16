#!/usr/bin/env bash
# codex-tab-title.sh — Ghostty tab title + fleet state for Codex CLI.
# Codex has no statusline API; hooks drive tab title on PreToolUse/Stop/UserPromptSubmit.
#
# Usage:
#   codex-tab-title.sh <state>   # working|attention|error|done|idle
#   codex-tab-title.sh --ctx     # print context % only

set -uo pipefail

COCKPIT_DIR="${HOME}/Projects/agent-infra/scripts"
# shellcheck source=/dev/null
source "$COCKPIT_DIR/cockpit_common.sh"

cockpit_tab_disabled && exit 0

MODE="${1:-working}"
PID="$(cockpit_agent_pid)"
TOOL="${CLAUDE_TOOL_NAME:-}"
now=$(date +%s)

CTX_OUT=$(PID="$PID" TOOL="$TOOL" python3 <<'PY' 2>/dev/null
import json, os, subprocess

pid = int(os.environ.get("PID") or os.getppid())
CACHE = f"/tmp/codex-rollout-{pid}"

def resolve_rollout(start_pid):
    try:
        with open(CACHE) as f:
            p = f.read().strip()
        if p and os.path.isfile(p):
            return p
    except Exception:
        pass
    seen, cur = set(), start_pid
    for _ in range(4):
        if not cur or cur in seen:
            break
        seen.add(cur)
        try:
            out = subprocess.run(["lsof", "-p", str(cur)], capture_output=True, text=True, timeout=2).stdout
        except Exception:
            out = ""
        paths = sorted({t for ln in out.splitlines() for t in ln.split()
                        if t.endswith(".jsonl") and "/sessions/" in t})
        if len(paths) == 1:
            try:
                with open(CACHE, "w") as f:
                    f.write(paths[0])
            except Exception:
                pass
            return paths[0]
        try:
            cur = int(subprocess.run(["ps", "-o", "ppid=", "-p", str(cur)],
                                     capture_output=True, text=True).stdout.strip())
        except Exception:
            break
    return None

def tail_text(path, n=200_000):
    with open(path, "rb") as f:
        f.seek(0, 2)
        sz = f.tell()
        f.seek(max(0, sz - n))
        return f.read().decode("utf-8", "ignore")

def head_lines(path, n=8):
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for _ in range(n):
            ln = f.readline()
            if not ln:
                break
            out.append(ln)
    return out

rollout = resolve_rollout(pid)
ctx_pct = None
project = os.path.basename(os.environ.get("PWD", "") or os.getcwd()) or "?"

if rollout:
    last = None
    for ln in tail_text(rollout).splitlines():
        if '"token_count"' in ln:
            try:
                last = json.loads(ln)["payload"]["info"]
            except Exception:
                pass
    if last:
        used = last.get("last_token_usage", {}).get("input_tokens", 0)
        win = last.get("model_context_window") or 0
        if win:
            ctx_pct = round(100 * used / win)
    for ln in head_lines(rollout):
        if '"cwd"' in ln:
            try:
                rec = json.loads(ln)
                cwd = rec.get("cwd") or rec.get("payload", {}).get("cwd")
                if cwd:
                    project = os.path.basename(cwd)
                    break
            except Exception:
                pass

print(json.dumps({"ctx_pct": ctx_pct, "project": project}))
PY
)

if [[ "$MODE" == "--ctx" ]]; then
  echo "$CTX_OUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("ctx_pct") or "")' 2>/dev/null
  exit 0
fi

project=$(echo "$CTX_OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("project","?"))' 2>/dev/null || echo "?")
ctx_pct=$(echo "$CTX_OUT" | python3 -c 'import json,sys; v=json.load(sys.stdin).get("ctx_pct"); print(v if v is not None else "")' 2>/dev/null || echo "")
pct_int=${ctx_pct:-0}

echo "$MODE" > "/tmp/claude-tab-state-$PID" 2>/dev/null || true
[[ "$MODE" == "working" ]] && date +%s > "/tmp/claude-tab-prompt-$PID" 2>/dev/null || true

attn_tag=$(cockpit_attn_tag "$PID" "$MODE" "$pct_int")
cockpit_loop_read "$PID" "$now"
cockpit_scan_aggregate "$PID" "$now"
cockpit_write_agent_state "codex" "$PID" "$MODE" "$project" "—" "$pct_int" "" "${COCKPIT_LOOP_LABEL:-}"

agg_badge=""
(( COCKPIT_AGG_ATTENTION > 0 || COCKPIT_AGG_ERROR > 0 || COCKPIT_AGG_WORKING > 0 )) && {
  agg_badge=" ["
  (( COCKPIT_AGG_ATTENTION > 0 )) && agg_badge+="${COCKPIT_AGG_ATTENTION}◆ "
  (( COCKPIT_AGG_ERROR > 0 )) && agg_badge+="${COCKPIT_AGG_ERROR}▲ "
  (( COCKPIT_AGG_WORKING > 0 )) && agg_badge+="${COCKPIT_AGG_WORKING}◐"
  agg_badge="${agg_badge% }]"
}

tab_dot=$(cockpit_tab_emoji "$MODE" 0)
attn_title=$(cockpit_attn_title "$attn_tag")
tab="${tab_dot} ⌘${project}"
[[ -n "$COCKPIT_LOOP_BADGE" ]] && tab+="${COCKPIT_LOOP_BADGE}"
if [[ "$MODE" == "working" ]]; then
  [[ -n "$TOOL" && "$TOOL" != "Bash" ]] && tab+=": ${TOOL}"
  [[ "$TOOL" == "Bash" ]] && tab+=": $"
  [[ -n "$COCKPIT_LOOP_COUNTDOWN" ]] && tab+=" · 🔁${COCKPIT_LOOP_COUNTDOWN}"
elif [[ -n "$attn_title" ]]; then
  tab+=" · ${attn_title}"
fi
tab+="${agg_badge}"
[[ -n "$ctx_pct" ]] && tab+=" · ${ctx_pct}%"

cockpit_ghostty_title "$tab"
exit 0
