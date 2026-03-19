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

# ── Claude Code Cockpit (status line + hooks) ──────────────

step "Setting up Claude Code cockpit"

mkdir -p "$HOME/.claude/hooks"

# cockpit.conf — toggle notifications
cat > "$HOME/.claude/cockpit.conf" <<'CONF'
# Cockpit configuration
# Toggle notifications when Claude finishes responding
notifications=on
CONF
ok "cockpit.conf"

# --- statusline.sh (325 lines) — rich status bar + Ghostty tab title ---
cat > "$HOME/.claude/statusline.sh" <<'STATUSLINE'
#!/usr/bin/env bash
# Claude Code status line — rich info bar + Ghostty tab title + aggregate HUD
# Line 1: project · cost (velocity) · context bar + tokens · tool · elapsed
# Line 2: throughput · cache% · context rate · lines

set -euo pipefail

input=$(cat)

model=$(echo "$input" | jq -r '.model.display_name // "?"')
cost=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
duration_ms=$(echo "$input" | jq -r '.cost.total_duration_ms // 0' | cut -d. -f1)
api_duration_ms=$(echo "$input" | jq -r '.cost.total_api_duration_ms // 0' | cut -d. -f1)
lines_add=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
lines_rm=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')
session_id=$(echo "$input" | jq -r '.session_id // ""')
workspace=$(echo "$input" | jq -r '.workspace.current_dir // "."')

