#!/usr/bin/env bash
# clash-detect.sh — daily SHADOW driver for governance clash-detection.
# Processes NEW captured directive-class messages (cursor-tracked, self-healing on
# rotation) against the governance index via gemini-3-flash; appends verdicts to
# ~/.claude/clash-shadow.jsonl. SURFACES NOTHING (shadow mode — precision is measured,
# not acted on). The driver that makes the 2-week precision window actually accumulate;
# without it captures rot unprocessed. Promote/cut: a human reviews `just clash-detect
# --summary` after ~2 weeks (ADR 2026-06-16-governance-clash-detection).
# Scheduled: com.agent-infra.clash-detect (daily 07:00). Manual: just clash-detect.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
# clash_detect.py is fail-safe: on dispatch error the cursor is NOT advanced (retried
# next day), and no-new-captures is a clean no-op. Tiny cost (one batched flash call).
exec uv run python3 "$REPO/scripts/clash_detect.py" --repo "$REPO"
