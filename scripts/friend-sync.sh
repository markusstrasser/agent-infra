#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Friend Infra Sync — pull repos, update tools, link new skills, report drift
# Run: ~/.local/bin/friend-sync.sh          (manual)
#      launchd runs daily at 06:00          (automatic)
# ============================================================================

BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
skip() { echo -e "  ${DIM}⊘${RESET} $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET} $1"; }
fail() { echo -e "  ${RED}✗${RESET} $1"; }
step() { echo -e "\n${BOLD}$1${RESET}"; }

PROJECTS="$HOME/Projects"
GITHUB_USER="markusstrasser"
LOG_FILE="$HOME/.local/log/friend-sync.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Timestamp for log
echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---" >> "$LOG_FILE"

# ── 1. Pull repos ───────────────────────────────────────────

step "Repos"

REPOS=(agent-infra skills research-mcp biomedical-mcp llmx emb parsers)
pulled=0
failed=0

for repo in "${REPOS[@]}"; do
    dir="$PROJECTS/$repo"
    if [ ! -d "$dir/.git" ]; then
        # Auto-clone if missing
        if git clone "git@github.com:${GITHUB_USER}/${repo}.git" "$dir" 2>/dev/null; then
            ok "$repo — cloned"
            pulled=$((pulled + 1))
        else
            warn "$repo — not found, clone failed"
            failed=$((failed + 1))
        fi
        continue
    fi

    # Check for local uncommitted changes
    if [ -n "$(git -C "$dir" status --porcelain 2>/dev/null)" ]; then
        skip "$repo — dirty working tree"
        continue
    fi

    before=$(git -C "$dir" rev-parse HEAD 2>/dev/null)
    if git -C "$dir" pull --ff-only --quiet 2>/dev/null; then
        after=$(git -C "$dir" rev-parse HEAD 2>/dev/null)
        if [ "$before" != "$after" ]; then
            count=$(git -C "$dir" rev-list --count "${before}..${after}" 2>/dev/null || echo "?")
            ok "$repo — ${count} new commits"
            pulled=$((pulled + 1))
        else
            skip "$repo — up to date"
        fi
    else
        warn "$repo — ff-only failed (diverged?)"
        failed=$((failed + 1))
    fi
done

# ── 2. Update CLI tools ─────────────────────────────────────

step "CLI tools"

# npm global packages
for pkg in @anthropic-ai/claude-code @google/gemini-cli @openai/codex; do
    name=$(echo "$pkg" | sed 's|.*/||')
    current=$(npm list -g "$pkg" --depth=0 2>/dev/null | grep "$pkg" | sed 's/.*@//' || echo "?")
    latest=$(npm view "$pkg" version 2>/dev/null || echo "?")
    if [ "$current" = "$latest" ]; then
        skip "$name $current"
    elif [ "$latest" != "?" ]; then
        npm install -g "$pkg" --quiet 2>/dev/null && ok "$name → $latest" || warn "$name update failed"
    else
        skip "$name — can't check version"
    fi
done

# Python tools (editable from local clones)
for tool in llmx emb parsers; do
    dir="$PROJECTS/$tool"
    if [ -d "$dir" ]; then
        uv tool install --editable "$dir" --quiet 2>/dev/null && ok "$tool (editable)" || skip "$tool — no changes"
    fi
done

# ── 3. Sync MCP dependencies ────────────────────────────────

step "MCP deps"

for mcp_dir in research-mcp agent-infra biomedical-mcp; do
    dir="$PROJECTS/$mcp_dir"
    if [ -d "$dir/pyproject.toml" ] || [ -d "$dir" ]; then
        (cd "$dir" && uv sync --quiet 2>/dev/null) && ok "$mcp_dir" || warn "$mcp_dir sync failed"
    fi
done

# ── 4. Link new skills ──────────────────────────────────────

step "Skills"

SKILLS_SRC="$PROJECTS/skills"
SKILLS_DST="$HOME/.claude/skills"
SKIP_DIRS="hooks|archive|goals|__pycache__|node_modules|\\.git"

