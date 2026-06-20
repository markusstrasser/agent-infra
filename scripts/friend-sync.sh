#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Friend Infra Sync — pull repos, update tools, link new skills, report drift
# Run: friend-sync.sh                       (symlinked into ~/.local/bin)
#      DRY_RUN=1 friend-sync.sh             (preview everything, mutate nothing)
# Note: not currently scheduled — run manually.
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
would() { echo -e "  ${YELLOW}↪${RESET} ${DIM}would${RESET} $1"; }

# DRY_RUN=1 → probe everything read-only (real git fetch + version checks),
# print what WOULD happen, mutate nothing. Usage: DRY_RUN=1 friend-sync.sh
DRY_RUN="${DRY_RUN:-0}"

PROJECTS="$HOME/Projects"
GITHUB_USER="markusstrasser"
LOG_FILE="$HOME/.local/log/friend-sync.log"
mkdir -p "$(dirname "$LOG_FILE")"

if [ "$DRY_RUN" = "1" ]; then
    echo -e "${BOLD}${YELLOW}DRY RUN${RESET} ${DIM}— probing read-only, nothing will be changed${RESET}"
else
    # Timestamp for log
    echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---" >> "$LOG_FILE"
fi

# ── 1. Pull repos ───────────────────────────────────────────

step "Repos"

REPOS=(agent-infra skills research-mcp biomedical-mcp llmx emb parsers)
pulled=0
failed=0

for repo in "${REPOS[@]}"; do
    dir="$PROJECTS/$repo"
    if [ ! -d "$dir/.git" ]; then
        if [ "$DRY_RUN" = "1" ]; then
            would "clone $repo from git@github.com:${GITHUB_USER}/${repo}.git"
            continue
        fi
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

    if [ "$DRY_RUN" = "1" ]; then
        git -C "$dir" fetch --quiet 2>/dev/null || true   # read-only: updates refs, not working tree
        before=$(git -C "$dir" rev-parse HEAD 2>/dev/null)
        upstream=$(git -C "$dir" rev-parse '@{u}' 2>/dev/null || echo "$before")
        if [ "$before" != "$upstream" ]; then
            count=$(git -C "$dir" rev-list --count "${before}..${upstream}" 2>/dev/null || echo "?")
            would "pull $repo — ${count} new commits"
        else
            skip "$repo — up to date"
        fi
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

export PATH="$HOME/.local/bin:$PATH"

# Claude Code (native — auto-updates in background; friend-sync nudges explicitly)
if [ "$DRY_RUN" = "1" ] && command -v claude &>/dev/null; then
    before=$(claude --version 2>/dev/null | sed 's/ (Claude Code)//' | head -1 || echo "?")
    would "run: claude update (current $before)"
elif command -v claude &>/dev/null && [ -d "$HOME/.local/share/claude" ]; then
    before=$(claude --version 2>/dev/null | sed 's/ (Claude Code)//' | head -1 || echo "?")
    if claude update &>/dev/null; then
        after=$(claude --version 2>/dev/null | sed 's/ (Claude Code)//' | head -1 || echo "?")
        if [ "$before" = "$after" ]; then
            skip "claude-code $after"
        else
            ok "claude-code $before → $after"
        fi
    else
        warn "claude-code update failed ($before)"
    fi
elif command -v claude &>/dev/null; then
    warn "claude-code via npm/legacy — reinstall: curl -fsSL https://claude.ai/install.sh | bash"
    if npm list -g @anthropic-ai/claude-code --depth=0 &>/dev/null 2>&1; then
        npm uninstall -g @anthropic-ai/claude-code 2>/dev/null || true
    fi
    curl -fsSL https://claude.ai/install.sh | bash 2>/dev/null \
        && ok "claude-code migrated to native $(claude --version 2>/dev/null | sed 's/ (Claude Code)//' | head -1)" \
        || warn "claude-code native install failed"
else
    curl -fsSL https://claude.ai/install.sh | bash 2>/dev/null \
        && ok "claude-code installed $(claude --version 2>/dev/null | sed 's/ (Claude Code)//' | head -1)" \
        || warn "claude-code install failed"
fi

# npm global packages (gemini, codex)
for pkg in @google/gemini-cli @openai/codex; do
    name=$(echo "$pkg" | sed 's|.*/||')
    current=$(npm list -g "$pkg" --depth=0 2>/dev/null | grep "$pkg" | sed 's/.*@//' || echo "?")
    latest=$(npm view "$pkg" version 2>/dev/null || echo "?")
    if [ "$current" = "$latest" ]; then
        skip "$name $current"
    elif [ "$latest" != "?" ]; then
        if [ "$DRY_RUN" = "1" ]; then
            would "update $name $current → $latest"
        else
            npm install -g "$pkg" --quiet 2>/dev/null && ok "$name → $latest" || warn "$name update failed"
        fi
    else
        skip "$name — can't check version"
    fi
done

# Python tools (editable from local clones)
for tool in llmx emb parsers; do
    dir="$PROJECTS/$tool"
    if [ -d "$dir" ]; then
        if [ "$DRY_RUN" = "1" ]; then
            would "uv tool install --editable $tool"
        else
            uv tool install --editable "$dir" --quiet 2>/dev/null && ok "$tool (editable)" || skip "$tool — no changes"
        fi
    fi
done

# ── 3. Sync MCP dependencies ────────────────────────────────

step "MCP deps"