total_in=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0' | cut -d. -f1)
total_out=$(echo "$input" | jq -r '.context_window.total_output_tokens // 0' | cut -d. -f1)
ctx_size=$(echo "$input" | jq -r '.context_window.context_window_size // 200000' | cut -d. -f1)
cache_read=$(echo "$input" | jq -r '.context_window.current_usage.cache_read_input_tokens // 0' | cut -d. -f1)
cache_create=$(echo "$input" | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0' | cut -d. -f1)
cur_input=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // 0' | cut -d. -f1)

project=$(basename "$workspace")
now=$(date +%s)

model_tag=""
[[ "$model" != "Opus 4.6" ]] && model_tag="$model "

cache="/tmp/statusline-git-cache"
if [[ -f "$cache" ]] && (( now - $(stat -f%m "$cache") < 5 )); then
  branch=$(cat "$cache")
else
  branch=$(git -C "$workspace" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "—")
  echo "$branch" > "$cache"
fi
branch_tag=""
[[ "$branch" != "main" && "$branch" != "—" ]] && branch_tag="($branch) "

pct_int=${pct:-0}
filled=$(( pct_int / 10 ))
empty=$(( 10 - filled ))
bar=""
(( filled > 0 )) && bar=$(printf '%0.s▓' $(seq 1 $filled))
(( empty > 0 )) && bar+=$(printf '%0.s░' $(seq 1 $empty))

fmt_k() { local n=$1; if (( n >= 1000 )); then echo "$((n / 1000))K"; else echo "$n"; fi; }
current_tokens=$(( pct_int * ctx_size / 100 ))
in_k=$(fmt_k "$current_tokens")
ctx_k=$(fmt_k "$ctx_size")

cache_total=$(( cache_read + cache_create + cur_input ))
cache_pct=0
(( cache_total > 0 )) && cache_pct=$(( cache_read * 100 / cache_total ))

throughput=""
if (( api_duration_ms > 0 && total_out > 0 )); then
  tps=$(( total_out * 1000 / api_duration_ms ))
  (( tps > 0 )) && throughput="${tps}t/s"
fi

cost_vel=""
if (( duration_ms > 60000 )); then
  vel=$(echo "scale=2; $cost * 60000 / $duration_ms" | bc -l 2>/dev/null || echo "")
  [[ "$vel" == .* ]] && vel="0${vel}"
  [[ -n "$vel" && "$vel" != "0" && "$vel" != "0.00" ]] && cost_vel="\$${vel}/m"
fi

ctx_rate=""
ctx_eta=""
if (( duration_ms > 60000 && pct_int > 5 )); then
  rate_per_min=$(echo "scale=1; $pct_int * 60000 / $duration_ms" | bc -l 2>/dev/null || echo "")
  if [[ -n "$rate_per_min" ]]; then
    ctx_rate="+${rate_per_min}%/m"
    remaining=$(( 100 - pct_int ))
    if [[ "$rate_per_min" != "0" && "$rate_per_min" != ".0" && "$rate_per_min" != "0.0" ]]; then
      eta_min=$(echo "scale=0; $remaining / $rate_per_min" | bc -l 2>/dev/null || echo "")
      if [[ -n "$eta_min" && "$eta_min" -gt 0 ]] 2>/dev/null; then
        (( eta_min > 60 )) && ctx_eta="~$((eta_min / 60))h left" || ctx_eta="~${eta_min}m left"
      fi
    fi
  fi
fi

reset='\033[0m'; dim='\033[2m'; bold='\033[1m'
if (( pct_int > 80 )); then ctx_color='\033[1;31m'
elif (( pct_int > 50 )); then ctx_color='\033[1;33m'
else ctx_color='\033[32m'; fi
cost_color='\033[33m'
cost_fmt=$(printf '$%.2f' "$cost")
ctx_warn=""
(( pct_int > 80 )) && ctx_warn=" ${bold}\033[31m→ /compact${reset}"

tool_action=""
tool_file="/tmp/claude-tab-tool-$PPID"
[[ -f "$tool_file" ]] && tool_action=$(cat "$tool_file" 2>/dev/null || true)

elapsed=""
prompt_file="/tmp/claude-tab-prompt-$PPID"
if [[ -f "$prompt_file" ]]; then
  prompt_time=$(cat "$prompt_file" 2>/dev/null || echo 0)
  if (( prompt_time > 0 )); then
    delta=$(( now - prompt_time ))
    if (( delta >= 3600 )); then elapsed="$((delta / 3600))h"
    elif (( delta >= 60 )); then elapsed="$((delta / 60))m"
    else elapsed="${delta}s"; fi
  fi
fi

spinners=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
spinner_file="/tmp/claude-tab-spinner-$PPID"
spinner_idx=0
[[ -f "$spinner_file" ]] && spinner_idx=$(cat "$spinner_file" 2>/dev/null || echo 0)
spinner="${spinners[$((spinner_idx % 10))]}"
echo $(( (spinner_idx + 1) % 10 )) > "$spinner_file" 2>/dev/null || true

tab_state=""
state_file="/tmp/claude-tab-state-$PPID"
[[ -f "$state_file" ]] && tab_state=$(cat "$state_file" 2>/dev/null || true)

error_file="/tmp/claude-tab-error-$PPID"
if [[ -f "$error_file" ]]; then
  error_val=$(cat "$error_file" 2>/dev/null || echo 0)
  (( error_val > 0 )) && tab_state="error" || true
fi
(( pct_int > 80 )) && [[ "$tab_state" != "error" && "$tab_state" != "done" ]] && tab_state="attention"

case "$tab_state" in
  working) state_glyph="◐"; state_color="$dim" ;;
  attention) state_glyph="◆"; state_color='\033[33m' ;;
  error) state_glyph="▲"; state_color='\033[31m' ;;
  done) state_glyph="●"; state_color='\033[32m' ;;
  *) state_glyph="·"; state_color="$dim" ;;
esac

echo "${tab_state:-idle}|${project}|${cost_fmt}|${pct_int}" > "/tmp/claude-agent-$PPID" 2>/dev/null || true

agg_working=0; agg_attention=0; agg_error=0
cutoff=$(( now - 21600 ))
for f in /tmp/claude-agent-*; do
  [[ -f "$f" ]] || continue
  fpid="${f##*-}"; [[ "$fpid" == "$PPID" ]] && continue
  fmtime=$(stat -f%m "$f" 2>/dev/null || echo 0)
  (( fmtime < cutoff )) && continue
  astate=$(cut -d'|' -f1 "$f" 2>/dev/null || echo "idle")
  case "$astate" in
    working) (( agg_working++ )) || true ;;
    attention) (( agg_attention++ )) || true ;;
    error) (( agg_error++ )) || true ;;
  esac
done

