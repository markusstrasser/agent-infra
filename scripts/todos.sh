#!/usr/bin/env bash
# Cross-project backlog aggregator
# Scans all projects for ## Backlog sections in CLAUDE.md and standalone TODOS.md
#
# Usage: ./scripts/todos.sh [--counts]

set -euo pipefail

PROJECTS=(
    "$HOME/Projects/agent-infra"
    "$HOME/Projects/intel"
    "$HOME/Projects/phenome"
    "$HOME/Projects/genomics"
    "$HOME/Projects/skills"
    "$HOME/Projects/anki"
    "$HOME/Projects/sean"
)

counts_only=false
[[ "${1:-}" == "--counts" ]] && counts_only=true

for project in "${PROJECTS[@]}"; do
    name=$(basename "$project")
    claude_md="$project/CLAUDE.md"
    todos_md="$project/TODOS.md"

    open=0
    done=0
    items=()

    # Extract ## Backlog section from CLAUDE.md
    if [[ -f "$claude_md" ]]; then
        in_backlog=false
        while IFS= read -r line; do
            if [[ "$line" =~ ^##[[:space:]]+Backlog ]]; then
                in_backlog=true
                continue
            fi
            if $in_backlog && [[ "$line" =~ ^## ]]; then
                break
            fi
            if $in_backlog; then
                if [[ "$line" =~ ^-\ \[\ \] ]]; then
                    ((open++)) || true
                    items+=("$line")
                elif [[ "$line" =~ ^-\ \[x\] ]]; then
                    ((done++)) || true
                fi
            fi
        done < "$claude_md"
    fi

    # Count TODOS.md if it exists
    todos_open=0
    todos_done=0
    if [[ -f "$todos_md" ]]; then
        todos_open=$(grep -c '^\- \[ \]' "$todos_md" 2>/dev/null || echo 0)
        todos_done=$(grep -c '^\- \[x\]' "$todos_md" 2>/dev/null || echo 0)
    fi

    total_open=$((open + todos_open))
    total_done=$((done + todos_done))

    if [[ $total_open -eq 0 && $total_done -eq 0 ]]; then
        continue
    fi

    if $counts_only; then
        printf "%-12s %3d open  %3d done" "$name" "$total_open" "$total_done"
        [[ $todos_open -gt 0 ]] && printf "  (TODOS.md: %d)" "$todos_open"
        printf "\n"
    else
        echo "━━━ $name ($total_open open, $total_done done) ━━━"
        for item in "${items[@]}"; do
            echo "  $item"
        done
        if [[ $todos_open -gt 0 ]]; then
            echo "  ... +${todos_open} more in TODOS.md"
        fi
        echo
    fi
done