for mcp_dir in research-mcp agent-infra biomedical-mcp; do
    dir="$PROJECTS/$mcp_dir"
    if [ -d "$dir/pyproject.toml" ] || [ -d "$dir" ]; then
        if [ "$DRY_RUN" = "1" ]; then
            would "uv sync in $mcp_dir"
        else
            (cd "$dir" && uv sync --quiet 2>/dev/null) && ok "$mcp_dir" || warn "$mcp_dir sync failed"
        fi
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
                if [ "$DRY_RUN" = "1" ]; then
                    would "relink $skill"
                else
                    ln -sf "$skill_dir" "$SKILLS_DST/$skill"
                    ok "$skill — relinked"
                fi
                new_skills=$((new_skills + 1))
            fi
        elif [ ! -e "$SKILLS_DST/$skill" ]; then
            if [ "$DRY_RUN" = "1" ]; then
                would "link NEW skill $skill"
            else
                ln -sf "$skill_dir" "$SKILLS_DST/$skill"
                ok "$skill — NEW"
            fi
            new_skills=$((new_skills + 1))
        fi
    done

    # Remove dead symlinks (skills deleted upstream)
    for link in "$SKILLS_DST"/*/; do
        [ -L "${link%/}" ] && [ ! -e "${link%/}" ] && {
            if [ "$DRY_RUN" = "1" ]; then
                would "remove dead link $(basename "${link%/}") (deleted upstream)"
            else
                rm "${link%/}"
                warn "$(basename "${link%/}") — removed (deleted upstream)"
            fi
        }
    done

    if [ "$new_skills" -eq 0 ]; then
        total=$(find "$SKILLS_DST" -maxdepth 1 -type l | wc -l | tr -d ' ')
        skip "all $total skills linked"
    fi

    # Codex discovery paths mirror Claude global set (~/.agents/skills primary)
    if [ -f "$PROJECTS/agent-infra/scripts/sync_agent_skills.py" ]; then
        if [ "$DRY_RUN" = "1" ]; then
            would "run sync_agent_skills.py (Codex skill discovery paths)"
        else
            (cd "$PROJECTS/agent-infra" && uv run python3 scripts/sync_agent_skills.py 2>&1 | sed 's/^/  /') || true
        fi
    fi
else
    warn "skills repo not found at $SKILLS_SRC"
fi

# ── 4c. LaunchAgents plists (ops/launchd → ~/Library/LaunchAgents) ──

step "LaunchAgents plists"

LAUNCHD_SRC="$PROJECTS/agent-infra/ops/launchd"
LAUNCHD_DST="$HOME/Library/LaunchAgents"
if [ -d "$LAUNCHD_SRC" ]; then
    mkdir -p "$LAUNCHD_DST"
    synced=0
    for src in "$LAUNCHD_SRC"/com.agent-infra.*.plist; do
        [ -f "$src" ] || continue
        base=$(basename "$src")
        dst="$LAUNCHD_DST/$base"
        if [ ! -f "$dst" ] || ! cmp -s "$src" "$dst"; then
            if [ "$DRY_RUN" = "1" ]; then
                would "sync plist $base → $LAUNCHD_DST"
            else
                cp "$src" "$dst"
                label="${base%.plist}"
                ok "$base — synced (reload: launchctl kickstart -k gui/$(id -u)/$label)"
            fi
            synced=$((synced + 1))
        fi
    done
    [ "$synced" -eq 0 ] && skip "all LaunchAgents plists match ops/launchd"
else
    skip "ops/launchd not found"
fi

# ── 4a. Cursor skills parity ────────────────────────────────────

step "Cursor skills"
AI_DIR="$PROJECTS/agent-infra"
if [ -x "$AI_DIR/scripts/cursor-skills-sync.sh" ]; then
    if [ "$DRY_RUN" = "1" ]; then
        would "run cursor-skills-sync.sh"
    else
        bash "$AI_DIR/scripts/cursor-skills-sync.sh" | sed 's/^/  /'
        ok "cursor skills synced"
    fi
else
    skip "cursor-skills-sync.sh not found"
fi

# ── 4b. Codex parity (mirror .claude/ assets into Codex layers) ──

step "Codex parity"

# Regenerate per-repo .codex/config.toml (delta MCP servers) + .codex/hooks.json
# (project hooks, paths absolutized) + ~/.codex/AGENTS.md -> ~/.claude/CLAUDE.md.
# Skills are linked via .agents/skills. All Codex-local mirrors are gitignored;
# source of truth is each repo's committed .claude/ + .mcp.json.
# See scripts/codex_parity_sync.py.
AI_DIR="$PROJECTS/agent-infra"
if [ -f "$AI_DIR/scripts/codex_parity_sync.py" ]; then
    if [ "$DRY_RUN" = "1" ]; then
        would "run codex_parity_sync.py (intel, genomics, phenome)"
    elif (cd "$AI_DIR" && uv run --no-project python3 scripts/codex_parity_sync.py 2>&1 | grep -E '✓|drift|✗' | sed 's/^/  /'); then
        ok "codex parity synced (intel, genomics, phenome)"
    else
        warn "codex parity sync had issues"
    fi
else
    skip "codex_parity_sync.py not found"
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
if [ "$DRY_RUN" = "1" ]; then
    echo -e "${BOLD}${YELLOW}DRY RUN complete.${RESET} ${DIM}Nothing changed — rerun without DRY_RUN=1 to apply.${RESET}"
else
    echo -e "${BOLD}Done.${RESET} ${pulled} repos updated, ${failed} failures."
    echo "$(date '+%Y-%m-%d %H:%M') — ${pulled} updated, ${failed} failed" >> "$LOG_FILE"
fi
