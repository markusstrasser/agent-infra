#!/usr/bin/env bash
# Push all main workspace repos (non-interactive).
#
# Usage:
#   ./scripts/git-push-all.sh              # push where ahead > 0
#   ./scripts/git-push-all.sh --dry-run
#   ./scripts/git-push-all.sh --status
#   ./scripts/git-push-all.sh -- origin main   # extra args → git push

set -uo pipefail

# Governed + shared infra (not every Projects/* mirror)
REPOS=(
    agent-infra
    intel
    genomics
    personal
    skills
    research-mcp
    llmx
    anim-workbench
    hutter
)

PROJECTS="${PROJECTS:-$HOME/Projects}"
dry_run=false
status_only=false
push_args=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) dry_run=true; shift ;;
        --status) status_only=true; shift ;;
        --) shift; push_args=("$@"); break ;;
        *) push_args+=("$1"); shift ;;
    esac
done

[[ ${#push_args[@]} -eq 0 ]] && push_args=(origin HEAD)

push_one() {
    local name="$1"
    local repo="$PROJECTS/$name"
    printf "  %-18s " "$name"

    if [[ ! -d "$repo/.git" ]]; then
        echo "skip (no repo)"
        return 0
    fi

    local branch ahead dirty upstream
    branch=$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    dirty=$(git -C "$repo" status --porcelain 2>/dev/null | wc -l | tr -d ' ')

    if ! upstream=$(git -C "$repo" rev-parse --abbrev-ref '@{u}' 2>/dev/null); then
        echo "skip (no upstream on $branch)"
        return 0
    fi

    ahead=$(git -C "$repo" rev-list --count '@{u}'..HEAD 2>/dev/null || echo 0)
    local behind
    behind=$(git -C "$repo" rev-list --count HEAD..'@{u}' 2>/dev/null || echo 0)

    if $status_only; then
        local extra=""
        [[ "$dirty" != "0" ]] && extra+=" dirty=$dirty"
        [[ "$ahead" != "0" ]] && extra+=" ahead=$ahead"
        [[ "$behind" != "0" ]] && extra+=" behind=$behind"
        [[ -z "$extra" ]] && extra=" in sync"
        echo "$branch$extra"
        return 0
    fi

    if [[ "$ahead" == "0" ]]; then
        echo "skip (nothing to push)"
        return 0
    fi

    if [[ "$dirty" != "0" ]]; then
        echo -n "dirty=$dirty "
    fi

    if $dry_run; then
        echo "would push $ahead → $upstream"
        return 0
    fi

    if git -C "$repo" push "${push_args[@]}" 2>&1 | tail -3; then
        echo "ok ($ahead pushed)"
    else
        echo "FAIL"
        return 1
    fi
}

failed=0
echo "=== push-all (main repos) ==="
for name in "${REPOS[@]}"; do
    push_one "$name" || failed=$((failed + 1))
done

if $status_only; then
    exit 0
fi

echo "=== done (${failed} failed) ==="
exit $(( failed > 0 ? 1 : 0 ))
