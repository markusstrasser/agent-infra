#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# AI Agent Workstation Setup
# Installs: CLI agents, terminal stack, repos, Claude Code config, skills
# Run: curl -sL https://gist.githubusercontent.com/markusstrasser/7576bba522c935ecb5c890ce31cd392f/raw/setup_friend_mac.sh | bash
# ============================================================================

BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
RED='\033[31m'
RESET='\033[0m'

step() { echo -e "\n${BOLD}${BLUE}▸ $1${RESET}"; }
ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
skip() { echo -e "  ${DIM}⊘ $1${RESET}"; }
warn() { echo -e "  ${YELLOW}⚠ $1${RESET}"; }
fail() { echo -e "  ${RED}✗ $1${RESET}"; }

GITHUB_USER="markusstrasser"
PROJECTS_DIR="$HOME/Projects"

# ── Prerequisites ────────────────────────────────────────────

step "Checking prerequisites"

if ! command -v brew &>/dev/null; then
    fail "Homebrew not found. Install: https://brew.sh"
    exit 1
fi
ok "Homebrew"

if ! command -v node &>/dev/null; then
    step "Installing Node.js via Homebrew"
    brew install node
fi
ok "Node.js $(node --version)"

if ! command -v uv &>/dev/null; then
    step "Installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
ok "uv $(uv --version 2>&1 | head -1)"

# ── Terminal Tools (brew) ──────────────────────────────────

step "Installing terminal tools"

BREW_FORMULAE=(
    # Shell & prompt
    starship        # cross-shell prompt with glyphs
    zoxide          # smart cd
    atuin           # shell history search (sync across machines)
    fzf             # fuzzy finder
    # Better defaults
    eza             # ls replacement (icons, git status)
    bat             # cat replacement (syntax highlighting)
    fd              # find replacement
    ripgrep         # grep replacement
    sd              # sed replacement
    # Dev tools
    git-delta       # better git diff
    lazygit         # terminal git UI
    gh              # GitHub CLI
    just            # task runner
    jq              # JSON processor
    # File management
    yazi            # terminal file manager
    gum             # glamorous shell scripts
    glow            # terminal markdown renderer
    tokei           # code stats
    # Utilities
    direnv          # per-directory env vars
    terminal-notifier  # macOS notifications from terminal
    thefuck         # correct previous command
)

for formula in "${BREW_FORMULAE[@]}"; do
    if brew list "$formula" &>/dev/null; then
        ok "$formula"
    else
        brew install "$formula" 2>/dev/null && ok "$formula" || warn "$formula install failed"
    fi
done

# Ghostty terminal (cask)
if ! brew list --cask ghostty &>/dev/null 2>&1; then
    brew install --cask ghostty 2>/dev/null && ok "Ghostty" || warn "Ghostty install failed"
else
    ok "Ghostty"
fi

# ── Nerd Font ──────────────────────────────────────────────

step "Installing Nerd Font (for terminal glyphs)"

if brew list --cask font-jetbrains-mono-nerd-font &>/dev/null 2>&1; then
    ok "JetBrains Mono Nerd Font"
else
    brew install --cask font-jetbrains-mono-nerd-font 2>/dev/null \
        && ok "JetBrains Mono Nerd Font" \
        || warn "Font install failed — install manually from nerdfonts.com"
fi

# ── AI CLI Tools ─────────────────────────────────────────────

step "Installing AI CLI tools"

# Claude Code
if ! command -v claude &>/dev/null; then
    npm install -g @anthropic-ai/claude-code
    ok "Claude Code installed"
else
    ok "Claude Code $(claude --version 2>/dev/null | head -1 || echo 'installed')"
fi

# Gemini CLI
if ! command -v gemini &>/dev/null; then
    npm install -g @google/gemini-cli
    ok "Gemini CLI installed"
else
    ok "Gemini CLI installed"
fi

# Codex CLI (OpenAI)
if ! command -v codex &>/dev/null; then
    npm install -g @openai/codex
    ok "Codex CLI installed"
else
    ok "Codex CLI installed"
