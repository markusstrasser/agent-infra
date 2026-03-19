#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Claude Code + AI Tools Setup
# Run: curl -sL <gist-url>/setup-friend.sh | bash
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

uv tool install git+https://github.com/markusstrasser/llmx.git 2>/dev/null && ok "llmx" || ok "llmx (already installed)"
uv tool install git+https://github.com/markusstrasser/emb.git 2>/dev/null && ok "emb" || ok "emb (already installed)"

# ── API Keys ─────────────────────────────────────────────────

step "Setting up API keys (stored in macOS Keychain)"
echo -e "  ${DIM}Keys are encrypted at rest. You can manage them later with: llmx keys list${RESET}"

KEYCHAIN_SERVICE="llmx"

store_key() {
    local key_name="$1"
    local display_name="$2"
    local signup_url="$3"
    local required="${4:-optional}"

    # Check if already set in env or keychain
    if [ -n "${!key_name:-}" ]; then
        ok "$display_name — already in environment"
        # Also store in keychain for persistence
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

# Required for core functionality
store_key "ANTHROPIC_API_KEY" "Anthropic (Claude API)" \
    "https://console.anthropic.com/settings/keys" "required"

store_key "OPENAI_API_KEY" "OpenAI (GPT models + Codex CLI)" \
    "https://platform.openai.com/api-keys" "required"

store_key "GEMINI_API_KEY" "Google Gemini" \
    "https://aistudio.google.com/apikey" "required"

# Useful additions
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

# ── Shell Integration ────────────────────────────────────────

step "Setting up shell integration"

SHELL_RC="$HOME/.zshrc"
if [ -n "${BASH_VERSION:-}" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

# Add keychain loader to shell rc
KEYCHAIN_LOADER='
# Load API keys from macOS Keychain (set by llmx keys / setup script)
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
'

if ! grep -q '_load_keychain_key' "$SHELL_RC" 2>/dev/null; then
    echo "$KEYCHAIN_LOADER" >> "$SHELL_RC"
    ok "Added Keychain loader to $SHELL_RC"
else
    skip "Keychain loader already in $SHELL_RC"
fi

# ── Summary ──────────────────────────────────────────────────

step "Setup complete!"
echo ""
echo -e "  ${BOLD}Installed tools:${RESET}"
echo "    claude    — Claude Code (AI coding agent)"
echo "    gemini    — Gemini CLI (free tier, subscription)"
echo "    codex     — Codex CLI (OpenAI coding agent)"
echo "    llmx      — Unified LLM CLI (all providers)"
echo "    emb       — Embed, index, search text corpora"
echo ""
echo -e "  ${BOLD}API keys:${RESET}"
echo "    Manage:   llmx keys list / set / get / delete"
echo "    Loaded:   automatically from Keychain on shell start"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo "    1. Open a new terminal (to load Keychain keys)"
echo "    2. Run: claude            — start Claude Code"
echo "    3. Run: llmx 'hello'      — test LLM access"
echo "    4. Run: gemini            — start Gemini CLI"
echo ""