agg_badge=""
agg_parts=()
(( agg_attention > 0 )) && agg_parts+=("${agg_attention}◆")
(( agg_error > 0 )) && agg_parts+=("${agg_error}▲")
(( agg_working > 0 )) && agg_parts+=("${agg_working}◐")
(( ${#agg_parts[@]} > 0 )) && agg_badge=" [$(IFS=' '; echo "${agg_parts[*]}")]"

tool_display=""; [[ -n "$tool_action" ]] && tool_display=" ${dim}·${reset} ${tool_action}"
elapsed_display=""; [[ -n "$elapsed" ]] && elapsed_display=" ${dim}${elapsed}${reset}"
cost_vel_display=""; [[ -n "$cost_vel" ]] && cost_vel_display=" ${dim}${cost_vel}${reset}"

printf '%b' "${state_color}${state_glyph}${reset} ${model_tag}${branch_tag}${bold}${project}${reset} ${dim}·${reset} ${cost_color}${cost_fmt}${reset}${cost_vel_display} ${dim}·${reset} ${ctx_color}${bar} ${pct_int}%${reset} ${dim}${in_k}/${ctx_k}${reset}${ctx_warn}${tool_display}${elapsed_display}"
echo

line2_parts=()
[[ -n "$throughput" ]] && line2_parts+=("${throughput}")
(( cache_total > 100 )) && line2_parts+=("cache ${cache_pct}%")
[[ -n "$ctx_rate" ]] && line2_parts+=("ctx ${ctx_rate}")
[[ -n "$ctx_eta" ]] && line2_parts+=("${ctx_eta}")
(( lines_add > 0 || lines_rm > 0 )) && line2_parts+=("Δ+${lines_add}/-${lines_rm}")
(( duration_ms > 300000 )) && line2_parts+=("$((duration_ms / 60000))m")
[[ -n "$agg_badge" ]] && line2_parts+=("others:${agg_badge}")

if (( ${#line2_parts[@]} > 0 )); then
  line2=""
  for part in "${line2_parts[@]}"; do
    [[ -n "$line2" ]] && line2+=" ${dim}·${reset} "
    line2+="${dim}${part}${reset}"
  done
  printf '%b' " $line2"; echo
fi

tab_parts="${state_glyph}"
if [[ "$tab_state" == "working" ]]; then
  tab_parts="${tab_parts} ${spinner} ${project}"
  [[ -n "$tool_action" ]] && tab_parts="${tab_parts}: ${tool_action}"
  tab_parts="${tab_parts}${agg_badge} · ${cost_fmt} ${pct_int}%"
  [[ -n "$elapsed" ]] && tab_parts="${tab_parts} ${elapsed}"
elif [[ "$tab_state" == "attention" ]]; then
  tab_parts="${tab_parts} ${project} · Needs input${agg_badge} · ${cost_fmt} ${pct_int}%"
else
  tab_parts="${tab_parts} ${project}${agg_badge} · ${cost_fmt} ${pct_int}%"
fi
[[ -n "$model_tag" ]] && tab_parts="${tab_parts} [${model}]"
printf '\033]2;%s\007' "$tab_parts" > /dev/tty 2>/dev/null || true

if [[ -n "$session_id" ]]; then
  jq -n --arg cost "$cost" --arg pct "$pct_int" --arg dur "$duration_ms" \
    --arg la "$lines_add" --arg lr "$lines_rm" --arg model "$model" \
    --arg branch "$branch" --arg project "$project" --arg out_tok "$total_out" \
    '{cost:$cost,context_pct:$pct,duration_ms:$dur,lines_added:$la,lines_removed:$lr,model:$model,branch:$branch,project:$project,output_tokens:$out_tok}' \
    > "/tmp/claude-cockpit-${session_id}" 2>/dev/null || true
fi
STATUSLINE
chmod +x "$HOME/.claude/statusline.sh"
ok "statusline.sh"

# --- tab-color.sh — Ghostty tab state management ---
cat > "$HOME/.claude/hooks/tab-color.sh" <<'TABCOLOR'
#!/usr/bin/env bash
# Set Ghostty tab state. States: working, attention, error, done, idle
STATE="${1:-idle}"
CONF="$HOME/.claude/cockpit.conf"
if [[ -f "$CONF" ]]; then
  tc=$(grep "^tab_colors=" "$CONF" 2>/dev/null | head -1 | cut -d= -f2-)
  [[ "$tc" == "off" ]] && exit 0
fi
PID="${CLAUDE_PID:-$PPID}"
STATE_FILE="/tmp/claude-tab-state-$PID"
PREV_STATE=""
[[ -f "$STATE_FILE" ]] && PREV_STATE=$(cat "$STATE_FILE" 2>/dev/null || true)
echo "$STATE" > "$STATE_FILE" 2>/dev/null || true
if [[ "$STATE" == "working" ]]; then
  echo 0 > "/tmp/claude-tab-error-$PID" 2>/dev/null || true
  date +%s > "/tmp/claude-tab-prompt-$PID" 2>/dev/null || true
  rm -f "/tmp/claude-last-notify-$PID" 2>/dev/null || true
fi
if [[ "$STATE" != "$PREV_STATE" && "$STATE" =~ ^(attention|error|done)$ ]]; then
  printf '\a' > /dev/tty 2>/dev/null || true
fi
exit 0
TABCOLOR
chmod +x "$HOME/.claude/hooks/tab-color.sh"
ok "tab-color.sh"

# --- tool-tracker.sh — Track last tool for tab title ---
cat > "$HOME/.claude/hooks/tool-tracker.sh" <<'TOOLTRACKER'
#!/usr/bin/env bash
# Track last tool action for Ghostty tab title. PreToolUse hook (catch-all).
trap 'exit 0' ERR
STDIN=$(cat)
TOOL=$(echo "$STDIN" | jq -r '.tool_name // ""' 2>/dev/null)
[[ -z "$TOOL" || "$TOOL" == "null" ]] && TOOL="${CLAUDE_TOOL_NAME:-unknown}"
INPUT=$(echo "$STDIN" | jq -r '.tool_input // ""' 2>/dev/null)
[[ -z "$INPUT" || "$INPUT" == "null" ]] && INPUT="${CLAUDE_TOOL_INPUT:-}"
case "$TOOL" in
  Read|Write|Edit)
    target=$(echo "$INPUT" | jq -r '.file_path // ""' 2>/dev/null)
    [[ -n "$target" ]] && target=$(basename "$target") || target=""
    action="$TOOL $target" ;;
  Bash)
    cmd=$(echo "$INPUT" | jq -r '.command // ""' 2>/dev/null | head -c 25)
    action="\$ $cmd" ;;
  Grep) action="Grep $(echo "$INPUT" | jq -r '.pattern // ""' 2>/dev/null | head -c 15)" ;;
  Glob) action="Glob $(echo "$INPUT" | jq -r '.pattern // ""' 2>/dev/null | head -c 15)" ;;
  Agent) action="Agent: $(echo "$INPUT" | jq -r '.description // ""' 2>/dev/null | head -c 20)" ;;
  mcp__*) action=$(echo "$TOOL" | sed 's/mcp__//;s/__/:/g' | head -c 15) ;;
  *) action="$TOOL" ;;