fi

# ── Python Tools (uv) ───────────────────────────────────────

step "Installing Python tools via uv"

uv tool install "git+https://github.com/${GITHUB_USER}/llmx.git" 2>/dev/null && ok "llmx" || ok "llmx (already installed)"
uv tool install "git+https://github.com/${GITHUB_USER}/emb.git" 2>/dev/null && ok "emb" || ok "emb (already installed)"

# ── Repos ──────────────────────────────────────────────────

step "Cloning repos"

mkdir -p "$PROJECTS_DIR"

clone_repo() {
    local name="$1"
    local dest="$PROJECTS_DIR/$name"
    if [ -d "$dest/.git" ]; then
        ok "$name (already cloned)"
        git -C "$dest" pull --rebase --quiet 2>/dev/null || true
    else
        git clone "https://github.com/${GITHUB_USER}/${name}.git" "$dest" 2>/dev/null \
            && ok "$name cloned" \
            || warn "$name clone failed (private repo? set up SSH keys first)"
    fi
}

clone_repo "meta"      # agent infrastructure, orchestrator, measurement
clone_repo "skills"    # shared Claude Code skills

# ── API Keys ─────────────────────────────────────────────────

step "Setting up API keys (stored in macOS Keychain)"
echo -e "  ${DIM}Keys are encrypted at rest. Manage later with: llmx keys list${RESET}"

KEYCHAIN_SERVICE="llmx"

store_key() {
    local key_name="$1"
    local display_name="$2"
    local signup_url="$3"
    local required="${4:-optional}"

    # Check if already set in env or keychain
    if [ -n "${!key_name:-}" ]; then
        ok "$display_name — already in environment"
        security delete-generic-password -a "$KEYCHAIN_SERVICE" -s "$key_name" 2>/dev/null || true
        security add-generic-password -a "$KEYCHAIN_SERVICE" -s "$key_name" -w "${!key_name}" 2>/dev/null
        return
    fi

    existing=$(security find-generic-password -a "$KEYCHAIN_SERVICE" -s "$key_name" -w 2>/dev/null || true)
    if [ -n "$existing" ]; then
        ok "$display_name — already in Keychain"
        return
    fi

    echo ""
    if [ "$required" = "required" ]; then
        echo -e "  ${BOLD}$display_name${RESET} ${RED}(required)${RESET}"
    else
        echo -e "  ${BOLD}$display_name${RESET} ${DIM}(optional)${RESET}"
    fi
    echo -e "  ${DIM}Get your key: ${signup_url}${RESET}"

    read -rp "  Enter $key_name (or press Enter to skip): " value
    if [ -n "$value" ]; then
        security delete-generic-password -a "$KEYCHAIN_SERVICE" -s "$key_name" 2>/dev/null || true
        security add-generic-password -a "$KEYCHAIN_SERVICE" -s "$key_name" -w "$value"
        ok "Stored $key_name in Keychain"
    else
        if [ "$required" = "required" ]; then
            warn "Skipped $key_name — you'll need this to use $display_name"
        else
            skip "Skipped $key_name"
        fi
    fi
}

store_key "ANTHROPIC_API_KEY" "Anthropic (Claude API)" \
    "https://console.anthropic.com/settings/keys" "required"

store_key "OPENAI_API_KEY" "OpenAI (GPT models + Codex CLI)" \
    "https://platform.openai.com/api-keys" "required"

store_key "GEMINI_API_KEY" "Google Gemini" \
    "https://aistudio.google.com/apikey" "required"

store_key "OPENROUTER_API_KEY" "OpenRouter (multi-model gateway)" \
    "https://openrouter.ai/keys" "optional"

store_key "EXA_API_KEY" "Exa (neural web search)" \
    "https://dashboard.exa.ai/api-keys" "optional"

store_key "BRAVE_API_KEY" "Brave Search API" \
    "https://brave.com/search/api/" "optional"

store_key "PERPLEXITY_API_KEY" "Perplexity (grounded search)" \
    "https://www.perplexity.ai/settings/api" "optional"

