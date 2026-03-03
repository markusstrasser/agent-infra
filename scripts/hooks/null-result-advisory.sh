#!/usr/bin/env bash
# null-result-advisory.sh — Advisory hook for null result preservation.
# PostToolUse:Write|Edit hook. Warns when research files are written
# without corresponding open_questions tracking.
#
# Phase 2.1: advisory only (logs warnings, never blocks).
# Shadow mode: logs "would-have-blocked" events for 2 weeks before
# any promotion to blocking.
# Add --enforce flag support for future promotion.
#
# Wire in settings.json as:
# {"event": "PostToolUse", "matcher": {"tool_name": "Write|Edit"},
#  "hooks": [{"type": "command", "command": "bash scripts/hooks/null-result-advisory.sh"}]}

trap 'exit 0' ERR

INPUT=$(cat)

# Extract file path from tool input
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    result = data.get('tool_input', {}).get('file_path', '')
    print(result)
except Exception:
    pass
" 2>/dev/null)

# Only check research files
case "$FILE_PATH" in
    */research/*|*/analysis/*|*/briefs/*) ;;
    *) exit 0 ;;
esac

# Only check markdown files
case "$FILE_PATH" in
    *.md) ;;
    *) exit 0 ;;
esac

# Check if the file contains a claims table (researcher output)
if ! grep -q '| Claim |' "$FILE_PATH" 2>/dev/null; then
    exit 0
fi

# Check if there's an open_questions file nearby
DIR=$(dirname "$FILE_PATH")
PROJECT_ROOT=$(echo "$FILE_PATH" | sed 's|/research/.*||;s|/analysis/.*||;s|/briefs/.*||')

HAS_OQ=false
for candidate in "$DIR/open_questions.md" "$PROJECT_ROOT/open_questions.md" "$PROJECT_ROOT/docs/open_questions.md"; do
    if [ -f "$candidate" ]; then
        HAS_OQ=true
        break
    fi
done

if [ "$HAS_OQ" = "false" ]; then
    echo "⚠ Research file with claims table but no open_questions.md found."
    echo "  Null results and refutations are first-class knowledge."
    echo "  Consider: schemas/open_questions.md template for tracking question resolutions."
    echo "  (Advisory only — not blocking. See Phase 2.1 in epistemic v2 plan.)"

    # Log to epistemic-metrics.jsonl for shadow mode tracking
    python3 -c "
import json
from datetime import datetime
from pathlib import Path

entry = {
    'ts': datetime.now().isoformat(),
    'metric': 'hook_event',
    'hook_name': 'null-result-advisory',
    'triggered': True,
    'bypassed': False,
    'would_block': True,
    'file_path': '$FILE_PATH',
}
metrics = Path.home() / '.claude' / 'epistemic-metrics.jsonl'
with open(metrics, 'a') as f:
    f.write(json.dumps(entry) + '\n')
" 2>/dev/null
fi

exit 0