esac
echo "$action" > "/tmp/claude-tab-tool-$PPID" 2>/dev/null || true
exit 0
TOOLTRACKER
chmod +x "$HOME/.claude/hooks/tool-tracker.sh"
ok "tool-tracker.sh"

# --- spinning-detector.sh — Detect tool-call loops ---
cat > "$HOME/.claude/hooks/spinning-detector.sh" <<'SPINNING'
#!/usr/bin/env bash
# Detect agent stuck in tool-call loops. PostToolUse hook.
trap 'exit 0' ERR
INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("tool_name",""))
except: print("")' 2>/dev/null)
[[ -z "$TOOL" ]] && exit 0
STATE="/tmp/claude-spinning-$PPID"
if [[ -f "$STATE" ]]; then
  LAST_TOOL=$(sed -n '1p' "$STATE"); COUNT=$(sed -n '2p' "$STATE"); COUNT=${COUNT:-0}
else
  LAST_TOOL=""; COUNT=0
fi
[[ "$TOOL" == "$LAST_TOOL" ]] && COUNT=$((COUNT + 1)) || COUNT=1
printf '%s\n%s\n' "$TOOL" "$COUNT" > "$STATE"
if (( COUNT == 4 )); then
  echo "{\"additionalContext\": \"SPINNING WARNING: You have called $TOOL $COUNT times consecutively. You may be stuck in a loop. Stop and reconsider your approach.\"}"