store_key "S2_API_KEY" "Semantic Scholar (paper search)" \
    "https://www.semanticscholar.org/product/api#api-key-form" "optional"

store_key "XAI_API_KEY" "xAI (Grok)" \
    "https://console.x.ai/" "optional"

store_key "MOONSHOT_API_KEY" "Kimi / Moonshot" \
    "https://platform.moonshot.cn/console/api-keys" "optional"

# ── Terminal Config ─────────────────────────────────────────

step "Setting up terminal config"

# Ghostty terminal config
mkdir -p "$HOME/.config/ghostty"
if [ ! -f "$HOME/.config/ghostty/config" ]; then
    cat > "$HOME/.config/ghostty/config" <<'GHOSTTY'
# Font
font-family = JetBrainsMono Nerd Font
font-size = 14

# Theme (Tokyo Night — matches starship colors)
theme = tokyonight

# Window
window-padding-x = 8
window-padding-y = 4
window-decoration = true
macos-titlebar-style = tabs
window-save-state = always

# Behavior
copy-on-select = clipboard
confirm-close-surface = false
mouse-hide-while-typing = true
shell-integration = zsh

# Keybinds
keybind = shift+enter=text:\x1b\r
GHOSTTY
    ok "Ghostty config"
else
    skip "Ghostty config already exists"
fi

# Starship prompt
mkdir -p "$HOME/.config"
if [ ! -f "$HOME/.config/starship.toml" ]; then
    cat > "$HOME/.config/starship.toml" <<'STARSHIP'
"$schema" = 'https://starship.rs/config-schema.json'

format = """
[╭─](#7aa2f7)\
$os\
$directory\
$git_branch\
$git_status\
$nodejs\
$python\
$rust\
$fill\
$cmd_duration\
$time\
$line_break\
[╰─](#7aa2f7)$character"""

[cmd_duration]
min_time = 2000
format = "[$duration]($style) "

[os]
disabled = false
style = "fg:#7aa2f7"

[os.symbols]
Macos = " "

[directory]
style = "fg:#7dcfff"
format = "[$path ]($style)"
truncation_length = 3
truncate_to_repo = true

[git_branch]
symbol = " "
style = "fg:#bb9af7"
format = "[$symbol$branch(:$remote_branch) ]($style)"

[git_status]
style = "fg:#f7768e"
format = '([$all_status$ahead_behind]($style) )'
conflicted = "≠"
ahead = "⇡"
behind = "⇣"
diverged = "⇕"
untracked = "◌"
stashed = "◫"
modified = "◉"
staged = "◈"
renamed = "➜"
deleted = "⊖"

[nodejs]
symbol = " "
style = "fg:#9ece6a"
format = "[$symbol$version ]($style)"
detect_files = ["package.json", ".nvmrc", "package-lock.json"]

[python]
symbol = " "
style = "fg:#ffcc02"
format = "[$symbol$version ]($style)"
detect_files = ["requirements.txt", ".python-version", "pyproject.toml"]

[rust]
symbol = " "
style = "fg:#ce422b"
format = "[$symbol$version ]($style)"
detect_files = ["Cargo.toml"]

[fill]
symbol = " "

[time]
disabled = false
format = '[$time ]($style)'
style = "fg:#545c7e"
time_format = "%H:%M"

[character]
success_symbol = "[❯](bold fg:#9ece6a)"
error_symbol = "[❯](bold fg:#f7768e)"
vimcmd_symbol = "[❮](bold fg:#7aa2f7)"
STARSHIP
    ok "Starship prompt config"
else
    skip "Starship config already exists"
fi

# ── Zsh Setup ───────────────────────────────────────────────

step "Setting up zsh"

SHELL_RC="$HOME/.zshrc"

# Install zinit if not present
ZINIT_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/zinit/zinit.git"
if [ ! -d "$ZINIT_HOME" ]; then
    git clone https://github.com/zdharma-continuum/zinit "$ZINIT_HOME"
    ok "Zinit installed"
else
    ok "Zinit already installed"
