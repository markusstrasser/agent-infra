#!/usr/bin/env bash
# pertinent-negatives-advisory.sh — Advisory hook for pertinent negatives.
# PostToolUse:Write|Edit hook. Warns when thesis-level analysis files
# are written without pertinent negatives.
#
# Phase 2.2: advisory only (logs warnings, never blocks).
# Lightweight — not full Wigmore charts (formalization tax kills adoption).

trap 'exit 0' ERR

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except Exception:
    pass
" 2>/dev/null)

# Only check thesis-level files (thesis checks, investment memos)
case "$FILE_PATH" in
    *thesis*|*_MEMO_*|*/briefs/*) ;;
    *) exit 0 ;;
esac

case "$FILE_PATH" in
    *.md|*.json) ;;
    *) exit 0 ;;
esac

# Check if a pertinent_negatives file exists alongside
DIR=$(dirname "$FILE_PATH")
BASE=$(basename "$FILE_PATH" .md)

HAS_PN=false
for candidate in "$DIR/${BASE}_negatives.json" "$DIR/pertinent_negatives.json" "$DIR/../pertinent_negatives.json"; do
    if [ -f "$candidate" ]; then
        HAS_PN=true
        break
    fi
done

# Also check if the file itself contains a "Pertinent Negatives" section
if grep -qi "pertinent negative" "$FILE_PATH" 2>/dev/null; then
    HAS_PN=true
fi

if [ "$HAS_PN" = "false" ]; then
    echo "⚠ Thesis-level analysis without pertinent negatives."
    echo "  What would you expect to see if the thesis were TRUE? What's absent?"
    echo "  Schema: schemas/pertinent_negatives.json"
    echo "  (Advisory only — not blocking.)"

    python3 -c "
import json
from datetime import datetime
from pathlib import Path

entry = {
    'ts': datetime.now().isoformat(),
    'metric': 'hook_event',
    'hook_name': 'pertinent-negatives-advisory',
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