elif (( COUNT >= 8 )); then
  echo "{\"additionalContext\": \"SPINNING ALERT: $TOOL called $COUNT times consecutively. STOP. Try a completely different approach.\"}"
fi
exit 0
SPINNING
chmod +x "$HOME/.claude/hooks/spinning-detector.sh"
ok "spinning-detector.sh"

# --- stop-notify.sh — macOS notifications on idle ---
cat > "$HOME/.claude/hooks/stop-notify.sh" <<'STOPNOTIFY'
#!/usr/bin/env bash
# Classified stop notifications + Ghostty title refresh.
trap 'exit 0' ERR
INPUT=$(cat)
CONF="$HOME/.claude/cockpit.conf"
notifications="on"
if [[ -f "$CONF" ]]; then
  val=$(grep "^notifications=" "$CONF" 2>/dev/null | head -1 | cut -d= -f2-)
  [[ -n "$val" ]] && notifications="$val"
fi
CLASSIFIED=$(echo "$INPUT" | python3 -c '
import json, os, sys
def first_line(msg):
    for line in msg.splitlines():
        line = line.strip()
        if line and not line.startswith("#"): return line[:120]
    return ""
try: data = json.load(sys.stdin)
except: sys.exit(0)
if data.get("stop_hook_active", False): sys.exit(0)
ppid = os.getppid()
cwd = data.get("cwd") or os.getcwd()
sid_path = os.path.join(cwd, ".claude", "current-session-id")
session_id = ""
if os.path.isfile(sid_path):
    try:
        with open(sid_path) as f: session_id = f.read().strip()
    except: pass
cockpit = {}
if session_id:
    cp = f"/tmp/claude-cockpit-{session_id}"
    if os.path.isfile(cp):
        try:
            with open(cp) as f: cockpit = json.load(f)
        except: pass
project = cockpit.get("project") or os.path.basename(cwd) or "?"
cost = float(cockpit.get("cost", 0) or 0)
context_pct = int(cockpit.get("context_pct", 0) or 0)
error_flag = "0"
ep = f"/tmp/claude-tab-error-{ppid}"
if os.path.isfile(ep):
    try:
        with open(ep) as f: error_flag = f.read().strip()
    except: pass
last_notify_path = f"/tmp/claude-last-notify-{ppid}"
last_event = ""
if os.path.isfile(last_notify_path):
    try:
        with open(last_notify_path) as f: last_event = f.read().strip()
    except: pass
msg = data.get("last_assistant_message", "")
summary = first_line(msg) or "Waiting for input"
event, state, title = "needs_input", "attention", "Needs Input"
body = summary
if error_flag == "1": event, state, title = "tests_failed", "error", "Tests Failed"
notify = event != last_event
try:
    with open(last_notify_path, "w") as f: f.write(event)
except: pass
print(json.dumps({"event":event,"state":state,"notify":notify,"title":title,"body":body,"project":project,"cost_fmt":f"${cost:.2f}","context_pct":context_pct}))
' 2>/dev/null)
[[ -z "$CLASSIFIED" ]] && exit 0
STATE=$(echo "$CLASSIFIED" | jq -r '.state // "attention"')
TITLE=$(echo "$CLASSIFIED" | jq -r '.title // "Needs Input"')
BODY=$(echo "$CLASSIFIED" | jq -r '.body // "Waiting for input"')
PROJECT=$(echo "$CLASSIFIED" | jq -r '.project // "?"')
COST_FMT=$(echo "$CLASSIFIED" | jq -r '.cost_fmt // "$0.00"')
CONTEXT_PCT=$(echo "$CLASSIFIED" | jq -r '.context_pct // 0')
NOTIFY=$(echo "$CLASSIFIED" | jq -r '.notify // false')
CLAUDE_PID=$PPID "$HOME/.claude/hooks/tab-color.sh" "$STATE" 2>/dev/null || true
case "$STATE" in working) glyph="◐";; attention) glyph="◆";; error) glyph="▲";; done) glyph="●";; *) glyph="·";; esac
printf '\033]2;%s %s · %s · %s %s%%\007' "$glyph" "$PROJECT" "$TITLE" "$COST_FMT" "$CONTEXT_PCT" > /dev/tty 2>/dev/null || true
[[ "$notifications" != "on" ]] && exit 0
[[ "$NOTIFY" != "true" ]] && exit 0
python3 - "$TITLE" "$BODY" <<'PY' 2>/dev/null
import subprocess, sys
title, body = sys.argv[1], sys.argv[2]
subprocess.run(["osascript","-e",f"display notification \"{body}\" with title \"{title}\""],capture_output=True,timeout=5)
PY
exit 0
STOPNOTIFY
chmod +x "$HOME/.claude/hooks/stop-notify.sh"
ok "stop-notify.sh"

