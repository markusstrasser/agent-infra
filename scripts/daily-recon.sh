#!/usr/bin/env bash
# Daily recon: one consolidated command for cross-project git activity.
# Eliminates the redundant-git-log pattern (improvement-log 2026-03-05).
#
# Usage: ./scripts/daily-recon.sh [YYYY-MM-DD]
# Default: today

set -euo pipefail

DATE="${1:-$(date +%Y-%m-%d)}"
NEXT_DATE=$(date -j -v+1d -f "%Y-%m-%d" "$DATE" "+%Y-%m-%d" 2>/dev/null || date -d "$DATE + 1 day" "+%Y-%m-%d")

PROJECTS=(
  ~/Projects/meta
  ~/Projects/intel
  ~/Projects/selve
  ~/Projects/genomics
  ~/Projects/skills
  ~/Projects/research-mcp
)

echo "=== Daily Recon: $DATE ==="
echo

# 1. Git commits across all projects
for dir in "${PROJECTS[@]}"; do
  name=$(basename "$dir")
  if [ ! -d "$dir/.git" ]; then continue; fi
  commits=$(git -C "$dir" log --oneline --after="$DATE" --before="$NEXT_DATE" 2>/dev/null || true)
  if [ -n "$commits" ]; then
    count=$(echo "$commits" | wc -l | tr -d ' ')
    echo "[$name] $count commits:"
    echo "$commits" | sed 's/^/  /'
    echo
  fi
done

# 2. Session receipts for the day
RECEIPTS=~/.claude/session-receipts.jsonl
if [ -f "$RECEIPTS" ]; then
  sessions=$(grep "\"$DATE" "$RECEIPTS" 2>/dev/null | wc -l | tr -d ' ')
  cost=$(grep "\"$DATE" "$RECEIPTS" 2>/dev/null | python3 -c "
import json, sys
total = 0
for line in sys.stdin:
    try: total += float(json.loads(line).get('cost_usd', 0))
    except: pass
print(f'\${total:.2f}')
" 2>/dev/null || echo "?")
  echo "Sessions: $sessions | Cost: $cost"
fi

# 3. Daily memory log (if exists)
DAILY_LOG=~/.claude/projects/-Users-alien-Projects-meta/memory/$DATE.md
if [ -f "$DAILY_LOG" ]; then
  echo
  echo "Daily log exists: $DAILY_LOG"
fi

# 4. Orchestrator tasks
DB=~/.claude/orchestrator.db
if [ -f "$DB" ]; then
  tasks=$(sqlite3 "$DB" "SELECT count(*), status FROM tasks WHERE date(created_at) = '$DATE' GROUP BY status" 2>/dev/null || true)
  if [ -n "$tasks" ]; then
    echo
    echo "Orchestrator tasks:"
    echo "$tasks" | sed 's/|/ /g; s/^/  /'
  fi
fi