if [ -d "$SKILLS_SRC" ]; then
    mkdir -p "$SKILLS_DST"
    new_skills=0
    for skill_dir in "$SKILLS_SRC"/*/; do
        skill=$(basename "$skill_dir")
        # Skip non-skill directories
        echo "$skill" | grep -qE "^($SKIP_DIRS)$" && continue
        # Skip if no SKILL.md (not a real skill)
        [ -f "$skill_dir/SKILL.md" ] || continue

        if [ -L "$SKILLS_DST/$skill" ]; then
            # Verify symlink target is correct
            target=$(readlink "$SKILLS_DST/$skill")
            if [ "$target" != "$skill_dir" ] && [ "$target" != "${skill_dir%/}" ]; then
                ln -sf "$skill_dir" "$SKILLS_DST/$skill"
                ok "$skill — relinked"
                new_skills=$((new_skills + 1))
            fi
        elif [ ! -e "$SKILLS_DST/$skill" ]; then
            ln -sf "$skill_dir" "$SKILLS_DST/$skill"
            ok "$skill — NEW"
            new_skills=$((new_skills + 1))
        fi
    done

    # Remove dead symlinks (skills deleted upstream)
    for link in "$SKILLS_DST"/*/; do
        [ -L "${link%/}" ] && [ ! -e "${link%/}" ] && {
            rm "${link%/}"
            warn "$(basename "${link%/}") — removed (deleted upstream)"
        }
    done

    if [ "$new_skills" -eq 0 ]; then
        total=$(find "$SKILLS_DST" -maxdepth 1 -type l | wc -l | tr -d ' ')
        skip "all $total skills linked"
    fi
else
    warn "skills repo not found at $SKILLS_SRC"
fi

# ── 5. Version report ───────────────────────────────────────

step "Versions"

claude_v=$(claude --version 2>/dev/null | head -1 || echo "?")
gemini_v=$(gemini --version 2>/dev/null | head -1 || echo "?")
codex_v=$(codex --version 2>/dev/null | head -1 || echo "?")
llmx_v=$(llmx --version 2>/dev/null | head -1 || echo "?")

echo -e "  claude  ${DIM}${claude_v}${RESET}"
echo -e "  gemini  ${DIM}${gemini_v}${RESET}"
echo -e "  codex   ${DIM}${codex_v}${RESET}"
echo -e "  llmx    ${DIM}${llmx_v}${RESET}"
echo -e "  uv      ${DIM}$(uv --version 2>&1 | head -1)${RESET}"
echo -e "  node    ${DIM}$(node --version 2>/dev/null)${RESET}"

# ── 6. MCP health check ─────────────────────────────────────

step "MCP servers"

# Check configured servers via claude mcp list (if available)
if command -v claude &>/dev/null; then
    servers=$(claude mcp list 2>/dev/null || echo "")
    if [ -n "$servers" ]; then
        echo -e "  ${DIM}${servers}${RESET}"
    else
        skip "couldn't list MCP servers"
    fi
fi

# ── 7. Settings drift detection ──────────────────────────────

step "Settings"

SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
    hook_count=$(jq '[.hooks // {} | to_entries[] | .value[] | .hooks[]?] | length' "$SETTINGS" 2>/dev/null || echo "?")
    has_statusline=$(jq -r '.statusLine.command // "none"' "$SETTINGS" 2>/dev/null)
    plugin_count=$(jq '[.enabledPlugins // {} | to_entries[] | select(.value == true)] | length' "$SETTINGS" 2>/dev/null || echo "?")
    echo -e "  hooks: ${DIM}${hook_count}${RESET}  plugins: ${DIM}${plugin_count}${RESET}  statusLine: ${DIM}${has_statusline}${RESET}"
else
    warn "no settings.json found"
fi

# ── Summary ──────────────────────────────────────────────────

echo ""
echo -e "${BOLD}Done.${RESET} ${pulled} repos updated, ${failed} failures."
echo "$(date '+%Y-%m-%d %H:%M') — ${pulled} updated, ${failed} failed" >> "$LOG_FILE"