fi

# Write zshrc if it doesn't have our marker
if ! grep -q '# --- agent-workstation-setup ---' "$SHELL_RC" 2>/dev/null; then
    # Back up existing zshrc
    if [ -f "$SHELL_RC" ]; then
        cp "$SHELL_RC" "${SHELL_RC}.backup.$(date +%s)"
        warn "Backed up existing .zshrc"
    fi

    cat > "$SHELL_RC" <<'ZSHRC'
# --- agent-workstation-setup ---

# Load API keys from ~/.env
if [ -f ~/.env ]; then
    source ~/.env
fi

# PATH (deduplicated)
typeset -gU path
path=(
  "$HOME/.local/bin"
  "$HOME/.bun/bin"
  "$HOME/.atuin/bin"
  /opt/homebrew/bin
  $path
)

# Shell options
setopt PROMPT_SUBST
setopt AUTO_CD
setopt HIST_IGNORE_DUPS
setopt HIST_REDUCE_BLANKS
setopt INTERACTIVE_COMMENTS

# Environment
export HOMEBREW_NO_AUTO_UPDATE=1
export EDITOR="nvim"
export BAT_THEME="Dracula"

# ── Zinit ──────────────────────────────────────────────────
ZINIT_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/zinit/zinit.git"
[[ ! -d "$ZINIT_HOME" ]] && git clone https://github.com/zdharma-continuum/zinit "$ZINIT_HOME"
source "$ZINIT_HOME/zinit.zsh"

zinit ice wait lucid; zinit light zsh-users/zsh-completions
zinit ice wait lucid; zinit light zsh-users/zsh-autosuggestions
zinit ice wait lucid; zinit light Aloxaf/fzf-tab
zinit ice wait lucid; zinit light hlissner/zsh-autopair
zinit light zdharma-continuum/fast-syntax-highlighting
zinit ice wait lucid; zinit light paulirish/git-open

autoload -Uz compinit && compinit
zinit cdreplay -q

# ── Better defaults ────────────────────────────────────────
alias ls='eza --icons=always --color=always --group-directories-first --classify'
alias ll='eza -la --icons=always --color=always --git --header --time-style=relative'
alias cat='bat'
alias tree='eza --tree --icons=auto'
alias treed='eza --tree --icons=auto --level'

# ── Git shortcuts ──────────────────────────────────────────
alias ga='git add .'
alias gc='git commit -m'
alias gac='git add . && git commit -m'
alias g='lazygit'
alias gb='git branch --sort=-committerdate | fzf --preview="git log --oneline --graph --color=always {}" | xargs git checkout'

# ── Navigation ─────────────────────────────────────────────
alias ..='cd ..'
alias ...='cd ../..'
alias p='z ~/Projects'
alias v='nvim'
alias vi='nvim'
alias vim='nvim'
alias rl='source ~/.zshrc'

# ── AI agent shortcuts ─────────────────────────────────────
cdx() {
  if [[ "$1" == "update" ]]; then
    brew upgrade codex
  else
    codex -m gpt-5.1-codex -c model_reasoning_effort="medium" --search "$@"
  fi
}

# ── FZF config ─────────────────────────────────────────────
export FZF_DEFAULT_OPTS='
--style full
--layout=reverse
--border=rounded
--color=fg:#f8f8f2,bg:#282a36,hl:#bd93f9
--color=fg+:#f8f8f2,bg+:#44475a,hl+:#bd93f9
--color=info:#ffb86c,prompt:#50fa7b,pointer:#ff79c6'
export FZF_CTRL_T_COMMAND='fd --type f --hidden --follow --exclude .git'
export FZF_ALT_C_COMMAND='fd --type d --hidden --follow --exclude .git'
export FZF_ALT_C_OPTS="--preview 'eza --tree --level=2 --icons=always {}'"

# ── Completion styling ─────────────────────────────────────
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'
zstyle ':fzf-tab:*' fzf-preview 'eza -1 --icons=auto --color=always $realpath 2>/dev/null || echo $desc'

