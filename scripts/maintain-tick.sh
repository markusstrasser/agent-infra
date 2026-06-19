#!/usr/bin/env bash
# maintain-tick.sh — the MOTOR half of the RSI loop (SAFE/dry-run).
# Picks ONE tier-0 (agent-infra-local + reversible + evidence>=2) candidate and
# writes a DRAFT proposal to artifacts/maintain/. Never edits code, commits, or
# deploys. Rate-gates on a live-`claude` cap inside the Python.
# Scheduled (when wired): com.agent-infra.maintain-tick (45m). Manual: just maintain-tick.
# NOTE: --apply is intentionally NOT passed here; the apply lane is double-gated off.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
exec uv run python3 "$REPO/scripts/maintain_tick.py"
