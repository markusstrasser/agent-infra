#!/usr/bin/env bash
# pretool-cost-awareness.sh — Advisory P95 cost threshold per project.
# PreToolUse hook. Fires every ~50 tool calls, checks if the COMPLETED session
# receipt (if any) exceeds the project's historical P95. Note: session-receipts.jsonl
# is written at SessionEnd, so this hook can only see costs from PRIOR sessions
# of the same ID (e.g., after --resume). It cannot measure live cost mid-session.
# Never blocks (always exit 0).

trap 'exit 0' ERR

# --- Counter gate: only check every 50 calls ---
COUNTER_FILE="/tmp/claude-cost-check-$PPID"
COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE" 2>/dev/null || true
[ $((COUNT % 50)) -ne 0 ] && exit 0

cat > /dev/null  # drain stdin (hook protocol)

# --- Determine project name from git root or PWD ---
PROJECT=$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null | xargs basename 2>/dev/null)
[ -z "$PROJECT" ] && PROJECT=$(basename "$PWD")

RECEIPTS="$HOME/.claude/session-receipts.jsonl"
[ -f "$RECEIPTS" ] || exit 0

SESSION_ID="${CLAUDE_SESSION_ID:-$PPID}"

# --- Compute P95, median, current session cost; emit advisory if over ---
# Fix: pass values via env vars, not string interpolation (GPT-5.4 finding #12)
ADVISORY=$(PROJECT="$PROJECT" SESSION_ID="$SESSION_ID" RECEIPTS="$RECEIPTS" python3 -c "
import json, sys, os

project = os.environ['PROJECT']
session_id = os.environ['SESSION_ID']
receipts = os.environ['RECEIPTS']

costs = []
current = 0.0
for line in open(receipts):
    try:
        r = json.loads(line)
    except:
        continue
    if r.get('project', '') != project:
        continue
    c = float(r.get('cost_usd', 0))
    costs.append(c)
    if r.get('session', '') == session_id:
        current = c

if len(costs) < 5:
    sys.exit(0)

costs.sort()
n = len(costs)
p95 = costs[min(int(n * 0.95), n - 1)]  # clamp index (off-by-one fix)
median = costs[n // 2]

if current <= p95:
    sys.exit(0)

print(json.dumps({'additionalContext': (
    f'Cost awareness: this session (\${current:.2f}) has exceeded P95 '
    f'(\${p95:.2f}) for project {project}. Project median: \${median:.2f}. '
    f'Consider whether this session should continue or checkpoint.'
)}))
" 2>/dev/null)

[ -z "$ADVISORY" ] && exit 0

echo "$ADVISORY"

TRIGGER="$HOME/Projects/skills/hooks/hook-trigger-log.sh"
[ -x "$TRIGGER" ] && "$TRIGGER" "cost-awareness" "warn" "project=$PROJECT" 2>/dev/null || true

exit 0
