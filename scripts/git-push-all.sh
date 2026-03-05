#!/usr/bin/env bash
# Push all relevant repos (selve, genomics, intel, sean, meta, skills)
#
# Usage: ./scripts/git-push-all.sh [--dry-run|--status]

set -euo pipefail

REPOS=(
    "$HOME/Projects/selve"
    "$HOME/Projects/genomics"
    "$HOME/Projects/intel"
    "$HOME/Projects/sean"
    "$HOME/Projects/meta"
    "$HOME/Projects/skills"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

dry_run=false
status_only=false

# Parse args
for arg in "${@:-}"; do
    case "$arg" in
        --dry-run) dry_run=true ;;
        --status) status_only=true ;;
    esac
done

push_repo() {
    local repo="$1"
    local name
    name=$(basename "$repo")
    
    echo -e "${BLUE}━━━ $name ━━━${NC}"
    
    if [[ ! -d "$repo/.git" ]]; then
        echo -e "${RED}  ✗ Not a git repo${NC}"
        echo
        return 1
    fi
    
    cd "$repo"
    
    # Check current branch
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    
    # Check for uncommitted changes
    local has_changes=false
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        has_changes=true
    fi
    
    # Check for unpushed commits
    local has_unpushed=false
    local unpushed_count=0
    if git rev-parse --abbrev-ref --symbolic-full-name @{u} &>/dev/null; then
        unpushed_count=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo 0)
        if [[ "$unpushed_count" -gt 0 ]]; then
            has_unpushed=true
        fi
        unpushed_count=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0)
        if [[ "$unpushed_count" -gt 0 ]]; then
            has_unpushed=true
        fi
    else
        # No upstream set
        unpushed_count=$(git rev-list --count --remotes --not HEAD 2>/dev/null || echo 0)
        if [[ "$unpushed_count" -gt 0 ]]; then
            has_unpushed=true
        fi
    fi
    
    # Get ahead/behind counts
    local ahead=0 behind=0
    if git rev-parse --abbrev-ref --symbolic-full-name @{u} &>/dev/null; then
        ahead=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0)
        behind=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo 0)
    fi
    
    # Display status
    echo "  Branch: $branch"
    
    if $has_changes; then
        local change_count
        change_count=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
        echo -e "  ${YELLOW}⚡ Uncommitted: $change_count files${NC}"
    else
        echo -e "  ${GREEN}✓ Clean working tree${NC}"
    fi
    
    if [[ "$ahead" -gt 0 ]]; then
        echo -e "  ${YELLOW}↑ $ahead commits ahead of remote${NC}"
    elif [[ "$behind" -gt 0 ]]; then
        echo -e "  ${YELLOW}↓ $behind commits behind remote${NC}"
    else
        echo -e "  ${GREEN}✓ In sync with remote${NC}"
    fi
    
    if $status_only; then
        echo
        return 0
    fi
    
    # Commit message prompt if there are changes
    if $has_changes; then
        echo
        echo -n "  Commit message (or 'skip' to skip, 'add' to add all): "
        read -r msg
        
        if [[ "$msg" == "skip" ]]; then
            echo "  Skipping commit"
        elif [[ "$msg" == "add" ]]; then
            echo -n "  Enter commit message: "
            read -r msg
            if [[ -n "$msg" ]]; then
                if $dry_run; then
                    echo "  [DRY RUN] Would: git add -A && git commit -m '$msg'"
                else
                    git add -A
                    git commit -m "$msg" && echo -e "  ${GREEN}✓ Committed${NC}"
                fi
            fi
        elif [[ -n "$msg" ]]; then
            if $dry_run; then
                echo "  [DRY RUN] Would: git commit -am '$msg'"
            else
                git commit -am "$msg" && echo -e "  ${GREEN}✓ Committed${NC}"
            fi
        fi
    fi
    
    # Push if there are unpushed commits or we just committed
    if [[ "$ahead" -gt 0 ]] || { ! $status_only && $has_changes && [[ "${msg:-}" != "skip" ]]; }; then
        if $dry_run; then
            echo "  [DRY RUN] Would: git push origin $branch"
        else
            if git push origin "$branch" 2>&1 | head -5; then
                echo -e "  ${GREEN}✓ Pushed to origin/$branch${NC}"
            else
                echo -e "  ${RED}✗ Push failed${NC}"
            fi
        fi
    fi
    
    echo
}

# Main
if $dry_run; then
    echo -e "${YELLOW}=== DRY RUN MODE ===${NC}"
    echo
elif $status_only; then
    echo -e "${BLUE}=== Git Status Overview ===${NC}"
    echo
fi

for repo in "${REPOS[@]}"; do
    push_repo "$repo"
done

echo -e "${GREEN}Done.${NC}"
