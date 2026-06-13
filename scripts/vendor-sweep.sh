#!/usr/bin/env bash
# vendor-sweep.sh — the deterministic, zero-API half of surveillance.
# Fetches latest vendor docs/changelogs + extracts the Claude Code binary's
# embedded skill prompts (an unpublished vendor changelog), then commits any
# diffs. The semantic half (trending-scout, agent-infra-sweep) is surfaced as
# DUE by `just freshness` and run by /improve maintain — NOT here.
#
# Scheduled daily via com.agent-infra.vendor-sweep; also runnable as
# `just vendor-sweep`. Idempotent: unchanged sources produce no git churn.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "[vendor-sweep] $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 1. Vendor docs / changelogs (curl; self-stales at 24h)
./scripts/sync-vendor-docs.sh || echo "[vendor-sweep] sync-vendor-docs returned non-zero (advisory)"

# 2. Claude Code binary skill-prompt extraction (no-op if version unchanged)
uv run python3 scripts/binary_skills_extract.py || echo "[vendor-sweep] binary_skills_extract returned non-zero (advisory)"

# 3. Commit any diffs on the narrow surveillance paths only.
# docs/vendor/ is gitignored (local reference cache; freshness tracked by mtime).
# Only binary-extracts/ is committed — the inter-version prompt diff is the
# unpublished vendor changelog worth keeping in history.
git -C "$REPO" add research/binary-extracts/ 2>/dev/null
if git -C "$REPO" diff --cached --quiet; then
    echo "[vendor-sweep] no changes."
else
    changed=$(git -C "$REPO" diff --cached --name-only | sed 's#^#    #')
    git -C "$REPO" commit -q -m "[vendor-sync] Capture Claude Code binary skill diff — scheduled surveillance

Daily deterministic fetch (vendor-sweep.sh); vendor-docs refreshed to local
cache (gitignored). New binary extract = a Claude Code version bump. Changed:
$(git -C "$REPO" diff --cached --name-only)

Native-First: launchd + curl + existing extractor, no new fetch engine." \
        && echo "[vendor-sweep] committed:" && echo "$changed"
fi

echo "[vendor-sweep] done."
