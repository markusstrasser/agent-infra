#!/usr/bin/env bash
# act-drain.sh — daily zero-LLM ACT drain for the RSI learning loop.
# Classifies captured signals + ranks disposition queue → act-drain-digest.md.
# Scheduled: com.agent-infra.act-drain. Manual: just act-drain.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec uv run python3 "$REPO/scripts/act_drain.py"
