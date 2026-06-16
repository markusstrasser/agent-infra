#!/usr/bin/env bash
# Symlink ~/Projects/skills into ~/.cursor/skills for Cursor Agent CLI parity.
# Run manually or from friend-sync. Idempotent.
set -euo pipefail

SRC="$HOME/Projects/skills"
DST="$HOME/.cursor/skills"
LINK=(
  research research-ops eval critique decide code-review cursor-agent
  verify-before execute improve observe sweep brainstorm analyze llmx-guide
)

mkdir -p "$DST"
for name in "${LINK[@]}"; do
  [ -f "$SRC/$name/SKILL.md" ] || continue
  ln -sfn "$SRC/$name" "$DST/$name"
done
echo "Cursor skills: $(find "$DST" -maxdepth 1 -type l | wc -l | tr -d ' ') symlinks in $DST"
