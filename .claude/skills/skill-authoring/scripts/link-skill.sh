#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SKILLS_DIR="${SKILLS_DIR:-$HOME/Projects/skills}"
PROJECT_SKILLS_DIR=".claude/skills"

# Helper functions
error() {
    echo -e "${RED}Error:${NC} $1" >&2
    exit 1
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

usage() {
    cat << 'EOF'
Usage: link-skill.sh [OPTIONS]

Manage individual skill symlinks for current project.

Options:
  -h, --help       Show this help message

Environment:
  SKILLS_DIR       Path to global skills directory
                   Default: $HOME/Projects/skills

Dependencies:
  gum - Install with: brew install gum

EOF
    exit 0
}

# Check if gum is available
has_gum() {
    command -v gum &> /dev/null
}

# Get list of available skills from global directory
get_available_skills() {
    if [[ ! -d "$SKILLS_DIR" ]]; then
        error "Global skills directory not found: $SKILLS_DIR"
    fi

    local skills=()
    for skill in "$SKILLS_DIR"/*; do
        if [[ -d "$skill" && -f "$skill/SKILL.md" ]]; then
            skills+=("$(basename "$skill")")
        fi
    done

    echo "${skills[@]}"
}

# Get skills that can be linked (exist in global but not in project)
get_linkable_skills() {
    local available
    read -ra available <<< "$(get_available_skills)"

    # If .claude/skills is itself a symlink, nothing is linkable
    if [[ -L "$PROJECT_SKILLS_DIR" ]]; then
        return 0
    fi

    local linkable=()
    for skill in "${available[@]}"; do
        if [[ ! -e "$PROJECT_SKILLS_DIR/$skill" ]]; then
            linkable+=("$skill")
        fi
    done

    echo "${linkable[@]}"
}

# Get skills that are currently symlinked
get_linked_skills() {
    # If .claude/skills is itself a symlink, don't look inside
    if [[ -L "$PROJECT_SKILLS_DIR" ]]; then
        return 0
    fi

    if [[ ! -d "$PROJECT_SKILLS_DIR" ]]; then
        return 0
    fi

    local linked=()
    for skill in "$PROJECT_SKILLS_DIR"/*; do
        if [[ -L "$skill" ]]; then
            linked+=("$(basename "$skill")")
        fi
    done

    echo "${linked[@]}"
}

# Get local skills (exist but aren't symlinks)
get_local_skills() {
    # If .claude/skills is itself a symlink, don't look inside
    if [[ -L "$PROJECT_SKILLS_DIR" ]]; then
        return 0
    fi

    if [[ ! -d "$PROJECT_SKILLS_DIR" ]]; then
        return 0
    fi

    local local_skills=()
    for skill in "$PROJECT_SKILLS_DIR"/*; do
        if [[ -d "$skill" && ! -L "$skill" && -f "$skill/SKILL.md" ]]; then
            local_skills+=("$(basename "$skill")")
        fi
    done

    echo "${local_skills[@]}"
}

# Link a skill
link_skill() {
    local skill_name="$1"
    local source="$SKILLS_DIR/$skill_name"
    local target="$PROJECT_SKILLS_DIR/$skill_name"

    # Ensure .claude/skills exists
    mkdir -p "$PROJECT_SKILLS_DIR" || return 1

    # Use absolute path
    ln -s "$source" "$target" || return 1

    return 0
}

# Unlink a skill
unlink_skill() {
    local skill_name="$1"
    local target="$PROJECT_SKILLS_DIR/$skill_name"

    if [[ -L "$target" ]]; then
        rm "$target" || return 1
        return 0
    fi

    return 1
}

# Unlink entire skills directory
unlink_skills_dir() {
    if [[ -L "$PROJECT_SKILLS_DIR" ]]; then
        rm "$PROJECT_SKILLS_DIR"
    fi
}

# Check if skill is in .gitignore
is_in_gitignore() {
    local skill_name="$1"
    local gitignore=".gitignore"

    if [[ ! -f "$gitignore" ]]; then
        return 1
    fi

    # Check for exact matches or patterns that would match
    local pattern="${PROJECT_SKILLS_DIR}/${skill_name}"
    if grep -q "^${pattern}\$" "$gitignore" 2>/dev/null || \
       grep -q "^${pattern}/\$" "$gitignore" 2>/dev/null || \
       grep -q "^\.claude/skills/\*\$" "$gitignore" 2>/dev/null || \
       grep -q "^\.claude/skills/\$" "$gitignore" 2>/dev/null; then
        return 0
    fi

    return 1
}

# Add skills to .gitignore
add_to_gitignore() {
    local skills=("$@")
    local gitignore=".gitignore"

    # Create .gitignore if it doesn't exist
    if [[ ! -f "$gitignore" ]]; then
        touch "$gitignore"
    fi

    # Add header comment if not already present
    if ! grep -q "# Claude Code skills" "$gitignore" 2>/dev/null; then
        echo "" >> "$gitignore"
        echo "# Claude Code skills (symlinked)" >> "$gitignore"
    fi

    # Add each skill
    for skill in "${skills[@]}"; do
        echo "${PROJECT_SKILLS_DIR}/${skill}" >> "$gitignore"
    done

    success "Added ${#skills[@]} skill(s) to .gitignore"
}

# Interactive menu
interactive_menu() {
    if ! has_gum; then
        error "gum is not installed. Install with: brew install gum"
    fi

    # Check if .claude/skills is a directory symlink
    if [[ -L "$PROJECT_SKILLS_DIR" ]]; then
        warning ".claude/skills is a directory symlink to: $(readlink "$PROJECT_SKILLS_DIR")"
        echo
        info "This script manages individual skill symlinks, not directory symlinks."
        echo
        if gum confirm "Remove directory symlink and switch to individual skill management?"; then
            unlink_skills_dir
            info "Directory symlink removed. Run script again to manage individual skills."
        fi
        exit 0
    fi

    # Get skill lists
    local linkable linked local_skills
    read -ra linkable <<< "$(get_linkable_skills)"
    read -ra linked <<< "$(get_linked_skills)"
    read -ra local_skills <<< "$(get_local_skills)"

    # Build menu
    local options=()

    # LINK section
    if [[ ${#linkable[@]} -gt 0 ]]; then
        options+=("━━━ LINK ━━━")
        for skill in "${linkable[@]}"; do
            options+=("  $skill")
        done
    fi

    # UNLINK section
    if [[ ${#linked[@]} -gt 0 ]]; then
        options+=("━━━ UNLINK ━━━")
        for skill in "${linked[@]}"; do
            options+=("  $skill")
        done
    fi

    # LOCAL SKILLS section (informational)
    if [[ ${#local_skills[@]} -gt 0 ]]; then
        options+=("━━━ LOCAL SKILLS ━━━")
        for skill in "${local_skills[@]}"; do
            options+=("  $skill (local)")
        done
    fi

    if [[ ${#options[@]} -eq 0 ]]; then
        info "No skills available to link or unlink"
        exit 0
    fi

    # Show multi-select
    local selected
    selected=$(printf '%s\n' "${options[@]}" | gum choose --no-limit)

    # Check if user made any selection
    if [[ -z "$selected" ]]; then
        info "No changes made"
        exit 0
    fi

    echo
    info "Processing selections..."

    # Debug: show what was selected
    echo "DEBUG: Selected items:" >&2
    echo "$selected" | while IFS= read -r line; do
        echo "  [$line]" >&2
    done
    echo >&2

    # Process selections
    local newly_linked=()
    local processed_count=0

    while IFS= read -r line; do
        echo "DEBUG: Processing line: [$line]" >&2

        # Skip empty lines
        if [[ -z "$line" ]]; then
            echo "DEBUG: Skipping empty line" >&2
            continue
        fi

        # Skip section headers (shouldn't be selected but just in case)
        if [[ "$line" == "━━━"* ]]; then
            echo "DEBUG: Skipping section header" >&2
            continue
        fi

        # Extract skill name (remove leading spaces and "(local)" suffix)
        local skill_name
        skill_name=$(echo "$line" | sed 's/^  //' | sed 's/ (local)$//')
        echo "DEBUG: Extracted skill_name: [$skill_name]" >&2

        # Skip if skill name is empty
        if [[ -z "$skill_name" ]]; then
            echo "DEBUG: Skill name is empty after extraction" >&2
            continue
        fi

        # Determine action based on current state, not section headers
        local target="$PROJECT_SKILLS_DIR/$skill_name"
        echo "DEBUG: Target: $target" >&2

        if [[ -L "$target" ]]; then
            echo "DEBUG: Target is symlink, unlinking" >&2
            # It's a symlink → unlink it
            if unlink_skill "$skill_name"; then
                success "Unlinked: $skill_name"
                ((processed_count++)) || true
            else
                warning "Failed to unlink: $skill_name"
            fi
        elif [[ -d "$target" ]]; then
            echo "DEBUG: Target is directory, skipping" >&2
            # It's a directory (local skill) → skip
            warning "Skipping local skill: $skill_name (not a symlink)"
        else
            echo "DEBUG: Target doesn't exist, linking" >&2
            # Doesn't exist → link it
            if link_skill "$skill_name"; then
                success "Linked: $skill_name"
                newly_linked+=("$skill_name")
                ((processed_count++)) || true
            else
                warning "Failed to link: $skill_name"
            fi
        fi
        echo "DEBUG: Finished processing $skill_name" >&2
    done <<< "$selected"

    echo "DEBUG: Exited loop" >&2

    if [[ $processed_count -eq 0 ]]; then
        warning "No skills were linked or unlinked"
        exit 0
    fi

    echo
    success "Processed $processed_count skill(s)"

    # Check .gitignore for newly linked skills
    if [[ ${#newly_linked[@]} -gt 0 ]]; then
        local needs_gitignore=()
        for skill in "${newly_linked[@]}"; do
            if ! is_in_gitignore "$skill"; then
                needs_gitignore+=("$skill")
            fi
        done

        if [[ ${#needs_gitignore[@]} -gt 0 ]]; then
            echo
            warning "The following skills are not in .gitignore:"
            for skill in "${needs_gitignore[@]}"; do
                echo "  - ${PROJECT_SKILLS_DIR}/${skill}"
            done
            echo

            if gum confirm "Add to .gitignore?"; then
                add_to_gitignore "${needs_gitignore[@]}"
            fi
        fi
    fi
}

# Main logic
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                usage
                ;;
            *)
                error "Unknown option: $1\n\nRun with --help for usage."
                ;;
        esac
    done

    interactive_menu
}

# Run main
main "$@"
