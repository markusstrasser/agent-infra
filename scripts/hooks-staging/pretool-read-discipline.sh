#!/usr/bin/env bash
# PreToolUse:Read — telemetry on full-file reads + advisory on repeats.
# Appends shadow log to ~/.claude/read-discipline-shadow.jsonl for analysis.
# Reads /tmp/claude-read-tracker-$PPID (written by posttool-dup-read.sh) for repeat detection.
# Advisory only — NEVER blocks (exit 0 always).

trap 'exit 0' ERR

INPUT=$(cat)
FPATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null)
[ -z "$FPATH" ] && exit 0

HAS_OFFSET=$(echo "$INPUT" | jq -r '.tool_input.offset // empty' 2>/dev/null)
HAS_LIMIT=$(echo "$INPUT" | jq -r '.tool_input.limit // empty' 2>/dev/null)

# Only act on full-file reads (no offset, no limit)
[ -n "$HAS_OFFSET" ] || [ -n "$HAS_LIMIT" ] && exit 0

EXT="${FPATH##*.}"
[ "$EXT" = "$FPATH" ] && EXT=""  # no extension

READS_FILE="/tmp/claude-read-tracker-${PPID}"
SHADOW="$HOME/.claude/read-discipline-shadow.jsonl"

# Count prior full-file reads of this exact path from the tracker
# Tracker format: "filepath:offset:limit" per line; full reads have empty offset+limit
PRIOR_FULL=0
if [ -f "$READS_FILE" ]; then
    # Fix: grep -c outputs 0 on no-match AND || echo 0 fires, giving "0\n0".
    # Use subshell to capture cleanly. (GPT-5.4 review finding #6)
    PRIOR_FULL=$(grep -cF "${FPATH}::" "$READS_FILE" 2>/dev/null)
    PRIOR_FULL="${PRIOR_FULL:-0}"
fi

# Log telemetry (use python3 for safe JSON encoding of file path)
python3 -c "
import json,sys,os
from datetime import datetime,timezone
print(json.dumps({
    'ts': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'file': sys.argv[1], 'ext': '.'+sys.argv[2],
    'has_offset': False, 'has_limit': False,
    'ppid': sys.argv[3], 'session_read_count': int(sys.argv[4])
}))
" "$FPATH" "$EXT" "$PPID" "$((PRIOR_FULL + 1))" >> "$SHADOW" 2>/dev/null || true

# Advisory if repeat full-file read
if [ "$PRIOR_FULL" -ge 1 ]; then
    BASENAME="${FPATH##*/}"
    MSG="Read discipline: $BASENAME was already read in full this session ($((PRIOR_FULL + 1))x). Consider using offset/limit to read specific sections, or Grep to find what you need."
    SAFE=$(echo "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
    echo "{\"additionalContext\": ${SAFE}}"
    TRIGGER="$HOME/Projects/skills/hooks/hook-trigger-log.sh"
    [ -x "$TRIGGER" ] && "$TRIGGER" "read-discipline" "warn" "$BASENAME reads=$((PRIOR_FULL + 1))" 2>/dev/null || true
fi

exit 0