# ── File browser ───────────────────────────────────────────
browse() {
    local dir="${1:-.}"
    gfind "$dir" -maxdepth 3 -type f -printf '%T@ %p\n' 2>/dev/null | \
       sort -nr | sd '^[0-9.]* ' '' | \
       fzf --preview 'bat --color=always --style=header,grid {}' \
           --preview-window=right:60% \
           --bind "enter:execute(${EDITOR:-nvim} {})+abort"
}
alias b='browse'

# ── Yazi file manager ──────────────────────────────────────
y() {
    local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
    yazi "$@" --cwd-file="$tmp"
    IFS= read -r -d '' cwd < "$tmp"
    [ -n "$cwd" ] && [ "$cwd" != "$PWD" ] && builtin cd -- "$cwd"
    rm -f -- "$tmp"
}

# ── Utilities ──────────────────────────────────────────────
uva() { [[ ! -d .venv ]] && uv venv; source .venv/bin/activate; }
killport() {
    local pids=$(lsof -ti:"$1" 2>/dev/null)
    [[ -z "$pids" ]] && echo "No process on port $1" && return 1
    echo "$pids" | xargs kill -9 && echo "Killed port $1"
}
notify() {
    local msg="${1:-Done}" title="${2:-Terminal}"
    terminal-notifier -title "$title" -message "$msg" -sound default
}
a() { alias | sed 's/=/\t→ /' | column -t -s $'\t' | fzf; }

# ── Zsh keybinds ───────────────────────────────────────────
bindkey '^f' undefined-key  # reserve for finder
autoload edit-command-line; zle -N edit-command-line; bindkey '^Xe' edit-command-line

# ── Inits (keep at end) ───────────────────────────────────
eval "$(atuin init zsh --disable-up-arrow)"
eval "$(starship init zsh)"
eval "$(zoxide init zsh)"
eval "$(direnv hook zsh)"

# Load API keys from macOS Keychain
_load_keychain_key() {
    local key="$1"
    if [ -z "${!key:-}" ]; then
        local val
        val=$(security find-generic-password -a "llmx" -s "$key" -w 2>/dev/null) && export "$key=$val"
    fi
}
for _k in ANTHROPIC_API_KEY OPENAI_API_KEY GEMINI_API_KEY OPENROUTER_API_KEY EXA_API_KEY BRAVE_API_KEY PERPLEXITY_API_KEY S2_API_KEY XAI_API_KEY MOONSHOT_API_KEY; do
    _load_keychain_key "$_k"
done
unset _k

# Agent utils
[[ -f "$HOME/.zsh_agent_utils" ]] && source "$HOME/.zsh_agent_utils"
ZSHRC
    ok "Wrote .zshrc (backup saved)"
else
    skip ".zshrc already set up"
fi

# Agent utils (sync + push aliases)
cat > "$HOME/.zsh_agent_utils" <<'AGENTUTILS'
#!/usr/bin/env zsh
alias agent-sync='bash -c '"'"'for d in skills meta llmx emb; do [ -d "$HOME/Projects/$d" ] && printf "  %-15s" "$d" && (git -C "$HOME/Projects/$d" pull --rebase --quiet 2>/dev/null && echo "ok" || echo "skip"); done; for t in llmx emb; do [ -d "$HOME/Projects/$t" ] && uv tool install --editable "$HOME/Projects/$t" --quiet 2>/dev/null; done'"'"''
alias push-all='bash -c '"'"'for d in "$HOME"/Projects/*/; do [ -d "$d/.git" ] || continue; ahead=$(git -C "$d" rev-list --count @{u}..HEAD 2>/dev/null) || continue; [ "$ahead" = "0" ] && continue; name=$(basename "$d"); printf "  %-15s %s ahead -> " "$name" "$ahead"; git -C "$d" push --quiet 2>/dev/null && echo "ok" || echo "fail"; done'"'"''
AGENTUTILS
ok "Agent utils (agent-sync, push-all)"

# ── Claude Code Config ──────────────────────────────────────

step "Setting up Claude Code"

