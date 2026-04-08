#!/usr/bin/env bash
# sync-vendor-docs.sh — fetch latest vendor API/OpenAPI docs into docs/vendor/
# Run manually or from session-init. Skips if fetched within STALE_HOURS.
#
# Usage: ./scripts/sync-vendor-docs.sh [--force]

set -euo pipefail

DOCS_DIR="$(cd "$(dirname "$0")/.." && pwd)/docs/vendor"
STALE_HOURS="${STALE_HOURS:-24}"
FORCE="${1:-}"

mkdir -p "$DOCS_DIR"

fetch_if_stale() {
    local name="$1" url="$2" dest="$DOCS_DIR/$3"

    if [ "$FORCE" != "--force" ] && [ -f "$dest" ]; then
        age=$(( ($(date +%s) - $(stat -f %m "$dest")) / 3600 ))
        if [ "$age" -lt "$STALE_HOURS" ]; then
            return 0
        fi
    fi

    tmp=$(mktemp)
    if curl -sfL --max-time 15 -o "$tmp" "$url" 2>/dev/null; then
        # Only update if content changed (avoid noisy git diffs)
        if [ -f "$dest" ] && cmp -s "$tmp" "$dest"; then
            rm "$tmp"
        else
            mv "$tmp" "$dest"
            echo "  ✓ $name"
        fi
    else
        rm -f "$tmp"
        echo "  ✗ $name (fetch failed)"
    fi
}

echo "[vendor-docs] Syncing (stale=${STALE_HOURS}h)..."

# ── OpenAPI specs ──
fetch_if_stale "scite"    "https://api.scite.ai/openapi.json"           "scite-openapi.json"

# ── FastMCP (PyPI JSON) ──
fetch_if_stale "fastmcp"  "https://pypi.org/pypi/fastmcp/json"         "fastmcp-pypi.json"

# ── Claude Code changelog (latest GH release) ──
fetch_if_stale "claude-code" \
    "https://api.github.com/repos/anthropics/claude-code/releases/latest" \
    "claude-code-release.json"

# ── Anthropic SDK (Python) ──
fetch_if_stale "anthropic-sdk" \
    "https://pypi.org/pypi/anthropic/json"                              \
    "anthropic-sdk-pypi.json"

# ── Claude Agent SDK ──
fetch_if_stale "claude-agent-sdk" \
    "https://pypi.org/pypi/claude-code-sdk/json"                        \
    "claude-agent-sdk-pypi.json"

# Note: Exa OpenAPI not publicly fetchable. Exa MCP is configured directly.

echo "[vendor-docs] Done."