# --- session-init.sh — Session startup ---
cat > "$HOME/.claude/hooks/session-init.sh" <<'SESSIONINIT'
#!/usr/bin/env bash
# Session init — persist session ID, reset tab state, snapshot git baseline.
trap 'exit 0' ERR
INPUT=$(cat)
eval "$(echo "$INPUT" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    sid = data.get("session_id", "")
    cwd = data.get("cwd", "")
    if sid and cwd: print(f"SESSION={sid}"); print(f"CWD={cwd}")
except: pass
')"
[ -z "$SESSION" ] || [ -z "$CWD" ] && exit 0
mkdir -p "$CWD/.claude"
echo "$SESSION" > "$CWD/.claude/current-session-id"
if [ -d "$CWD/.git" ]; then
    git -C "$CWD" status --short > "/tmp/session-baseline-${SESSION}.txt" 2>/dev/null || true
fi
CLAUDE_PID=$PPID "$HOME/.claude/hooks/tab-color.sh" idle 2>/dev/null || true
if [ -n "$CLAUDE_ENV_FILE" ]; then
    echo "export CLAUDE_SESSION_ID=$SESSION" >> "$CLAUDE_ENV_FILE"
fi
exit 0
SESSIONINIT
chmod +x "$HOME/.claude/hooks/session-init.sh"
ok "session-init.sh"

# --- settings.json — Wire everything together ---
if [ ! -f "$HOME/.claude/settings.json" ]; then
    cat > "$HOME/.claude/settings.json" <<'SETTINGS'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "cmd=$(echo \"$CLAUDE_TOOL_INPUT\" | grep -oE '\"command\":\\s*\"[^\"]*\"' | head -1); if echo \"$cmd\" | grep -qE '\"(python |python3 )' && ! echo \"$cmd\" | grep -q 'uv run'; then echo 'BLOCK: use \"uv run python\" not bare python'; exit 2; fi"
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/tool-tracker.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/spinning-detector.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/stop-notify.sh"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/tab-color.sh working"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/session-init.sh"
          }
        ]
      }
    ]
  },
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  }
}
SETTINGS
    ok "settings.json (hooks wired)"
else
    skip "settings.json already exists"
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
echo -e "  ${BOLD}Cockpit (Claude Code UI):${RESET}"
echo "    Status line — 2-line display: project, cost, context bar, throughput"
echo "    Tab title   — live Ghostty tab with spinner, tool action, state glyphs"
echo "    Notifications — macOS alerts when Claude needs input"
echo "    Spinning detector — warns if stuck in tool-call loops"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo "    1. Open Ghostty, set font to 'JetBrainsMono Nerd Font'"
echo "    2. Open a new terminal (to load everything)"
echo "    3. Run: claude            — start Claude Code"
echo "    4. Run: llmx 'hello'      — test multi-model access"
echo "    5. Run: agent-sync        — pull latest from all repos"
echo ""