mkdir -p "$HOME/.claude"

# Starter global CLAUDE.md
if [ ! -f "$HOME/.claude/CLAUDE.md" ]; then
    cat > "$HOME/.claude/CLAUDE.md" <<'CLAUDEMD'
# Global Rules

## Communication
Never start responses with positive adjectives. Skip flattery, respond directly.

## Git Workflow
All commits go to main. No branches. Auto-commit after completing tasks.
Granular semantic commits — one logical change per commit.

### Commit Format
```
[scope] Verb thing — why
```

## Python & Environment
- Use `python3` not `python` (macOS has no `python` binary).
- All projects use `uv`. Run scripts with `uv run python3 script.py`.
- Prefer writing `.py` files over inline `python3 -c` for multi-line code.

## Technical Pushback
"No" is a valid answer. If you have strong technical grounds to disagree, say so before writing code.

### Pre-Build Checks
1. Does this already exist? Check vendor repos, changelog, SDKs, API docs, OSS.
2. Will this work in our environment?
3. Can we validate at 1/10 the complexity? Build simplest version first.
CLAUDEMD
    ok "Global CLAUDE.md (starter)"
else
    skip "Global CLAUDE.md already exists"
fi

# ── Git Config ──────────────────────────────────────────────

step "Setting up git config"

# Global gitignore
if [ ! -f "$HOME/.gitignore" ]; then
    cat > "$HOME/.gitignore" <<'GITIGNORE'
.DS_Store
Desktop.ini
._*
Thumbs.db
.Spotlight-V100
.Trashes
node_modules
*.pyc
__pycache__
.env.local
GITIGNORE
    ok "Global .gitignore"
else
    skip "Global .gitignore already exists"
fi

# Git config — delta pager, good defaults, aliases
if ! git config --global core.pager | grep -q delta 2>/dev/null; then
    # Core
    git config --global core.excludesfile "$HOME/.gitignore"
    git config --global core.pager "delta --word-diff-regex=."
    git config --global core.autocrlf input

    # Delta (rich diffs)
    git config --global delta.syntax-theme base16
    git config --global delta.hyperlinks true
    git config --global delta.navigate true
    git config --global delta.file-style "bold yellow ul"
    git config --global delta.hunk-header-decoration-style blue
    git config --global interactive.diffFilter "delta --color-only"

    # Push/pull
    git config --global push.default current
    git config --global push.autoSetupRemote true
    git config --global pull.ff only
    git config --global fetch.prune true

    # UX
    git config --global help.autocorrect 1
    git config --global log.date human
    git config --global rerere.enabled true
    git config --global diff.colorMoved default
    git config --global merge.conflictStyle zdiff3
    git config --global credential.helper osxkeychain

    # Aliases
    git config --global alias.s status
    git config --global alias.c "commit -am"
    git config --global alias.co checkout
    git config --global alias.lg "log --color --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cd) %C(bold blue)<%an>%Creset' --abbrev-commit"
    git config --global alias.undocommit "reset HEAD~"
    git config --global alias.amend "commit --amend --all --no-edit"

    # Use SSH for GitHub
    git config --global url."git@github.com:".insteadOf "https://github.com/"

    ok "Git config (delta, aliases, SSH)"
else
    skip "Git config already has delta"
fi

# Prompt for git identity if not set
if [ -z "$(git config --global user.name)" ]; then
    echo ""
    read -rp "  Git name (e.g. 'Jane Doe'): " git_name
    [ -n "$git_name" ] && git config --global user.name "$git_name"
    read -rp "  Git email: " git_email
    [ -n "$git_email" ] && git config --global user.email "$git_email"
    ok "Git identity set"
else
    ok "Git identity: $(git config --global user.name) <$(git config --global user.email)>"
fi

# SSH key for GitHub
if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
    echo ""
    echo -e "  ${BOLD}SSH key for GitHub${RESET}"
    echo -e "  ${DIM}Needed to push/pull private repos${RESET}"
    read -rp "  Generate SSH key? (y/n): " gen_ssh
    if [ "$gen_ssh" = "y" ]; then
        ssh-keygen -t ed25519 -C "$(git config --global user.email)" -f "$HOME/.ssh/id_ed25519" -N ""
        eval "$(ssh-agent -s)" >/dev/null
        ssh-add "$HOME/.ssh/id_ed25519" 2>/dev/null
        pbcopy < "$HOME/.ssh/id_ed25519.pub"
        ok "SSH key generated + copied to clipboard"
        echo -e "  ${YELLOW}→ Paste at: https://github.com/settings/ssh/new${RESET}"
        echo -e "  ${DIM}Press Enter after adding to GitHub...${RESET}"
        read -r
    else
        skip "SSH key"
    fi
else
    ok "SSH key exists"
fi

# ── Skill Symlinks ──────────────────────────────────────────

step "Wiring shared skills"

SKILLS_DIR="$PROJECTS_DIR/skills"
if [ -d "$SKILLS_DIR" ]; then
    # Skills that are useful across projects
    GLOBAL_SKILLS=(
        brainstorm
        claude-api
        data-acquisition
        de-slop
        knowledge-diff
        model-guide
        model-review
        researcher
        retro
    )

    # Wire skills to meta project as an example
    META_SKILLS="$PROJECTS_DIR/meta/.claude/skills"
    if [ -d "$PROJECTS_DIR/meta" ]; then
        mkdir -p "$META_SKILLS"
        for skill in "${GLOBAL_SKILLS[@]}"; do
            if [ -d "$SKILLS_DIR/$skill" ] && [ ! -L "$META_SKILLS/$skill" ]; then
                ln -sf "$SKILLS_DIR/$skill" "$META_SKILLS/$skill"
            fi
        done
        ok "Skills symlinked to meta project"
    fi

    echo -e "  ${DIM}To add skills to other projects:${RESET}"
    echo -e "  ${DIM}  ln -sf ~/Projects/skills/<skill> <project>/.claude/skills/${RESET}"
else
    warn "Skills repo not found — clone manually or re-run"
fi

# ── Summary ──────────────────────────────────────────────────

step "Setup complete!"
echo ""
echo -e "  ${BOLD}Terminal:${RESET}"
echo "    Ghostty     — terminal emulator (set font to JetBrainsMono Nerd Font)"
echo "    Starship    — prompt with git status, language versions, glyphs"
echo "    eza/bat/fd  — modern ls/cat/find replacements"
echo "    fzf         — fuzzy finder (Ctrl+R history, Ctrl+T files, Alt+C dirs)"
echo "    yazi        — terminal file manager (y to launch)"
echo "    lazygit     — terminal git UI (g to launch)"
echo "    zoxide      — smart cd (z <partial-path>)"
echo "    atuin       — searchable shell history"
echo ""
echo -e "  ${BOLD}AI tools:${RESET}"
echo "    claude      — Claude Code (AI coding agent)"
echo "    gemini      — Gemini CLI (free tier)"
echo "    codex       — Codex CLI (OpenAI agent)"
echo "    llmx        — unified LLM CLI (all providers)"
echo "    emb         — embed + search text corpora"
echo ""
echo -e "  ${BOLD}Repos:${RESET}"
echo "    ~/Projects/meta    — agent infrastructure"
echo "    ~/Projects/skills  — shared Claude Code skills"
echo ""
echo -e "  ${BOLD}Shortcuts:${RESET}"
echo "    agent-sync  — pull all repos + reinstall editable tools"
echo "    push-all    — push all repos with unpushed commits"
echo "    g           — lazygit"
echo "    y           — yazi file manager"
echo "    b           — fuzzy file browser"
echo "    a           — search all aliases"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo "    1. Open Ghostty, set font to 'JetBrainsMono Nerd Font'"
echo "    2. Open a new terminal (to load everything)"
echo "    3. Run: claude            — start Claude Code"
echo "    4. Run: llmx 'hello'      — test multi-model access"
echo "    5. Run: agent-sync        — pull latest from all repos"
echo ""
